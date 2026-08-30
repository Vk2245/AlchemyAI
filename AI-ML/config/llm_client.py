"""
Unified LLM client for the AI-ML pipeline.

Wraps litellm for multi-provider support and instructor for schema-validated
structured extraction. Every module calls these functions instead of
hitting provider APIs directly.

Default: qwen3.5:4b via Ollama (local, free, used for everything).
Fallback: Groq or Gemini (only when local quality is insufficient).
"""

from typing import Any, Optional, Type, TypeVar

import litellm
import instructor
from pydantic import BaseModel

from config.settings import (
    PROVIDER_MODELS,
    DEFAULT_PROVIDER,
    VLLM_BASE_URL,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    FALLBACK_GEMINI_API_KEY,
)

# Prevent crashes when falling back to providers that don't support certain kwargs
litellm.drop_params = True

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True

T = TypeVar("T", bound=BaseModel)


def _get_model_string(provider: str) -> str:
    """Map a provider key to the litellm model string."""
    if provider not in PROVIDER_MODELS:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Available: {list(PROVIDER_MODELS.keys())}"
        )
    return PROVIDER_MODELS[provider]


def _build_kwargs(provider: str) -> dict[str, Any]:
    """Build extra keyword arguments for litellm based on the provider."""
    kwargs: dict[str, Any] = {}

    if provider == "vllm":
        kwargs["api_base"] = VLLM_BASE_URL
        kwargs["api_key"] = "dummy-key"  # vLLM/OpenAI format requires a dummy key
    elif provider == "groq":
        kwargs["api_key"] = GROQ_API_KEY
    elif provider == "gemini":
        kwargs["api_key"] = GEMINI_API_KEY
        kwargs["safety_settings"] = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

    # Active Fallback Configuration (litellm will automatically try these if the primary fails)
    fallbacks = []
    
    # Do not use fallbacks for Gemini, because Gemini uses safety_settings which crash other providers
    # and local vLLM cannot handle the context length anyway.
    if provider == "gemini":
        if FALLBACK_GEMINI_API_KEY:
            # If the primary Gemini key hits a rate limit, fallback to the secondary Gemini key
            fallbacks.append({"model": PROVIDER_MODELS["gemini"], "api_key": FALLBACK_GEMINI_API_KEY})
    else:
        if provider != "groq" and GROQ_API_KEY:
            fallbacks.append({"model": PROVIDER_MODELS["groq"], "api_key": GROQ_API_KEY})
        # REMOVED GEMINI FALLBACK: We want instructor to natively retry 429 rate limits on Groq
        if provider != "vllm" and VLLM_BASE_URL:
            fallbacks.append({"model": PROVIDER_MODELS["vllm"], "api_base": VLLM_BASE_URL, "api_key": "dummy-key"})
        
    if fallbacks:
        kwargs["fallbacks"] = fallbacks

    return kwargs


def get_completion(
    prompt: str,
    system_prompt: str = "",
    provider: str = DEFAULT_PROVIDER,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """
    Send a plain text prompt to the LLM and return the response string.

    Use this for free-form generation (explanations, summaries, classifications)
    where you do not need a validated Pydantic object back.

    Defaults to vllm. Pass provider='groq' or 'gemini' only
    as a fallback when local quality is insufficient.
    """
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model = _get_model_string(provider)
    kwargs = _build_kwargs(provider)

    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )

    if not response or not hasattr(response, "choices") or len(response.choices) == 0:
        return ""
        
    content = response.choices[0].message.content
    return content if content else ""


async def get_completion_stream(
    prompt: str,
    system_prompt: str = "",
    provider: str = DEFAULT_PROVIDER,
    temperature: float = 0.1,
    max_tokens: int = 4096,
):
    """
    Asynchronously yields chunks of text from the LLM for streaming responses.
    """
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model = _get_model_string(provider)
    kwargs = _build_kwargs(provider)

    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        **kwargs,
    )

    async for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def get_structured_output(
    prompt: str,
    response_model: type[T],
    system_prompt: str = "",
    provider: str = DEFAULT_PROVIDER,
    temperature: float = 0.1,
    max_retries: int = 3,
    max_tokens: int = 8192,
) -> T:
    """
    Send a prompt to the LLM and return a validated Pydantic object.

    Uses instructor to auto-retry until the output matches the schema.
    This is the primary function for all structured extraction tasks.
    """
    if provider == "vllm":
        json_instruction = (
            "You MUST return your response as a valid JSON object. "
            "Do NOT wrap it in markdown blocks. Do NOT include any explanations before or after the JSON."
        )
        if system_prompt:
            system_prompt += f"\n\n{json_instruction}"
        else:
            system_prompt = json_instruction

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model = _get_model_string(provider)
    kwargs = _build_kwargs(provider)

    # Create an instructor-patched client via litellm
    if provider == "vllm":
        # Use Mode.JSON which handles markdown stripping natively, 
        # instead of JSON_SCHEMA which strictly expects raw valid JSON string.
        client = instructor.from_litellm(litellm.completion, mode=instructor.Mode.JSON)
    else:
        client = instructor.from_litellm(litellm.completion)

    # For vLLM, max_tokens + input_tokens cannot exceed max_model_len
    if provider == "vllm":
        total_prompt_chars = sum(len(m["content"]) for m in messages)
        estimated_input_tokens = total_prompt_chars // 3
        model_context_limit = 32768  # Assume vLLM is running with --max-model-len 32768
        safe_max_tokens = min(max_tokens, model_context_limit - estimated_input_tokens - 100)
        safe_max_tokens = max(safe_max_tokens, 256)
    else:
        safe_max_tokens = max_tokens

    result = client.chat.completions.create(
        model=model,
        messages=messages,
        response_model=response_model,
        temperature=temperature,
        max_retries=max_retries,
        max_tokens=safe_max_tokens,
        **kwargs,
    )

    return result


def get_embedding(
    text: str,
    model: Optional[str] = None,
) -> list[float]:
    """
    Generate a text embedding vector using sentence-transformers (fully local).
    """
    from sentence_transformers import SentenceTransformer

    embed_model = model or "nomic-ai/nomic-embed-text-v1.5"
    embedder = SentenceTransformer(embed_model, trust_remote_code=True)
    embedding = embedder.encode(text)
    return embedding.tolist()


def get_embeddings_batch(
    texts: list[str],
    model: Optional[str] = None,
) -> list[list[float]]:
    """
    Generate embedding vectors for a batch of texts using sentence-transformers.
    """
    from sentence_transformers import SentenceTransformer

    embed_model = model or "nomic-ai/nomic-embed-text-v1.5"
    embedder = SentenceTransformer(embed_model, trust_remote_code=True)
    embeddings = embedder.encode(texts)
    return embeddings.tolist()


def get_image_embedding(image_path: str) -> list[float]:
    """
    Generate an embedding vector for an image using nomic-embed-vision-v1.5.

    Runs fully locally via the transformers library (no API calls).
    Downloads the model on first use and caches it.
    """
    from transformers import AutoModel, AutoProcessor
    from PIL import Image
    import torch

    model_name = "nomic-ai/nomic-embed-vision-v1.5"

    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    model.eval()

    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)

    # Use the last hidden state's CLS token as the embedding
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().tolist()
    return embedding


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing LLM client...")
    print(f"Default provider: {DEFAULT_PROVIDER}")
    print(f"Model: {_get_model_string(DEFAULT_PROVIDER)}")
    print()

    # Test plain completion
    try:
        result = get_completion("Say 'hello' and nothing else.")
        print(f"Completion test: {result}")
    except Exception as e:
        print(f"Completion test failed (is Ollama running?): {e}")

    # Test embedding
    try:
        vec = get_embedding("test embedding")
        print(f"Embedding test: vector dim = {len(vec)}")
    except Exception as e:
        print(f"Embedding test failed: {e}")

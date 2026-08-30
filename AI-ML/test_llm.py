import sys
import logging
from config.llm_client import get_structured_output, _build_kwargs
from pydantic import BaseModel
from config.settings import DEFAULT_PROVIDER, PROVIDER_MODELS

class TestModel(BaseModel):
    test: str

print("DEFAULT_PROVIDER:", DEFAULT_PROVIDER)
print("PROVIDER_MODELS:", PROVIDER_MODELS)
print("vLLM kwargs:", _build_kwargs("vllm"))

import litellm
litellm.set_verbose = True

try:
    res = get_structured_output(
        prompt="Test",
        system_prompt="Test",
        response_model=TestModel,
        provider="vllm"
    )
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()

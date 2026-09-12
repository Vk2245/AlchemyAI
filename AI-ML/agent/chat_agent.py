"""
LangGraph-based RAG Chat Agent for Alchemy AI.

Provides a conversational interface over a user's product scan history.
Uses a simple StateGraph: retrieve → generate.

The agent is grounded ONLY in the user's own data — it will never
hallucinate or reveal another user's records.
"""

import re
from typing import Any, TypedDict, AsyncGenerator

from langgraph.graph import StateGraph, END

from config.llm_client import get_completion, get_completion_stream
from config.settings import DEFAULT_PROVIDER


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class ChatState(TypedDict):
    user_question: str
    user_records: list[dict]       # All product records belonging to the user
    chat_history: list[dict]       # Previous messages [{"role": ..., "content": ...}]
    retrieved_context: str         # Relevant records serialized as text
    response: str                  # Final LLM answer
    provider: str                  # LLM provider to use


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_record(rec: dict) -> str:
    """Convert a product record dict into a readable text block."""
    lines = []
    lines.append(f"Document Title: {rec.get('document_title', 'Unknown')}")
    if rec.get("primary_party"):
        lines.append(f"  Primary Party: {rec['primary_party']}")
    if rec.get("document_type"):
        lines.append(f"  Document Type: {rec['document_type']}")
    if rec.get("category"):
        lines.append(f"  Category: {rec['category']}")
    if rec.get("part_number"):
        lines.append(f"  Part Number: {rec['part_number']}")
    if rec.get("record_confidence") is not None:
        lines.append(f"  Confidence Score: {rec['record_confidence']:.0%}")
    if rec.get("risk_level"):
        lines.append(f"  Risk Level: {rec['risk_level']}")
    if rec.get("validation_passed") is not None:
        lines.append(f"  Validation Passed: {'Yes' if rec['validation_passed'] else 'No'}")
    if rec.get("uploaded_at"):
        lines.append(f"  Uploaded: {rec['uploaded_at']}")
    if rec.get("original_filename"):
        lines.append(f"  Source File: {rec['original_filename']}")

    # Include key attributes from record_data if available
    record_data = rec.get("record_data", {})
    if isinstance(record_data, dict):
        if record_data.get("summary"):
            lines.append(f"  Summary: {record_data['summary']}")
            
        if record_data.get("financial_summary"):
            fs = record_data["financial_summary"]
            lines.append(f"  Financials: Revenue {fs.get('total_revenue', 'N/A')}, Net Income {fs.get('net_income', 'N/A')}, Total Assets {fs.get('total_assets', 'N/A')}, Total Liabilities {fs.get('total_liabilities', 'N/A')}")
            
        if record_data.get("key_dates"):
            lines.append("  Key Dates:")
            for kd in record_data["key_dates"]:
                lines.append(f"    - {kd.get('date', 'Unknown')}: {kd.get('event', 'Unknown')} ({kd.get('importance', 'N/A')})")
                
        if record_data.get("entities"):
            lines.append("  Key Entities:")
            for ent in record_data["entities"]:
                lines.append(f"    - {ent.get('name', 'Unknown')} ({ent.get('type', 'Unknown')})")

        # Handle Standard PDF Records legacy attributes
        attrs = record_data.get("attributes", record_data.get("extracted_attributes", []))
        if isinstance(attrs, list) and attrs:
            lines.append("  Key Attributes:")
            for attr in attrs[:15]:  # Cap at 15 to avoid context overflow
                if isinstance(attr, dict):
                    name = attr.get("name", attr.get("attribute", ""))
                    value = attr.get("value", "")
                    if name and value:
                        lines.append(f"    - {name}: {value}")

    return "\n".join(lines)


def _keyword_score(question: str, record: dict) -> int:
    """Simple keyword relevance scoring between question and record."""
    question_lower = question.lower()
    score = 0

    searchable_fields = [
        record.get("product_name", ""),
        record.get("manufacturer", ""),
        record.get("industry", ""),
        record.get("category", ""),
        record.get("part_number", ""),
        record.get("risk_level", ""),
        record.get("original_filename", ""),
    ]

    for field in searchable_fields:
        if field and isinstance(field, str):
            for word in re.split(r'\W+', field.lower()):
                if word and len(word) > 2 and word in question_lower:
                    score += 3

    # Check for risk/confidence keywords
    if any(w in question_lower for w in ["risk", "risky", "danger", "warning"]):
        if record.get("risk_level", "").lower() in ["high", "medium"]:
            score += 5
    if any(w in question_lower for w in ["confidence", "accurate", "quality", "score"]):
        score += 2
    if any(w in question_lower for w in ["all", "every", "list", "show", "scans", "products"]):
        score += 1  # Boost all records slightly for listing queries

    return score


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def retrieve(state: ChatState) -> dict:
    """
    Retrieve relevant product records based on the user's question.

    For broad queries ("what have I scanned?"), returns all records.
    For specific queries, ranks by keyword relevance and returns top matches.
    """
    question = state["user_question"]
    records = state["user_records"]

    if not records:
        return {"retrieved_context": "No product records found for this account. The user has not scanned any documents yet."}

    question_lower = question.lower().strip('?!., ')

    # Check for simple greetings
    greetings = ["hi", "hello", "hey", "how are you", "who are you", "what are you", "greetings", "good morning", "good evening"]
    if question_lower in greetings:
        return {"retrieved_context": ""}

    # Check if it's a broad/listing query
    broad_keywords = ["all", "every", "list", "show me", "what have", "how many", "summary", "overview"]
    is_broad = any(kw in question_lower for kw in broad_keywords)

    if is_broad or len(records) <= 5:
        # Return all records for broad queries or small datasets
        context_parts = [f"=== Product {i+1} of {len(records)} ===\n{_serialize_record(r)}"
                        for i, r in enumerate(records)]
    else:
        # Rank by keyword relevance
        scored = [(r, _keyword_score(question, r)) for r in records]
        scored.sort(key=lambda x: x[1], reverse=True)
        # Take top 5 or all with score > 0
        top = [r for r, s in scored if s > 0][:5]
        if not top:
            top = records[:5]  # Fallback to first 5
        context_parts = [f"=== Product {i+1} of {len(top)} (relevant) ===\n{_serialize_record(r)}"
                        for i, r in enumerate(top)]

    return {"retrieved_context": "\n\n".join(context_parts)}


def _build_chat_prompts(state: ChatState) -> tuple[str, str]:
    """Helper to build system and user prompts from state."""
    system_prompt = """You are Alchemy AI Assistant, a smart, conversational AI for a Product Intelligence Platform.
You help users understand their product scan history and analysis results.

ABOUT THE PLATFORM:
Alchemy AI is an Open-Source Product Intelligence platform. It allows users to upload PDF product catalogs, datasheets, and specs. The AI pipeline extracts attributes, detects industries, scores confidence, researches missing data using web agents, and generates tamper-proof PDF reports.
It also supports Bulk Excel processing, where messy strings are cleaned and categorized using LLMs.

PLATFORM FEATURES & STEPS:
1. Upload & Analyze: Users upload a PDF or an Excel file. The system parses it, extracts data, and automatically categorizes the industry (e.g. Electrical, Pharma).
2. Autonomous Web Research: If data is missing (e.g. no IP rating found), our 3-tier LangGraph agent searches the web (DuckDuckGo, Jina, Gemini) to fill gaps.
3. Risk Radar: The system dynamically generates and checks safety/compliance risks based on the specific industry detected.
4. Export & Report: A comprehensive markdown/PDF report and executive one-pager are generated. For Excel, we group by Category/Tag to generate one report per category.
5. Tamper-Proofing: All records are secured with an HMAC-SHA256 hash.

CHATTING ABOUT EXCEL DATA:
- When a user asks about items uploaded via Excel, the system groups them by "Category" (or Tag).
- For each Category, a dedicated PDF Intelligence Report is generated.
- If the user asks about a specific messy item (e.g., "3/8 CPLG BRS"), look at its Category in the context provided below. Explain what the item is, and then naturally tell the user that they can find its detailed PDF intelligence report in the dashboard under that specific Category name.

CHATBOT CAPABILITIES & LIMITATIONS:
- I CAN answer questions about products the user has already scanned and analyzed (provided in the context below).
- I CAN compare products, summarize risk levels, and list extracted attributes from the user's history.
- I CAN explain how the platform works and guide them on usage.
- I DO NOT have access to the live internet. I can ONLY discuss products that the user has ALREADY scanned and exist in the provided context.
- I DO NOT have the ability to modify, delete, or create new records.

RULES:
1. Be friendly, conversational, and helpful. If the user greets you, greet them back naturally.
2. ONLY answer data-specific questions using the product data provided in the context below. Never invent data.
3. If the context says the user hasn't scanned any documents, politely inform them that their scan history is empty and they need to upload a file in the dashboard.
4. IMPORTANT: If there is data in the BACKGROUND KNOWLEDGE section, DO NOT ask the user to provide data. Treat the BACKGROUND KNOWLEDGE as the user's data.
5. If the user asks about product details not in the context, say "I don't have that information in your scan history."
6. When comparing products, use clear formatting.
7. Refer to scans naturally (e.g., "Your motor analysis shows..." or "The items in your bulk upload...").
8. If asked "who are you?", say "I am Alchemy AI Assistant, an AI chatbot for a Product Intelligence Platform." Do not mention the underlying LLM model name.
9. VERY IMPORTANT: The chat interface DOES NOT support Markdown. DO NOT use asterisks (** or *) for bolding/italics, and DO NOT use markdown lists or headers. Output plain text ONLY with normal spaces and newlines.
"""

    context = state["retrieved_context"]
    history = state.get("chat_history", [])
    question = state["user_question"]

    # Format chat history (last 10 turns max)
    history_text = ""
    if history:
        recent = history[-10:]
        history_parts = [f"{m['role'].title()}: {m['content']}" for m in recent]
        history_text = "\n".join(history_parts) + "\n\n"

    # Only inject the massive product data block if there is actually data retrieved
    background = f"BACKGROUND KNOWLEDGE (USER'S PRODUCT DATA):\n{context}\n\n" if context else ""

    prompt = f"""{background}{f"CONVERSATION HISTORY:{chr(10)}{history_text}" if history_text else ""}
USER'S MESSAGE: {question}

INSTRUCTIONS FOR ASSISTANT:
1. If the user asks about their products, scans, or data, answer using ONLY the BACKGROUND KNOWLEDGE.
2. If the user asks a general question like "what can you do?" or "how does this work?", explain your capabilities based on the 'CHATBOT CAPABILITIES' and 'ABOUT THE PLATFORM' sections above. Do NOT just list their files unless they specifically ask for them.
3. If there is data in the BACKGROUND KNOWLEDGE, DO NOT ask the user to upload data.
4. Respond to the user naturally.
"""
    return system_prompt, prompt


def generate(state: ChatState) -> dict:
    """
    Generate a conversational response grounded in the retrieved context.
    """
    system_prompt, prompt = _build_chat_prompts(state)
    provider = state.get("provider", DEFAULT_PROVIDER)

    response = get_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        provider=provider,
        temperature=0.4,
        max_tokens=1024,
    )

    return {"response": response}



# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_chat_graph() -> StateGraph:
    """Construct the LangGraph StateGraph for the chat agent."""
    graph = StateGraph(ChatState)

    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Compile once at module level
_chat_graph = build_chat_graph()


def chat_with_records(
    question: str,
    user_records: list[dict],
    chat_history: list[dict] | None = None,
    provider: str = DEFAULT_PROVIDER,
) -> str:
    """
    Run the RAG chat agent on the user's question.

    Args:
        question: The user's natural language question.
        user_records: List of product record dicts belonging to this user.
        chat_history: Previous conversation messages.
        provider: LLM provider to use.

    Returns:
        The assistant's text response.
    """
    question_lower = question.strip().lower()
    greetings = ["hi", "hello", "hey", "how are you", "who are you", "what are you", "greetings", "good morning", "good evening"]
    if question_lower in greetings:
        return "Hello there! I am Alchemy AI Assistant. How can I help you with your product scans today?"

    state: ChatState = {
        "user_question": question,
        "user_records": user_records,
        "chat_history": chat_history or [],
        "retrieved_context": "",
        "response": "",
        "provider": provider,
    }

    result = _chat_graph.invoke(state)
    return result["response"]


async def chat_with_records_stream(
    question: str,
    user_records: list[dict],
    chat_history: list[dict] | None = None,
    provider: str = DEFAULT_PROVIDER,
) -> AsyncGenerator[str, None]:
    """
    Asynchronous version of chat_with_records that yields text chunks.
    """
    question_lower = question.strip().lower()
    greetings = ["hi", "hello", "hey", "how are you", "who are you", "what are you", "greetings", "good morning", "good evening"]
    if question_lower in greetings:
        yield "Hello there! I am Alchemy AI Assistant. How can I help you with your product scans today?"
        return

    state: ChatState = {
        "user_question": question,
        "user_records": user_records,
        "chat_history": chat_history or [],
        "retrieved_context": "",
        "response": "",
        "provider": provider,
    }

    # Run the retrieval manually (since it's a simple sync function)
    retrieved = retrieve(state)
    state["retrieved_context"] = retrieved["retrieved_context"]

    # Build prompts
    system_prompt, prompt = _build_chat_prompts(state)

    # Stream chunks
    stream = get_completion_stream(
        prompt=prompt,
        system_prompt=system_prompt,
        provider=provider,
        temperature=0.4,
        max_tokens=1024,
    )
    
    is_thinking = False
    buffer = ""

    async for chunk in stream:
        buffer += chunk

        if not is_thinking:
            if "<think>" in buffer:
                parts = buffer.split("<think>", 1)
                if parts[0]:
                    yield parts[0]
                is_thinking = True
                buffer = parts[1]
            else:
                # To prevent yielding half of a forming '<think>' tag, 
                # we hold back if a '<' is near the end.
                last_lt = buffer.rfind("<")
                if last_lt != -1 and last_lt >= len(buffer) - 8:
                    yield buffer[:last_lt]
                    buffer = buffer[last_lt:]
                else:
                    yield buffer
                    buffer = ""

        if is_thinking:
            if "</think>" in buffer:
                parts = buffer.split("</think>", 1)
                is_thinking = False
                # Trim leading newlines from the part right after </think>
                buffer = parts[1].lstrip("\n\r")
            else:
                # We are inside <think>, so we drop everything.
                # Just keep the last 9 chars in case </think> is cut in half.
                if len(buffer) > 9:
                    buffer = buffer[-9:]

    if not is_thinking and buffer:
        if "<think" not in buffer:
            yield buffer


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample_records = [
        {
            "product_name": "Pro-Series Industrial Motor 400V",
            "manufacturer": "IndustrialCorp",
            "industry": "Electrical",
            "record_confidence": 0.94,
            "risk_level": "low",
            "validation_passed": True,
            "uploaded_at": "2026-08-16",
        },
        {
            "product_name": "Paracetamol 500mg Tablet",
            "manufacturer": "PharmaGen",
            "industry": "Pharmaceutical",
            "record_confidence": 0.89,
            "risk_level": "medium",
            "validation_passed": True,
            "uploaded_at": "2026-08-15",
        },
    ]

    response = chat_with_records(
        question="What products have I scanned?",
        user_records=sample_records,
    )
    print(f"Assistant: {response}")

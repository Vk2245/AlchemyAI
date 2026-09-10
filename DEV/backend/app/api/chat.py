"""
Chat API: LangGraph RAG chatbot for account-specific product intelligence.

Users can ask natural language questions about their own scans, product records,
confidence scores, risk levels, and extracted attributes. All answers are
grounded in the authenticated user's data — no cross-account leakage.
"""

import sys
import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Document, DocumentRecord, ChatMessage, get_db, async_session_factory,
)
from app.api.auth import get_current_user, User
from app.core.config import AI_ML_DIR, DEFAULT_PROVIDER


router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = Field(None, max_length=50)


class ChatResponse(BaseModel):
    conversation_id: str
    response: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_user_records(user_id: int, db: AsyncSession) -> list[dict]:
    """Load all product records belonging to the user, joined with document info."""
    result = await db.execute(
        select(Document, DocumentRecord)
        .outerjoin(DocumentRecord, DocumentRecord.document_id == Document.id)
        .where(Document.owner_id == user_id)
        .order_by(Document.uploaded_at.desc())
    )
    rows = result.all()

    records = []
    for doc, pr in rows:
        rec = {
            "document_id": doc.id,
            "original_filename": doc.original_filename,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        }
        if pr:
            rec.update({
                "document_title": pr.document_title,
                "primary_party": pr.primary_party,
                "part_number": pr.part_number,
                "document_type": pr.document_type,
                "category": pr.category,
                "record_confidence": pr.record_confidence,
                "validation_passed": pr.validation_passed,
                "risk_level": pr.risk_level,
                "record_data": pr.record_data, # MINI COPY FOR CHATBOT!
            })
        records.append(rec)

    return records


async def _load_chat_history(
    user_id: int, conversation_id: str, db: AsyncSession
) -> list[dict]:
    """Load previous messages in this conversation."""
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.conversation_id == conversation_id,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]


# ---------------------------------------------------------------------------
# POST /api/chat — Send a message, get AI response
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
@router.post("/", summary="Chat with your product records")
async def chat_endpoint(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if str(AI_ML_DIR) not in sys.path:
        sys.path.insert(0, str(AI_ML_DIR))

    conversation_id = body.conversation_id or str(uuid.uuid4())[:8]

    # Load user's product records
    user_records = await _load_user_records(user.id, db)

    # Load chat history for this conversation
    chat_history = await _load_chat_history(user.id, conversation_id, db)

    # Save user message
    user_msg = ChatMessage(
        user_id=user.id,
        conversation_id=conversation_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    from agent.chat_agent import chat_with_records_stream

    async def stream_generator():
        accumulated_response = ""
        try:
            stream = chat_with_records_stream(
                question=body.message,
                user_records=user_records,
                chat_history=chat_history,
                provider="groq",
            )
            async for chunk in stream:
                accumulated_response += chunk
                yield chunk
        except Exception as e:
            err = f"\n\n[Error: {str(e)[:100]}]"
            accumulated_response += err
            yield err

        # After streaming is complete, save the assistant's message to the DB
        # We need a new session since the request's dependency session might close 
        # unexpectedly if the client disconnects, but doing it directly usually works.
        try:
            assistant_msg = ChatMessage(
                user_id=user.id,
                conversation_id=conversation_id,
                role="assistant",
                content=accumulated_response.strip(),
            )
            db.add(assistant_msg)
            await db.commit()
        except Exception:
            pass

    return StreamingResponse(
        stream_generator(), 
        media_type="text/event-stream",
        headers={"X-Conversation-ID": conversation_id}
    )



# ---------------------------------------------------------------------------
# GET /api/chat/history — Get chat history
# ---------------------------------------------------------------------------

@router.get("/history")
async def get_chat_history(
    conversation_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get chat history for the current user.

    If conversation_id is provided, returns messages for that conversation.
    Otherwise, returns a list of all conversation IDs with their last message.
    """
    if conversation_id:
        # Return full conversation
        messages = await _load_chat_history(user.id, conversation_id, db)
        return {"conversation_id": conversation_id, "messages": messages}

    # Return list of conversations
    result = await db.execute(
        select(ChatMessage.conversation_id)
        .where(ChatMessage.user_id == user.id)
        .group_by(ChatMessage.conversation_id)
        .order_by(ChatMessage.created_at.desc())
    )
    conv_ids = result.scalars().all()

    conversations = []
    for cid in conv_ids:
        # Get the last message for preview
        last_msg_result = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user.id,
                ChatMessage.conversation_id == cid,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none()
        conversations.append({
            "conversation_id": cid,
            "last_message": last_msg.content[:100] if last_msg else "",
            "last_role": last_msg.role if last_msg else "",
            "last_at": last_msg.created_at.isoformat() if last_msg else None,
        })

    return {"conversations": conversations}

# ---------------------------------------------------------------------------
# DELETE /api/chat/history - Clear chat history
# ---------------------------------------------------------------------------

from sqlalchemy import delete

@router.delete("/history")
async def clear_chat_history(
    conversation_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Clear chat history for the current user.
    If conversation_id is provided, deletes only that conversation.
    Otherwise, deletes ALL conversations for the user.
    """
    stmt = delete(ChatMessage).where(ChatMessage.user_id == user.id)
    if conversation_id:
        stmt = stmt.where(ChatMessage.conversation_id == conversation_id)
    
    await db.execute(stmt)
    await db.commit()
    
    return {"message": "Chat history cleared successfully"}

"""
SQLAlchemy database models and async engine setup.

Tables:
  - users: JWT auth accounts
  - documents: uploaded PDFs
  - product_records: extracted intelligence + tamper-proof hash
  - reports: generated PDF reports
  - audit_log: security audit trail
"""

import json
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, Session,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)

from app.core.config import DATABASE_URL


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)  # UUID-based
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of file
    status: Mapped[str] = mapped_column(
        String(50), default="uploaded"
    )  # uploaded, processing, completed, failed
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="documents")
    product_record: Mapped[Optional["ProductRecord"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )
    report: Mapped[Optional["Report"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Document {self.original_filename} ({self.status})>"


class ProductRecord(Base):
    __tablename__ = "product_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), unique=True, nullable=False)

    # Core product info
    product_name: Mapped[str] = mapped_column(String(500), nullable=True, index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    part_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Full extracted data (JSON blob)
    record_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Quality metrics
    record_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Tamper-proof: HMAC-SHA256 of record_data
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="product_record")

    def __repr__(self) -> str:
        return f"<ProductRecord {self.product_name} (conf={self.record_confidence:.0%})>"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), unique=True, nullable=False)

    # Report files
    report_html_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    report_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    report_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="report")

    def __repr__(self) -> str:
        return f"<Report for doc={self.document_id}>"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class ChatMessage(Base):
    """Persists chat messages between users and the RAG assistant."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<ChatMessage {self.role} conv={self.conversation_id}>"

# ---------------------------------------------------------------------------
# Engine & Session
# ---------------------------------------------------------------------------

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Called at application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# CLI: create tables
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def main():
        print("Creating database tables...")
        await init_db()
        print("Done. Tables created.")

        # Show table names
        async with engine.begin() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: list(Base.metadata.tables.keys())
            )
        print(f"Tables: {tables}")

    asyncio.run(main())

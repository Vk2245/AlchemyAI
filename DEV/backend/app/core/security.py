"""
Security utilities: JWT, password hashing, HMAC tamper-proof records.

All open-source:
  - python-jose[cryptography] for JWT
  - passlib[bcrypt] for password hashing
  - hmac + hashlib (stdlib) for tamper-proof content hashes
"""

import hmac
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, HMAC_KEY


# ---------------------------------------------------------------------------
# Password Hashing (bcrypt)
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# HMAC Tamper-Proof Content Hash
# ---------------------------------------------------------------------------

def compute_content_hash(data: dict[str, Any]) -> str:
    """
    Compute an HMAC-SHA256 hash of a product record.

    This creates a cryptographic signature that proves the record
    hasn't been tampered with. If anyone modifies the data, the
    hash won't match.
    """
    # Canonical JSON: sorted keys, no whitespace, ensure deterministic
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    signature = hmac.new(
        HMAC_KEY.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def verify_content_hash(data: dict[str, Any], expected_hash: str) -> bool:
    """
    Verify that a record's content hash matches.

    Returns True if the record is intact, False if tampered.
    """
    computed = compute_content_hash(data)
    return hmac.compare_digest(computed, expected_hash)


# ---------------------------------------------------------------------------
# CAPTCHA: Altcha (open-source, proof-of-work, self-hosted)
# ---------------------------------------------------------------------------

def generate_altcha_challenge() -> dict[str, Any]:
    """
    Generate an Altcha proof-of-work challenge.

    The client must find a number that, when appended to the salt,
    produces a SHA-256 hash starting with the required number of
    zero bits. This is computationally expensive for bots but
    trivial for humans (the JS widget solves it in <1 second).
    """
    from app.core.config import ALTCHA_HMAC_KEY

    salt = secrets.token_hex(16)
    secret_number = secrets.randbelow(100000)
    difficulty = 10000  # ~0.5s to solve

    # The challenge string the client must hash
    challenge = hashlib.sha256(f"{salt}{secret_number}".encode()).hexdigest()

    # HMAC signature so we can verify without storing state
    signature = hmac.new(
        ALTCHA_HMAC_KEY.encode(),
        challenge.encode(),
        hashlib.sha256,
    ).hexdigest()

    return {
        "algorithm": "SHA-256",
        "challenge": challenge,
        "salt": salt,
        "maxnumber": difficulty,
        "signature": signature,
    }


def verify_altcha_solution(
    payload: dict[str, Any],
) -> bool:
    """
    Verify an Altcha proof-of-work solution from the client.
    """
    from app.core.config import ALTCHA_HMAC_KEY

    algorithm = payload.get("algorithm", "")
    challenge = payload.get("challenge", "")
    number = payload.get("number", 0)
    salt = payload.get("salt", "")
    signature = payload.get("signature", "")

    if algorithm != "SHA-256":
        return False

    # Verify the HMAC signature (proves challenge came from us)
    expected_sig = hmac.new(
        ALTCHA_HMAC_KEY.encode(),
        challenge.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        return False

    # Verify the solution
    computed = hashlib.sha256(f"{salt}{number}".encode()).hexdigest()
    return hmac.compare_digest(computed, challenge)


# ---------------------------------------------------------------------------
# Secure Headers Middleware
# ---------------------------------------------------------------------------

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
}


# ---------------------------------------------------------------------------
# File Upload Safety
# ---------------------------------------------------------------------------

def generate_safe_filename(original_filename: str) -> str:
    """Generate a UUID-based filename to prevent path traversal."""
    import uuid
    from pathlib import Path
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def validate_file_upload(
    filename: str,
    file_size: int,
    allowed_extensions: set[str],
    max_size_mb: int,
) -> tuple[bool, str]:
    """Validate an uploaded file. Returns (is_valid, error_message)."""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        return False, f"File type '{ext}' not allowed. Allowed: {allowed_extensions}"

    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File too large ({file_size / 1024 / 1024:.1f}MB). Max: {max_size_mb}MB"

    return True, ""


# ---------------------------------------------------------------------------
# CLI: test security functions
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test password hashing
    password = "test_password_123"
    hashed = hash_password(password)
    print(f"Password hash: {hashed}")
    print(f"Verify correct: {verify_password(password, hashed)}")
    print(f"Verify wrong:   {verify_password('wrong', hashed)}")
    print()

    # Test JWT
    token = create_access_token({"sub": "user@example.com", "user_id": 1})
    print(f"JWT: {token[:50]}...")
    payload = verify_token(token)
    print(f"Verified payload: {payload}")
    print()

    # Test tamper-proof hash
    record = {"product_name": "ABB SACE Tmax", "voltage": "690V"}
    content_hash = compute_content_hash(record)
    print(f"Content hash: {content_hash}")
    print(f"Verify intact: {verify_content_hash(record, content_hash)}")

    tampered = record.copy()
    tampered["voltage"] = "999V"
    print(f"Verify tampered: {verify_content_hash(tampered, content_hash)}")
    print()

    # Test CAPTCHA
    challenge = generate_altcha_challenge()
    print(f"Altcha challenge: {json.dumps(challenge, indent=2)}")
    print()

    # Test file validation
    valid, err = validate_file_upload("catalog.pdf", 5_000_000, {".pdf"}, 50)
    print(f"Valid PDF: {valid} ({err})")
    valid, err = validate_file_upload("hack.exe", 5_000_000, {".pdf"}, 50)
    print(f"Valid EXE: {valid} ({err})")

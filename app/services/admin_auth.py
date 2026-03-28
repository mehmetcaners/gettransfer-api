from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import anyio
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.admin_user import AdminRole, AdminUser

PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000


def _admin_auth_error(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("utf-8"))


def _get_admin_token_secret(settings: Settings) -> str:
    return settings.admin_token_secret or settings.token_salt_secret


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")

    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}"
        f"${_b64url_encode(salt)}${_b64url_encode(derived)}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = stored_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_PREFIX:
            return False
        iterations = int(iterations_raw)
        salt = _b64url_decode(salt_raw)
        expected = _b64url_decode(digest_raw)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)


async def _scalar_one_or_none(session: AsyncSession | Session, stmt):
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return result.scalars().first()

    def _run():
        result = session.execute(stmt)
        return result.scalars().first()

    return await anyio.to_thread.run_sync(_run)


async def _commit(session: AsyncSession | Session, refresh: AdminUser | None = None) -> None:
    if isinstance(session, AsyncSession):
        await session.commit()
        if refresh is not None:
            await session.refresh(refresh)
        return

    def _run() -> None:
        session.commit()
        if refresh is not None:
            session.refresh(refresh)

    await anyio.to_thread.run_sync(_run)


async def get_admin_by_email(session: AsyncSession | Session, email: str) -> AdminUser | None:
    normalised = email.strip().lower()
    stmt = select(AdminUser).where(AdminUser.email == normalised)
    return await _scalar_one_or_none(session, stmt)


async def get_admin_by_username(session: AsyncSession | Session, username: str) -> AdminUser | None:
    normalised = username.strip().lower()
    stmt = select(AdminUser).where(AdminUser.username == normalised)
    return await _scalar_one_or_none(session, stmt)


async def get_admin_by_id(session: AsyncSession | Session, admin_id: uuid.UUID) -> AdminUser | None:
    stmt = select(AdminUser).where(AdminUser.id == admin_id)
    return await _scalar_one_or_none(session, stmt)


async def ensure_bootstrap_admin(session: AsyncSession | Session) -> AdminUser | None:
    settings = get_settings()
    bootstrap_username = (settings.admin_bootstrap_username or "").strip().lower()
    bootstrap_password = settings.admin_bootstrap_password or ""
    if not bootstrap_username or not bootstrap_password:
        return None

    existing = await get_admin_by_username(session, bootstrap_username)
    if existing:
        return existing

    bootstrap_email = (settings.admin_bootstrap_email or f"{bootstrap_username}@gettransfer.local").strip().lower()
    admin = AdminUser(
        username=bootstrap_username,
        email=bootstrap_email,
        password_hash=hash_password(bootstrap_password),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
    )
    session.add(admin)
    await _commit(session, refresh=admin)
    return admin


async def authenticate_admin(
    session: AsyncSession | Session, *, username: str, password: str
) -> AdminUser | None:
    admin = await get_admin_by_username(session, username)
    if not admin or not admin.is_active:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


async def mark_admin_logged_in(session: AsyncSession | Session, admin: AdminUser) -> AdminUser:
    admin.last_login_at = datetime.now(timezone.utc)
    session.add(admin)
    await _commit(session, refresh=admin)
    return admin


def create_admin_access_token(admin: AdminUser, settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=active_settings.admin_token_ttl_minutes)
    payload = {
        "sub": str(admin.id),
        "username": admin.username,
        "email": admin.email,
        "role": admin.role.value,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    payload_segment = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        _get_admin_token_secret(active_settings).encode("utf-8"),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_segment}.{_b64url_encode(signature)}"


def decode_admin_access_token(token: str, settings: Settings | None = None) -> dict[str, str | int]:
    active_settings = settings or get_settings()
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError as exc:
        raise _admin_auth_error("Invalid token") from exc

    expected_signature = hmac.new(
        _get_admin_token_secret(active_settings).encode("utf-8"),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    provided_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise _admin_auth_error("Invalid token")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise _admin_auth_error("Invalid token") from exc

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(datetime.now(timezone.utc).timestamp()):
        raise _admin_auth_error("Token expired")

    return payload


def parse_admin_token_subject(token: str) -> uuid.UUID:
    payload = decode_admin_access_token(token)
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _admin_auth_error("Invalid token subject")
    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        raise _admin_auth_error("Invalid token subject") from exc

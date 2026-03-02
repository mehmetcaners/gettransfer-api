import hashlib
import hmac
import secrets

from app.core.config import get_settings


def hash_token(token: str, salt: str) -> str:
    data = (token + salt).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def generate_token() -> tuple[str, str]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token, settings.token_salt_secret)
    return token, token_hash


def verify_token(token: str, expected_hash: str) -> bool:
    settings = get_settings()
    computed = hash_token(token, settings.token_salt_secret)
    return hmac.compare_digest(computed, expected_hash)

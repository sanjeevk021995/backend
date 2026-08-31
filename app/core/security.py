from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import settings

ALGORITHM = "HS256"
ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False

def create_token(subject: str, token_type: str, expires: timedelta):
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

def create_access_token(user_id: str):
    return create_token(user_id, "access", timedelta(minutes=settings.jwt_access_minutes))

def create_refresh_token(user_id: str):
    return create_token(user_id, "refresh", timedelta(days=settings.jwt_refresh_days))

# --- FORGOT / RESET PASSWORD TOKENS ---

def create_password_reset_token(user_id: str) -> str:
    """Generates a short-lived token (15 mins) specifically for resetting a password."""
    return create_token(user_id, "password_reset", timedelta(minutes=15))

def decode_token(token: str):
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
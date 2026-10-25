from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import JWT_SECRET

ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=12)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET está vazio. Preencha backend/.env e tente de novo.")
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Retorna o id do usuário, ou None se o token for inválido ou expirado."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None

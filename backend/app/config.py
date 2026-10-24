import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


DATABASE_URL = _env("DATABASE_URL")
JWT_SECRET = _env("JWT_SECRET")
CORS_ORIGINS = _env("CORS_ORIGINS")

# TODO(confirmar) pesos e limiares com o pesquisador antes do teste
WEIGHTS = {"auto": 0.3, "gestor": 0.5, "rh": 0.2}
HAS_THRESHOLD = 6
REQUIRED_THRESHOLD = 6
MIN_GAP = 1.0
MAX_ITEMS = 5

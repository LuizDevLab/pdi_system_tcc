from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registra as tabelas em Base.metadata)
from app.config import CORS_ORIGINS, JWT_SECRET
from app.db import Base, get_engine
from app.routers import auth, dev_tests, evaluations, pdi

MIN_JWT_SECRET_LEN = 32


def check_jwt_secret(secret: str) -> None:
    if len(secret) < MIN_JWT_SECRET_LEN:
        raise RuntimeError(
            f"JWT_SECRET tem {len(secret)} caracteres; o mínimo é {MIN_JWT_SECRET_LEN}. "
            "Defina um segredo longo e aleatório em backend/.env e inicie de novo."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_jwt_secret(JWT_SECRET)
    Base.metadata.create_all(get_engine())
    yield


app = FastAPI(title="Sistema de PDI", lifespan=lifespan)

origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(evaluations.router)
app.include_router(pdi.router)
app.include_router(dev_tests.router)  # TODO(remover)

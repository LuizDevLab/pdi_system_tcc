import os

os.environ["JWT_SECRET"] = "test-secret"  # antes de importar app.config

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import EvaluationLink, User
from app.security import hash_password

PASSWORD = "senha-teste"


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)  # sem "with": não dispara o lifespan (create_all no Neon)
    app.dependency_overrides.clear()


def _user(db, name, role, consented=True):
    u = User(
        name=name,
        email=f"{name}@exemplo.com",
        password_hash=hash_password(PASSWORD),
        role=role,
        is_participant=role == "colaborador",
        consented_at=datetime(2026, 1, 1) if consented else None,
    )
    db.add(u)
    db.commit()
    return u


@pytest.fixture()
def users(db):
    u = {
        "admin": _user(db, "admin", "admin"),
        "gestor": _user(db, "gestor", "gestor"),
        "colab": _user(db, "colab", "colaborador"),
        "fora": _user(db, "fora", "colaborador"),
        "novo": _user(db, "novo", "colaborador", consented=False),
    }
    db.add(EvaluationLink(evaluator_id=u["gestor"].id, evaluated_id=u["colab"].id, type="gestor"))
    db.commit()
    return u


@pytest.fixture()
def auth(client, users):
    def headers(key):
        r = client.post("/auth/login", json={"email": users[key].email, "password": PASSWORD})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return headers

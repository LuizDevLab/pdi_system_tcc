import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import MIN_JWT_SECRET_LEN, check_jwt_secret


def test_segredo_curto_rejeitado():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_jwt_secret("x" * (MIN_JWT_SECRET_LEN - 1))
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_jwt_secret("")


def test_segredo_longo_aceito():
    check_jwt_secret("x" * MIN_JWT_SECRET_LEN)


def test_lifespan_aborta_com_segredo_curto(monkeypatch):
    monkeypatch.setattr(main, "JWT_SECRET", "curto")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(main.app):
            pass

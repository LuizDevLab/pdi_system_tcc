from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EvaluationLink, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_user_no_consent(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Usuário autenticado, SEM exigir consentimento.

    ATENÇÃO: só para /me e /me/consent. Rotas novas devem usar get_consented_user,
    senão o bloqueio de consentimento é burlado.
    """
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado.")
    if creds is None:
        raise unauthorized
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise unauthorized
    return user


def get_consented_user(user: User = Depends(get_user_no_consent)) -> User:
    """Usuário autenticado que já aceitou o termo. Base de todas as demais rotas."""
    if user.consented_at is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "É preciso aceitar o termo de consentimento.")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_consented_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para este recurso.")
        return user

    return checker


def can_access_evaluated(db: Session, user: User, evaluated_id: int) -> bool:
    """admin: todos; qualquer papel: a si mesmo; gestor: avaliados vinculados a ele."""
    if user.role == "admin" or user.id == evaluated_id:
        return True
    if user.role != "gestor":
        return False
    link_id = db.scalar(
        select(EvaluationLink.id).where(
            EvaluationLink.evaluator_id == user.id,
            EvaluationLink.evaluated_id == evaluated_id,
        )
    )
    return link_id is not None


def require_evaluated_scope(
    user_id: int,
    user: User = Depends(get_consented_user),
    db: Session = Depends(get_db),
) -> User:
    """Dependência de rota com parâmetro de caminho `user_id` (o avaliado)."""
    if not can_access_evaluated(db, user, user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para este avaliado.")
    return user

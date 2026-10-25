from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_user_no_consent
from app.models import User
from app.schemas import LoginIn, TokenOut, UserOut
from app.security import create_access_token, verify_password

router = APIRouter()


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos.")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_user_no_consent)):
    return user


@router.post("/me/consent", response_model=UserOut)
def consent(user: User = Depends(get_user_no_consent),db: Session = Depends(get_db)):
    if user.consented_at is None:
        user.consented_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(user)
    return user

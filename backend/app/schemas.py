from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    cargo_id: int | None
    department: str | None
    is_participant: bool
    consented_at: datetime | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

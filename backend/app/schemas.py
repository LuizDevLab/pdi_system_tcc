from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


DEV_TYPES = (
    "curso",
    "treinamento_interno",
    "mentoria",
    "acompanhamento",
    "atividades_praticas",
    "projeto_desafio",
    "certificacao",
    "outro",
)
STAY_IN_ROLE = ("sim", "nao", "nao_sei")
TIMEFRAMES = ("ate_3m", "3_6m", "6_12m", "mais_12m")


class EvaluationMineOut(BaseModel):
    id: int
    evaluated_id: int
    evaluated_name: str
    type: str
    status: str


class CompetencyScoreOut(BaseModel):
    code: str
    name: str
    description: str
    score: int | None


class EvaluationDetailOut(BaseModel):
    id: int
    evaluated_id: int
    evaluated_name: str
    type: str
    status: str
    submitted_at: datetime | None
    competencies: list[CompetencyScoreOut]
    development_input: dict | None


class ScoreItem(BaseModel):
    competency_code: str
    score: int = Field(ge=0, le=10)


class EvaluationWriteIn(BaseModel):
    scores: list[ScoreItem] = Field(default_factory=list)
    development_input: dict | None = None


class EvaluationSubmitIn(BaseModel):
    scores: list[ScoreItem]
    development_input: dict

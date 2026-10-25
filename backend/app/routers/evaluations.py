from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_consented_user
from app.models import Competency, DevelopmentInput, EvaluationLink, Score, User
from app.schemas import (
    DEV_TYPES,
    STAY_IN_ROLE,
    TIMEFRAMES,
    CompetencyScoreOut,
    EvaluationDetailOut,
    EvaluationMineOut,
    EvaluationSubmitIn,
    EvaluationWriteIn,
    ScoreItem,
)

router = APIRouter()

GESTOR_KEYS = ("needs", "priority_competency", "priority_reason")
AUTO_KEYS = GESTOR_KEYS + (
    "main_goal",
    "stay_in_role",
    "future_role",
    "dev_types",
    "timeframe",
)


def _link_or_404(db: Session, link_id: int) -> EvaluationLink:
    link = db.get(EvaluationLink, link_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vínculo não encontrado.")
    return link


def _require_evaluator(link: EvaluationLink, user: User) -> None:
    if link.evaluator_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o avaliador deste vínculo pode acessá-lo.")


def _reject_if_submitted(link: EvaluationLink) -> None:
    if link.status == "completo":
        raise HTTPException(status.HTTP_409_CONFLICT, "Avaliação já enviada; não pode ser editada.")


def _competencies(db: Session) -> list[Competency]:
    return list(db.scalars(select(Competency).order_by(Competency.id)).all())


def _known_codes(competencies: list[Competency]) -> set[str]:
    return {c.code for c in competencies}


def _evaluated_name(db: Session, evaluated_id: int) -> str:
    name = db.scalar(select(User.name).where(User.id == evaluated_id))
    return name or ""


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


def _validate_needs_and_priority(data: dict, known: set[str], required: bool) -> None:
    if "needs" not in data:
        if required:
            raise _bad_request("needs é obrigatório.")
        if "priority_competency" in data:
            raise _bad_request("priority_competency deve ser uma das needs.")
        return
    needs = data["needs"]
    if not isinstance(needs, list):
        raise _bad_request("needs deve ser uma lista de códigos.")
    if len(needs) > 5:
        raise _bad_request("needs admite no máximo 5 códigos.")
    if required and len(needs) < 1:
        raise _bad_request("needs deve ter ao menos um código.")
    seen: set[str] = set()
    for code in needs:
        if not isinstance(code, str) or code not in known:
            raise _bad_request(f"Código inválido em needs: {code!r}.")
        if code in seen:
            raise _bad_request("needs não pode repetir códigos.")
        seen.add(code)
    if "priority_competency" not in data:
        if required:
            raise _bad_request("priority_competency é obrigatório.")
        return
    priority = data["priority_competency"]
    if priority not in seen:
        raise _bad_request("priority_competency deve ser uma das needs.")


def _require_str(data: dict, key: str, allow_empty: bool = False) -> str:
    if key not in data or not isinstance(data[key], str):
        raise _bad_request(f"Campo obrigatório: {key}.")
    value = data[key].strip() if key != "priority_reason" else data[key]
    if not allow_empty and not value.strip():
        raise _bad_request(f"Campo obrigatório: {key}.")
    return data[key]


def _validate_development_input(
    data: dict | None,
    link_type: str,
    known: set[str],
    required: bool,
) -> dict | None:
    if data is None:
        if required:
            raise _bad_request("development_input é obrigatório.")
        return None
    if not isinstance(data, dict):
        raise _bad_request("development_input inválido.")
    _validate_needs_and_priority(data, known, required)
    if not required:
        return data

    _require_str(data, "priority_reason")
    if link_type in ("gestor", "rh"):
        return {k: data[k] for k in GESTOR_KEYS}

    if link_type != "auto":
        raise _bad_request(f"Tipo de vínculo inválido: {link_type}.")

    _require_str(data, "main_goal")
    stay = _require_str(data, "stay_in_role")
    if stay not in STAY_IN_ROLE:
        raise _bad_request("stay_in_role inválido.")
    if "future_role" in data and data["future_role"] is not None and not isinstance(data["future_role"], str):
        raise _bad_request("future_role inválido.")
    dev_types = data.get("dev_types")
    if not isinstance(dev_types, list) or not dev_types:
        raise _bad_request("dev_types é obrigatório.")
    for item in dev_types:
        if item not in DEV_TYPES:
            raise _bad_request(f"dev_types inválido: {item!r}.")
    timeframe = _require_str(data, "timeframe")
    if timeframe not in TIMEFRAMES:
        raise _bad_request("timeframe inválido.")
    out = {k: data[k] for k in AUTO_KEYS if k in data}
    if "future_role" not in out:
        out["future_role"] = None
    return out


def _upsert_scores(db: Session, link: EvaluationLink, scores: list[ScoreItem], known: dict[str, Competency]) -> None:
    seen: set[str] = set()
    for item in scores:
        if item.competency_code in seen:
            raise _bad_request(f"Nota duplicada para {item.competency_code}.")
        seen.add(item.competency_code)
        competency = known.get(item.competency_code)
        if competency is None:
            raise _bad_request(f"Código inválido: {item.competency_code}.")
        existing = db.get(Score, (link.id, competency.id))
        if existing is None:
            db.add(Score(link_id=link.id, competency_id=competency.id, score=item.score))
        else:
            existing.score = item.score


def _upsert_development_input(db: Session, link: EvaluationLink, data: dict) -> None:
    existing = db.get(DevelopmentInput, link.id)
    if existing is None:
        db.add(DevelopmentInput(link_id=link.id, data=data))
    else:
        existing.data = data


def _detail(db: Session, link: EvaluationLink, competencies: list[Competency]) -> EvaluationDetailOut:
    scores = {
        s.competency_id: s.score
        for s in db.scalars(select(Score).where(Score.link_id == link.id)).all()
    }
    dev = db.get(DevelopmentInput, link.id)
    return EvaluationDetailOut(
        id=link.id,
        evaluated_id=link.evaluated_id,
        evaluated_name=_evaluated_name(db, link.evaluated_id),
        type=link.type,
        status=link.status,
        submitted_at=link.submitted_at,
        competencies=[
            CompetencyScoreOut(
                code=c.code,
                name=c.name,
                description=c.description,
                score=scores.get(c.id),
            )
            for c in competencies
        ],
        development_input=dev.data if dev else None,
    )


@router.get("/evaluations/mine", response_model=list[EvaluationMineOut])
def list_mine(
    user: User = Depends(get_consented_user),
    db: Session = Depends(get_db),
):
    links = list(
        db.scalars(
            select(EvaluationLink).where(EvaluationLink.evaluator_id == user.id).order_by(EvaluationLink.id)
        ).all()
    )
    if not links:
        return []
    names = {
        u.id: u.name
        for u in db.scalars(select(User).where(User.id.in_({lk.evaluated_id for lk in links}))).all()
    }
    return [
        EvaluationMineOut(
            id=lk.id,
            evaluated_id=lk.evaluated_id,
            evaluated_name=names.get(lk.evaluated_id, ""),
            type=lk.type,
            status=lk.status,
        )
        for lk in links
    ]


@router.get("/evaluations/{link_id}", response_model=EvaluationDetailOut)
def get_evaluation(
    link_id: int,
    user: User = Depends(get_consented_user),
    db: Session = Depends(get_db),
):
    link = _link_or_404(db, link_id)
    _require_evaluator(link, user)
    return _detail(db, link, _competencies(db))


@router.put("/evaluations/{link_id}", response_model=EvaluationDetailOut)
def save_draft(
    link_id: int,
    body: EvaluationWriteIn,
    user: User = Depends(get_consented_user),
    db: Session = Depends(get_db),
):
    link = _link_or_404(db, link_id)
    _require_evaluator(link, user)
    _reject_if_submitted(link)
    competencies = _competencies(db)
    known = {c.code: c for c in competencies}
    _upsert_scores(db, link, body.scores, known)
    if body.development_input is not None:
        data = _validate_development_input(body.development_input, link.type, set(known), required=False)
        _upsert_development_input(db, link, data or body.development_input)
    if link.status == "pendente":
        link.status = "rascunho"
    db.commit()
    db.refresh(link)
    return _detail(db, link, competencies)


@router.post("/evaluations/{link_id}/submit", response_model=EvaluationDetailOut)
def submit_evaluation(
    link_id: int,
    body: EvaluationSubmitIn,
    user: User = Depends(get_consented_user),
    db: Session = Depends(get_db),
):
    link = _link_or_404(db, link_id)
    _require_evaluator(link, user)
    _reject_if_submitted(link)
    competencies = _competencies(db)
    known = {c.code: c for c in competencies}
    if len(body.scores) != len(competencies):
        raise _bad_request("É preciso informar as 20 notas.")
    submitted_codes = {item.competency_code for item in body.scores}
    if submitted_codes != set(known):
        raise _bad_request("É preciso informar as 20 notas, uma por competência.")
    data = _validate_development_input(body.development_input, link.type, set(known), required=True)
    _upsert_scores(db, link, body.scores, known)
    _upsert_development_input(db, link, data or body.development_input)
    link.status = "completo"
    link.submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(link)
    return _detail(db, link, competencies)

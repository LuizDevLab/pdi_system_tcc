from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import engine
from app.db import get_db
from app.deps import require_evaluated_scope, require_roles
from app.models import (
    ActionCatalog,
    CargoReference,
    Competency,
    DevelopmentInput,
    EvaluationLink,
    Pdi,
    PdiItem,
    Score,
    User,
)

router = APIRouter()


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


def _completed_links(db: Session, user: User) -> list[EvaluationLink]:
    return list(
        db.scalars(
            select(EvaluationLink).where(
                EvaluationLink.evaluated_id == user.id,
                EvaluationLink.status == "completo",
            )
        ).all()
    )


def _build_result(db: Session, user: User) -> dict:
    """Carrega os dados do banco e delega todo o cálculo ao engine."""
    if user.cargo_id is None:
        raise _bad_request("O usuário não tem cargo definido.")
    links = _completed_links(db, user)
    kinds = {lk.type for lk in links}
    if "auto" not in kinds:
        raise _bad_request("Não é possível gerar o PDI: falta a autoavaliação completa.")
    if "gestor" not in kinds:
        raise _bad_request("Não é possível gerar o PDI: falta ao menos uma avaliação de gestor completa.")

    competencies = {c.id: c for c in db.scalars(select(Competency)).all()}
    refs = db.scalars(select(CargoReference).where(CargoReference.cargo_id == user.cargo_id)).all()
    if {r.competency_id for r in refs} != set(competencies):
        raise _bad_request("O perfil de referência do cargo não cobre as 20 competências.")
    reference = {competencies[r.competency_id].code: r.expected_level for r in refs}

    evaluations: dict[str, list[dict[str, float]]] = {"auto": [], "gestor": [], "rh": []}
    self_inputs: dict | None = None
    manager_inputs: list[dict] = []
    for lk in links:
        scores = {
            competencies[s.competency_id].code: s.score
            for s in db.scalars(select(Score).where(Score.link_id == lk.id)).all()
        }
        if len(scores) != len(competencies):
            raise _bad_request("Há avaliação marcada como completa com notas faltando.")
        evaluations[lk.type].append(scores)
        dev = db.get(DevelopmentInput, lk.id)
        if dev is not None:
            if lk.type == "auto":
                self_inputs = dev.data
            else:
                manager_inputs.append(dev.data)

    actions: dict[str, list[dict]] = {}
    for a in db.scalars(select(ActionCatalog).order_by(ActionCatalog.id)).all():
        actions.setdefault(competencies[a.competency_id].code, []).append({"id": a.id, "type": a.type})

    try:
        result = engine.build_pdi(
            evaluations,
            reference,
            actions,
            self_inputs=self_inputs,
            manager_inputs=manager_inputs,
            reference_provisional=any(r.provisional for r in refs),
        )
    except engine.NotEligibleError as e:
        raise _bad_request(str(e))
    result["reference"] = reference
    return result


def _save(db: Session, user: User, result: dict) -> Pdi:
    codes = {c.code: c.id for c in db.scalars(select(Competency)).all()}
    old = db.scalar(select(Pdi).where(Pdi.user_id == user.id))
    if old is not None:
        db.execute(delete(PdiItem).where(PdiItem.pdi_id == old.id))
        db.delete(old)
        db.flush()
    pdi = Pdi(
        user_id=user.id,
        generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        consolidated={
            "scores": result["consolidated"],
            "reference": result["reference"],
            "by_type": result["by_type"],
            "divergence": result["divergence"],
        },
        cosine=result["cosine"],
        jaccard=result["jaccard"],
        config_snapshot=result["config_snapshot"],
        reference_provisional=result["reference_provisional"],
    )
    db.add(pdi)
    db.flush()
    for item in result["items"]:
        db.add(
            PdiItem(
                pdi_id=pdi.id,
                competency_id=codes[item["competency"]],
                gap=item["gap"],
                rank=item["rank"],
                action_id=item["action_id"],
                timeframe=item["timeframe"],
                divergence=item["divergence"],
            )
        )
    db.commit()
    return pdi


@router.post("/admin/pdi/{user_id}/generate")
def generate_pdi(
    user_id: int,
    _admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None or not user.is_participant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avaliado não encontrado.")
    pdi = _save(db, user, _build_result(db, user))
    return {"id": pdi.id, "user_id": user.id, "generated_at": pdi.generated_at}


def _pdi_payload(db: Session, pdi: Pdi, owner: User, full: bool) -> dict:
    """`full=False` (o próprio avaliado): nunca inclui notas por avaliador nem divergência."""
    data = pdi.consolidated
    competencies = list(db.scalars(select(Competency).order_by(Competency.id)).all())
    rows = []
    for c in competencies:
        row = {
            "code": c.code,
            "name": c.name,
            "consolidated": data["scores"][c.code],
            "expected": data["reference"][c.code],
            "gap": data["reference"][c.code] - data["scores"][c.code],
        }
        if full:
            row["by_type"] = {k: v[c.code] for k, v in data["by_type"].items()}
            row["divergence"] = data["divergence"].get(c.code)
        rows.append(row)

    items = []
    for it in sorted(pdi.items, key=lambda i: i.rank):
        item = {
            "rank": it.rank,
            "code": it.competency.code,
            "name": it.competency.name,
            "gap": it.gap,
            "timeframe": it.timeframe,
            "action": (
                {"title": it.action.title, "type": it.action.type, "description": it.action.description}
                if it.action
                else None
            ),
        }
        if full:
            item["divergence"] = it.divergence
        items.append(item)

    return {
        "user_id": owner.id,
        "user_name": owner.name,
        "cargo": owner.cargo.name if owner.cargo else None,
        "generated_at": pdi.generated_at,
        "cosine": pdi.cosine,
        "jaccard": pdi.jaccard,
        "reference_provisional": pdi.reference_provisional,
        "competencies": rows,
        "items": items,
    }


@router.get("/pdi/{user_id}")
def get_pdi(
    user_id: int,
    viewer: User = Depends(require_evaluated_scope),
    db: Session = Depends(get_db),
):
    pdi = db.scalar(select(Pdi).where(Pdi.user_id == user_id))
    if pdi is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "O PDI ainda não foi gerado.")
    owner = db.get(User, user_id)
    # Quem vê o próprio PDI (inclusive gestor avaliado) recebe a versão restrita.
    return _pdi_payload(db, pdi, owner, full=viewer.id != user_id)

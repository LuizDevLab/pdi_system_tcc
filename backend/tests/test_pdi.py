import pytest
from sqlalchemy import func, select

from app.models import (
    ActionCatalog,
    Cargo,
    CargoReference,
    Competency,
    DevelopmentInput,
    EvaluationLink,
    Pdi,
    PdiItem,
    Score,
)
from seed import COMPETENCIES

AUTO_SCORE, GESTOR_SCORE = 8, 2
SELF_DATA = {
    "needs": ["communication"],
    "priority_competency": "communication",
    "priority_reason": "x",
    "dev_types": ["mentoria"],
    "timeframe": "3_6m",
}


@pytest.fixture()
def setup(db, users):
    comps = []
    for code, name, description in COMPETENCIES:
        c = Competency(code=code, name=name, description=description)
        db.add(c)
        comps.append(c)
    cargo = Cargo(name="Cargo teste", department="Fiscal")
    db.add(cargo)
    db.flush()
    for c in comps:
        db.add(CargoReference(cargo_id=cargo.id, competency_id=c.id, expected_level=7, provisional=True))
        db.add(ActionCatalog(competency_id=c.id, title=f"Curso {c.code}", type="curso", description="d"))
        db.add(ActionCatalog(competency_id=c.id, title=f"Mentoria {c.code}", type="mentoria", description="d"))
    users["colab"].cargo_id = cargo.id
    db.commit()
    return comps


def _complete(db, comps, link, value, data):
    for c in comps:
        db.add(Score(link_id=link.id, competency_id=c.id, score=value))
    db.add(DevelopmentInput(link_id=link.id, data=data))
    link.status = "completo"
    db.commit()


@pytest.fixture()
def ready(db, users, setup):
    """colab com autoavaliação (nota 8) e gestor (nota 2) completos."""
    auto = EvaluationLink(evaluator_id=users["colab"].id, evaluated_id=users["colab"].id, type="auto")
    db.add(auto)
    db.commit()
    _complete(db, setup, auto, AUTO_SCORE, SELF_DATA)
    gestor = db.scalar(select(EvaluationLink).where(EvaluationLink.type == "gestor"))
    _complete(db, setup, gestor, GESTOR_SCORE, {"needs": ["teamwork"], "priority_competency": "teamwork", "priority_reason": "y"})
    return users


def _generate(client, auth, users):
    return client.post(f"/admin/pdi/{users['colab'].id}/generate", headers=auth("admin"))


def _all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_keys(v)


def test_generate_requires_admin(client, auth, ready):
    assert client.post(f"/admin/pdi/{ready['colab'].id}/generate", headers=auth("gestor")).status_code == 403
    assert client.post(f"/admin/pdi/{ready['colab'].id}/generate", headers=auth("colab")).status_code == 403


def test_generate_fails_without_self_evaluation(client, auth, users, setup):
    r = _generate(client, auth, users)
    assert r.status_code == 400
    assert "autoavaliação" in r.json()["detail"]


def test_generate_fails_without_manager(client, auth, db, users, setup):
    auto = EvaluationLink(evaluator_id=users["colab"].id, evaluated_id=users["colab"].id, type="auto")
    db.add(auto)
    db.commit()
    _complete(db, setup, auto, 5, SELF_DATA)
    r = _generate(client, auth, users)
    assert r.status_code == 400
    assert "gestor" in r.json()["detail"]


def test_generate_and_replace(client, auth, db, ready):
    assert _generate(client, auth, ready).status_code == 200
    assert _generate(client, auth, ready).status_code == 200
    assert db.scalar(select(func.count()).select_from(Pdi)) == 1
    assert db.scalar(select(func.count()).select_from(PdiItem)) == 5
    pdi = db.scalar(select(Pdi))
    assert pdi.reference_provisional is True
    # (0.3*8 + 0.5*2) / 0.8, RH ausente
    assert pdi.consolidated["scores"]["communication"] == pytest.approx(4.25)


def test_colaborador_never_gets_manager_scores_or_divergence(client, auth, ready):
    _generate(client, auth, ready)
    r = client.get(f"/pdi/{ready['colab'].id}", headers=auth("colab"))
    assert r.status_code == 200
    body = r.json()
    keys = set(_all_keys(body))
    assert not keys & {"by_type", "divergence", "gestor", "auto", "rh"}
    assert body["reference_provisional"] is True
    assert body["items"][0]["code"] == "communication"  # prioritária vence o desempate
    assert body["items"][0]["action"]["type"] == "mentoria"
    assert body["competencies"][0]["consolidated"] == pytest.approx(4.25)
    assert body["competencies"][0]["expected"] == 7


def test_gestor_and_admin_get_everything(client, auth, ready):
    _generate(client, auth, ready)
    for who in ("gestor", "admin"):
        body = client.get(f"/pdi/{ready['colab'].id}", headers=auth(who)).json()
        row = body["competencies"][0]
        assert row["by_type"]["gestor"] == GESTOR_SCORE
        assert row["divergence"] == AUTO_SCORE - GESTOR_SCORE
        assert body["items"][0]["divergence"] == AUTO_SCORE - GESTOR_SCORE


def test_pdi_scope(client, auth, ready):
    _generate(client, auth, ready)
    assert client.get(f"/pdi/{ready['colab'].id}", headers=auth("fora")).status_code == 403


def test_pdi_not_generated_is_404(client, auth, ready):
    assert client.get(f"/pdi/{ready['colab'].id}", headers=auth("colab")).status_code == 404

import pytest
from sqlalchemy import select

from app.models import Competency, EvaluationLink
from seed import COMPETENCIES


def _codes():
    return [c[0] for c in COMPETENCIES]


@pytest.fixture()
def competencies(db):
    for code, name, description in COMPETENCIES:
        db.add(Competency(code=code, name=name, description=description))
    db.commit()


@pytest.fixture()
def links(db, users, competencies):
    db.add(EvaluationLink(evaluator_id=users["colab"].id, evaluated_id=users["colab"].id, type="auto"))
    db.commit()
    gestor_link = db.scalar(
        select(EvaluationLink).where(
            EvaluationLink.evaluator_id == users["gestor"].id,
            EvaluationLink.evaluated_id == users["colab"].id,
        )
    )
    auto = db.scalar(
        select(EvaluationLink).where(
            EvaluationLink.evaluator_id == users["colab"].id,
            EvaluationLink.type == "auto",
        )
    )
    return {"gestor": gestor_link, "auto": auto}


def _scores(n=20, value=5, override=None):
    items = [{"competency_code": code, "score": value} for code in _codes()[:n]]
    if override:
        for code, score in override.items():
            for item in items:
                if item["competency_code"] == code:
                    item["score"] = score
    return items


def _auto_input(**extra):
    data = {
        "main_goal": "crescer no cargo",
        "needs": ["communication", "teamwork"],
        "priority_competency": "communication",
        "priority_reason": "preciso me comunicar melhor",
        "stay_in_role": "sim",
        "future_role": "",
        "dev_types": ["curso", "mentoria"],
        "timeframe": "3_6m",
    }
    data.update(extra)
    return data


def _gestor_input(**extra):
    data = {
        "needs": ["organization", "time_management"],
        "priority_competency": "organization",
        "priority_reason": "organizar a rotina",
    }
    data.update(extra)
    return data


def test_mine_so_vinculos_em_que_sou_avaliador(client, auth, users, links):
    mine = client.get("/evaluations/mine", headers=auth("gestor")).json()
    assert len(mine) == 1
    assert mine[0]["evaluated_name"] == users["colab"].name
    assert mine[0]["type"] == "gestor"
    assert mine[0]["status"] == "pendente"

    colab_mine = client.get("/evaluations/mine", headers=auth("colab")).json()
    assert len(colab_mine) == 1
    assert colab_mine[0]["type"] == "auto"
    assert colab_mine[0]["id"] == links["auto"].id

    assert client.get("/evaluations/mine", headers=auth("fora")).json() == []


def test_so_avaliador_acessa_detalhe(client, auth, links):
    link_id = links["gestor"].id
    ok = client.get(f"/evaluations/{link_id}", headers=auth("gestor"))
    assert ok.status_code == 200
    body = ok.json()
    assert len(body["competencies"]) == 20
    assert {c["code"] for c in body["competencies"]} == set(_codes())
    assert all(c["score"] is None for c in body["competencies"])
    assert body["competencies"][0]["name"]
    assert body["competencies"][0]["description"]

    assert client.get(f"/evaluations/{link_id}", headers=auth("colab")).status_code in (403, 404)
    assert client.get(f"/evaluations/{link_id}", headers=auth("fora")).status_code in (403, 404)
    assert client.get(f"/evaluations/{link_id}", headers=auth("admin")).status_code in (403, 404)


def test_sem_consentimento_bloqueado(client, auth, users, db, competencies):
    novo = users["novo"]
    db.add(EvaluationLink(evaluator_id=novo.id, evaluated_id=novo.id, type="auto"))
    db.commit()
    link_id = db.scalar(select(EvaluationLink.id).where(EvaluationLink.evaluator_id == novo.id))
    h = auth("novo")
    assert client.get("/evaluations/mine", headers=h).status_code == 403
    assert client.get(f"/evaluations/{link_id}", headers=h).status_code == 403
    assert client.put(f"/evaluations/{link_id}", headers=h, json={"scores": []}).status_code == 403
    assert client.post(
        f"/evaluations/{link_id}/submit",
        headers=h,
        json={"scores": _scores(), "development_input": _auto_input()},
    ).status_code == 403


def test_rascunho_parcial_e_nota_zero(client, auth, links):
    h = auth("gestor")
    link_id = links["gestor"].id
    r = client.put(
        f"/evaluations/{link_id}",
        headers=h,
        json={
            "scores": [
                {"competency_code": "communication", "score": 0},
                {"competency_code": "teamwork", "score": 7},
            ],
            "development_input": {"needs": ["communication"], "priority_competency": "communication"},
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rascunho"
    by_code = {c["code"]: c["score"] for c in r.json()["competencies"]}
    assert by_code["communication"] == 0
    assert by_code["teamwork"] == 7
    assert by_code["leadership"] is None
    assert r.json()["development_input"]["needs"] == ["communication"]

    again = {c["code"]: c["score"] for c in client.get(f"/evaluations/{link_id}", headers=h).json()["competencies"]}
    assert again["communication"] == 0


def test_nota_onze_rejeitada(client, auth, links):
    r = client.put(
        f"/evaluations/{links['gestor'].id}",
        headers=auth("gestor"),
        json={"scores": [{"competency_code": "communication", "score": 11}]},
    )
    assert r.status_code in (400, 422)
    r2 = client.post(
        f"/evaluations/{links['gestor'].id}/submit",
        headers=auth("gestor"),
        json={
            "scores": _scores(override={"communication": 11}),
            "development_input": _gestor_input(),
        },
    )
    assert r2.status_code in (400, 422)


def test_dezenove_notas_rejeitadas(client, auth, links):
    r = client.post(
        f"/evaluations/{links['gestor'].id}/submit",
        headers=auth("gestor"),
        json={"scores": _scores(n=19), "development_input": _gestor_input()},
    )
    assert r.status_code in (400, 422)


def test_codes_invalidos_em_needs(client, auth, links):
    r = client.put(
        f"/evaluations/{links['auto'].id}",
        headers=auth("colab"),
        json={"development_input": {"needs": ["nao_existe"], "priority_competency": "nao_existe"}},
    )
    assert r.status_code in (400, 422)

    r2 = client.post(
        f"/evaluations/{links['auto'].id}/submit",
        headers=auth("colab"),
        json={
            "scores": _scores(),
            "development_input": _auto_input(needs=["communication"] * 6, priority_competency="communication"),
        },
    )
    assert r2.status_code in (400, 422)

    r3 = client.post(
        f"/evaluations/{links['auto'].id}/submit",
        headers=auth("colab"),
        json={
            "scores": _scores(),
            "development_input": _auto_input(priority_competency="leadership"),
        },
    )
    assert r3.status_code in (400, 422)


def test_submit_gestor_com_zero_e_nao_edita_depois(client, auth, links):
    h = auth("gestor")
    link_id = links["gestor"].id
    r = client.post(
        f"/evaluations/{link_id}/submit",
        headers=h,
        json={"scores": _scores(value=0), "development_input": _gestor_input()},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completo"
    assert body["submitted_at"] is not None
    assert all(c["score"] == 0 for c in body["competencies"])

    put = client.put(
        f"/evaluations/{link_id}",
        headers=h,
        json={"scores": [{"competency_code": "communication", "score": 8}]},
    )
    assert put.status_code == 409
    post = client.post(
        f"/evaluations/{link_id}/submit",
        headers=h,
        json={"scores": _scores(value=8), "development_input": _gestor_input()},
    )
    assert post.status_code == 409
    again = client.get(f"/evaluations/{link_id}", headers=h).json()
    assert all(c["score"] == 0 for c in again["competencies"])


def test_submit_auto_completo(client, auth, links):
    r = client.post(
        f"/evaluations/{links['auto'].id}/submit",
        headers=auth("colab"),
        json={"scores": _scores(value=6), "development_input": _auto_input()},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completo"
    assert r.json()["development_input"]["main_goal"] == "crescer no cargo"


def test_outro_usuario_nao_salva_nem_envia(client, auth, links):
    link_id = links["gestor"].id
    h = auth("fora")
    assert client.put(
        f"/evaluations/{link_id}",
        headers=h,
        json={"scores": [{"competency_code": "communication", "score": 5}]},
    ).status_code in (403, 404)
    assert client.post(
        f"/evaluations/{link_id}/submit",
        headers=h,
        json={"scores": _scores(), "development_input": _gestor_input()},
    ).status_code in (403, 404)

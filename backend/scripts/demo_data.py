"""Cria 2 usuários de demonstração com avaliações completas (para ver o PDI sem esperar o teste).

Uso (dentro de backend/):  python scripts/demo_data.py [--generate | --clean]

Só mexe nos usuários demo1@exemplo.com e demo2@exemplo.com (e em dados ligados a eles).
Usuários reais nunca são alterados; o gestor real só aparece como avaliador dos vínculos demo.
"""

import argparse
import random
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import delete, select

from app.db import get_session_factory
from app.models import (
    Cargo,
    Competency,
    DevelopmentInput,
    EvaluationLink,
    Pdi,
    PdiItem,
    Score,
    User,
)

# (e-mail, nome, cargo existente, e-mail do gestor existente, semente das notas)
DEMOS = [
    ("demo1@exemplo.com", "[DEMO] Colaborador Fiscal", "Analista Fiscal", "tercio@exemplo.com", 1),
    ("demo2@exemplo.com", "[DEMO] Colaborador Pessoal", "Analista de Departamento Pessoal", "tatiana.bernardo@exemplo.com", 2),
]
DEMO_EMAILS = [d[0] for d in DEMOS]
ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def clean(session) -> None:
    ids = list(session.scalars(select(User.id).where(User.email.in_(DEMO_EMAILS))).all())
    if not ids:
        return
    link_ids = select(EvaluationLink.id).where(
        EvaluationLink.evaluated_id.in_(ids) | EvaluationLink.evaluator_id.in_(ids)
    )
    pdi_ids = select(Pdi.id).where(Pdi.user_id.in_(ids))
    session.execute(delete(PdiItem).where(PdiItem.pdi_id.in_(pdi_ids)))
    session.execute(delete(Pdi).where(Pdi.user_id.in_(ids)))
    session.execute(delete(DevelopmentInput).where(DevelopmentInput.link_id.in_(link_ids)))
    session.execute(delete(Score).where(Score.link_id.in_(link_ids)))
    session.execute(
        delete(EvaluationLink).where(
            EvaluationLink.evaluated_id.in_(ids) | EvaluationLink.evaluator_id.in_(ids)
        )
    )
    session.execute(delete(User).where(User.id.in_(ids)))
    session.commit()


def _scores(rng: random.Random, codes: list[str]) -> tuple[dict[str, int], dict[str, int]]:
    auto = {c: rng.randint(4, 9) for c in codes}
    gestor = {c: max(0, min(10, s + rng.randint(-3, 2))) for c, s in auto.items()}
    gestor[codes[-1]] = 0  # nota 0 é válida
    return auto, gestor


def _link(session, evaluator: User, evaluated: User, kind: str, scores: dict[str, int], comps, data: dict):
    link = EvaluationLink(
        evaluator_id=evaluator.id,
        evaluated_id=evaluated.id,
        type=kind,
        status="completo",
        submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(link)
    session.flush()
    for code, score in scores.items():
        session.add(Score(link_id=link.id, competency_id=comps[code].id, score=score))
    session.add(DevelopmentInput(link_id=link.id, data=data))


def create(session) -> None:
    comps = {c.code: c for c in session.scalars(select(Competency).order_by(Competency.id)).all()}
    if not comps:
        sys.exit("Competências não encontradas. Rode seed.py antes.")
    codes = list(comps)
    for email, name, cargo_name, gestor_email, seed in DEMOS:
        cargo = session.scalar(select(Cargo).where(Cargo.name == cargo_name))
        gestor = session.scalar(select(User).where(User.email == gestor_email, User.role == "gestor"))
        if cargo is None or gestor is None:
            sys.exit(f"Cargo '{cargo_name}' ou gestor '{gestor_email}' não encontrado. Rode seed.py antes.")
        password = "".join(secrets.choice(ALPHABET) for _ in range(12))
        user = User(
            name=name,
            email=email,
            password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
            role="colaborador",
            cargo_id=cargo.id,
            department=cargo.department,
            tenure_band="1-2a",
            is_participant=True,
            consented_at=datetime.now(timezone.utc).replace(tzinfo=None),
            active=True,
        )
        session.add(user)
        session.flush()
        rng = random.Random(seed)
        auto, gestor_scores = _scores(rng, codes)
        needs = rng.sample(codes, 3)
        _link(
            session, user, user, "auto", auto, comps,
            {
                "main_goal": "Crescer no cargo atual.",
                "needs": needs,
                "priority_competency": needs[0],
                "priority_reason": "Quero evoluir nesta competência.",
                "stay_in_role": "sim",
                "future_role": None,
                "dev_types": ["curso", "mentoria"],
                "timeframe": "3_6m",
            },
        )
        g_needs = rng.sample(codes, 2)
        _link(
            session, gestor, user, "gestor", gestor_scores, comps,
            {"needs": g_needs, "priority_competency": g_needs[0], "priority_reason": "Observado no dia a dia."},
        )
        print(f"{email}  senha: {password}  (id {user.id}, gestor: {gestor.name})")
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="já gera o PDI dos 2 usuários demo")
    parser.add_argument("--clean", action="store_true", help="apaga só os dados dos 2 usuários demo")
    args = parser.parse_args()
    with get_session_factory()() as session:
        clean(session)
        if args.clean:
            print("Dados demo removidos.")
            return
        create(session)
        if args.generate:
            from app.routers.pdi import _build_result, _save

            for user in session.scalars(select(User).where(User.email.in_(DEMO_EMAILS))):
                _save(session, user, _build_result(session, user))
                print(f"PDI gerado para {user.email}")
        else:
            print("Pronto. Gere o PDI como admin: POST /admin/pdi/{id}/generate (ou rode com --generate)")


if __name__ == "__main__":
    main()

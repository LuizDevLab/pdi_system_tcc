"""Motor de cálculo do PDI: só funções puras (sem banco, sem FastAPI).

Convenção: notas e níveis são dicts {code da competência: valor}.
"""

from collections.abc import Iterable, Mapping, Sequence

import numpy as np

from app import config

_DIGITS = 9  # tolerância de ponto flutuante só nas comparações (6.000000000000001 >= 6)


class NotEligibleError(ValueError):
    """Falta autoavaliação completa ou avaliação de gestor completa."""


def _r(x: float) -> float:
    return round(x, _DIGITS)


def is_eligible(evaluations: Mapping[str, Sequence[Mapping[str, float]]]) -> bool:
    """Regra 1: precisa de pelo menos uma autoavaliação e uma de gestor (completas). RH é opcional."""
    return bool(evaluations.get("auto")) and bool(evaluations.get("gestor"))


def average_by_type(
    evaluations: Mapping[str, Sequence[Mapping[str, float]]],
) -> dict[str, dict[str, float]]:
    """Regra 2a: média por competência das avaliações completas de cada tipo. Tipos sem avaliação ficam de fora."""
    result: dict[str, dict[str, float]] = {}
    for kind, evals in evaluations.items():
        if not evals:
            continue
        codes = evals[0].keys()
        result[kind] = {code: sum(e[code] for e in evals) / len(evals) for code in codes}
    return result


def consolidate(
    by_type: Mapping[str, Mapping[str, float]],
    weights: Mapping[str, float] = config.WEIGHTS,
) -> dict[str, float]:
    """Regra 2b: média ponderada entre os tipos presentes, com pesos renormalizados só entre eles.

    Nota 0 é uma nota válida (entra na conta como 0).
    """
    present = [k for k in by_type if k in weights]
    total_weight = sum(weights[k] for k in present)
    if not present or total_weight == 0:
        raise ValueError("nenhum tipo de avaliação com peso")
    codes = by_type[present[0]].keys()
    return {code: sum(weights[k] * by_type[k][code] for k in present) / total_weight for code in codes}


def cosine_similarity(u: Sequence[float], v: Sequence[float]) -> float:
    """Regra 3: cos = (u·v) / (‖u‖·‖v‖); vetor nulo retorna 0."""
    a = np.asarray(u, dtype=float)
    b = np.asarray(v, dtype=float)
    if a.shape != b.shape:
        raise ValueError("vetores de tamanhos diferentes")
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Regra 4: |A ∩ B| / |A ∪ B|; união vazia retorna 1,0."""
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 1.0
    return len(sa & sb) / len(union)


def codes_at_or_above(levels: Mapping[str, float], threshold: float) -> set[str]:
    """Competências com valor >= limiar (conjuntos A e B do Jaccard)."""
    return {code for code, value in levels.items() if _r(value) >= threshold}


def compute_gaps(reference: Mapping[str, float], consolidated: Mapping[str, float]) -> dict[str, float]:
    """Regra 5: gap = esperado - consolidado, com sinal (negativo = acima do esperado)."""
    return {code: reference[code] - consolidated[code] for code in reference}


def prioritize(
    gaps: Mapping[str, float],
    consolidated: Mapping[str, float],
    priority_codes: Iterable[str] = (),
    needs: Iterable[str] = (),
    min_gap: float = config.MIN_GAP,
    max_items: int = config.MAX_ITEMS,
) -> list[str]:
    """Regra 6: candidatas (gap >= min_gap), ordenadas por gap decrescente.

    Desempate: prioritária (colaborador ou gestor), depois citada em needs,
    depois menor nota consolidada, depois ordem alfabética do code.
    """
    priority, needed = set(priority_codes), set(needs)
    candidates = [c for c, g in gaps.items() if _r(g) >= min_gap]
    candidates.sort(
        key=lambda c: (-_r(gaps[c]), c not in priority, c not in needed, _r(consolidated[c]), c)
    )
    return candidates[:max_items]


def pick_action(actions: Sequence[Mapping], dev_types: Iterable[str] = ()) -> int | None:
    """Regra 7: ação (dict com id e type) do tipo preferido do colaborador; senão a de menor id."""
    if not actions:
        return None
    ordered = sorted(actions, key=lambda a: a["id"])
    preferred = set(dev_types)
    for action in ordered:
        if action["type"] in preferred:
            return action["id"]
    return ordered[0]["id"]


def pick_timeframe(gap: float, is_own_priority: bool = False, own_timeframe: str | None = None) -> str:
    """Regra 8: prioritária do colaborador usa o prazo dele; senão pelo tamanho da lacuna."""
    if is_own_priority and own_timeframe:
        return own_timeframe
    g = _r(gap)
    if g >= 4:
        return "6_12m"
    if g >= 2:
        return "3_6m"
    return "ate_3m"


def divergence(auto: Mapping[str, float], gestor: Mapping[str, float]) -> dict[str, float]:
    """Regra 9: autoavaliação menos gestor, por competência (positivo = se vê acima do gestor)."""
    return {code: auto[code] - gestor[code] for code in auto if code in gestor}


def build_pdi(
    evaluations: Mapping[str, Sequence[Mapping[str, float]]],
    reference: Mapping[str, float],
    actions_by_competency: Mapping[str, Sequence[Mapping]],
    self_inputs: Mapping | None = None,
    manager_inputs: Sequence[Mapping] = (),
    reference_provisional: bool = False,
    weights: Mapping[str, float] = config.WEIGHTS,
    has_threshold: float = config.HAS_THRESHOLD,
    required_threshold: float = config.REQUIRED_THRESHOLD,
    min_gap: float = config.MIN_GAP,
    max_items: int = config.MAX_ITEMS,
) -> dict:
    """Monta o resultado do PDI (regras 1 a 9) a partir de dados simples.

    evaluations: {"auto"|"gestor"|"rh": [ {code: nota}, ... ]} só avaliações completas.
    reference: {code: expected_level} do cargo.
    actions_by_competency: {code: [ {"id", "type"}, ... ]}.
    self_inputs: development_inputs da autoavaliação (priority_competency, needs, dev_types, timeframe).
    manager_inputs: development_inputs de gestor/RH (priority_competency, needs).
    """
    if not is_eligible(evaluations):
        raise NotEligibleError("PDI exige autoavaliação completa e ao menos uma avaliação de gestor completa")

    self_inputs = self_inputs or {}
    by_type = average_by_type(evaluations)
    consolidated = consolidate(by_type, weights)

    codes = sorted(reference)
    missing = [c for c in codes if c not in consolidated]
    if missing:
        raise ValueError(f"competências sem nota consolidada: {missing}")

    cosine = cosine_similarity([consolidated[c] for c in codes], [reference[c] for c in codes])
    has = codes_at_or_above(consolidated, has_threshold)
    required = codes_at_or_above(reference, required_threshold)
    gaps = compute_gaps(reference, consolidated)
    diverg = divergence(by_type["auto"], by_type["gestor"])

    own_priority = self_inputs.get("priority_competency")
    priority_codes = {own_priority, *(m.get("priority_competency") for m in manager_inputs)} - {None}
    needs = set(self_inputs.get("needs") or [])
    for m in manager_inputs:
        needs.update(m.get("needs") or [])

    ranked = prioritize(gaps, consolidated, priority_codes, needs, min_gap, max_items)
    dev_types = self_inputs.get("dev_types") or []
    items = [
        {
            "competency": code,
            "gap": gaps[code],
            "rank": rank,
            "action_id": pick_action(actions_by_competency.get(code, ()), dev_types),
            "timeframe": pick_timeframe(
                gaps[code], code == own_priority, self_inputs.get("timeframe")
            ),
            "divergence": diverg.get(code),
        }
        for rank, code in enumerate(ranked, start=1)
    ]

    return {
        "consolidated": consolidated,
        "by_type": by_type,
        "cosine": cosine,
        "jaccard": jaccard(has, required),
        "gaps": gaps,
        "divergence": diverg,
        "items": items,
        "reference_provisional": reference_provisional,
        "config_snapshot": {
            "weights": dict(weights),
            "has_threshold": has_threshold,
            "required_threshold": required_threshold,
            "min_gap": min_gap,
            "max_items": max_items,
        },
    }

"""Testes do engine.py. Os cálculos de cada caso estão nos comentários, para conferir à mão."""

import math

import pytest

from app import engine

W = {"auto": 0.3, "gestor": 0.5, "rh": 0.2}


# ---------- cosseno ----------

def test_cosine_identical_vectors_is_1():
    # u = v = [3,4]: u·v = 9+16 = 25; ‖u‖ = ‖v‖ = 5; cos = 25 / (5·5) = 1
    assert engine.cosine_similarity([3, 4], [3, 4]) == pytest.approx(1.0)


def test_cosine_ignores_magnitude():
    # u=[3,4], v=[6,8]: u·v = 18+32 = 50; ‖u‖ = 5; ‖v‖ = 10; cos = 50 / (5·10) = 1
    assert engine.cosine_similarity([3, 4], [6, 8]) == pytest.approx(1.0)


def test_cosine_orthogonal_is_0():
    # u=[1,0], v=[0,1]: u·v = 0·1 + 1·0 = 0; cos = 0
    assert engine.cosine_similarity([1, 0], [0, 1]) == 0.0


def test_cosine_null_vector_is_0():
    # ‖u‖ = 0 → denominador zero → retorna 0 (e não erro/NaN)
    assert engine.cosine_similarity([0, 0], [3, 4]) == 0.0
    assert engine.cosine_similarity([3, 4], [0, 0]) == 0.0


def test_cosine_general_case():
    # u=[1,2], v=[2,1]: u·v = 2+2 = 4; ‖u‖ = ‖v‖ = √5; cos = 4/5 = 0,8
    assert engine.cosine_similarity([1, 2], [2, 1]) == pytest.approx(0.8)


# ---------- Jaccard ----------

def test_jaccard_half():
    # A={a,b,c}, B={b,c,d}: A∩B={b,c} → 2; A∪B={a,b,c,d} → 4; J = 2/4 = 0,5
    assert engine.jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5


def test_jaccard_empty_union_is_1():
    assert engine.jaccard(set(), set()) == 1.0


def test_jaccard_disjoint_is_0():
    # A={a}, B={b}: ∩ = 0; ∪ = 2; J = 0
    assert engine.jaccard({"a"}, {"b"}) == 0.0


def test_codes_at_or_above_threshold_is_inclusive():
    # limiar 6: 6 entra (>=), 5.99 não, 0 não
    assert engine.codes_at_or_above({"a": 6, "b": 5.99, "c": 0, "d": 10}, 6) == {"a", "d"}


# ---------- consolidação ----------

def test_average_by_type_averages_multiple_managers():
    # gestor 1: a=6, b=2 / gestor 2: a=8, b=4 → a = (6+8)/2 = 7; b = (2+4)/2 = 3
    by_type = engine.average_by_type({"gestor": [{"a": 6, "b": 2}, {"a": 8, "b": 4}], "rh": []})
    assert by_type == {"gestor": {"a": 7, "b": 3}}  # tipo sem avaliação fica de fora


def test_consolidate_without_rh_renormalizes_weights():
    # Sem RH: pesos 0,3 e 0,5 somam 0,8 → auto = 0,3/0,8 = 0,375; gestor = 0,5/0,8 = 0,625
    # a: 0,375·8 + 0,625·6 = 3 + 3,75 = 6,75
    # b: 0,375·2 + 0,625·4 = 0,75 + 2,5 = 3,25
    result = engine.consolidate({"auto": {"a": 8, "b": 2}, "gestor": {"a": 6, "b": 4}}, W)
    assert result["a"] == pytest.approx(6.75)
    assert result["b"] == pytest.approx(3.25)


def test_consolidate_with_rh_uses_original_weights():
    # Pesos 0,3 + 0,5 + 0,2 = 1,0 (sem renormalizar)
    # a: 0,3·8 + 0,5·6 + 0,2·10 = 2,4 + 3 + 2 = 7,4
    # b: 0,3·2 + 0,5·4 + 0,2·10 = 0,6 + 2 + 2 = 4,6
    result = engine.consolidate(
        {"auto": {"a": 8, "b": 2}, "gestor": {"a": 6, "b": 4}, "rh": {"a": 10, "b": 10}}, W
    )
    assert result["a"] == pytest.approx(7.4)
    assert result["b"] == pytest.approx(4.6)


def test_consolidate_score_zero_counts_as_zero_not_empty():
    # a: auto=0, gestor=6, sem RH → 0,375·0 + 0,625·6 = 3,75
    # Se o 0 fosse tratado como "vazio", só o gestor contaria (peso 1) e daria 6.
    result = engine.consolidate({"auto": {"a": 0}, "gestor": {"a": 6}}, W)
    assert result["a"] == pytest.approx(3.75)


def test_consolidate_all_zero_stays_zero():
    result = engine.consolidate({"auto": {"a": 0}, "gestor": {"a": 0}}, W)
    assert result["a"] == 0


def test_average_then_consolidate_zero_in_average():
    # gestores a=0 e a=4 → média 2; auto a=10; sem RH → 0,375·10 + 0,625·2 = 3,75 + 1,25 = 5
    by_type = engine.average_by_type({"auto": [{"a": 10}], "gestor": [{"a": 0}, {"a": 4}]})
    assert engine.consolidate(by_type, W)["a"] == pytest.approx(5.0)


# ---------- lacunas e priorização ----------

def test_gaps_keep_sign():
    # a: 7-5 = 2 (falta); b: 7-9 = -2 (acima do esperado)
    assert engine.compute_gaps({"a": 7, "b": 7}, {"a": 5, "b": 9}) == {"a": 2, "b": -2}


def test_prioritize_sorts_by_gap_and_filters_min_gap():
    # a=3, b=0,99 (abaixo de 1,0, fora), c=1,0 (entra: >=), d=-2 (fora), e=5
    gaps = {"a": 3, "b": 0.99, "c": 1.0, "d": -2, "e": 5}
    cons = {k: 5 for k in gaps}
    assert engine.prioritize(gaps, cons, min_gap=1.0, max_items=5) == ["e", "a", "c"]


def test_prioritize_respects_max_items():
    gaps = {"a": 5, "b": 4, "c": 3, "d": 2}
    assert engine.prioritize(gaps, {k: 0 for k in gaps}, max_items=2) == ["a", "b"]


def test_prioritize_gap_beats_priority():
    # prioridade só desempata: a (gap 2) vem depois de b (gap 3), mesmo sendo prioritária
    gaps = {"a": 2, "b": 3}
    assert engine.prioritize(gaps, {"a": 5, "b": 4}, priority_codes={"a"}) == ["b", "a"]


def test_prioritize_tie_priority_then_needs_then_alphabetical():
    # 5 competências com gap 2 e consolidado 5 (empate total, exceto prioridade/needs)
    # ordem esperada: d (prioritária), c (citada em needs), depois alfabética: a, b
    gaps = {k: 2 for k in "abcde"}
    cons = {k: 5 for k in "abcde"}
    result = engine.prioritize(gaps, cons, priority_codes={"d"}, needs={"c"}, max_items=4)
    assert result == ["d", "c", "a", "b"]


def test_prioritize_tie_lower_consolidated_first():
    # a: esperado 9, consolidado 6 → gap 3; b: esperado 7, consolidado 4 → gap 3
    # empate no gap, sem prioridade/needs → menor consolidado primeiro: b (4) antes de a (6)
    gaps = {"a": 3, "b": 3}
    assert engine.prioritize(gaps, {"a": 6, "b": 4}) == ["b", "a"]


def test_prioritize_tie_alphabetical_last_resort():
    gaps = {"z": 2, "m": 2, "a": 2}
    cons = {"z": 5, "m": 5, "a": 5}
    assert engine.prioritize(gaps, cons) == ["a", "m", "z"]


def test_prioritize_is_deterministic_regardless_of_input_order():
    cons = {"a": 5, "b": 5, "c": 5, "d": 4}
    gaps_1 = {"a": 2, "b": 2, "c": 2, "d": 3}
    gaps_2 = dict(reversed(list(gaps_1.items())))
    expected = ["d", "a", "b", "c"]
    assert engine.prioritize(gaps_1, cons) == expected
    assert engine.prioritize(gaps_2, cons) == expected


def test_float_noise_does_not_drop_candidate_nor_break_tie():
    # 6·0,3/1 + 6·0,5/1 + 6·0,2/1 pode dar 6,000000000000001 em ponto flutuante;
    # o gap esperado é exatamente 1,0 e a competência deve continuar candidata.
    cons = engine.consolidate({"auto": {"a": 6}, "gestor": {"a": 6}, "rh": {"a": 6}}, W)
    gaps = engine.compute_gaps({"a": 7}, cons)
    assert engine.prioritize(gaps, cons, min_gap=1.0) == ["a"]


# ---------- ação e prazo ----------

ACTIONS = [
    {"id": 7, "type": "certificacao"},
    {"id": 3, "type": "curso"},
    {"id": 5, "type": "mentoria"},
]


def test_pick_action_prefers_collaborator_type():
    assert engine.pick_action(ACTIONS, ["mentoria", "projeto_desafio"]) == 5


def test_pick_action_several_preferred_takes_lowest_id():
    # curso (id 3) e mentoria (id 5) estão nas preferências → a de menor id
    assert engine.pick_action(ACTIONS, ["mentoria", "curso"]) == 3


def test_pick_action_falls_back_to_first_by_id():
    assert engine.pick_action(ACTIONS, ["acompanhamento"]) == 3
    assert engine.pick_action(ACTIONS, []) == 3


def test_pick_action_without_catalog_is_none():
    assert engine.pick_action([], ["curso"]) is None


@pytest.mark.parametrize(
    "gap, expected",
    [(1.0, "ate_3m"), (1.99, "ate_3m"), (2.0, "3_6m"), (3.99, "3_6m"), (4.0, "6_12m"), (7.5, "6_12m")],
)
def test_timeframe_by_gap(gap, expected):
    assert engine.pick_timeframe(gap) == expected


def test_timeframe_own_priority_uses_collaborator_choice():
    # gap 5 daria 6_12m, mas a prioritária do colaborador usa o prazo dele
    assert engine.pick_timeframe(5, True, "ate_3m") == "ate_3m"
    assert engine.pick_timeframe(5, False, "ate_3m") == "6_12m"


# ---------- divergência ----------

def test_divergence_is_auto_minus_gestor():
    # a: 8-6 = 2; b: 3-5 = -2; c: 0-0 = 0 (zero é nota válida); d só existe na auto → ignorada
    result = engine.divergence({"a": 8, "b": 3, "c": 0, "d": 9}, {"a": 6, "b": 5, "c": 0})
    assert result == {"a": 2, "b": -2, "c": 0}


# ---------- build_pdi ----------

REFERENCE = {c: 7 for c in "abcd"}
EVALS = {
    "auto": [{"a": 8, "b": 6, "c": 5, "d": 9}],
    "gestor": [{"a": 6, "b": 4, "c": 5, "d": 7}],
}
CATALOG = {
    "b": [{"id": 2, "type": "curso"}, {"id": 1, "type": "mentoria"}],
    "c": [{"id": 4, "type": "curso"}],
}


def test_build_pdi_full_example():
    # Sem RH → pesos 0,375 (auto) e 0,625 (gestor)
    # consolidado: a = 0,375·8+0,625·6 = 6,75 | b = 0,375·6+0,625·4 = 4,75
    #              c = 0,375·5+0,625·5 = 5    | d = 0,375·9+0,625·7 = 7,75
    # referência 7 em todas → gaps: a 0,25 | b 2,25 | c 2,0 | d -0,75 → candidatas: b e c
    # cosseno: u=[6,75; 4,75; 5; 7,75], v=[7,7,7,7]
    #          u·v = 7·24,25 = 169,75; ‖u‖² = 45,5625+22,5625+25+60,0625 = 153,1875; ‖v‖ = 14
    # Jaccard: A (>=6) = {a,d}; B (>=6) = {a,b,c,d} → 2/4 = 0,5
    # divergência (auto - gestor): a 2 | b 2 | c 0 | d 2
    r = engine.build_pdi(
        EVALS,
        REFERENCE,
        CATALOG,
        self_inputs={"dev_types": ["curso"], "priority_competency": "c", "timeframe": "mais_12m"},
        reference_provisional=True,
    )
    assert r["consolidated"] == pytest.approx({"a": 6.75, "b": 4.75, "c": 5.0, "d": 7.75})
    assert r["gaps"] == pytest.approx({"a": 0.25, "b": 2.25, "c": 2.0, "d": -0.75})
    assert r["cosine"] == pytest.approx(169.75 / (math.sqrt(153.1875) * 14))
    assert r["jaccard"] == 0.5
    assert r["divergence"] == {"a": 2, "b": 2, "c": 0, "d": 2}
    assert r["reference_provisional"] is True

    b, c = r["items"]
    # b: gap 2,25 maior que o de c (2,0) → rank 1 mesmo c sendo prioritária; ação do tipo curso (id 2)
    assert (b["competency"], b["rank"], b["action_id"], b["timeframe"], b["divergence"]) == ("b", 1, 2, "3_6m", 2)
    # c: prioritária do colaborador → prazo dele (mais_12m), em vez de 3_6m pelo gap
    assert (c["competency"], c["rank"], c["action_id"], c["timeframe"], c["divergence"]) == ("c", 2, 4, "mais_12m", 0)


def test_build_pdi_uses_manager_priority_and_needs_in_tie_break():
    # todas com gap 2 (consolidado 5, ref 7); gestor prioriza "c"; colaborador cita "b" em needs
    evals = {"auto": [{k: 5 for k in "abcd"}], "gestor": [{k: 5 for k in "abcd"}]}
    r = engine.build_pdi(
        evals,
        REFERENCE,
        {},
        self_inputs={"needs": ["b"]},
        manager_inputs=[{"priority_competency": "c"}],
    )
    assert [i["competency"] for i in r["items"]] == ["c", "b", "a", "d"]
    assert all(i["action_id"] is None for i in r["items"])


def test_build_pdi_with_rh_and_zero_scores():
    # RH presente: pesos 0,3/0,5/0,2. a: auto 0, gestor 10, rh 5 → 0 + 5 + 1 = 6
    evals = {"auto": [{"a": 0}], "gestor": [{"a": 10}], "rh": [{"a": 5}]}
    r = engine.build_pdi(evals, {"a": 7}, {})
    assert r["consolidated"]["a"] == pytest.approx(6.0)
    assert r["items"][0]["gap"] == pytest.approx(1.0)


def test_build_pdi_snapshot_records_config():
    r = engine.build_pdi(EVALS, REFERENCE, CATALOG, max_items=1)
    assert r["config_snapshot"]["max_items"] == 1
    assert r["config_snapshot"]["weights"] == W
    assert len(r["items"]) == 1


@pytest.mark.parametrize(
    "evals",
    [
        {"auto": [{"a": 5}]},  # sem gestor
        {"gestor": [{"a": 5}]},  # sem autoavaliação
        {"auto": [], "gestor": [{"a": 5}], "rh": [{"a": 5}]},  # auto vazia
        {"rh": [{"a": 5}]},
    ],
)
def test_build_pdi_requires_auto_and_gestor(evals):
    assert not engine.is_eligible(evals)
    with pytest.raises(engine.NotEligibleError):
        engine.build_pdi(evals, {"a": 7}, {})

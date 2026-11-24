from unittest.mock import patch
import pytest

from combat_calculator import CombatDamageCalculator
from combat_constants import estimate_expected_cases


def test_estimate_expected_cases_calibrated():
    # Field data: 498 hits at 17% loot, 98% precision -> 78 Case I, 2 Case II
    case1, case2 = estimate_expected_cases(hits=498, loot_chance_ratio=0.17, eff_prec_ratio=0.98)
    assert case1 == pytest.approx(78.0, abs=0.1)
    assert case2 == pytest.approx(2.0, abs=0.05)
    assert estimate_expected_cases(hits=0, loot_chance_ratio=0.17, eff_prec_ratio=0.98) == (0.0, 0.0)


def test_calculate_all_strategies_basic(sample_player, mock_market_cache):
    with patch("combat_calculator.load_market_cheapest_cache", return_value=mock_market_cache):
        res = CombatDamageCalculator().calculate_all_strategies(
            sample_player,
            target_damage=2_000_000,
        )

    assert "strategies" in res
    assert "best_strategy" in res
    assert len(res["strategies"]) > 0

    best = res["best_strategy"]
    assert best is not None
    assert best["is_best_value"] is True
    assert best["avg_dmg_per_hit"] > 0
    assert best["hits_needed"] > 0
    assert best["grand_total_cost"] >= 0

    # Best strategy should have minimal net_cost among reachable (or all) strategies
    reachable = [s for s in res["strategies"] if s.get("can_reach_in_session")]
    pool = reachable if reachable else res["strategies"]
    min_net = min(s["net_cost"] for s in pool)
    assert best["net_cost"] == pytest.approx(min_net, rel=1e-6)


def test_calculate_respects_ammo_and_food_filters(sample_player, mock_market_cache):
    with patch("combat_calculator.load_market_cheapest_cache", return_value=mock_market_cache):
        res = CombatDamageCalculator().calculate_all_strategies(
            sample_player,
            target_damage=1_500_000,
            selected_ammo="heavyAmmo",
            custom_food_key="cookedFish",
        )

    assert len(res["strategies"]) > 0
    for s in res["strategies"]:
        assert s["ammo_key"] == "heavyAmmo"
        assert s["food_key"] == "cookedFish"


def test_calculate_higher_battle_bonus_reduces_hits(sample_player, mock_market_cache):
    with patch("combat_calculator.load_market_cheapest_cache", return_value=mock_market_cache):
        res_low = CombatDamageCalculator().calculate_all_strategies(
            sample_player, target_damage=2_000_000, battle_bonus=20.0, selected_ammo="ammo", custom_food_key="steak"
        )
        res_high = CombatDamageCalculator().calculate_all_strategies(
            sample_player, target_damage=2_000_000, battle_bonus=100.0, selected_ammo="ammo", custom_food_key="steak"
        )

    low_map = {s["strategy_key"]: s for s in res_low["strategies"]}
    high_map = {s["strategy_key"]: s for s in res_high["strategies"]}

    common_keys = set(low_map.keys()) & set(high_map.keys())
    non_naked_keys = [k for k in common_keys if not low_map[k].get("is_naked") and low_map[k]["avg_dmg_per_hit"] > 0]
    assert len(non_naked_keys) > 0
    for k in non_naked_keys:
        assert high_map[k]["avg_dmg_per_hit"] > low_map[k]["avg_dmg_per_hit"]
        assert high_map[k]["hits_needed"] <= low_map[k]["hits_needed"]


def test_calculate_live_consumables_override(sample_player, mock_market_cache):
    with patch("combat_calculator.load_market_cheapest_cache", return_value=mock_market_cache):
        res = CombatDamageCalculator().calculate_all_strategies(
            sample_player,
            target_damage=1_000_000,
            live_consumables={"cocain": 99.5, "ammo": 1.25},
        )

    assert res["consumable_prices"]["cocain"] == pytest.approx(99.5)
    assert res["consumable_prices"]["ammo"] == pytest.approx(1.25)


def test_calculate_zero_target_damage_edge_case(sample_player, mock_market_cache):
    with patch("combat_calculator.load_market_cheapest_cache", return_value=mock_market_cache):
        res = CombatDamageCalculator().calculate_all_strategies(
            sample_player,
            target_damage=0.0,
        )

    assert len(res["strategies"]) > 0
    assert res["best_strategy"] is not None

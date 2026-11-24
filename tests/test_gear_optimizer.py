from unittest.mock import patch
import pytest

from gear_optimizer import GearOptimizer


def test_optimize_set_for_target_basic(sample_player, mock_market_cache):
    with patch("gear_optimizer.load_market_cheapest_cache", return_value=mock_market_cache):
        res = GearOptimizer().optimize_set_for_target(
            sample_player,
            target_damage=2_000_000,
        )

    assert res["status"] == "ok"
    assert res["best_strategy"] is not None
    assert len(res["strategies"]) > 0

    best = res["best_strategy"]
    assert best["is_best_value"] is True
    assert best["avg_dmg_per_hit"] > 0
    assert best["hits_needed"] > 0
    assert 0.0 <= best["eff_dodge"] <= 100.0
    assert 0.0 <= best["eff_armor"] <= 100.0
    assert 0.0 <= best["eff_precision"] <= 100.0


def test_optimize_unbounded_rank_bonus_and_prestige(sample_player, mock_market_cache):
    """Verifies rank bonus > 37.5% and prestige SPs increase damage per hit."""
    with patch("gear_optimizer.load_market_cheapest_cache", return_value=mock_market_cache):
        res_base = GearOptimizer().optimize_set_for_target(
            sample_player,
            target_damage=2_000_000,
            selected_weapon="sniper",
            selected_ammo="ammo",
            selected_food="steak",
            custom_rank_bonus=37.5,
            custom_prestige=0,
        )
        res_high = GearOptimizer().optimize_set_for_target(
            sample_player,
            target_damage=2_000_000,
            selected_weapon="sniper",
            selected_ammo="ammo",
            selected_food="steak",
            custom_rank_bonus=100.0,
            custom_prestige=5,
        )

    assert res_high["best_strategy"]["avg_dmg_per_hit"] > res_base["best_strategy"]["avg_dmg_per_hit"]


def test_optimize_filters_weapon_ammo_food(sample_player, mock_market_cache):
    with patch("gear_optimizer.load_market_cheapest_cache", return_value=mock_market_cache):
        res = GearOptimizer().optimize_set_for_target(
            sample_player,
            target_damage=2_000_000,
            selected_weapon="tank",
            selected_ammo="heavyAmmo",
            selected_food="cookedFish",
        )

    assert res["status"] == "ok"
    for s in res["strategies"]:
        assert s["ammo_key"] == "heavyAmmo"
        assert s["food_key"] == "cookedFish"
        assert s["slots"]["weapon"]["code"] == "tank"


def test_optimize_locked_saved_build(sample_player, mock_market_cache):
    saved_build = {
        "weapon": "sniper",
        "helmet": "helmet4",
        "chest": "chest4",
        "pants": "pants4",
        "boots": "boots4",
        "gloves": "gloves4",
        "ammo": "ammo",
        "food": "steak",
    }
    with patch("gear_optimizer.load_market_cheapest_cache", return_value=mock_market_cache):
        res = GearOptimizer().optimize_set_for_target(
            sample_player,
            target_damage=1_500_000,
            saved_build=saved_build,
            is_build_locked=True,
        )

    assert res["status"] == "ok"
    assert res["is_build_locked"] is True
    assert res["best_strategy"]["is_saved_build"] is True
    assert res["best_strategy"]["weapon"] == "sniper"
    assert res["best_strategy"]["ammo"] == "ammo"
    assert res["best_strategy"]["food"] == "steak"
    assert res["best_strategy"]["hits_needed"] > 0

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


def test_optimize_uses_cheapest_price_and_stat_filtered_live_offers(sample_player):
    """Verifies GearOptimizer reads cheapest_price/offers and filters live offers by min roll."""
    cache_with_cheapest_price = {
        "items": {
            "rifle": {"cheapest_price": 19.5},
            "sniper": {"cheapest_price": 55.0},
            "helmet4": {
                "cheapest_price": 46.0,
                "offers": [
                    {"price": 46.0, "skills": {"criticalDamages": 71}},
                    {"price": 50.98, "skills": {"criticalDamages": 78}},
                ],
            },
            "chest4": {"cheapest_price": 48.0},
            "pants4": {"cheapest_price": 49.0},
            "boots4": {"cheapest_price": 44.0},
            "gloves4": {"cheapest_price": 45.0},
        },
        "consumables": {
            "cookedFish": 7.85,
            "steak": 3.05,
            "lightAmmo": 0.20,
            "ammo": 0.84,
            "heavyAmmo": 3.08,
            "cocain": 34.80,
        },
    }

    class DummyMarketApp:
        latest_market_offers = {
            "helmet4": [
                {"price": 46.0, "item": {"skills": {"criticalDamages": 71}}},
                {"price": 50.98, "item": {"skills": {"criticalDamages": 78}}},
            ]
        }

    with patch("gear_optimizer.load_market_cheapest_cache", return_value=cache_with_cheapest_price):
        res = GearOptimizer(market_app=DummyMarketApp()).optimize_set_for_target(
            sample_player,
            target_damage=2_000_000,
            selected_weapon="rifle",
        )

    assert res["status"] == "ok"
    best = res["best_strategy"]
    assert best["slots"]["weapon"]["price"] == 19.5
    if best["slots"]["helmet"]["code"] == "helmet4":
        assert best["slots"]["helmet"]["price"] == 50.98


def test_saved_build_refreshes_equipment_prices(sample_player):
    """Verifies locked/saved builds refresh stale equipment unit_price from live market offers."""
    cache = {
        "items": {
            "helmet4": {
                "cheapest_price": 46.0,
                "offers": [
                    {"price": 46.0, "skills": {"criticalDamages": 71}},
                    {"price": 50.98, "skills": {"criticalDamages": 78}},
                ],
            },
        },
        "consumables": {"cookedFish": 7.85, "lightAmmo": 0.20, "cocain": 34.80},
    }
    saved_build = {
        "strategy_key": "opt_rifle_4_4_2_lightAmmo_cookedFish",
        "label": "🔥 Гвинтівка T3 · Гібрид",
        "avg_dmg_per_hit": 5200.0,
        "hp_cost_per_hit": 20.0,
        "eff_dodge": 50.0,
        "eff_armor": 30.0,
        "eff_precision": 1.0,
        "ammo_key": "lightAmmo",
        "food_key": "cookedFish",
        "build_slots": [
            {"slot": "helmet", "item_code": "helmet4", "unit_price": 47.2, "qty_needed": 2, "total_price": 94.4},
        ],
    }

    with patch("gear_optimizer.load_market_cheapest_cache", return_value=cache):
        res = GearOptimizer().optimize_set_for_target(
            sample_player,
            target_damage=2_000_000,
            saved_build=saved_build,
            is_build_locked=True,
        )

    assert res["status"] == "ok"
    helmet_slot = next(s for s in res["best_strategy"]["build_slots"] if s["slot"] == "helmet")
    assert helmet_slot["unit_price"] == 50.98
    assert helmet_slot["total_price"] == round(50.98 * helmet_slot["qty_needed"], 2)

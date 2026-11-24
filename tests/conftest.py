import pytest


@pytest.fixture
def sample_player():
    """Standard mid-high level player fixture for deterministic combat math tests."""
    return {
        "username": "TestFighter",
        "level": 35,
        "prestige": 2,
        "rank_bonus_pct": 50.0,
        "health_max": 200,
        "health_curr": 200,
        "health_regen": 20.0,
        "hunger_max": 10,
        "hunger_curr": 10,
        "hunger_regen": 1.0,
        "skills": {
            "attack": {"total": 160, "militaryRankPercent": 50.0},
            "precision": {"total": 60},
            "criticalChance": {"total": 30},
            "criticalDamages": {"total": 150},
            "armor": {"total": 20},
            "dodge": {"total": 20},
            "health": {"total": 200, "currentBarValue": 200, "hourlyBarRegen": 20.0},
            "hunger": {"total": 10, "currentBarValue": 10, "hourlyBarRegen": 1.0},
        },
        "equipment": {},
    }


@pytest.fixture
def mock_market_cache():
    """Deterministic market cache fixture avoiding disk/network dependencies."""
    return {
        "items": {
            "rifle": {"price": 13.5, "url": "https://app.warera.io/market/rifle"},
            "sniper": {"price": 42.0, "url": "https://app.warera.io/market/sniper"},
            "tank": {"price": 144.0, "url": "https://app.warera.io/market/tank"},
            "jet": {"price": 450.0, "url": "https://app.warera.io/market/jet"},
            "helmet4": {"price": 45.0},
            "chest4": {"price": 43.0},
            "pants4": {"price": 44.0},
            "boots4": {"price": 41.0},
            "gloves4": {"price": 42.0},
        },
        "consumables": {
            "cookedFish": 7.5,
            "steak": 3.0,
            "fish": 3.9,
            "bread": 1.4,
            "lightAmmo": 0.2,
            "ammo": 0.8,
            "heavyAmmo": 3.0,
            "cocain": 15.0,
            "case": 50.0,
            "caseElite": 200.0,
        },
    }

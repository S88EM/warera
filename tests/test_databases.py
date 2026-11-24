from datetime import datetime, timezone, timedelta

from clan_history_db import ClanHistoryDB
from price_history_db import MarketHistoryDB


def test_clan_history_game_date_rollover():
    kyiv_tz = timezone(timedelta(hours=2))
    before_rollover = datetime(2026, 11, 24, 1, 59, tzinfo=kyiv_tz)
    after_rollover = datetime(2026, 11, 24, 2, 0, tzinfo=kyiv_tz)

    assert ClanHistoryDB.get_game_date(before_rollover) == "2026-11-23"
    assert ClanHistoryDB.get_game_date(after_rollover) == "2026-11-24"
    assert ClanHistoryDB.get_yesterday_game_date("2026-11-24") == "2026-11-23"


def test_clan_history_snapshot_and_damage_delta(tmp_path):
    db = ClanHistoryDB(db_path=tmp_path / "clan_test.db")
    game_date = "2026-11-24"

    # First snapshot sets baseline
    db.record_members_snapshot(
        [{"user_id": "u1", "username": "Alice", "total_damage": 1_000_000, "weekly_damage": 5_000_000}],
        game_date=game_date,
    )
    # Second snapshot updates latest
    db.record_members_snapshot(
        [{"user_id": "u1", "username": "Alice", "total_damage": 1_750_000, "weekly_damage": 5_750_000}],
        game_date=game_date,
    )

    stats = db.get_damage_stats("u1", current_total_dmg=1_900_000, current_weekly_dmg=5_900_000, game_date=game_date)
    assert stats["today_damage"] == 900_000
    assert stats["has_yesterday"] is False
    assert stats["yesterday_damage"] is None


def test_market_history_save_and_deduplicate(tmp_path):
    db = MarketHistoryDB(db_path=tmp_path / "market_test.db")
    now_iso = datetime.now(timezone.utc).isoformat()
    txs = [
        {
            "_id": "tx1",
            "itemCode": "sniper",
            "money": 40.0,
            "createdAt": now_iso,
            "item": {"code": "sniper", "state": 100, "skills": {"attack": 120, "criticalChance": 18}},
        },
        {
            "_id": "tx2",
            "itemCode": "sniper",
            "money": 50.0,
            "createdAt": now_iso,
            "item": {"code": "sniper", "state": 100, "skills": {"attack": 120, "criticalChance": 18}},
        },
    ]

    inserted = db.save_transactions(txs)
    assert inserted == 2

    # Duplicate insert should ignore existing IDs
    inserted_dup = db.save_transactions(txs)
    assert inserted_dup == 0

    summary = db.get_stat_price_summary("sniper", days=3)
    assert 120.0 in summary
    assert summary[120.0]["count"] == 2
    assert summary[120.0]["median"] == 45.0

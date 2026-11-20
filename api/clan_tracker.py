"""
Clan Tracker Service for WarEra Suite.
Handles periodic snapshots of clan members, battle damage, and combat activity.
Decoupled from the equipment market scanner.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger("WarEraClanTracker")


class ClanTrackerService:
    def __init__(self, interval_seconds: int = 900):
        self.interval = interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Runs periodic clan damage snapshot every `interval` seconds."""
        self.running = True
        logger.info(f"ClanTrackerService started (interval={self.interval}s).")
        # Initial sleep so we do not stress network or CPU during boot
        await asyncio.sleep(60)

        while self.running:
            try:
                from clan_analyzer import WarEraClanAnalyzer
                analyzer = WarEraClanAnalyzer()
                await analyzer.analyze_clan()
                logger.info("Clan damage snapshot successfully recorded.")
            except Exception as e:
                logger.warning(f"Error in clan damage snapshot: {e}")

            for _ in range(self.interval):
                if not self.running:
                    return
                await asyncio.sleep(1)

    def stop(self):
        """Stops the clan tracking loop."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("ClanTrackerService stopped.")


_tracker_instance: Optional[ClanTrackerService] = None


def get_clan_tracker() -> ClanTrackerService:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ClanTrackerService()
    return _tracker_instance

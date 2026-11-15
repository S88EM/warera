from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import statistics

from equipment_data import EQUIPMENT_METADATA, calculate_roll_quality
from price_history_db import MarketHistoryDB

# Допуски для порівняння характеристик (± відхилення)
STAT_TOLERANCES = {
    "attack": 3,
    "criticalChance": 1,
    "armor": 2,
    "dodge": 2,
    "precision": 2,
    "criticalDamages": 4,
}

# Мінімальна кількість порівнюваних пропозицій для надійного розрахунку медіани
MIN_COMPARABLE_OFFERS = 2


@dataclass
class EquipmentOpportunity:
    opp_type: str  # "MARKET_DISCOUNT" | "STAT_3D_DISCOUNT" | "FLOOR_UNDERCUT"
    offer_id: str
    item_code: str
    item_name: str
    rarity: str
    tier: int
    price: float
    reference_price: float
    discount_pct: float
    potential_profit: float
    skills: Dict[str, Any]
    roll_quality: float
    state: int
    user_id: str
    notes: str


class EquipmentAnalyzer:
    def __init__(
        self,
        min_discount_pct: float = 5.0,
        god_roll_threshold: float = 75.0,
        pricing_mode: str = "live",
        db: Optional[MarketHistoryDB] = None,
    ):
        self.min_discount_pct = min_discount_pct
        self.god_roll_threshold = god_roll_threshold
        self.pricing_mode = "history" if pricing_mode.lower() in ("history", "3d", "db", "історія") else "live"
        self.db = db or MarketHistoryDB()
        self.seen_offers = set()

    def set_pricing_mode(self, mode: str):
        self.pricing_mode = "history" if mode.lower() in ("history", "3d", "db", "історія") else "live"

    def is_offer_seen(self, offer_id: str) -> bool:
        return offer_id in self.seen_offers

    def mark_offer_seen(self, offer_id: str):
        self.seen_offers.add(offer_id)
        if len(self.seen_offers) > 5000:
            self.seen_offers.clear()

    @staticmethod
    def _exact_stats_match(skills1: dict, skills2: dict) -> bool:
        """Перевірка абсолютного збігу характеристик."""
        keys = set(skills1.keys()) | set(skills2.keys())
        if not keys:
            return False
        for k in keys:
            try:
                if float(skills1.get(k, 0)) != float(skills2.get(k, 0)):
                    return False
            except (ValueError, TypeError):
                return False
        return True

    @staticmethod
    def _similar_stats_match(skills1: dict, skills2: dict) -> bool:
        """Перевірка подібності характеристик у межах допуску."""
        keys = set(skills1.keys()) | set(skills2.keys())
        if not keys:
            return False
        for k in keys:
            try:
                v1 = float(skills1.get(k, 0))
                v2 = float(skills2.get(k, 0))
                tol = STAT_TOLERANCES.get(k, 2)
                if abs(v1 - v2) > tol:
                    return False
            except (ValueError, TypeError):
                return False
        return True

    def _find_comparable_offers(
        self, item_code: str, target_skills: dict, target_quality: float, all_offers: list, exclude_id: str
    ) -> Tuple[List[dict], str]:
        """
        Знаходить відкриті ордери на ринку для порівняння ціни за ієрархією:
        1. Точний збіг статів (Exact match)
        2. Схожі стати з допуском (Similar match)
        3. Схожа якість ролу ±10% (Roll tier match)
        """
        exact = []
        similar = []
        quality_matched = []

        for offer in all_offers:
            if offer.get("_id") == exclude_id:
                continue
            other_item = offer.get("item", {})
            other_skills = other_item.get("skills", {})

            if self._exact_stats_match(target_skills, other_skills):
                exact.append(offer)
            elif self._similar_stats_match(target_skills, other_skills):
                similar.append(offer)

            other_q = calculate_roll_quality(item_code, other_skills)
            if abs(other_q - target_quality) <= 10.0:
                quality_matched.append(offer)

        # 1. Точні збіги
        if len(exact) >= MIN_COMPARABLE_OFFERS:
            return exact, "точний збіг"

        # 2. Точні + схожі в межах допуску
        combined = exact + similar
        if len(combined) >= MIN_COMPARABLE_OFFERS:
            return combined, "схожі стати"

        # 3. Схожа загальна якість ролу
        if len(quality_matched) >= MIN_COMPARABLE_OFFERS:
            return quality_matched, "схожа якість ролу"

        # Недостатньо подібних пропозицій
        return [], "insufficient"

    @staticmethod
    def _format_stat_desc(skills: dict) -> str:
        """Форматує стати для компактного читабельного вигляду."""
        parts = []
        if "attack" in skills:
            parts.append(f"Atk {int(float(skills['attack']))}")
        if "criticalChance" in skills:
            parts.append(f"Crit {int(float(skills['criticalChance']))}%")
        if "armor" in skills:
            parts.append(f"Armor {int(float(skills['armor']))}")
        if "dodge" in skills:
            parts.append(f"Dodge {int(float(skills['dodge']))}")
        if "precision" in skills:
            parts.append(f"Prec {int(float(skills['precision']))}")
        if "criticalDamages" in skills:
            parts.append(f"CritDmg {int(float(skills['criticalDamages']))}")
        return ", ".join(parts) if parts else "без статів"

    def analyze_offers(
        self, item_code: str, offers: List[Dict[str, Any]]
    ) -> List[EquipmentOpportunity]:
        opportunities: List[EquipmentOpportunity] = []
        if not offers:
            return opportunities

        meta = EQUIPMENT_METADATA.get(item_code, {
            "name": item_code,
            "type": "item",
            "rarity": "unknown",
            "tier": 0
        })

        # Фільтруємо валідні пропозиції (ціна > 0, стан >= 90%)
        valid_offers = [
            o for o in offers
            if float(o.get("price", 0)) > 0
            and int(o.get("item", {}).get("state", 0)) >= 90
        ]
        if not valid_offers:
            return opportunities

        valid_offers.sort(key=lambda x: float(x.get("price", 0)))

        # 1. Оцінка вигідності згідно з обраним режимом (Історія чи Реальний час)
        if self.pricing_mode == "history":
            # --- РЕЖИМ: 3-денна історія завершених угод (Database) ---
            for offer in valid_offers[:10]:
                off_id = offer.get("_id", "")
                off_price = float(offer.get("price", 0.0))
                item_obj = offer.get("item", {})
                skills = item_obj.get("skills", {})
                state = item_obj.get("state", 100)
                roll_quality = calculate_roll_quality(item_code, skills)

                eval_res = self.db.get_stat_evaluation(item_code, skills, current_price=off_price, days=3)
                if eval_res and eval_res.get("is_cheap"):
                    discount = float(eval_res["discount_pct"])
                    profit = float(eval_res["profit"])
                    if discount >= self.min_discount_pct and profit >= 1.0:
                        top_badge = f"🌟 ТОП РОЛ ({roll_quality:.1f}% якості)! " if roll_quality >= self.god_roll_threshold else ""
                        note = (
                            f"{top_badge}{eval_res['verdict']}! [{eval_res['stat_desc']}] зазвичай коштує {eval_res['expected_price']:.2f} "
                            f"(медіана за 3 дні, {eval_res['sample_count']} угод). "
                            f"Виставлено за {off_price:.2f} (знижка {discount:.1f}%, вигода +{profit:.2f})"
                        )
                        opportunities.append(
                            EquipmentOpportunity(
                                opp_type="STAT_3D_DISCOUNT",
                                offer_id=off_id,
                                item_code=item_code,
                                item_name=meta["name"],
                                rarity=meta["rarity"],
                                tier=meta["tier"],
                                price=off_price,
                                reference_price=eval_res["expected_price"],
                                discount_pct=discount,
                                potential_profit=profit,
                                skills=skills,
                                roll_quality=roll_quality,
                                state=state,
                                user_id=offer.get("user", ""),
                                notes=note,
                            )
                        )
        else:
            # --- РЕЖИМ: Реальний час по відкритих ринкових ордерах (Live Orders) ---
            for offer in valid_offers[:10]:
                off_id = offer.get("_id", "")
                off_price = float(offer.get("price", 0.0))
                item_obj = offer.get("item", {})
                skills = item_obj.get("skills", {})
                state = item_obj.get("state", 100)
                roll_quality = calculate_roll_quality(item_code, skills)

                comparable, match_label = self._find_comparable_offers(
                    item_code, skills, roll_quality, valid_offers, off_id
                )

                if len(comparable) < MIN_COMPARABLE_OFFERS:
                    continue

                comparable_prices = [float(o.get("price", 0)) for o in comparable]
                median_price = round(statistics.median(comparable_prices), 2)

                if median_price <= off_price:
                    continue

                discount = ((median_price - off_price) / median_price) * 100.0
                profit = median_price - off_price

                if discount >= self.min_discount_pct and profit >= 1.0:
                    stat_desc = self._format_stat_desc(skills)
                    verdict = "🔥 ДУЖЕ ДЕШЕВО" if discount >= 15.0 else "💎 ДЕШЕВО"
                    top_badge = f"🌟 ТОП РОЛ ({roll_quality:.1f}% якості)! " if roll_quality >= self.god_roll_threshold else ""

                    note = (
                        f"{top_badge}{verdict}! [{stat_desc}] на ринку коштує {median_price:.2f} "
                        f"(медіана відкритих ордерів, {len(comparable)} шт, {match_label}). "
                        f"Виставлено за {off_price:.2f} (знижка {discount:.1f}%, вигода +{profit:.2f})"
                    )
                    opportunities.append(
                        EquipmentOpportunity(
                            opp_type="MARKET_DISCOUNT",
                            offer_id=off_id,
                            item_code=item_code,
                            item_name=meta["name"],
                            rarity=meta["rarity"],
                            tier=meta["tier"],
                            price=off_price,
                            reference_price=median_price,
                            discount_pct=round(discount, 1),
                            potential_profit=round(profit, 2),
                            skills=skills,
                            roll_quality=roll_quality,
                            state=state,
                            user_id=offer.get("user", ""),
                            notes=note,
                        )
                    )

        # 2. Демпінг мінімальної ціни (Floor Undercut): слот #0 vs слот #1
        cheapest = valid_offers[0]
        cheapest_id = cheapest.get("_id", "")
        cheapest_price = float(cheapest.get("price", 0.0))
        second_price = (
            float(valid_offers[1].get("price", 0.0))
            if len(valid_offers) > 1
            else cheapest_price
        )

        already_flagged = any(o.offer_id == cheapest_id for o in opportunities)
        if not already_flagged and second_price > cheapest_price:
            undercut_pct = ((second_price - cheapest_price) / second_price) * 100.0
            if undercut_pct >= self.min_discount_pct:
                item_obj = cheapest.get("item", {})
                skills = item_obj.get("skills", {})
                profit = second_price - cheapest_price
                if profit >= 1.0:
                    roll_q = calculate_roll_quality(item_code, skills)
                    top_badge = f"🌟 ТОП РОЛ ({roll_q:.1f}% якості)! " if roll_q >= self.god_roll_threshold else ""
                    opportunities.append(
                        EquipmentOpportunity(
                            opp_type="FLOOR_UNDERCUT",
                            offer_id=cheapest_id,
                            item_code=item_code,
                            item_name=meta["name"],
                            rarity=meta["rarity"],
                            tier=meta["tier"],
                            price=cheapest_price,
                            reference_price=second_price,
                            discount_pct=round(undercut_pct, 1),
                            potential_profit=round(profit, 2),
                            skills=skills,
                            roll_quality=roll_q,
                            state=item_obj.get("state", 100),
                            user_id=cheapest.get("user", ""),
                            notes=f"{top_badge}Демпінг мінімальної ціни! Дешевше за 2-й лот ({second_price:.2f}) на {undercut_pct:.1f}%",
                        )
                    )

        return opportunities

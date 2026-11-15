"""
Metadata and stat roll ranges for all WarEra weapons and equipment.
"""

EQUIPMENT_METADATA = {
    # Weapons
    "knife": {
        "name": "Ніж (Knife)",
        "type": "weapon",
        "rarity": "common",
        "tier": 1,
        "ranges": {"attack": [21, 40], "criticalChance": [1, 5]},
    },
    "gun": {
        "name": "Пістолет (Gun)",
        "type": "weapon",
        "rarity": "uncommon",
        "tier": 2,
        "ranges": {"attack": [51, 60], "criticalChance": [6, 10]},
    },
    "rifle": {
        "name": "Гвинтівка (Rifle)",
        "type": "weapon",
        "rarity": "rare",
        "tier": 3,
        "ranges": {"attack": [71, 90], "criticalChance": [11, 15]},
    },
    "sniper": {
        "name": "Снайперка (Sniper)",
        "type": "weapon",
        "rarity": "epic",
        "tier": 4,
        "ranges": {"attack": [101, 130], "criticalChance": [16, 20]},
    },
    "tank": {
        "name": "Танк (Tank)",
        "type": "weapon",
        "rarity": "legendary",
        "tier": 5,
        "ranges": {"attack": [141, 170], "criticalChance": [26, 35]},
    },
    "jet": {
        "name": "Винищувач (Jet)",
        "type": "weapon",
        "rarity": "mythic",
        "tier": 6,
        "ranges": {"attack": [221, 300], "criticalChance": [41, 50]},
    },
    # Helmets (Critical Damages)
    "helmet1": {"name": "Шолом I", "type": "helmet", "rarity": "common", "tier": 1, "ranges": {"criticalDamages": [1, 15]}},
    "helmet2": {"name": "Шолом II", "type": "helmet", "rarity": "uncommon", "tier": 2, "ranges": {"criticalDamages": [16, 30]}},
    "helmet3": {"name": "Шолом III", "type": "helmet", "rarity": "rare", "tier": 3, "ranges": {"criticalDamages": [31, 50]}},
    "helmet4": {"name": "Шолом IV", "type": "helmet", "rarity": "epic", "tier": 4, "ranges": {"criticalDamages": [71, 90]}},
    "helmet5": {"name": "Шолом V", "type": "helmet", "rarity": "legendary", "tier": 5, "ranges": {"criticalDamages": [91, 110]}},
    "helmet6": {"name": "Шолом VI", "type": "helmet", "rarity": "mythic", "tier": 6, "ranges": {"criticalDamages": [121, 150]}},
    # Chests (Armor)
    "chest1": {"name": "Броня I", "type": "chest", "rarity": "common", "tier": 1, "ranges": {"armor": [1, 5]}},
    "chest2": {"name": "Броня II", "type": "chest", "rarity": "uncommon", "tier": 2, "ranges": {"armor": [6, 10]}},
    "chest3": {"name": "Броня III", "type": "chest", "rarity": "rare", "tier": 3, "ranges": {"armor": [11, 15]}},
    "chest4": {"name": "Броня IV", "type": "chest", "rarity": "epic", "tier": 4, "ranges": {"armor": [21, 30]}},
    "chest5": {"name": "Броня V", "type": "chest", "rarity": "legendary", "tier": 5, "ranges": {"armor": [36, 50]}},
    "chest6": {"name": "Броня VI", "type": "chest", "rarity": "mythic", "tier": 6, "ranges": {"armor": [56, 70]}},
    # Pants (Armor)
    "pants1": {"name": "Штани I", "type": "pants", "rarity": "common", "tier": 1, "ranges": {"armor": [1, 5]}},
    "pants2": {"name": "Штани II", "type": "pants", "rarity": "uncommon", "tier": 2, "ranges": {"armor": [6, 10]}},
    "pants3": {"name": "Штани III", "type": "pants", "rarity": "rare", "tier": 3, "ranges": {"armor": [11, 15]}},
    "pants4": {"name": "Штани IV", "type": "pants", "rarity": "epic", "tier": 4, "ranges": {"armor": [21, 30]}},
    "pants5": {"name": "Штани V", "type": "pants", "rarity": "legendary", "tier": 5, "ranges": {"armor": [36, 50]}},
    "pants6": {"name": "Штани VI", "type": "pants", "rarity": "mythic", "tier": 6, "ranges": {"armor": [56, 70]}},
    # Boots (Dodge)
    "boots1": {"name": "Чоботи I", "type": "boots", "rarity": "common", "tier": 1, "ranges": {"dodge": [1, 5]}},
    "boots2": {"name": "Чоботи II", "type": "boots", "rarity": "uncommon", "tier": 2, "ranges": {"dodge": [6, 10]}},
    "boots3": {"name": "Чоботи III", "type": "boots", "rarity": "rare", "tier": 3, "ranges": {"dodge": [11, 15]}},
    "boots4": {"name": "Чоботи IV", "type": "boots", "rarity": "epic", "tier": 4, "ranges": {"dodge": [21, 25]}},
    "boots5": {"name": "Чоботи V", "type": "boots", "rarity": "legendary", "tier": 5, "ranges": {"dodge": [31, 40]}},
    "boots6": {"name": "Чоботи VI", "type": "boots", "rarity": "mythic", "tier": 6, "ranges": {"dodge": [51, 60]}},
    # Gloves (Precision)
    "gloves1": {"name": "Рукавиці I", "type": "gloves", "rarity": "common", "tier": 1, "ranges": {"precision": [1, 5]}},
    "gloves2": {"name": "Рукавиці II", "type": "gloves", "rarity": "uncommon", "tier": 2, "ranges": {"precision": [6, 10]}},
    "gloves3": {"name": "Рукавиці III", "type": "gloves", "rarity": "rare", "tier": 3, "ranges": {"precision": [11, 15]}},
    "gloves4": {"name": "Рукавиці IV", "type": "gloves", "rarity": "epic", "tier": 4, "ranges": {"precision": [21, 25]}},
    "gloves5": {"name": "Рукавиці V", "type": "gloves", "rarity": "legendary", "tier": 5, "ranges": {"precision": [31, 40]}},
    "gloves6": {"name": "Рукавиці VI", "type": "gloves", "rarity": "mythic", "tier": 6, "ranges": {"precision": [51, 60]}},
}

def calculate_roll_quality(item_code: str, skills: dict) -> float:
    """Calculate overall roll quality percentage (0% to 100%) for an item."""
    meta = EQUIPMENT_METADATA.get(item_code)
    if not meta or not meta.get("ranges"):
        return 50.0

    qualities = []
    for stat_name, (min_val, max_val) in meta["ranges"].items():
        val = skills.get(stat_name, min_val)
        if max_val == min_val:
            qualities.append(100.0)
        else:
            q = (val - min_val) / (max_val - min_val) * 100.0
            qualities.append(max(0.0, min(100.0, q)))

    return round(sum(qualities) / len(qualities), 1) if qualities else 50.0


def get_item_image_url(item_code: str) -> str:
    """Get the official WarEra CDN image URL for an item code."""
    base = item_code
    for prefix in ("boots", "helmet", "chest", "pants", "gloves"):
        if item_code.startswith(prefix):
            base = prefix
            break
    return f"https://media.warera.io/images/itemsv2/{base}.png"


RARITY_CONFIG = {
    "mythic": {"name": "Міфічний", "emoji": "🔴", "color": "Червоний"},
    "legendary": {"name": "Легендарний", "emoji": "🟡", "color": "Золотий"},
    "epic": {"name": "Елітний", "emoji": "🟣", "color": "Фіолетовий"},
    "rare": {"name": "Поліпшений", "emoji": "🔵", "color": "Синій"},
    "uncommon": {"name": "Незвичайний", "emoji": "🟢", "color": "Зелений"},
    "common": {"name": "Звичайний", "emoji": "⚪", "color": "Сірий"},
}

ITEM_ICONS = {
    # Weapons
    "jet": "🛩",
    "tank": "🛡",
    "sniper": "🎯",
    "rifle": "🔫",
    "gun": "🔫",
    "knife": "🗡",
    # Equipment types
    "helmet": "🪖",
    "chest": "🦺",
    "gloves": "🧤",
    "pants": "👖",
    "boots": "👢",
}

COMMODITY_ICONS = {
    "steel": "🔩",
    "ammo": "💥",
    "heavyAmmo": "💥",
    "lightAmmo": "💥",
    "bread": "🍞",
    "grain": "🌾",
    "oil": "🛢",
    "iron": "⛏",
    "wood": "🪵",
    "concrete": "🧱",
    "gold": "🪙",
    "fish": "🐟",
    "cookedFish": "🐟",
    "steak": "🥩",
    "livestock": "🐄",
    "lead": "⚙️",
    "limestone": "🪨",
    "coca": "🌿",
    "cocain": "🧪",
    "petroleum": "⛽",
    "scraps": "⚙️",
    "paper": "📄",
    "case1": "📦",
    "case2": "📦",
    "woodenCase": "📦",
}

def get_item_icon(item_code: str) -> str:
    """Return an emoji icon for the item or commodity."""
    if item_code in ITEM_ICONS:
        return ITEM_ICONS[item_code]
    for prefix in ("boots", "helmet", "chest", "pants", "gloves"):
        if item_code.startswith(prefix):
            return ITEM_ICONS[prefix]
    return COMMODITY_ICONS.get(item_code, "📦")

def get_rarity_info(rarity: str) -> dict:
    """Return dictionary with Ukrainian name and emoji color for rarity."""
    return RARITY_CONFIG.get(rarity.lower(), {
        "name": rarity.capitalize(),
        "emoji": "⚪",
        "color": "Сірий"
    })


# --- Quality / Rarity Tiers Definition ---
QUALITY_TIERS = {
    "mythic": {
        "tier": 6,
        "name": "Міфічний",
        "label": "Міфічні (Т6)",
        "emoji": "🔴",
        "items": ["jet", "helmet6", "chest6", "pants6", "boots6", "gloves6"],
    },
    "legendary": {
        "tier": 5,
        "name": "Легендарний",
        "label": "Легендарні (Т5)",
        "emoji": "🟡",
        "items": ["tank", "helmet5", "chest5", "pants5", "boots5", "gloves5"],
    },
    "epic": {
        "tier": 4,
        "name": "Елітний",
        "label": "Елітні (Т4)",
        "emoji": "🟣",
        "items": ["sniper", "helmet4", "chest4", "pants4", "boots4", "gloves4"],
    },
    "rare": {
        "tier": 3,
        "name": "Поліпшений",
        "label": "Поліпшені (Т3)",
        "emoji": "🔵",
        "items": ["rifle", "helmet3", "chest3", "pants3", "boots3", "gloves3"],
    },
    "uncommon": {
        "tier": 2,
        "name": "Незвичайний",
        "label": "Незвичайні (Т2)",
        "emoji": "🟢",
        "items": ["gun", "helmet2", "chest2", "pants2", "boots2", "gloves2"],
    },
    "common": {
        "tier": 1,
        "name": "Звичайний",
        "label": "Звичайні (Т1)",
        "emoji": "⚪",
        "items": ["knife", "helmet1", "chest1", "pants1", "boots1", "gloves1"],
    },
}

ALL_QUALITIES = ["mythic", "legendary", "epic", "rare", "uncommon", "common"]
DEFAULT_ACTIVE_QUALITIES = ["mythic", "legendary", "epic", "rare"]

QUALITY_ALIASES = {
    "mythic": "mythic", "t6": "mythic", "т6": "mythic", "6": "mythic", "міфічний": "mythic", "міфічні": "mythic", "мифический": "mythic", "миф": "mythic", "red": "mythic", "червоний": "mythic",
    "legendary": "legendary", "t5": "legendary", "т5": "legendary", "5": "legendary", "легендарний": "legendary", "легендарні": "legendary", "легендарный": "legendary", "лег": "legendary", "gold": "legendary", "золотий": "legendary",
    "epic": "epic", "t4": "epic", "т4": "epic", "4": "epic", "елітний": "epic", "елітні": "epic", "епічний": "epic", "эпический": "epic", "епік": "epic", "purple": "epic", "фіолетовий": "epic",
    "rare": "rare", "t3": "rare", "т3": "rare", "3": "rare", "поліпшений": "rare", "поліпшені": "rare", "рідкісний": "rare", "редкий": "rare", "рар": "rare", "blue": "rare", "синій": "rare",
    "uncommon": "uncommon", "t2": "uncommon", "т2": "uncommon", "2": "uncommon", "незвичайний": "uncommon", "незвичайні": "uncommon", "необычный": "uncommon", "анкоммон": "uncommon", "green": "uncommon", "зелений": "uncommon",
    "common": "common", "t1": "common", "т1": "common", "1": "common", "звичайний": "common", "звичайні": "common", "обычный": "common", "коммон": "common", "white": "common", "сірий": "common",
}

def normalize_quality_key(raw: str) -> str:
    """Resolve quality key from alias, name or tier."""
    if not raw:
        return ""
    clean = raw.strip().lower().lstrip("/")
    return QUALITY_ALIASES.get(clean, "")

def get_items_for_qualities(qualities: list) -> list:
    """Return all item codes corresponding to the specified active qualities in order."""
    items = []
    seen = set()
    for q in ALL_QUALITIES:
        if q in qualities and q in QUALITY_TIERS:
            for item in QUALITY_TIERS[q]["items"]:
                if item not in seen:
                    items.append(item)
                    seen.add(item)
    return items



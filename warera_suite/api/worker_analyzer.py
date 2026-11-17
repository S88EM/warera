"""
WarEra Worker & Factory Economic Analyzer.
Analyzes owner's factories, employee workforce, wage profitability,
margin per PP, relocation recommendations, and retirement risks.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import httpx

# Ensure api directory is in path
CURRENT_DIR = Path(__file__).parent.resolve()
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import config

logger = logging.getLogger("WarEraWorkerAnalyzer")


@dataclass
class ItemEconomics:
    code: str
    name: str
    item_type: str  # 'raw' or 'product'
    pp_per_item: float
    market_price: float
    raw_needs: Dict[str, float]
    raw_cost: float
    unit_margin: float
    margin_per_pp: float


@dataclass
class EmployeeAnalysis:
    employee_id: str
    name: str
    gender: str
    age: int
    company_id: str
    company_name: str
    item_code: str
    base_prod: float
    trained_prod: float
    total_prod: float
    hourly_pp: float
    daily_pp: float
    wage: float
    daily_wage: float
    hourly_gross_rev: float
    hourly_raw_cost: float
    hourly_net_profit: float
    daily_net_profit: float
    breakeven_wage: float
    profit_margin_pct: float
    spec_days: int
    bonus_total_pct: float
    bonus_contributions: List[Dict[str, Any]]
    tool_name: Optional[str]
    tool_bonus_pct: float
    tool_state_pct: float
    retire_in_days: int
    quit_chance: float
    potential: int = 0
    potential_max: int = 0
    happiness: float = 50.0
    traits: List[Dict[str, Any]] = field(default_factory=list)
    trained_stats: Dict[str, Any] = field(default_factory=dict)
    wage_expectation: float = 0.0
    trainings_left: int = 0
    specializations: Dict[str, int] = field(default_factory=dict)
    nationality: str = ""
    status: str = "KEEP"  # 'TOXIC', 'RELOCATE', 'UNDERPERFORMER', 'KEEP'
    recommendation: str = ""
    relocation_target: Optional[Dict[str, Any]] = None


@dataclass
class CompanyAnalysis:
    company_id: str
    name: str
    item_code: str
    region_id: str
    region_name: str = ""
    country_name: str = ""
    country_code: str = ""
    is_full: bool = False
    upgrades: Dict[str, int] = field(default_factory=dict)
    staff_count: int = 0
    staff_cap: int = 0
    hourly_pp: float = 0.0
    daily_pp: float = 0.0
    hourly_units: float = 0.0
    daily_units: float = 0.0
    engine_daily_pp: float = 0.0
    engine_daily_units: float = 0.0
    total_daily_pp: float = 0.0
    total_daily_units: float = 0.0
    employees_share_pct: float = 0.0
    engine_share_pct: float = 0.0
    hourly_revenue: float = 0.0
    hourly_raw_cost: float = 0.0
    hourly_wage_cost: float = 0.0
    hourly_net_profit: float = 0.0
    daily_net_profit: float = 0.0
    goods_value_daily: float = 0.0
    wages_daily: float = 0.0
    raw_cost_daily: float = 0.0
    in_game_profit: float = 0.0
    self_work_daily_net: float = 0.0
    net_daily_with_self_work: float = 0.0
    raw_from_own: bool = False
    taxes: Dict[str, int] = field(default_factory=dict)
    avg_wage: float = 0.0
    recommended_max_wage: float = 0.0
    employees: List[EmployeeAnalysis] = field(default_factory=list)


FALLBACK_COMMUNITY_KEYS = [
    "wae_0e8535186c34523a7d92eeda045bf116b77eb770fc0e9777cb6b093355880383",
    "wae_548fbf5cf22fd5f2b4f952338c66aba2aca3fbca930004caaf6cd1ee012c9e58",
]
_cached_community_keys: Optional[List[str]] = None


async def fetch_community_keys() -> List[str]:
    """Fetch public community API keys from Arcana Era pool, with fallback."""
    global _cached_community_keys
    if _cached_community_keys:
        return _cached_community_keys
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get("https://arcana.warera.wiki/api/keys")
            if r.status_code == 200:
                data = r.json()
                keys = data.get("keys", [])
                if keys:
                    _cached_community_keys = keys
                    return keys
    except Exception as e:
        logger.debug(f"Failed to fetch community keys from Arcana: {e}")
    return list(FALLBACK_COMMUNITY_KEYS)


class WarEraWorkerAnalyzer:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.user_api_key = (api_key or config.get_api_key()).strip()
        self.api_key = self.user_api_key
        self.is_community_key: bool = False
        self.community_fallback_enabled: bool = True
        self._community_keys: List[str] = list(FALLBACK_COMMUNITY_KEYS)

        # If user didn't provide a key, use community key right away
        if not self.api_key:
            self.api_key = self._community_keys[0]
            self.is_community_key = True

        self.base_url = (base_url or config.API_BASE_URL).rstrip("/")
        self.proxy_url = "https://gateway.warerastats.io/trpc"
        
        self.auth_failed: bool = False
        self.auth_error_msg: str = ""
        self._client: Optional[httpx.AsyncClient] = None
        self._cached_config: Optional[Dict[str, Any]] = None
        self._cached_prices: Optional[Dict[str, float]] = None
        self._cached_regions: Optional[Dict[str, Any]] = None
        self._cached_countries: Optional[List[Dict[str, Any]]] = None

    def _get_headers(self, key_override: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "WarEraWorkerSuite/1.0",
        }
        active_key = key_override or self.api_key
        if active_key:
            # Use ONLY lowercase 'x-api-key' to avoid duplicate header conflicts in WarEra API
            headers["x-api-key"] = active_key
        return headers

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=30)
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call_trpc(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, use_proxy_fallback: bool = True) -> Any:
        client = await self.get_client()
        input_param = json.dumps(payload or {})
        primary_url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers(self.api_key)

        # Try with current active key
        try:
            r = await client.get(primary_url, params={"input": input_param}, headers=headers)
            if r.status_code == 200:
                data = r.json()
                if "result" in data:
                    return data["result"].get("data")
            elif r.status_code == 401:
                # If personal key returned 401, automatically fallback to community keys!
                if self.community_fallback_enabled and not self.is_community_key:
                    logger.info(f"User API key rejected (401) for {endpoint}. Falling back to community keys...")
                    remote_keys = await fetch_community_keys()
                    all_c_keys = list(dict.fromkeys(remote_keys + FALLBACK_COMMUNITY_KEYS))
                    for c_key in all_c_keys:
                        try:
                            r_comm = await client.get(primary_url, params={"input": input_param}, headers=self._get_headers(c_key))
                            if r_comm.status_code == 200:
                                data = r_comm.json()
                                if "result" in data:
                                    self.api_key = c_key
                                    self.is_community_key = True
                                    self.auth_failed = False
                                    logger.info(f"Successfully switched to community key for {endpoint}")
                                    return data["result"].get("data")
                        except Exception:
                            pass
                
                self.auth_failed = True
                try:
                    err_json = r.json()
                    self.auth_error_msg = err_json.get("error", {}).get("message", "API token required (401)")
                except Exception:
                    self.auth_error_msg = "API token required (401)"
                logger.warning(f"WarEra API returned 401 for {endpoint}: {self.auth_error_msg}")
            elif r.status_code == 403:
                logger.warning(f"WarEra API returned 403 Forbidden for {endpoint}")
        except Exception as e:
            logger.debug(f"Direct call failed for {endpoint}: {e}")

        # If primary failed with 401 and we haven't tried community key yet
        if self.community_fallback_enabled and self.auth_failed and not self.is_community_key:
            remote_keys = await fetch_community_keys()
            for c_key in remote_keys + FALLBACK_COMMUNITY_KEYS:
                try:
                    r_comm = await client.get(primary_url, params={"input": input_param}, headers=self._get_headers(c_key))
                    if r_comm.status_code == 200:
                        data = r_comm.json()
                        if "result" in data:
                            self.api_key = c_key
                            self.is_community_key = True
                            self.auth_failed = False
                            return data["result"].get("data")
                except Exception:
                    pass

        # Try proxy fallback if applicable
        if use_proxy_fallback:
            proxy_url = f"{self.proxy_url}/{endpoint}"
            try:
                r2 = await client.get(proxy_url, params={"input": input_param}, headers=headers)
                if r2.status_code == 200:
                    data = r2.json()
                    if "result" in data:
                        return data["result"].get("data")
            except Exception as e:
                logger.debug(f"Proxy call failed for {endpoint}: {e}")

        return None

    async def get_game_config(self) -> Dict[str, Any]:
        if self._cached_config is None:
            data = await self._call_trpc("gameConfig.getGameConfig", {})
            self._cached_config = data or {}
        return self._cached_config

    async def get_market_prices(self) -> Dict[str, float]:
        if self._cached_prices is None:
            data = await self._call_trpc("itemTrading.getPrices", {})
            self._cached_prices = data or {}
        return self._cached_prices

    async def get_regions(self) -> Dict[str, Any]:
        if self._cached_regions is None:
            data = await self._call_trpc("region.getRegionsObject", {})
            self._cached_regions = data or {}
        return self._cached_regions

    async def get_countries(self) -> List[Dict[str, Any]]:
        if self._cached_countries is None:
            data = await self._call_trpc("country.getAllCountries", {})
            self._cached_countries = data or []
        return self._cached_countries

    async def find_user_by_name(self, nickname: str) -> Optional[Dict[str, Any]]:
        """Search user by username or nick and return their user object."""
        search_res = await self._call_trpc("search.searchAnything", {"searchText": nickname})
        if not search_res:
            return None
        
        user_ids = search_res.get("userIds", [])
        if not user_ids:
            return None
        
        # Fetch first matched user
        for uid in user_ids:
            u_data = await self._call_trpc("user.getUserById", {"userId": uid})
            if u_data and u_data.get("username", "").lower() == nickname.lower():
                return u_data
        
        # Fallback to first user
        return await self._call_trpc("user.getUserById", {"userId": user_ids[0]})

    async def get_owner_user_id(self) -> Optional[str]:
        """Detect the user ID of the current API key owner from their workforce."""
        workforce = await self._call_trpc("employee.getMyEmployees", {})
        if workforce and len(workforce) > 0:
            return workforce[0].get("owner")
        return None

    def compute_item_economics(self, item_code: str, items_cfg: Dict[str, Any], prices: Dict[str, float]) -> ItemEconomics:
        info = items_cfg.get(item_code, {})
        item_type = info.get("type", "raw")
        pp_per_item = float(info.get("productionPoints", 1.0))
        if pp_per_item <= 0:
            pp_per_item = 1.0

        market_price = float(prices.get(item_code, 0.0))
        raw_needs = info.get("productionNeeds", {})
        
        raw_cost = 0.0
        for raw_k, needed_qty in raw_needs.items():
            raw_cost += float(prices.get(raw_k, 0.0)) * float(needed_qty)

        unit_margin = market_price - raw_cost
        margin_per_pp = unit_margin / pp_per_item

        return ItemEconomics(
            code=item_code,
            name=info.get("name", item_code.capitalize()),
            item_type=item_type,
            pp_per_item=pp_per_item,
            market_price=market_price,
            raw_needs=raw_needs,
            raw_cost=raw_cost,
            unit_margin=unit_margin,
            margin_per_pp=margin_per_pp
        )

    async def analyze_user(self, nickname_or_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main analysis method. Resolves user, all their companies,
        rosters, prices, profit metrics, relocation opportunities, and recommendations.
        """
        # 1. Fetch game config & prices concurrently
        cfg_task = asyncio.create_task(self.get_game_config())
        prices_task = asyncio.create_task(self.get_market_prices())
        reg_task = asyncio.create_task(self.get_regions())
        country_task = asyncio.create_task(self.get_countries())
        cfg, prices, regions_obj, countries_list = await asyncio.gather(cfg_task, prices_task, reg_task, country_task)
        items_cfg = cfg.get("items", {})
        country_dict = {c.get("_id"): c for c in (countries_list or []) if isinstance(c, dict)}
        country_map = {cid: c.get("name", "Україна") for cid, c in country_dict.items()}

        # 2. Resolve user
        user_data = None
        user_id = None

        if nickname_or_id:
            # Check if it looks like a 24-char ObjectId
            if len(nickname_or_id) == 24 and all(c in "0123456789abcdefABCDEF" for c in nickname_or_id):
                user_data = await self._call_trpc("user.getUserById", {"userId": nickname_or_id})
                if user_data:
                    user_id = user_data.get("_id")

            if not user_data:
                user_data = await self.find_user_by_name(nickname_or_id)
                if user_data:
                    user_id = user_data.get("_id")

        if not user_id:
            # Autodetect from key
            user_id = await self.get_owner_user_id()
            if user_id:
                user_data = await self._call_trpc("user.getUserById", {"userId": user_id})

        if not user_id or not user_data:
            raise ValueError(f"Гравець '{nickname_or_id}' не знайдений або API-токен не має доступу.")

        username = user_data.get("username", "Unknown")

        # 3. Fetch user companies
        companies_res = await self._call_trpc("company.getCompanies", {"userId": user_id})
        comp_ids = companies_res.get("items", []) if isinstance(companies_res, dict) else (companies_res or [])

        # 4. Fetch details for all companies
        async def fetch_comp_data(cid: str) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
            c_info = await self._call_trpc("company.getById", {"companyId": cid})
            c_roster = await self._call_trpc("employee.getCompanyRoster", {"companyId": cid})
            return cid, c_info, c_roster

        comp_tasks = [fetch_comp_data(cid) for cid in comp_ids]
        raw_companies = await asyncio.gather(*comp_tasks)

        # 5. Build Item Economics Cache for all factory items
        item_econ_cache: Dict[str, ItemEconomics] = {}
        user_items = set()
        for _, c_info, _ in raw_companies:
            if c_info:
                icode = c_info.get("itemCode", "")
                if icode:
                    user_items.add(icode)
                if icode and icode not in item_econ_cache:
                    item_econ_cache[icode] = self.compute_item_economics(icode, items_cfg, prices)

        # 6. First pass: Collect all companies and basic employee data
        companies_list: List[CompanyAnalysis] = []
        all_employees: List[EmployeeAnalysis] = []

        for cid, c_info, c_roster in raw_companies:
            if not c_info:
                continue

            c_name = c_info.get("name", "Unknown")
            item_code = c_info.get("itemCode", "unknown")
            region_id = c_info.get("region", "")
            is_full = c_info.get("isFull", False)
            upgrades = c_info.get("activeUpgradeLevels", {})

            item_econ = item_econ_cache.get(item_code)
            if not item_econ:
                item_econ = self.compute_item_economics(item_code, items_cfg, prices)
                item_econ_cache[item_code] = item_econ

            roster_emps = c_roster.get("employees", []) if c_roster else []
            roster_hourly = c_roster.get("hourly", {}) if c_roster else {}

            reg_info = regions_obj.get(region_id, {}) if isinstance(regions_obj, dict) else {}
            reg_name = reg_info.get("name", "Україна")
            c_country_id = reg_info.get("country", "")
            c_country_obj = country_dict.get(c_country_id, {})
            c_country_name = c_country_obj.get("name", "Україна")
            c_country_code = c_country_obj.get("code", "ua")
            c_country_taxes = c_country_obj.get("taxes", {"income": 20, "market": 0, "manager": 0})

            comp_analysis = CompanyAnalysis(
                company_id=cid,
                name=c_name,
                item_code=item_code,
                region_id=region_id,
                region_name=reg_name,
                country_name=c_country_name,
                country_code=c_country_code,
                is_full=is_full,
                upgrades=upgrades,
                taxes=c_country_taxes,
                staff_count=len(roster_emps),
                staff_cap=int(roster_hourly.get("cap", len(roster_emps))),
                hourly_pp=0.0,
                daily_pp=0.0,
                hourly_units=0.0,
                daily_units=0.0,
                engine_daily_pp=0.0,
                engine_daily_units=0.0,
                total_daily_pp=0.0,
                total_daily_units=0.0,
                employees_share_pct=0.0,
                engine_share_pct=0.0,
                hourly_revenue=0.0,
                hourly_raw_cost=0.0,
                hourly_wage_cost=0.0,
                hourly_net_profit=0.0,
                daily_net_profit=0.0,
                goods_value_daily=0.0,
                wages_daily=0.0,
                raw_cost_daily=0.0,
                in_game_profit=0.0,
                self_work_daily_net=0.0,
                net_daily_with_self_work=0.0,
                raw_from_own=False,
                avg_wage=0.0,
                recommended_max_wage=0.0,
                employees=[]
            )

            for emp in roster_emps:
                emp_id = emp.get("_id", "")
                ename = emp.get("name", "Worker")
                egender = emp.get("gender", "unknown")
                eage = emp.get("age", 0)
                ewage = float(emp.get("wage", 0.0))
                
                base_prod = float(emp.get("base", {}).get("production", 0.0))
                trained_prod = float(emp.get("trained", {}).get("production", 0.0))
                total_prod = base_prod + trained_prod

                e_est = emp.get("estimate", {})
                hourly_pp = float(e_est.get("production", 0.0))
                daily_pp = hourly_pp * 24.0

                # Production outputs
                hourly_units = hourly_pp / item_econ.pp_per_item
                hourly_gross_rev = hourly_units * item_econ.market_price
                hourly_raw_cost = hourly_units * item_econ.raw_cost
                hourly_net_profit = (hourly_units * item_econ.unit_margin) - ewage
                daily_net_profit = hourly_net_profit * 24.0

                breakeven_wage = hourly_units * item_econ.unit_margin
                profit_margin_pct = (hourly_net_profit / hourly_gross_rev * 100.0) if hourly_gross_rev > 0 else 0.0

                # Specialization & loyalty
                specs = emp.get("specializations", {})
                spec_days = int(specs.get(item_code, 0))

                # Bonuses
                prod_bonus_obj = emp.get("productionBonus", {})
                bonus_total_pct = float(prod_bonus_obj.get("total", 0.0))
                bonus_contribs = prod_bonus_obj.get("contributions", [])

                # Tool status
                t_item = emp.get("toolItem")
                t_status = emp.get("toolStatus", {})
                tool_name = t_item.get("code") if t_item else None
                tool_bonus_pct = float(t_status.get("bonusPercent", 0.0))
                tool_state_pct = float(t_item.get("state", 0.0)) if t_item else 0.0

                # Risks & Extra fields
                retire_in_days = int(emp.get("retireInDays", 999))
                quit_chance = float(emp.get("happinessBreakdown", {}).get("quitChance", 0.0))
                potential = int(emp.get("potential", 0))
                potential_max = int(emp.get("potentialMax", 0))
                happiness = float(emp.get("happinessBreakdown", {}).get("value", 50.0))
                traits = emp.get("traits", [])
                trained_stats = emp.get("trained", {})
                wage_expectation = float(emp.get("wageExpectation", 0.0))
                trainings_per_day = int(emp.get("trainingsPerDay", 1))
                trainings_today = int(emp.get("trainingsToday", 0))
                trainings_left = max(0, trainings_per_day - trainings_today)
                specializations = emp.get("specializations", {})
                nationality = emp.get("nationality", "")

                emp_analysis = EmployeeAnalysis(
                    employee_id=emp_id,
                    name=ename,
                    gender=egender,
                    age=eage,
                    company_id=cid,
                    company_name=c_name,
                    item_code=item_code,
                    base_prod=base_prod,
                    trained_prod=trained_prod,
                    total_prod=total_prod,
                    hourly_pp=hourly_pp,
                    daily_pp=daily_pp,
                    wage=ewage,
                    daily_wage=ewage * 24.0,
                    hourly_gross_rev=hourly_gross_rev,
                    hourly_raw_cost=hourly_raw_cost,
                    hourly_net_profit=hourly_net_profit,
                    daily_net_profit=daily_net_profit,
                    breakeven_wage=breakeven_wage,
                    profit_margin_pct=profit_margin_pct,
                    spec_days=spec_days,
                    bonus_total_pct=bonus_total_pct,
                    bonus_contributions=bonus_contribs,
                    tool_name=tool_name,
                    tool_bonus_pct=tool_bonus_pct,
                    tool_state_pct=tool_state_pct,
                    retire_in_days=retire_in_days,
                    quit_chance=quit_chance,
                    potential=potential,
                    potential_max=potential_max,
                    happiness=happiness,
                    traits=traits,
                    trained_stats=trained_stats,
                    wage_expectation=wage_expectation,
                    trainings_left=trainings_left,
                    specializations=specializations,
                    nationality=nationality,
                    status="KEEP",
                    recommendation=""
                )

                comp_analysis.employees.append(emp_analysis)
                all_employees.append(emp_analysis)

                comp_analysis.hourly_pp += hourly_pp
                comp_analysis.hourly_units += hourly_units
                comp_analysis.hourly_revenue += hourly_gross_rev
                comp_analysis.hourly_raw_cost += hourly_raw_cost
                comp_analysis.hourly_wage_cost += ewage
                comp_analysis.hourly_net_profit += hourly_net_profit

            # Engine & daily metrics
            engine_level = int(upgrades.get("automatedEngine", 0))
            engine_daily_pp = float(engine_level * 24.0)
            engine_daily_units = (engine_daily_pp / item_econ.pp_per_item) if item_econ.pp_per_item > 0 else 0.0

            staff_daily_pp = comp_analysis.hourly_pp * 24.0
            staff_daily_units = comp_analysis.hourly_units * 24.0

            total_daily_pp = staff_daily_pp + engine_daily_pp
            total_daily_units = staff_daily_units + engine_daily_units

            employees_share_pct = round((staff_daily_pp / total_daily_pp * 100), 1) if total_daily_pp > 0 else 0.0
            engine_share_pct = round(100.0 - employees_share_pct, 1)

            # Check if raw supplies are produced by player's other factories
            raw_needs = item_econ.raw_needs or {}
            raw_from_own = bool(raw_needs and any(req in user_items for req in raw_needs))

            goods_value_daily = total_daily_units * item_econ.market_price
            wages_daily = comp_analysis.hourly_wage_cost * 24.0
            raw_cost_daily = total_daily_units * item_econ.raw_cost

            daily_net_profit = goods_value_daily - wages_daily - (0.0 if raw_from_own else raw_cost_daily)
            in_game_employee_profit = (staff_daily_units * item_econ.market_price) - wages_daily

            # Self work calculation
            user_prod_skill = user_data.get("skills", {}).get("production", {})
            user_prod_val = float(user_prod_skill.get("value", 50))
            self_work_pp = user_prod_val + (user_prod_skill.get("level", 0) * 1.0)
            self_work_daily_net = (self_work_pp / item_econ.pp_per_item) * item_econ.unit_margin if item_econ.pp_per_item > 0 else 0.0
            net_daily_with_self_work = daily_net_profit + self_work_daily_net

            comp_analysis.engine_daily_pp = engine_daily_pp
            comp_analysis.engine_daily_units = engine_daily_units
            comp_analysis.total_daily_pp = total_daily_pp
            comp_analysis.total_daily_units = total_daily_units
            comp_analysis.employees_share_pct = employees_share_pct
            comp_analysis.engine_share_pct = engine_share_pct
            comp_analysis.daily_pp = staff_daily_pp
            comp_analysis.daily_units = staff_daily_units
            comp_analysis.goods_value_daily = goods_value_daily
            comp_analysis.wages_daily = wages_daily
            comp_analysis.raw_cost_daily = raw_cost_daily
            comp_analysis.daily_net_profit = daily_net_profit
            comp_analysis.in_game_profit = in_game_employee_profit
            comp_analysis.self_work_daily_net = self_work_daily_net
            comp_analysis.net_daily_with_self_work = net_daily_with_self_work
            comp_analysis.raw_from_own = raw_from_own

            if comp_analysis.staff_count > 0:
                comp_analysis.avg_wage = comp_analysis.hourly_wage_cost / comp_analysis.staff_count
                comp_analysis.recommended_max_wage = (comp_analysis.hourly_pp * item_econ.margin_per_pp) / comp_analysis.staff_count

            companies_list.append(comp_analysis)

        # 7. Second pass: Decision Engine (Categorization & Relocation analysis)
        # Find factories with best margin per PP
        sorted_factories_by_margin = sorted(
            [c for c in companies_list if c.staff_count < c.staff_cap or c.staff_count < 4],
            key=lambda c: item_econ_cache[c.item_code].margin_per_pp,
            reverse=True
        )

        for emp in all_employees:
            current_econ = item_econ_cache[emp.item_code]

            # Scenario 1: TOXIC
            if emp.hourly_net_profit <= 0:
                emp.status = "TOXIC"
                emp.recommendation = (
                    f"🚨 ЗБИТКОВИЙ: Зарплата ({emp.wage:.4f}) перевищує вартість продукції ({emp.breakeven_wage:.4f}). "
                    f"Негайно звільнити або знизити ставку нижче {emp.breakeven_wage * 0.85:.4f} Coins/год."
                )
                continue

            # Scenario 2: UNDERPERFORMER (Retirement or Quit risk or Low production)
            if emp.retire_in_days <= 4:
                emp.status = "UNDERPERFORMER"
                emp.recommendation = (
                    f"⚠️ ПЕНСІЯ ЧЕРЕЗ {emp.retire_in_days} ДН.: Працівник скоро завершує кар'єру. "
                    f"Підготуйте заміну на ринку праці заздалегідь, щоб уникнути простою фабрики."
                )
                continue

            if emp.quit_chance >= 8.0:
                emp.status = "UNDERPERFORMER"
                emp.recommendation = (
                    f"⚠️ РИЗИК ЗВІЛЬНЕННЯ {emp.quit_chance:.1f}%: Низьке щастя (happiness). "
                    f"Підвищіть зарплату або підготуйте кандидата на заміну."
                )
                continue

            # Scenario 3: RELOCATE (High skill, low fidelity, higher-margin destination exists)
            # Check other companies owned by user
            best_relocation = None
            max_profit_diff = 0.0

            if emp.spec_days <= 3 and emp.hourly_pp >= 1.8:
                for target_comp in companies_list:
                    if target_comp.company_id == emp.company_id:
                        continue
                    
                    target_econ = item_econ_cache[target_comp.item_code]
                    if target_econ.margin_per_pp > current_econ.margin_per_pp * 1.08:
                        # Estimate simulated PP on target company
                        # (Without current item specialization, but with base + trained + other persistent bonuses)
                        spec_pct_loss = min(emp.spec_days * 1.0, 10.0) # approximate spec %
                        simulated_pp = emp.hourly_pp * (1.0 - (spec_pct_loss / 100.0))
                        simulated_net_val = (simulated_pp / target_econ.pp_per_item) * target_econ.unit_margin
                        simulated_profit = simulated_net_val - emp.wage
                        profit_diff_hourly = simulated_profit - emp.hourly_net_profit

                        if profit_diff_hourly > max_profit_diff and profit_diff_hourly > 0.02:
                            max_profit_diff = profit_diff_hourly
                            best_relocation = {
                                "target_company_id": target_comp.company_id,
                                "target_company_name": target_comp.name,
                                "target_item": target_comp.item_code,
                                "current_hourly_profit": emp.hourly_net_profit,
                                "simulated_hourly_profit": simulated_profit,
                                "hourly_gain": profit_diff_hourly,
                                "daily_gain": profit_diff_hourly * 24.0,
                            }

            if best_relocation:
                emp.status = "RELOCATE"
                emp.relocation_target = best_relocation
                emp.recommendation = (
                    f"🔄 ПЕРЕВЕСТИ на '{best_relocation['target_company_name']}' ({best_relocation['target_item'].upper()}): "
                    f"Спеціалізація ще мала ({emp.spec_days} дн.), а маржа ресурсу вища. "
                    f"Очікуваний приріст: +{best_relocation['daily_gain']:.2f} Coins/добу!"
                )
                continue

            # Scenario 4: KEEP
            emp.status = "KEEP"
            emp.recommendation = (
                f"💎 ЕФЕКТИВНИЙ (ЯДРО): Спеціалізація {emp.spec_days} дн., чистий прибуток +{emp.daily_net_profit:.2f}/добу. "
                f"Утримувати та підтримувати інструмент у робочому стані."
            )

        # 8. Totals and Summary
        total_hourly_profit = sum(c.hourly_net_profit for c in companies_list)
        total_daily_profit = sum(c.daily_net_profit for c in companies_list)
        total_daily_output = sum(c.total_daily_pp for c in companies_list)
        total_employee_output = sum(c.daily_pp for c in companies_list)
        total_engine_output = sum(c.engine_daily_pp for c in companies_list)
        total_goods_value_daily = sum(c.goods_value_daily for c in companies_list)
        total_wages_daily = sum(c.wages_daily for c in companies_list)
        in_game_profit_daily = sum(c.in_game_profit for c in companies_list)
        total_daily_profit_with_self = total_daily_profit + sum(c.self_work_daily_net for c in companies_list[:1])

        total_workforce = len(all_employees)
        toxic_count = sum(1 for e in all_employees if e.status == "TOXIC")
        relocate_count = sum(1 for e in all_employees if e.status == "RELOCATE")
        underperformer_count = sum(1 for e in all_employees if e.status == "UNDERPERFORMER")
        keep_count = sum(1 for e in all_employees if e.status == "KEEP")

        # Toolboxes expectation: base ~0.10/worker/day + perks + luck
        total_toolboxes_daily = round(sum(
            0.10 + 
            (0.08 if any(t.get("code") in ("luckyCharm", "salvager") for t in e.traits) else 0.0) +
            (float(e.trained_stats.get("luck", 0)) * 0.01)
            for e in all_employees
        ), 1)

        trainable_count = sum(1 for e in all_employees if e.potential < e.potential_max or e.trained_prod < 5 or e.trainings_left > 0)

        # Lowest tax countries (top 3-4)
        valid_countries = [c for c in (countries_list or []) if isinstance(c, dict) and "taxes" in c and c.get("name")]
        valid_countries.sort(key=lambda c: (c["taxes"].get("income", 100), c["taxes"].get("market", 100)))
        lowest_tax_countries = [
            {
                "name": c.get("name", ""),
                "code": c.get("code", ""),
                "income_tax": c.get("taxes", {}).get("income", 0),
                "market_tax": c.get("taxes", {}).get("market", 0),
                "manager_tax": c.get("taxes", {}).get("manager", 0),
            }
            for c in valid_countries[:4]
        ]

        # Best products right now (top 3 by margin_per_pp * 100)
        sorted_econ_items = sorted(item_econ_cache.values(), key=lambda x: x.margin_per_pp, reverse=True)
        best_products = [
            {
                "code": it.code,
                "name": it.name,
                "margin_per_100": round(it.margin_per_pp * 100, 3),
                "daily_at_output": round(total_daily_output * it.margin_per_pp, 2),
                "price": round(it.market_price, 4),
            }
            for it in sorted_econ_items[:4]
        ]

        user_country_id = user_data.get("country", "")
        user_country_obj = country_dict.get(user_country_id, {})
        mgmt_skill = user_data.get("skills", {}).get("management", {})
        mgmt_val = mgmt_skill.get("value", 0)

        return {
            "user": {
                "user_id": user_id,
                "username": username,
                "level": user_data.get("leveling", {}).get("level", 0),
                "country_id": user_country_id,
                "country_name": user_country_obj.get("name", "Україна"),
                "country_code": user_country_obj.get("code", "ua"),
                "management_pts": mgmt_val,
                "management_bonus_pct": mgmt_val * 2.0,
                "production_skill": user_data.get("skills", {}).get("production", {}),
            },
            "auth": {
                "key_present": bool(self.api_key),
                "is_community_key": self.is_community_key,
                "auth_failed": self.auth_failed,
                "error_message": self.auth_error_msg,
            },
            "summary": {
                "total_companies": len(companies_list),
                "companies_with_staff": sum(1 for c in companies_list if c.staff_count > 0),
                "companies_with_manager": 0,
                "total_workforce": total_workforce,
                "total_daily_output": total_daily_output,
                "total_employee_output": total_employee_output,
                "total_engine_output": total_engine_output,
                "total_goods_value_daily": total_goods_value_daily,
                "total_wages_daily": total_wages_daily,
                "total_manager_daily": 0.0,
                "in_game_profit_daily": in_game_profit_daily,
                "total_hourly_profit": total_hourly_profit,
                "total_daily_profit": total_daily_profit,
                "total_daily_profit_with_self": total_daily_profit_with_self,
                "total_toolboxes_daily": total_toolboxes_daily,
                "trainable_count": trainable_count,
                "toxic_count": toxic_count,
                "relocate_count": relocate_count,
                "underperformer_count": underperformer_count,
                "keep_count": keep_count,
                "lowest_tax_countries": lowest_tax_countries,
                "best_products": best_products,
            },
            "economics_by_item": {k: vars(v) for k, v in item_econ_cache.items()},
            "companies": [
                {
                    "company_id": c.company_id,
                    "name": c.name,
                    "item_code": c.item_code,
                    "region_id": c.region_id,
                    "region_name": c.region_name,
                    "country_name": c.country_name,
                    "country_code": c.country_code,
                    "is_full": c.is_full,
                    "upgrades": c.upgrades,
                    "engine_level": c.upgrades.get("automatedEngine", 0),
                    "storage_level": c.upgrades.get("storage", 0),
                    "break_room_level": c.upgrades.get("breakRoom", 0),
                    "staff_count": c.staff_count,
                    "staff_cap": c.staff_cap,
                    "hourly_pp": c.hourly_pp,
                    "daily_pp": c.daily_pp,
                    "hourly_units": c.hourly_units,
                    "daily_units": c.daily_units,
                    "engine_daily_pp": c.engine_daily_pp,
                    "engine_daily_units": c.engine_daily_units,
                    "total_daily_pp": c.total_daily_pp,
                    "total_daily_units": c.total_daily_units,
                    "employees_share_pct": c.employees_share_pct,
                    "engine_share_pct": c.engine_share_pct,
                    "hourly_revenue": c.hourly_revenue,
                    "goods_value_daily": c.goods_value_daily,
                    "hourly_raw_cost": c.hourly_raw_cost,
                    "raw_cost_daily": c.raw_cost_daily,
                    "hourly_wage_cost": c.hourly_wage_cost,
                    "wages_daily": c.wages_daily,
                    "hourly_net_profit": c.hourly_net_profit,
                    "daily_net_profit": c.daily_net_profit,
                    "in_game_profit": c.in_game_profit,
                    "self_work_daily_net": c.self_work_daily_net,
                    "net_daily_with_self_work": c.net_daily_with_self_work,
                    "raw_from_own": c.raw_from_own,
                    "taxes": c.taxes,
                    "avg_wage": c.avg_wage,
                    "recommended_max_wage": c.recommended_max_wage,
                    "margin_per_pp": item_econ_cache[c.item_code].margin_per_pp,
                    "employees": [vars(e) for e in c.employees]
                }
                for c in companies_list
            ],
            "employees_flat": [vars(e) for e in all_employees]
        }


# =====================================================================
# CLI Runner
# =====================================================================

def print_cli_report(data: Dict[str, Any]):
    u = data["user"]
    s = data["summary"]
    auth = data.get("auth", {})

    print("\n" + "=" * 80)
    print(f"🏰 WARERA FACTORY & WORKFORCE INTELLIGENCE — ГРАВЕЦЬ: {u['username']} (Lv.{u['level']})")
    print("=" * 80)

    if auth.get("auth_failed"):
        print("⚠️  УВАГА: WarEra API повернув 401 Unauthorized (API token required)!")
        print("   Оновіть API-токен у налаштуваннях профілю WarEra (Settings -> API Key).")
        print("-" * 80)
    elif auth.get("is_community_key"):
        print("🌐 РЕЖИМ СПІЛЬНОТИ: Використовується публічний ключ спільноти (Arcana Era Pool).")
        print("   Всі фабрики та працівники доступні автоматично без власного токена!")
        print("-" * 80)
    elif not auth.get("key_present"):
        print("ℹ️  API-токен не вказано.")
        print("-" * 80)

    print(f"🏭 Фабрик: {s['total_companies']} | 👥 Працівників: {s['total_workforce']}")
    print(f"💰 Чистий прибуток: {s['total_hourly_profit']:+.4f} Coins/год  ==>  {s['total_daily_profit']:+.2f} Coins/ДОБУ")
    print(f"📊 Статуси кадрів: 💎 Ядро: {s['keep_count']} | 🔄 На переведення: {s['relocate_count']} | ⚠️ Слабкі: {s['underperformer_count']} | 🚨 Збиткові: {s['toxic_count']}")
    print("-" * 80)

    for c in data["companies"]:
        print(f"\n🏢 Фабрика: [{c['name']}] | Товар: {c['item_code'].upper()} | Маржа: {c['margin_per_pp']:.5f}/PP | Персонал: {c['staff_count']}/{c['staff_cap']}")
        print(f"   Випуск: {c['hourly_pp']:.2f} PP/год ({c['hourly_units']:.2f} од/год) | Зарплати: {c['hourly_wage_cost']:.4f}/год | Прибуток: {c['hourly_net_profit']:+.4f}/год ({c['daily_net_profit']:+.2f}/добу)")
        
        if not c["employees"]:
            print("   (Немає працівників)")
            continue

        print(f"   {'-'*76}")
        print(f"   {'Статус':<8} | {'Ім\'я працівника':<18} | {'PP/год':>6} | {'Зарплата':>8} | {'Прибуток/год':>12} | {'/добу':>7} | {'Стаж':>4} | {'Пенсія':>6}")
        print(f"   {'-'*76}")

        for e in c["employees"]:
            status_symbol = {
                "TOXIC": "🚨 ЗБИТОК",
                "RELOCATE": "🔄 ПЕРЕВОД",
                "UNDERPERFORMER": "⚠️ СЛАБКИЙ",
                "KEEP": "💎 ОК"
            }.get(e["status"], e["status"])

            print(f"   {status_symbol:<8} | {e['name'][:18]:<18} | {e['hourly_pp']:6.2f} | {e['wage']:8.4f} | {e['hourly_net_profit']:+12.4f} | {e['daily_net_profit']:+7.2f} | {e['spec_days']:3}д | {e['retire_in_days']:4}д")
            if e["status"] in ("TOXIC", "RELOCATE", "UNDERPERFORMER"):
                print(f"            ↳ 💡 {e['recommendation']}")

    print("\n" + "=" * 80 + "\n")


async def async_main(target_nick: Optional[str] = None, output_json: bool = False):
    import argparse
    if target_nick is None and "--help" in sys.argv:
        parser = argparse.ArgumentParser(description="WarEra Worker & Factory Analyzer")
        parser.add_argument("--nick", type=str, default=None, help="Нікнейм гравця або ID (за замовчуванням: власник токена)")
        parser.add_argument("--json", action="store_true", help="Вивести результат у форматі JSON")
        args = parser.parse_args()
        target_nick = args.nick
        output_json = args.json

    analyzer = WarEraWorkerAnalyzer()
    try:
        report = await analyzer.analyze_user(target_nick)
        if output_json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print_cli_report(report)
    finally:
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(async_main())

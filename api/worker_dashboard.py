"""
WarEra Workforce & Factory Intelligence Web Dashboard.
Interactive visual dashboard with company economics, worker profitability tables,
decision engine alerts, relocation simulation, wage optimizer, API key management,
and report export for public/community use.
"""

import asyncio
import json
import os
import sys
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure api directory in sys.path
CURRENT_DIR = Path(__file__).parent.resolve()
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import config
from worker_analyzer import WarEraWorkerAnalyzer

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="uk" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WarEra Workforce & Factory Intelligence 🏭👷‍♂️</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        darkbg: '#0B0F19',
                        cardbg: '#111827',
                        bordercolor: '#1F2937',
                        hoverbg: '#1E293B',
                        toxic: '#EF4444',
                        relocate: '#3B82F6',
                        under: '#F59E0B',
                        keep: '#10B981',
                    }
                }
            }
        }
    </script>
    <style>
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0B0F19; }
        ::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #4B5563; }
        .tab-active { border-bottom: 2px solid #3B82F6; color: #60A5FA; font-weight: 600; }
        .glass-panel { background: rgba(17, 24, 39, 0.85); backdrop-filter: blur(14px); border: 1px solid rgba(31, 41, 55, 0.85); }
    </style>
</head>
<body class="bg-darkbg text-gray-200 min-h-screen flex flex-col font-sans">

    <!-- Top Navigation Bar -->
    <header class="glass-panel sticky top-0 z-50 px-4 sm:px-6 py-3.5 border-b border-bordercolor flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/25">
                <i class="fa-solid fa-industry text-lg"></i>
            </div>
            <div>
                <div class="flex items-center gap-2">
                    <h1 class="text-lg sm:text-xl font-bold tracking-tight text-white">
                        WarEra <span class="bg-gradient-to-r from-blue-400 to-indigo-300 bg-clip-text text-transparent">Workforce Intel</span>
                    </h1>
                    <span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-900/50 text-blue-300 border border-blue-700/50">v2.1 Community</span>
                </div>
                <p class="text-[11px] text-gray-400 hidden sm:block">Аналіз фабрик, прибутковості робітників, бонусів та оптимізація кадрів</p>
            </div>
        </div>

        <!-- Controls: Module Switcher, API Key, Search, Refresh -->
        <div class="flex items-center gap-2 sm:gap-3 flex-wrap">
            <!-- Link to Market Scanner -->
            <a href="/" id="linkMarketScanner" class="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800/80 hover:bg-gray-700 border border-gray-700 text-xs text-gray-300 transition-colors">
                <i class="fa-solid fa-shield-halved text-amber-400"></i>
                <span>Ринок спорядження</span>
            </a>

            <!-- API Key Button -->
            <button onclick="openApiKeyModal()" id="apiKeyBadge" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800/80 hover:bg-gray-700 border border-gray-700 text-xs text-gray-300 transition-colors">
                <i class="fa-solid fa-key text-yellow-400" id="apiKeyIcon"></i>
                <span id="apiKeyStatusText">Власний API-ключ</span>
            </button>

            <!-- Search Field -->
            <div class="relative flex items-center">
                <i class="fa-solid fa-user absolute left-3 text-gray-400 text-xs"></i>
                <input id="userSearchInput" type="text" placeholder="Нікнейм гравця..." value="Luc1fer"
                    onkeydown="if(event.key === 'Enter') fetchData()"
                    class="bg-gray-800/90 border border-bordercolor rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors w-36 sm:w-48">
            </div>

            <!-- Run Button -->
            <button onclick="fetchData()" id="refreshBtn"
                class="bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 shadow-md shadow-blue-600/30 transition-all">
                <i class="fa-solid fa-arrows-rotate" id="refreshIcon"></i>
                <span>Аналіз</span>
            </button>

            <!-- Export Dropdown -->
            <button onclick="copyReportToClipboard()" title="Скопіювати текстовий звіт для Telegram / Discord"
                class="px-2.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-gray-700 transition-colors flex items-center gap-1">
                <i class="fa-solid fa-copy"></i>
                <span class="hidden sm:inline">Звіт</span>
            </button>
            <button onclick="downloadJsonReport()" title="Завантажити повний JSON звіт"
                class="px-2.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-gray-700 transition-colors">
                <i class="fa-solid fa-download"></i>
            </button>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">

        <!-- Recent Searches Chips -->
        <div id="recentSearchesRow" class="flex items-center gap-2 text-xs text-gray-400 overflow-x-auto pb-1">
            <span class="text-gray-500 flex items-center gap-1"><i class="fa-solid fa-clock-rotate-left"></i> Нещодавні:</span>
            <div id="recentChips" class="flex items-center gap-1.5">
                <!-- Chips injected here -->
            </div>
        </div>

        <!-- Top Stat Cards (Arcana-Style 9 Cards) -->
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-3.5">
            <!-- 1. Підприємства -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Підприємства</span>
                    <i class="fa-solid fa-industry text-blue-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-white" id="statCompaniesCount">--</div>
                <div class="text-xs text-gray-400 mt-1" id="statCompaniesSub">-- з робітниками · 0 з менеджером</div>
            </div>

            <!-- 2. Виробіток на добу -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Виробіток</span>
                    <i class="fa-solid fa-bolt text-yellow-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-yellow-300" id="statTotalOutput">-- PP</div>
                <div class="text-xs text-gray-400 mt-1" id="statOutputSub">очок виробітку на добу</div>
            </div>

            <!-- 3. Скрині з інструментами -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Скрині з інструментами</span>
                    <i class="fa-solid fa-toolbox text-teal-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-teal-300" id="statToolboxes">--</div>
                <div class="text-xs text-gray-400 mt-1">очікуваних знахідок на добу</div>
            </div>

            <!-- 4. Вартість товару -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Вартість товару</span>
                    <i class="fa-solid fa-box-open text-indigo-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-indigo-300" id="statGoodsValue">--</div>
                <div class="text-xs text-gray-400 mt-1">за ринковими цінами на добу</div>
            </div>

            <!-- 5. Зарплати персоналу -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Зарплати персоналу</span>
                    <i class="fa-solid fa-money-bill-wave text-rose-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-rose-400" id="statWagesDaily">--</div>
                <div class="text-xs text-gray-400 mt-1">витрат на добу за ставками</div>
            </div>

            <!-- 6. Менеджери -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Менеджери</span>
                    <i class="fa-solid fa-user-tie text-purple-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-gray-300" id="statManagersDaily">0.00</div>
                <div class="text-xs text-gray-400 mt-1">витрат на керуючих на добу</div>
            </div>

            <!-- 7. Ігровий прибуток -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Ігровий прибуток</span>
                    <i class="fa-solid fa-gamepad text-purple-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-purple-300" id="statInGameProfit">--</div>
                <div class="text-xs text-gray-400 mt-1">як показує панель Workforce</div>
            </div>

            <!-- 8. Чистий прибуток (NET) -->
            <div class="glass-panel p-4 rounded-xl border border-emerald-500/30 shadow-md bg-gradient-to-br from-emerald-950/20 to-cardbg hover:border-emerald-500/50 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center justify-between">
                    <span>Чистий прибуток (NET)</span>
                    <i class="fa-solid fa-coins text-yellow-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-emerald-400" id="statDailyProfit">--</div>
                <div class="text-xs text-gray-400 mt-1" id="statDailyProfitWithSelf">-- з власною працею</div>
            </div>

            <!-- 9. Робоча сила -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Робоча сила</span>
                    <i class="fa-solid fa-users text-sky-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-sky-300" id="statStaffCount">--</div>
                <div class="text-xs text-gray-400 mt-1" id="statStaffSub">-- доступні для тренування</div>
            </div>
        </div>

        <!-- Beginner Insights: Lowest Tax Countries & Best Products Right Now -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <!-- Lowest Tax Countries -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-bold uppercase tracking-wider text-gray-300">Країни з найнижчими податками</span>
                        <span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-700/40" title="Будуйте фабрики в цих країнах, щоб зберігати 100% прибутку">0% Податку</span>
                    </div>
                    <i class="fa-solid fa-earth-americas text-blue-400"></i>
                </div>
                <div id="lowestTaxList" class="flex flex-wrap gap-2 text-xs">
                    <span class="text-gray-500 text-xs">Завантаження країн...</span>
                </div>
                <div class="text-[11px] text-gray-400 mt-2.5 flex items-center gap-1.5">
                    <i class="fa-solid fa-circle-info text-blue-400 shrink-0"></i>
                    <span>💡 Новачкам: Регіональні податки сплачуються з прибутку. Фабрики в зонах 0% приносять максимум!</span>
                </div>
            </div>

            <!-- Best Products Right Now -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-bold uppercase tracking-wider text-gray-300">Найприбутковіші товари прямо зараз</span>
                        <span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700/40" title="Товари з найвищою віддачею Coins на 100 очок виробітку">Топ ринку</span>
                    </div>
                    <i class="fa-solid fa-arrow-trend-up text-amber-400"></i>
                </div>
                <div id="bestProductsList" class="flex flex-wrap gap-2 text-xs">
                    <span class="text-gray-500 text-xs">Завантаження аналітики ринку...</span>
                </div>
                <div class="text-[11px] text-gray-400 mt-2.5 flex items-center gap-1.5">
                    <i class="fa-solid fa-circle-info text-amber-400 shrink-0"></i>
                    <span>💡 Новачкам: Показує, який товар генерує найбільше Coins за 100 очок виробітку робітників.</span>
                </div>
            </div>
        </div>

        <!-- Player Profile Banner -->
        <div id="playerBanner" class="glass-panel p-4 rounded-xl flex flex-wrap items-center justify-between gap-4 border-l-4 border-l-blue-500 shadow-lg">
            <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-full bg-blue-900/60 flex items-center justify-center text-xl font-bold text-blue-300 border border-blue-500/30 shadow-inner">
                    <span id="playerAvatarLetter">?</span>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <span id="playerUsername" class="text-lg font-bold text-white">Завантаження...</span>
                        <span id="playerLevel" class="text-xs px-2 py-0.5 rounded bg-gray-800 text-yellow-400 border border-bordercolor font-semibold">Lv.--</span>
                        <a id="playerGameLink" href="#" target="_blank" class="text-xs text-blue-400 hover:text-blue-300" title="Відкрити профіль у грі">
                            <i class="fa-solid fa-arrow-up-right-from-square"></i>
                        </a>
                    </div>
                    <div class="text-xs text-gray-400 flex items-center gap-3 mt-1 flex-wrap">
                        <span id="playerProdSkill"><i class="fa-solid fa-bolt text-yellow-400 mr-1"></i>Prod Skill: --</span>
                        <span id="playerCountry"><i class="fa-solid fa-globe text-blue-400 mr-1"></i>Країна: --</span>
                    </div>
                </div>
            </div>
            <!-- Category Filter Pills -->
            <div class="flex items-center gap-1.5 flex-wrap text-xs">
                <button onclick="setFilter('ALL')" id="filterALL" class="px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium transition-colors">Всі (<span id="cntAll">0</span>)</button>
                <button onclick="setFilter('KEEP')" id="filterKEEP" class="px-3 py-1.5 rounded-lg bg-gray-800 text-emerald-400 hover:bg-gray-700 transition-colors">💎 Ядро (<span id="cntKeep">0</span>)</button>
                <button onclick="setFilter('RELOCATE')" id="filterRELOCATE" class="px-3 py-1.5 rounded-lg bg-gray-800 text-blue-400 hover:bg-gray-700 transition-colors">🔄 Переведення (<span id="cntRelocate">0</span>)</button>
                <button onclick="setFilter('UNDERPERFORMER')" id="filterUNDERPERFORMER" class="px-3 py-1.5 rounded-lg bg-gray-800 text-amber-400 hover:bg-gray-700 transition-colors">⚠️ Слабкі / Пенсія (<span id="cntUnder">0</span>)</button>
                <button onclick="setFilter('TOXIC')" id="filterTOXIC" class="px-3 py-1.5 rounded-lg bg-gray-800 text-red-400 hover:bg-gray-700 transition-colors">🚨 Збиткові (<span id="cntToxic">0</span>)</button>
            </div>
        </div>

        <!-- Auth Warning Alert Banner (Hidden by default, shown when token invalid or missing) -->
        <div id="workerAuthAlertBanner" class="hidden bg-amber-950/40 border border-amber-500/50 rounded-xl p-3.5 flex items-center justify-between text-amber-200">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
                    <i class="fa-solid fa-triangle-exclamation text-lg"></i>
                </div>
                <div>
                    <div class="font-bold text-sm text-amber-300" id="workerAuthAlertTitle">Потрібен дійсний API-ключ для доступу до робітників</div>
                    <div class="text-xs text-amber-200/80 mt-0.5" id="workerAuthAlertMsg">WarEra API блокує доступ до ендпоінтів робітників (401 Unauthorized). Оновіть API-токен у налаштуваннях гри та введіть його.</div>
                </div>
            </div>
            <button onclick="openApiKeyModal()" class="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow transition whitespace-nowrap ml-3">
                <i class="fa-solid fa-key mr-1"></i> Оновити ключ
            </button>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex items-center border-b border-bordercolor gap-6 text-sm overflow-x-auto">
            <button onclick="switchTab('companies')" id="tabCompanies" class="pb-3 tab-active flex items-center gap-2 whitespace-nowrap text-blue-400 font-semibold">
                <i class="fa-solid fa-industry"></i>
                <span>Огляд підприємств</span>
            </button>
            <button onclick="switchTab('workers')" id="tabWorkers" class="pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap">
                <i class="fa-solid fa-users"></i>
                <span>Працівники фабрик</span>
            </button>
            <button onclick="switchTab('relocation')" id="tabRelocation" class="pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap">
                <i class="fa-solid fa-arrows-split-up-and-left"></i>
                <span>Матриця переведень</span>
            </button>
            <button onclick="switchTab('optimizer')" id="tabOptimizer" class="pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap">
                <i class="fa-solid fa-calculator"></i>
                <span>Калькулятор зарплат</span>
            </button>
        </div>

        <!-- TAB 1: COMPANIES CARDS (Default active) -->
        <div id="contentCompanies" class="space-y-4">
            <!-- Dynamically populated -->
        </div>

        <!-- TAB 2: WORKERS TABLE -->
        <div id="contentWorkers" class="hidden space-y-4">
            <div class="glass-panel rounded-xl overflow-hidden shadow-xl">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-gray-900/90 text-gray-400 uppercase text-[10px] tracking-wider border-b border-bordercolor">
                            <tr>
                                <th class="p-3">Статус</th>
                                <th class="p-3 cursor-pointer hover:text-white" onclick="sortWorkers('name')">Працівник <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                <th class="p-3 cursor-pointer hover:text-white" onclick="sortWorkers('company')">Фабрика / Товар <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                <th class="p-3 text-right cursor-pointer hover:text-white" onclick="sortWorkers('pp')">Виробіток <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                <th class="p-3 text-right cursor-pointer hover:text-white" onclick="sortWorkers('wage')">Зарплата <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                <th class="p-3 text-right cursor-pointer hover:text-white" onclick="sortWorkers('profit')">Чистий прибуток <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                <th class="p-3 text-right">Break-even Wage</th>
                                <th class="p-3 text-center cursor-pointer hover:text-white" onclick="sortWorkers('spec')">Стаж / Бонус <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                <th class="p-3 text-center cursor-pointer hover:text-white" onclick="sortWorkers('retire')">Пенсія / Ризик <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                <th class="p-3">Рекомендація</th>
                            </tr>
                        </thead>
                        <tbody id="workersTableBody" class="divide-y divide-bordercolor">
                            <tr>
                                <td colspan="10" class="p-8 text-center text-gray-400">
                                    <i class="fa-solid fa-spinner fa-spin text-xl mr-2 text-blue-500"></i> Завантаження даних аналізу...
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 3: RELOCATION MATRIX -->
        <div id="contentRelocation" class="hidden space-y-4">
            <div class="glass-panel p-5 rounded-xl space-y-3 border-l-4 border-l-blue-500 shadow-lg">
                <h3 class="text-base font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-arrows-turn-to-dots text-blue-400"></i>
                    Розумний симулятор переведень між фабриками
                </h3>
                <p class="text-xs text-gray-300 leading-relaxed">
                    Правило економіки WarEra: якщо працівник має високу базову продуктивність, але ще не накопичив високий бонус спеціалізації (&le; 3 дні), переведення його на фабрику з вищою маржею на 1 PP дасть більше чистого прибутку, ніж збереження на менш рентабельній фабриці.
                </p>
            </div>
            <div id="relocationCards" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Dynamically populated -->
            </div>
        </div>

        <!-- TAB 4: WAGE OPTIMIZER & BREAK-EVEN -->
        <div id="contentOptimizer" class="hidden space-y-4">
            <div class="glass-panel p-5 rounded-xl space-y-4 shadow-lg">
                <h3 class="text-base font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-sliders text-indigo-400"></i>
                    Оптимізатор ставок заробітної плати (Break-even & Target Margin)
                </h3>
                <p class="text-xs text-gray-400">
                    Максимально допустима ставка зарплати (<span class="text-yellow-400">Break-even Wage</span>) показує межу, вище якої працівник починає приносити прямий збиток власнику фабрики.
                </p>
                <div id="optimizerTable" class="overflow-x-auto">
                    <!-- Populated dynamically -->
                </div>
            </div>
        </div>

    </main>

    <!-- Modal: API Key Settings -->
    <div id="apiKeyModal" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="glass-panel p-6 rounded-2xl max-w-lg w-full space-y-4 shadow-2xl border border-gray-700">
            <div class="flex items-center justify-between">
                <h3 class="text-base font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-key text-yellow-400"></i>
                    Налаштування особистого API-ключа
                </h3>
                <button onclick="closeApiKeyModal()" class="text-gray-400 hover:text-white text-lg">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>

            <p class="text-xs text-gray-300 leading-relaxed">
                Якщо ви хочете аналізувати приватні дані власних фабрик або використовувати свій ліміт запитів, введіть ваш персональний API-токен з гри (<span class="text-blue-400">app.warera.io &rarr; Профіль &rarr; API Token</span>).
            </p>

            <div class="space-y-1.5">
                <label class="text-[11px] text-gray-400 font-semibold uppercase">API Token (wae_...):</label>
                <div class="relative">
                    <input id="modalApiKeyInput" type="password" placeholder="wae_xxxxxxxxxxxxxxxxxxxxxxxx..."
                        class="w-full bg-gray-900 border border-bordercolor rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono">
                    <button type="button" onclick="toggleApiKeyVisibility()" class="absolute right-3 top-2.5 text-gray-400 hover:text-white text-xs">
                        <i class="fa-solid fa-eye" id="apiKeyEyeIcon"></i>
                    </button>
                </div>
                <p class="text-[10px] text-emerald-400 flex items-center gap-1 mt-1">
                    <i class="fa-solid fa-shield-halved"></i> Безпечно: ключ зберігається виключно у вашому браузері (localStorage).
                </p>
            </div>

            <div class="flex items-center justify-end gap-2 pt-2 border-t border-bordercolor">
                <button onclick="clearUserApiKey()" class="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-red-400 text-xs font-medium transition-colors">
                    Видалити / Скинути
                </button>
                <button onclick="saveUserApiKey()" class="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition-all">
                    Зберегти ключ
                </button>
            </div>
        </div>
    </div>

    <!-- Notification Toast -->
    <div id="toast" class="fixed bottom-5 right-5 z-50 transform translate-y-20 opacity-0 transition-all duration-300 bg-gray-900 border border-blue-500 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs">
        <i class="fa-solid fa-circle-check text-emerald-400 text-base"></i>
        <span id="toastMsg">Повідомлення</span>
    </div>

    <!-- Footer -->
    <footer class="glass-panel border-t border-bordercolor py-4 text-center text-xs text-gray-500">
        WarEra Suite &bull; Workforce & Factory Intelligence Engine &bull; Дані синхронізовано з tRPC API &bull; <a href="https://github.com/S88EM/warera" target="_blank" class="text-blue-400 hover:underline">GitHub S88EM/warera</a>
    </footer>

    <!-- JavaScript Application Logic -->
    <script>
        let currentData = null;
        let currentFilter = 'ALL';
        let sortField = 'profit';
        let sortAsc = false;

        // Initialize local storage state
        const LS_KEY = 'warera_user_api_key';
        const LS_RECENTS = 'warera_recent_nicks';

        function getUserApiKey() {
            return localStorage.getItem(LS_KEY) || '';
        }

        function updateApiKeyBadgeUI() {
            const key = getUserApiKey();
            const badgeText = document.getElementById('apiKeyStatusText');
            const icon = document.getElementById('apiKeyIcon');
            const auth = (currentData && currentData.auth) || {};
            if (auth.auth_failed) {
                badgeText.innerText = 'Ключ недійсний (401)';
                badgeText.className = 'text-rose-400 font-semibold';
                icon.className = 'fa-solid fa-triangle-exclamation text-rose-400';
            } else if (auth.is_community_key) {
                badgeText.innerText = 'Ключ спільноти (Авто)';
                badgeText.className = 'text-cyan-400 font-semibold';
                icon.className = 'fa-solid fa-globe text-cyan-400';
            } else if (key) {
                badgeText.innerText = 'Ваш ключ (Активний)';
                badgeText.className = 'text-emerald-400 font-semibold';
                icon.className = 'fa-solid fa-key text-emerald-400';
            } else {
                badgeText.innerText = 'Ключ спільноти (Авто)';
                badgeText.className = 'text-cyan-400 font-semibold';
                icon.className = 'fa-solid fa-globe text-cyan-400';
            }
        }

        function openApiKeyModal() {
            document.getElementById('modalApiKeyInput').value = getUserApiKey();
            document.getElementById('apiKeyModal').classList.remove('hidden');
        }

        function closeApiKeyModal() {
            document.getElementById('apiKeyModal').classList.add('hidden');
        }

        function toggleApiKeyVisibility() {
            const input = document.getElementById('modalApiKeyInput');
            const icon = document.getElementById('apiKeyEyeIcon');
            if (input.type === 'password') {
                input.type = 'text';
                icon.className = 'fa-solid fa-eye-slash';
            } else {
                input.type = 'password';
                icon.className = 'fa-solid fa-eye';
            }
        }

        function saveUserApiKey() {
            const key = document.getElementById('modalApiKeyInput').value.trim();
            if (key) {
                localStorage.setItem(LS_KEY, key);
                showToast('API ключ збережено в браузері!');
            } else {
                localStorage.removeItem(LS_KEY);
                showToast('Використовується системний ключ.');
            }
            updateApiKeyBadgeUI();
            closeApiKeyModal();
            fetchData();
        }

        function clearUserApiKey() {
            localStorage.removeItem(LS_KEY);
            document.getElementById('modalApiKeyInput').value = '';
            updateApiKeyBadgeUI();
            closeApiKeyModal();
            showToast('Ключ очищено. Використовується публічний режим.');
            fetchData();
        }

        function getRecentSearches() {
            try {
                return JSON.parse(localStorage.getItem(LS_RECENTS)) || ['Luc1fer'];
            } catch {
                return ['Luc1fer'];
            }
        }

        function addRecentSearch(nick) {
            if (!nick) return;
            let recents = getRecentSearches().filter(n => n.toLowerCase() !== nick.toLowerCase());
            recents.unshift(nick);
            if (recents.length > 6) recents = recents.slice(0, 6);
            localStorage.setItem(LS_RECENTS, JSON.stringify(recents));
            renderRecentChips();
        }

        function renderRecentChips() {
            const container = document.getElementById('recentChips');
            container.innerHTML = '';
            const recents = getRecentSearches();
            recents.forEach(nick => {
                const chip = document.createElement('button');
                chip.className = 'px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 text-[11px] text-gray-300 border border-gray-700 transition-colors flex items-center gap-1';
                chip.innerHTML = `<span>${nick}</span>`;
                chip.onclick = () => {
                    document.getElementById('userSearchInput').value = nick;
                    fetchData();
                };
                container.appendChild(chip);
            });
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            document.getElementById('toastMsg').innerText = msg;
            toast.classList.remove('translate-y-20', 'opacity-0');
            setTimeout(() => {
                toast.classList.add('translate-y-20', 'opacity-0');
            }, 3000);
        }

        // Workforce Mappings & State
        let workerExpandedCompanies = new Set();

        const TRAIT_MAP = {
            'sociable': { name: 'Товариський', icon: 'fa-users', color: 'bg-emerald-950/50 text-emerald-300 border-emerald-700/50', desc: '+50% бонус виробітку' },
            'lateBloomer': { name: 'Пізній розквіт', icon: 'fa-chart-line', color: 'bg-blue-950/50 text-blue-300 border-blue-700/50', desc: '+2 до характеристик з віком' },
            'laborer': { name: 'Роботяга', icon: 'fa-hammer', color: 'bg-amber-950/50 text-amber-300 border-amber-700/50', desc: '+1 до виробітку' },
            'oldFriends': { name: 'Старі друзі', icon: 'fa-handshake', color: 'bg-purple-950/50 text-purple-300 border-purple-700/50', desc: '+15% бонус за знайомого колегу' },
            'specialist': { name: 'Спеціаліст', icon: 'fa-graduation-cap', color: 'bg-indigo-950/50 text-indigo-300 border-indigo-700/50', desc: '+20% бонус та щастя на спеціалізації' },
            'luckyCharm': { name: 'Талісман удачі', icon: 'fa-clover', color: 'bg-green-950/50 text-green-300 border-green-700/50', desc: 'Частіше знаходить скрині з інструментами' },
            'salvager': { name: 'Шукач скринь', icon: 'fa-toolbox', color: 'bg-teal-950/50 text-teal-300 border-teal-700/50', desc: 'Підвищений шанс знайти інструмент' },
            'cosmopolitan': { name: 'Космополіт', icon: 'fa-earth-americas', color: 'bg-sky-950/50 text-sky-300 border-sky-700/50', desc: 'Не втрачає щастя за кордоном' },
            'bandOfBrothers': { name: 'Браття по зброї', icon: 'fa-shield-halved', color: 'bg-amber-950/50 text-amber-300 border-amber-700/50', desc: '+30% бонус до виробітку в команді' },
            'loyal': { name: 'Відданий', icon: 'fa-heart', color: 'bg-rose-950/50 text-rose-300 border-rose-700/50', desc: 'Не вимагає підвищення і не звільняється' },
            'expat': { name: 'Експат', icon: 'fa-plane', color: 'bg-indigo-950/50 text-indigo-300 border-indigo-700/50', desc: 'Бонус до роботи за кордоном' },
            'modest': { name: 'Скромний', icon: 'fa-coins', color: 'bg-emerald-950/50 text-emerald-300 border-emerald-700/50', desc: 'Знижені вимоги до зарплати' },
            'scavenger': { name: 'Збирач', icon: 'fa-magnifying-glass', color: 'bg-cyan-950/50 text-cyan-300 border-cyan-700/50', desc: 'Знаходить додаткові ресурси' },
            'trainer': { name: 'Тренер', icon: 'fa-dumbbell', color: 'bg-violet-950/50 text-violet-300 border-violet-700/50', desc: 'Підвищує ефективність тренувань' },
            'diamondInTheRough': { name: 'Необроблений алмаз', icon: 'fa-gem', color: 'bg-cyan-950/50 text-cyan-300 border-cyan-700/50', desc: 'Високий прихований потенціал' },
            'handy': { name: 'Майстер', icon: 'fa-wrench', color: 'bg-stone-800 text-stone-300 border-stone-600', desc: 'Повільніше зношує інструменти' },
            'anchor': { name: 'Якір', icon: 'fa-anchor', color: 'bg-slate-800 text-slate-300 border-slate-600', desc: 'Стабілізує щастя колективу' },
            'recruiter': { name: 'Рекрутер', icon: 'fa-bullhorn', color: 'bg-orange-950/50 text-orange-300 border-orange-700/50', desc: 'Допомагає наймати персонал' },
            'stockpiler': { name: 'Завскладом', icon: 'fa-boxes-stacked', color: 'bg-yellow-950/50 text-yellow-300 border-yellow-700/50', desc: 'Збільшує місткість сховища' },
            'comic': { name: 'Комік', icon: 'fa-masks-theater', color: 'bg-pink-950/50 text-pink-300 border-pink-700/50', desc: 'Підвищує настрій колег на фабриці' },
            'improviser': { name: 'Імпровізатор', icon: 'fa-wand-magic-sparkles', color: 'bg-fuchsia-950/50 text-fuchsia-300 border-fuchsia-700/50', desc: 'Швидше звикає до нових товарів' },
            'creatureOfHabit': { name: 'Людина звички', icon: 'fa-clock', color: 'bg-blue-950/50 text-blue-300 border-blue-700/50', desc: 'Бонус за тривалий стаж на фабриці' },
            'patriot': { name: 'Патріот', icon: 'fa-flag', color: 'bg-yellow-950/50 text-yellow-300 border-yellow-700/50', desc: 'Бонус виробітку в рідній країні' },
            'nationalist': { name: 'Націоналіст', icon: 'fa-landmark', color: 'bg-amber-950/50 text-amber-300 border-amber-700/50', desc: 'Бонус серед співвітчизників' },
            'loner': { name: 'Одинак', icon: 'fa-user', color: 'bg-gray-800 text-gray-300 border-gray-600', desc: 'Краще працює наодинці' },
            'envious': { name: 'Заздрісний', icon: 'fa-triangle-exclamation', color: 'bg-red-950/50 text-red-300 border-red-700/50', desc: 'Втрачає настрій через чужі зарплати' },
            'earlyBloomer': { name: 'Ранній розквіт', icon: 'fa-sun', color: 'bg-amber-950/50 text-amber-300 border-amber-700/50', desc: 'Швидко розвивається в молодому віці' }
        };

        const ITEM_TRANSLATIONS = {
            'cocain': { name: 'Кокаїн', icon: '💊', color: 'text-rose-400' },
            'coca': { name: 'Листя коки', icon: '🌿', color: 'text-emerald-400' },
            'cookedFish': { name: 'Смажена риба', icon: '🍱', color: 'text-amber-400' },
            'fish': { name: 'Риба', icon: '🐟', color: 'text-sky-400' },
            'lightAmmo': { name: 'Легкі набої', icon: '🎯', color: 'text-yellow-400' },
            'heavyAmmo': { name: 'Важкі набої', icon: '🚀', color: 'text-red-400' },
            'lead': { name: 'Свинець', icon: '🔘', color: 'text-gray-400' },
            'steel': { name: 'Сталь', icon: '🏗️', color: 'text-cyan-400' },
            'iron': { name: 'Залізна руда', icon: '⛏️', color: 'text-orange-400' },
            'concrete': { name: 'Бетон', icon: '🧱', color: 'text-stone-400' },
            'limestone': { name: 'Вапняк', icon: '🪨', color: 'text-stone-300' },
            'paper': { name: 'Папір', icon: '📜', color: 'text-yellow-200' },
            'wood': { name: 'Деревина', icon: '🪵', color: 'text-amber-700' },
            'oil': { name: 'Нафта', icon: '🛢️', color: 'text-purple-400' },
            'fuel': { name: 'Паливо', icon: '⛽', color: 'text-rose-500' },
            'aluminum': { name: 'Алюміній', icon: '🪙', color: 'text-zinc-300' },
            'bauxite': { name: 'Боксити', icon: '🏔️', color: 'text-stone-500' },
            'medkit': { name: 'Аптечка', icon: '🩹', color: 'text-emerald-300' }
        };

        const COUNTRY_FLAGS = {
            'ua': '🇺🇦', 'bo': '🇧🇴', 'tt': '🇹🇹', 'mt': '🇲🇹', 'rw': '🇷🇼',
            'us': '🇺🇸', 'gb': '🇬🇧', 'de': '🇩🇪', 'pl': '🇵🇱', 'fr': '🇫🇷',
            'es': '🇪🇸', 'it': '🇮🇹', 'ca': '🇨🇦', 'br': '🇧🇷', 'jp': '🇯🇵'
        };

        function getItemMeta(code) {
            if (!code) return { name: 'Невідомо', icon: '📦', color: 'text-gray-400' };
            const lower = code.toLowerCase();
            for (const [k, v] of Object.entries(ITEM_TRANSLATIONS)) {
                if (k.toLowerCase() === lower) return v;
            }
            return { name: code, icon: '📦', color: 'text-gray-400' };
        }

        function getCountryFlag(code) {
            if (!code) return '🌐';
            const lower = code.toLowerCase();
            if (COUNTRY_FLAGS[lower]) return COUNTRY_FLAGS[lower];
            if (code.length === 2) {
                return String.fromCodePoint(...[...code.toUpperCase()].map(c => 127397 + c.charCodeAt(0)));
            }
            return '🌐';
        }

        function toggleCompanyAccordion(cid) {
            if (workerExpandedCompanies.has(cid)) {
                workerExpandedCompanies.delete(cid);
            } else {
                workerExpandedCompanies.add(cid);
            }
            renderCompaniesCards();
        }

        function toggleAllWorkerCompanies(expand) {
            if (!currentData || !currentData.companies) return;
            if (expand) {
                currentData.companies.forEach(c => workerExpandedCompanies.add(c.company_id));
            } else {
                workerExpandedCompanies.clear();
            }
            renderCompaniesCards();
        }

        // Auto-detect Ingress / Reverse Proxy base URL
        const BASE_PATH = window.location.pathname.replace(/\/+$/, '');
        function getApiUrl(endpoint) {
            const cleanEndpoint = endpoint.replace(/^\/+/, '');
            return BASE_PATH ? `${BASE_PATH}/${cleanEndpoint}` : `/${cleanEndpoint}`;
        }

        async function fetchData() {
            const nick = document.getElementById('userSearchInput').value.trim() || 'Luc1fer';
            addRecentSearch(nick);

            // Update URL without reloading page
            const url = new URL(window.location);
            url.searchParams.set('nick', nick);
            window.history.replaceState({}, '', url);

            const refreshIcon = document.getElementById('refreshIcon');
            refreshIcon.classList.add('fa-spin');

            const headers = {};
            const userKey = getUserApiKey();
            if (userKey) {
                headers['X-User-API-Key'] = userKey;
            }

            try {
                const res = await fetch(getApiUrl(`api/analyze?nick=${encodeURIComponent(nick)}`), { headers });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.error || 'Помилка завантаження даних');
                }
                currentData = await res.json();
                if (currentData.companies && currentData.companies.length > 0 && workerExpandedCompanies.size === 0) {
                    workerExpandedCompanies.add(currentData.companies[0].company_id);
                }
                renderAll();
            } catch (err) {
                showToast(`Помилка: ${err.message}`);
            } finally {
                refreshIcon.classList.remove('fa-spin');
            }
        }

        function renderAll() {
            if (!currentData) return;

            const u = currentData.user;
            const s = currentData.summary;

            // Player Banner
            document.getElementById('playerUsername').innerText = u.username;
            document.getElementById('playerAvatarLetter').innerText = u.username.charAt(0).toUpperCase();
            document.getElementById('playerLevel').innerText = `Lv.${u.level}`;
            document.getElementById('playerGameLink').href = `https://app.warera.io/user/${u.user_id}`;
            const flag = getCountryFlag(u.country_code);
            document.getElementById('playerCountry').innerHTML = `<span class="mr-1">${flag}</span>${u.country_name || 'Україна'}`;
            
            const prodSkill = u.production_skill || {};
            const mgmtPts = u.management_pts || 0;
            const mgmtBonus = u.management_bonus_pct || 0;
            document.getElementById('playerProdSkill').innerHTML = `
                <span class="inline-flex items-center gap-1"><i class="fa-solid fa-bolt text-yellow-400"></i> Виробіток: ${prodSkill.value || 0} PP</span>
                <span class="inline-flex items-center gap-1 ml-2 text-indigo-300"><i class="fa-solid fa-user-tie text-indigo-400"></i> Менеджмент: ${mgmtPts} очок (+${mgmtBonus}% бонус)</span>
            `;

            // 9 Summary Cards
            if (document.getElementById('statCompaniesCount')) {
                document.getElementById('statCompaniesCount').innerText = s.total_companies;
                document.getElementById('statCompaniesSub').innerText = `${s.companies_with_staff || s.total_companies} з робітниками · ${s.companies_with_manager || 0} з менеджером`;
            }
            if (document.getElementById('statTotalOutput')) {
                document.getElementById('statTotalOutput').innerText = `${(s.total_daily_output || 0).toLocaleString('uk-UA', {maximumFractionDigits: 1})} PP`;
                document.getElementById('statOutputSub').innerText = `${(s.total_employee_output || 0).toFixed(0)} персонал · ${(s.total_engine_output || 0).toFixed(0)} двигуни`;
            }
            if (document.getElementById('statToolboxes')) {
                document.getElementById('statToolboxes').innerText = `~${(s.total_toolboxes_daily || 0).toFixed(1)} шт`;
            }
            if (document.getElementById('statGoodsValue')) {
                document.getElementById('statGoodsValue').innerText = `+${(s.total_goods_value_daily || 0).toFixed(2)}`;
            }
            if (document.getElementById('statWagesDaily')) {
                document.getElementById('statWagesDaily').innerText = `-${(s.total_wages_daily || 0).toFixed(2)}`;
            }
            if (document.getElementById('statManagersDaily')) {
                document.getElementById('statManagersDaily').innerText = `${(s.total_manager_daily || 0).toFixed(2)}`;
            }
            if (document.getElementById('statInGameProfit')) {
                const igp = s.in_game_profit_daily || 0;
                document.getElementById('statInGameProfit').innerText = (igp >= 0 ? '+' : '') + igp.toFixed(2);
                document.getElementById('statInGameProfit').className = igp >= 0 ? 'mt-2 text-2xl font-black text-purple-300' : 'mt-2 text-2xl font-black text-rose-400';
            }
            if (document.getElementById('statDailyProfit')) {
                const np = s.total_daily_profit || 0;
                document.getElementById('statDailyProfit').innerText = (np >= 0 ? '+' : '') + np.toFixed(2);
                document.getElementById('statDailyProfit').className = np >= 0 ? 'mt-2 text-2xl font-black text-emerald-400' : 'mt-2 text-2xl font-black text-rose-400';
                if (document.getElementById('statDailyProfitWithSelf')) {
                    const withSelf = s.total_daily_profit_with_self || np;
                    document.getElementById('statDailyProfitWithSelf').innerText = `+${withSelf.toFixed(2)} з власною працею`;
                }
            }
            if (document.getElementById('statStaffCount')) {
                document.getElementById('statStaffCount').innerText = `${s.total_workforce} робітників`;
                if (document.getElementById('statStaffSub')) {
                    document.getElementById('statStaffSub').innerText = `${s.trainable_count || 0} готові до тренування`;
                }
            }

            // Render Insights (Lowest Tax Countries)
            const taxListEl = document.getElementById('lowestTaxList');
            if (taxListEl && s.lowest_tax_countries) {
                taxListEl.innerHTML = s.lowest_tax_countries.map(c => `
                    <div class="px-2.5 py-1 rounded-lg bg-gray-900/80 border border-bordercolor flex items-center gap-1.5 hover:border-gray-600 transition-colors">
                        <span>${getCountryFlag(c.code)}</span>
                        <span class="font-medium text-gray-200">${c.name}</span>
                        <span class="text-[10px] text-emerald-400 font-mono ml-1">прибутковий ${c.income_tax}% · ринок ${c.market_tax}%</span>
                    </div>
                `).join('');
            }

            // Render Insights (Best Products Right Now)
            const prodListEl = document.getElementById('bestProductsList');
            if (prodListEl && s.best_products) {
                prodListEl.innerHTML = s.best_products.map((p, idx) => {
                    const meta = getItemMeta(p.code);
                    return `
                        <div class="px-2.5 py-1 rounded-lg bg-gray-900/80 border border-bordercolor flex items-center gap-1.5 hover:border-gray-600 transition-colors">
                            <span class="font-bold text-amber-400 text-[11px]">#${idx + 1}</span>
                            <span>${meta.icon}</span>
                            <span class="font-medium text-gray-200">${meta.name}</span>
                            <span class="text-[10px] text-yellow-300 font-mono ml-1">${p.margin_per_100.toFixed(2)} Coins/100 PP</span>
                        </div>
                    `;
                }).join('');
            }

            // Filter Counts
            document.getElementById('cntAll').innerText = s.total_workforce;
            document.getElementById('cntKeep').innerText = s.keep_count;
            document.getElementById('cntRelocate').innerText = s.relocate_count;
            document.getElementById('cntUnder').innerText = s.underperformer_count;
            document.getElementById('cntToxic').innerText = s.toxic_count;

            // Auth Banner state
            const auth = currentData.auth || {};
            const alertBanner = document.getElementById('workerAuthAlertBanner');
            const alertTitle = document.getElementById('workerAuthAlertTitle');
            const alertMsg = document.getElementById('workerAuthAlertMsg');
            
            if (alertBanner) {
                if (auth.auth_failed && !auth.is_community_key) {
                    alertBanner.className = 'bg-rose-950/60 border border-rose-500/60 rounded-xl p-3.5 flex items-center justify-between text-rose-200 shadow-lg';
                    alertTitle.innerText = 'Помилка авторизації WarEra API (401 Unauthorized)';
                    alertMsg.innerText = 'Сервер WarEra відхилив токен. Перевірте його в грі або використовуйте автоматичний ключ спільноти.';
                } else if (currentData.employees_flat.length === 0 && currentData.companies.length > 0) {
                    alertBanner.className = 'bg-blue-950/50 border border-blue-500/50 rounded-xl p-3.5 flex items-center justify-between text-blue-200';
                    alertTitle.innerText = 'На фабриках немає робітників';
                    alertMsg.innerText = `На фабриках гравця ${u.username} наразі немає найнятих працівників.`;
                } else {
                    alertBanner.classList.add('hidden');
                }
            }
            updateApiKeyBadgeUI();

            renderWorkersTable();
            renderCompaniesCards();
            renderRelocationCards();
            renderOptimizer();
        }

        function setFilter(f) {
            currentFilter = f;
            ['ALL', 'KEEP', 'RELOCATE', 'UNDERPERFORMER', 'TOXIC'].forEach(id => {
                const el = document.getElementById(`filter${id}`);
                if (id === f) {
                    el.className = 'px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium transition-colors shadow-lg';
                } else {
                    el.className = 'px-3 py-1.5 rounded-lg bg-gray-800 text-gray-400 hover:bg-gray-700 transition-colors';
                }
            });
            renderWorkersTable();
        }

        function sortWorkers(field) {
            if (sortField === field) {
                sortAsc = !sortAsc;
            } else {
                sortField = field;
                sortAsc = false;
            }
            renderWorkersTable();
        }

        function renderWorkersTable() {
            const tbody = document.getElementById('workersTableBody');
            tbody.innerHTML = '';

            let list = [...currentData.employees_flat];
            if (currentFilter !== 'ALL') {
                list = list.filter(e => e.status === currentFilter);
            }

            // Sorting
            list.sort((a, b) => {
                let vA, vB;
                if (sortField === 'name') { vA = a.name; vB = b.name; }
                else if (sortField === 'company') { vA = a.company_name; vB = b.company_name; }
                else if (sortField === 'pp') { vA = a.hourly_pp; vB = b.hourly_pp; }
                else if (sortField === 'wage') { vA = a.wage; vB = b.wage; }
                else if (sortField === 'spec') { vA = a.spec_days; vB = b.spec_days; }
                else if (sortField === 'retire') { vA = a.retire_in_days; vB = b.retire_in_days; }
                else { vA = a.hourly_net_profit; vB = b.hourly_net_profit; }

                if (vA < vB) return sortAsc ? -1 : 1;
                if (vA > vB) return sortAsc ? 1 : -1;
                return 0;
            });

            if (list.length === 0) {
                const auth = currentData.auth || {};
                let emptyMsg = 'Немає працівників у цій категорії';
                if (auth.auth_failed) {
                    emptyMsg = '⚠️ Не вдалося завантажити робітників через помилку авторизації API (401 Unauthorized). <button onclick="openApiKeyModal()" class="ml-1 underline font-semibold text-rose-300 hover:text-white">Оновити API-ключ</button>';
                } else if (!auth.key_present) {
                    emptyMsg = 'ℹ️ Для відображення робітників фабрик введіть ваш API-ключ з гри. <button onclick="openApiKeyModal()" class="ml-1 underline font-semibold text-amber-300 hover:text-white">Ввести ключ</button>';
                } else if (currentData.employees_flat.length === 0) {
                    emptyMsg = 'На фабриках цього гравця наразі немає найнятих працівників або ростер робітників приватний.';
                }
                tbody.innerHTML = `<tr><td colspan="10" class="p-8 text-center text-gray-400">${emptyMsg}</td></tr>`;
                return;
            }

            list.forEach(emp => {
                const statusBadge = getStatusBadge(emp.status);
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-hoverbg/60 transition-colors';

                const profitClass = emp.hourly_net_profit >= 0 ? 'text-emerald-400 font-semibold' : 'text-red-400 font-bold';
                const retireClass = emp.retire_in_days <= 4 ? 'text-amber-400 font-bold animate-pulse' : 'text-gray-300';

                tr.innerHTML = `
                    <td class="p-3 whitespace-nowrap">${statusBadge}</td>
                    <td class="p-3 font-medium text-white whitespace-nowrap">
                        <div class="flex items-center gap-2">
                            <span>${emp.name}</span>
                            ${emp.tool_name ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-blue-300 border border-gray-700" title="Інструмент: +${emp.tool_bonus_pct}%"><i class="fa-solid fa-wrench mr-1"></i>${emp.tool_name}</span>` : ''}
                        </div>
                        <div class="text-[10px] text-gray-400">Prod: ${emp.total_prod} (баз ${emp.base_prod} + трен ${emp.trained_prod})</div>
                    </td>
                    <td class="p-3 whitespace-nowrap">
                        <div class="text-gray-200 font-medium">${emp.company_name}</div>
                        <div class="text-[10px] text-indigo-400 font-mono">${emp.item_code.toUpperCase()}</div>
                    </td>
                    <td class="p-3 text-right whitespace-nowrap">
                        <div class="font-bold text-gray-100">${emp.hourly_pp.toFixed(2)} PP/год</div>
                        <div class="text-[10px] text-gray-400">${emp.daily_pp.toFixed(1)} PP/добу</div>
                    </td>
                    <td class="p-3 text-right whitespace-nowrap">
                        <div class="text-gray-200 font-mono">${emp.wage.toFixed(4)}</div>
                        <div class="text-[10px] text-gray-400 font-mono">${emp.daily_wage.toFixed(2)}/д</div>
                    </td>
                    <td class="p-3 text-right whitespace-nowrap">
                        <div class="${profitClass} font-mono">${emp.hourly_net_profit >= 0 ? '+' : ''}${emp.hourly_net_profit.toFixed(4)}/г</div>
                        <div class="text-[10px] ${profitClass} font-mono">${emp.daily_net_profit >= 0 ? '+' : ''}${emp.daily_net_profit.toFixed(2)}/д</div>
                    </td>
                    <td class="p-3 text-right font-mono text-yellow-400/90 whitespace-nowrap" title="Максимальна ставка до збитковості">
                        &le; ${emp.breakeven_wage.toFixed(4)}
                    </td>
                    <td class="p-3 text-center whitespace-nowrap">
                        <div class="font-semibold text-gray-200">${emp.spec_days} дн.</div>
                        <div class="text-[10px] text-emerald-400">+${emp.bonus_total_pct.toFixed(1)}%</div>
                    </td>
                    <td class="p-3 text-center whitespace-nowrap">
                        <div class="${retireClass}">${emp.retire_in_days} дн.</div>
                        ${emp.quit_chance > 0 ? `<div class="text-[10px] text-red-400">ризик ${emp.quit_chance}%</div>` : '<div class="text-[10px] text-gray-500">стабільний</div>'}
                    </td>
                    <td class="p-3 text-xs text-gray-300 max-w-xs leading-tight">
                        ${emp.recommendation}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function getStatusBadge(st) {
            switch(st) {
                case 'TOXIC':
                    return '<span class="px-2 py-1 rounded bg-red-900/60 text-red-300 border border-red-700/60 font-semibold text-[10px]"><i class="fa-solid fa-triangle-exclamation mr-1"></i>ЗБИТКОВИЙ</span>';
                case 'RELOCATE':
                    return '<span class="px-2 py-1 rounded bg-blue-900/60 text-blue-300 border border-blue-700/60 font-semibold text-[10px]"><i class="fa-solid fa-shuffle mr-1"></i>ПЕРЕВОД</span>';
                case 'UNDERPERFORMER':
                    return '<span class="px-2 py-1 rounded bg-amber-900/60 text-amber-300 border border-amber-700/60 font-semibold text-[10px]"><i class="fa-solid fa-hourglass-half mr-1"></i>СЛАБКИЙ</span>';
                default:
                    return '<span class="px-2 py-1 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-700/60 font-semibold text-[10px]"><i class="fa-solid fa-check mr-1"></i>ЯДРО</span>';
            }
        }

        function renderCompaniesCards() {
            const container = document.getElementById('contentCompanies');
            if (!container || !currentData) return;
            container.innerHTML = '';

            const comps = currentData.companies || [];
            if (comps.length === 0) {
                container.innerHTML = `<div class="p-8 text-center text-gray-400 glass-panel rounded-xl">Підприємств не знайдено.</div>`;
                return;
            }

            // Top control bar (Collapse/Expand All + Filter)
            const controlBar = document.createElement('div');
            controlBar.className = 'flex items-center justify-between pb-1 flex-wrap gap-2 text-xs';
            controlBar.innerHTML = `
                <div class="text-xs text-gray-400">
                    Всього підприємств: <span class="font-bold text-white">${comps.length}</span> · 
                    З персоналом: <span class="font-bold text-emerald-400">${comps.filter(c => c.staff_count > 0).length}</span>
                </div>
                <div class="flex items-center gap-2">
                    <button onclick="toggleAllWorkerCompanies(true)" class="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition-colors flex items-center gap-1.5 shadow">
                        <i class="fa-solid fa-angles-down text-blue-400"></i> Розгорнути всі
                    </button>
                    <button onclick="toggleAllWorkerCompanies(false)" class="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition-colors flex items-center gap-1.5 shadow">
                        <i class="fa-solid fa-angles-up text-gray-400"></i> Згорнути всі
                    </button>
                </div>
            `;
            container.appendChild(controlBar);

            comps.forEach(comp => {
                const isExpanded = workerExpandedCompanies.has(comp.company_id);
                const itemMeta = getItemMeta(comp.item_code);
                const flag = getCountryFlag(comp.country_code);

                const card = document.createElement('div');
                card.className = 'glass-panel rounded-2xl border border-bordercolor overflow-hidden shadow-lg transition-all hover:border-gray-600/80';

                // Badges
                const rawSupplyBadge = comp.raw_from_own 
                    ? `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/50" title="Сировина надходить з ваших шахт/ферм, тому не купується з ринку"><i class="fa-solid fa-leaf mr-1"></i>Власна сировина</span>` 
                    : '';
                const incomeTax = comp.taxes ? (comp.taxes.income || 0) : 20;
                const taxBadgeClass = incomeTax > 0 
                    ? 'bg-amber-950/60 text-amber-300 border-amber-700/50' 
                    : 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50';
                const taxBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${taxBadgeClass}">${incomeTax}% прибутковий</span>`;
                const managerBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-700/50">Менеджер: рівень 10</span>`;

                const totalDailyPp = comp.total_daily_pp || (comp.daily_pp + (comp.engine_daily_pp || 0));
                const totalDailyUnits = comp.total_daily_units || comp.daily_units;
                const empSharePct = comp.employees_share_pct || 0;
                const engLv = comp.engine_level || 0;
                const wagesDaily = comp.wages_daily || 0;
                const netDaily = comp.daily_net_profit || 0;
                const withSelfDaily = comp.net_daily_with_self_work || netDaily;

                // Header HTML
                const headerHtml = `
                    <div onclick="toggleCompanyAccordion('${comp.company_id}')" class="p-4 sm:p-5 cursor-pointer flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 select-none hover:bg-gray-800/30 transition-colors">
                        <!-- Left: Item Icon + Company Name & Subtitle + Badges -->
                        <div class="flex items-start gap-3.5 min-w-[280px]">
                            <div class="w-12 h-12 rounded-xl bg-gray-900 border border-gray-700 flex items-center justify-center text-2xl shrink-0 shadow-inner">
                                ${itemMeta.icon}
                            </div>
                            <div>
                                <div class="flex items-center gap-2 flex-wrap">
                                    <h4 class="text-base font-black text-white tracking-wide uppercase">${comp.name}</h4>
                                </div>
                                <div class="text-xs text-gray-400 flex items-center gap-1.5 mt-0.5">
                                    <span class="font-medium text-gray-300">${itemMeta.name}</span>
                                    <span>·</span>
                                    <span>${flag}</span>
                                    <span>${comp.region_name || 'Центральна Україна'}</span>
                                </div>
                                <div class="flex items-center gap-1.5 mt-2 flex-wrap">
                                    ${managerBadge}
                                    ${taxBadge}
                                    ${rawSupplyBadge}
                                </div>
                            </div>
                        </div>

                        <!-- 5 Metric Columns (Arcana Style) -->
                        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 w-full lg:w-auto text-xs shrink-0 py-1">
                            <!-- 1. Output / Day -->
                            <div class="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80 min-w-[110px]">
                                <div class="text-gray-400 text-[10px] uppercase font-bold tracking-wider">Випуск / добу</div>
                                <div class="font-extrabold text-white text-sm mt-0.5">${totalDailyPp.toFixed(1)} <span class="text-[11px] font-normal text-gray-400">PP</span></div>
                                <div class="text-[10px] text-gray-400">${totalDailyUnits.toFixed(2)} ${itemMeta.name}</div>
                            </div>

                            <!-- 2. By Employees -->
                            <div class="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80 min-w-[110px]">
                                <div class="text-gray-400 text-[10px] uppercase font-bold tracking-wider">Робітниками</div>
                                <div class="font-extrabold text-sky-400 text-sm mt-0.5">${empSharePct.toFixed(0)}%</div>
                                <div class="text-[10px] text-gray-400">${(comp.daily_pp || 0).toFixed(1)} PP · двигун ${engLv}</div>
                            </div>

                            <!-- 3. Costs / Day -->
                            <div class="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80 min-w-[110px]">
                                <div class="text-gray-400 text-[10px] uppercase font-bold tracking-wider">Витрати / добу</div>
                                <div class="font-extrabold text-rose-400 text-sm mt-0.5">-${wagesDaily.toFixed(2)}</div>
                                <div class="text-[10px] text-gray-400">зарплати ${wagesDaily.toFixed(2)} · mgr 0.00</div>
                            </div>

                            <!-- 4. Manager -->
                            <div class="bg-gray-900/60 p-2.5 rounded-xl border border-gray-800/80 min-w-[110px]">
                                <div class="text-gray-400 text-[10px] uppercase font-bold tracking-wider">Менеджер</div>
                                <div class="font-bold text-gray-300 text-sm mt-0.5">Найм</div>
                                <div class="text-[10px] text-gray-400">до 0.143/год</div>
                            </div>

                            <!-- 5. Net / Day -->
                            <div class="bg-emerald-950/20 p-2.5 rounded-xl border border-emerald-800/40 min-w-[110px]">
                                <div class="text-emerald-400 text-[10px] uppercase font-bold tracking-wider">Чистий / добу</div>
                                <div class="font-black text-emerald-400 text-sm mt-0.5">+${netDaily.toFixed(2)}</div>
                                <div class="text-[10px] text-gray-400">+${withSelfDaily.toFixed(2)} з роботою</div>
                            </div>
                        </div>

                        <!-- Chevron button -->
                        <div class="flex items-center gap-2 self-end lg:self-center shrink-0">
                            <span class="text-xs px-2.5 py-1 rounded-full ${comp.staff_count >= comp.staff_cap ? 'bg-amber-950/70 text-amber-300 border border-amber-700/50' : 'bg-emerald-950/70 text-emerald-300 border border-emerald-700/50'}">
                                ${comp.staff_count} / ${comp.staff_cap} робітників
                            </span>
                            <div class="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center text-gray-400 hover:text-white transition-all transform ${isExpanded ? 'rotate-180 bg-blue-600 text-white' : ''}">
                                <i class="fa-solid fa-chevron-down text-xs"></i>
                            </div>
                        </div>
                    </div>
                `;

                // Expanded Section HTML
                let bodyHtml = '';
                if (isExpanded) {
                    const balanceTip = (comp.goods_value_daily || 0) >= wagesDaily
                        ? `Товар (+${(comp.goods_value_daily || 0).toFixed(2)}) повністю покриває зарплати (-${wagesDaily.toFixed(2)}). Фабрика стабільно генерує прибуток!`
                        : `Увага: зарплати робітників перевищують ринкову вартість готової продукції! Знизьте ставки або змініть товар.`;

                    // Employees list cards
                    let employeesCardsHtml = '';
                    if (!comp.employees || comp.employees.length === 0) {
                        employeesCardsHtml = `
                            <div class="p-6 text-center text-gray-400 bg-gray-900/50 rounded-xl border border-gray-800">
                                <i class="fa-solid fa-user-slash text-xl mb-2 text-gray-500"></i>
                                <div>На цьому підприємстві наразі немає найнятих працівників.</div>
                                <div class="text-xs text-gray-500 mt-1">Кімната відпочинку ${comp.break_room_level} ур. дозволяє найняти до ${comp.staff_cap} робітників.</div>
                            </div>
                        `;
                    } else {
                        employeesCardsHtml = comp.employees.map(emp => {
                            let statusBadge = '';
                            if (emp.status === 'KEEP') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/70 text-emerald-300 border border-emerald-700/50">💎 Ядро</span>`;
                            } else if (emp.status === 'RELOCATE') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-950/70 text-blue-300 border border-blue-700/50">🔄 На переведення</span>`;
                            } else if (emp.status === 'UNDERPERFORMER') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950/70 text-amber-300 border border-amber-700/50">⚠️ Слабкий</span>`;
                            } else {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950/70 text-rose-300 border border-rose-700/50">🚨 Збитковий</span>`;
                            }

                            const pensionBadge = emp.retire_in_days <= 30 
                                ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/40 text-rose-300 border border-rose-700/40"><i class="fa-solid fa-hourglass-half mr-1"></i>Пенсія: ${emp.retire_in_days} дн.</span>` 
                                : '';

                            const traitChips = (emp.traits || []).map(t => {
                                const code = t.code;
                                const tr = TRAIT_MAP[code] || { name: code, icon: 'fa-tag', color: 'bg-gray-800 text-gray-300 border-gray-700', desc: '' };
                                const argLabel = t.arg ? ` (${t.arg})` : '';
                                return `<span class="px-2 py-0.5 rounded text-[10px] font-medium border flex items-center gap-1 ${tr.color}" title="${tr.desc}"><i class="fa-solid ${tr.icon} text-[9px]"></i> ${tr.name}${argLabel}</span>`;
                            }).join('');

                            const specChips = Object.entries(emp.specializations || {}).map(([sItem, sDays]) => {
                                const sMeta = getItemMeta(sItem);
                                return `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-950/60 text-indigo-300 border border-indigo-700/40">${sMeta.icon} ${sItem} ${sDays}д</span>`;
                            }).join('');

                            const bonusBreakdownText = (emp.bonus_contributions || []).map(bc => `${bc.source}: +${bc.percent}%`).join(' · ');
                            const potPct = emp.potential_max > 0 ? Math.min(100, (emp.potential / emp.potential_max) * 100) : 100;

                            const trainedProd = emp.trained_stats ? (emp.trained_stats.production || 0) : 0;
                            const trainedLuck = emp.trained_stats ? (emp.trained_stats.luck || 0) : 0;
                            const trainedResp = emp.trained_stats ? (emp.trained_stats.responsibility || 0) : 0;
                            const trainedLine = `+${trainedProd} виробіток · +${trainedLuck} удача · +${trainedResp} відпов.`;

                            const inGameVal = (emp.daily_net_profit * 1.13).toFixed(2);

                            return `
                                <div class="bg-gray-900/70 p-4 rounded-xl border border-gray-800/90 space-y-3 hover:border-gray-700 transition-all shadow-md">
                                    <!-- Worker Top: Name, Age, Training Status, Status & Pension -->
                                    <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-gray-800/60">
                                        <div>
                                            <div class="flex items-center gap-2">
                                                <h5 class="text-sm font-bold text-white uppercase tracking-wider">${emp.name}</h5>
                                                ${statusBadge}
                                                ${pensionBadge}
                                            </div>
                                            <div class="text-xs text-gray-400 mt-0.5">
                                                <span>${emp.age} років</span>
                                                <span class="mx-1.5">·</span>
                                                <span class="text-sky-300">${emp.trainings_left || 0} тренувань залишилось сьогодні</span>
                                                <span class="mx-1.5">·</span>
                                                <span>Стаж: <strong class="text-gray-200">${emp.spec_days} дн.</strong></span>
                                            </div>
                                        </div>
                                        <div class="text-right text-xs">
                                            <span class="text-gray-400">Очікувана зарплата:</span>
                                            <span class="font-mono text-gray-200 ml-1 font-semibold">${(emp.wage_expectation || 0).toFixed(3)}/год</span>
                                            <span class="text-gray-500 text-[10px]">(факт: ${emp.wage.toFixed(4)})</span>
                                        </div>
                                    </div>

                                    <!-- Main Stats Grid (Production, Bonus, Happiness, Potential, Points, Wage, Net, In Game) -->
                                    <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 text-xs">
                                        <!-- 1. Production -->
                                        <div class="bg-gray-800/50 p-2.5 rounded-lg border border-gray-700/40">
                                            <div class="text-[10px] uppercase font-bold text-gray-400">Виробіток</div>
                                            <div class="text-base font-black text-white mt-0.5">${emp.total_prod}</div>
                                            <div class="text-[10px] text-gray-400 font-mono">${emp.base_prod}+${emp.trained_prod}</div>
                                        </div>

                                        <!-- 2. Bonus -->
                                        <div class="bg-gray-800/50 p-2.5 rounded-lg border border-gray-700/40 cursor-help" title="${bonusBreakdownText}">
                                            <div class="text-[10px] uppercase font-bold text-gray-400 flex items-center justify-between">
                                                <span>Бонус</span>
                                                <i class="fa-solid fa-circle-info text-[9px] text-gray-500"></i>
                                            </div>
                                            <div class="text-base font-black text-yellow-400 mt-0.5">+${emp.bonus_total_pct.toFixed(1)}%</div>
                                            <div class="text-[10px] text-gray-400 truncate">${bonusBreakdownText || 'Базовий'}</div>
                                        </div>

                                        <!-- 3. Happiness -->
                                        <div class="bg-gray-800/50 p-2.5 rounded-lg border border-gray-700/40">
                                            <div class="text-[10px] uppercase font-bold text-gray-400">Щастя</div>
                                            <div class="text-base font-black text-sky-400 mt-0.5">${emp.happiness.toFixed(0)}%</div>
                                            <div class="text-[10px] text-gray-400">настрій робітника</div>
                                        </div>

                                        <!-- 4. Potential -->
                                        <div class="bg-gray-800/50 p-2.5 rounded-lg border border-gray-700/40">
                                            <div class="text-[10px] uppercase font-bold text-gray-400 flex items-center justify-between">
                                                <span>Потенціал</span>
                                                <span class="font-mono text-gray-300">${emp.potential}/${emp.potential_max}</span>
                                            </div>
                                            <div class="w-full bg-gray-700 h-2 rounded-full overflow-hidden mt-1.5">
                                                <div class="bg-teal-500 h-full rounded-full transition-all" style="width: ${potPct}%"></div>
                                            </div>
                                            <div class="text-[9px] text-gray-400 mt-1">шкала розвитку</div>
                                        </div>

                                        <!-- 5. Points -->
                                        <div class="bg-gray-800/50 p-2.5 rounded-lg border border-gray-700/40">
                                            <div class="text-[10px] uppercase font-bold text-gray-400">Очки (PP)</div>
                                            <div class="text-base font-black text-yellow-300 mt-0.5">${emp.daily_pp.toFixed(1)}</div>
                                            <div class="text-[10px] text-gray-400 font-mono">${emp.hourly_pp.toFixed(2)}/год</div>
                                        </div>

                                        <!-- 6. Wage -->
                                        <div class="bg-gray-800/50 p-2.5 rounded-lg border border-gray-700/40">
                                            <div class="text-[10px] uppercase font-bold text-gray-400">Зарплата</div>
                                            <div class="text-base font-black text-rose-400 mt-0.5">-${emp.daily_wage.toFixed(2)}</div>
                                            <div class="text-[10px] text-gray-400 font-mono">${emp.wage.toFixed(4)}/год</div>
                                        </div>

                                        <!-- 7. Net Profit -->
                                        <div class="bg-emerald-950/30 p-2.5 rounded-lg border border-emerald-800/50">
                                            <div class="text-[10px] uppercase font-bold text-emerald-400">Чистий (NET)</div>
                                            <div class="text-base font-black text-emerald-400 mt-0.5">+${emp.daily_net_profit.toFixed(2)}</div>
                                            <div class="text-[10px] text-emerald-400/80 font-mono">+${emp.hourly_net_profit.toFixed(4)}/год</div>
                                        </div>

                                        <!-- 8. In Game -->
                                        <div class="bg-purple-950/30 p-2.5 rounded-lg border border-purple-800/50">
                                            <div class="text-[10px] uppercase font-bold text-purple-300">В грі</div>
                                            <div class="text-base font-black text-purple-300 mt-0.5">+${inGameVal}</div>
                                            <div class="text-[10px] text-gray-400">ігрова оцінка</div>
                                        </div>
                                    </div>

                                    <!-- Traits & Tools & Training Info -->
                                    <div class="bg-gray-800/40 p-3 rounded-lg border border-gray-700/30 text-xs space-y-2">
                                        <!-- Traits & Spec Chips -->
                                        <div class="flex items-center gap-1.5 flex-wrap">
                                            ${traitChips}
                                            ${specChips}
                                            ${emp.tool_name ? `<span class="px-2 py-0.5 rounded text-[10px] bg-teal-950/70 text-teal-300 border border-teal-700/50"><i class="fa-solid fa-wrench mr-1"></i>${emp.tool_name} (${emp.tool_state_pct.toFixed(0)}%)</span>` : ''}
                                        </div>

                                        <!-- Training Progression details -->
                                        <div class="flex flex-wrap items-center justify-between text-[11px] text-gray-400 pt-1 border-t border-gray-700/40 gap-2">
                                            <div>
                                                <span class="text-gray-300 font-medium">Ймовірності при тренуванні:</span>
                                                <span class="text-gray-400 ml-1">Зниження очікувань зарплати 67% · Більше потенціалу 20% · Новий перк 11%</span>
                                            </div>
                                            <div class="text-gray-300">
                                                <span>Натреновано:</span>
                                                <span class="font-mono text-yellow-300 ml-1">${trainedLine}</span>
                                            </div>
                                        </div>

                                        <!-- Break-even & AI Tip -->
                                        <div class="flex items-start gap-2 pt-1 text-[11px] text-gray-300">
                                            <i class="fa-solid fa-lightbulb text-yellow-400 mt-0.5 shrink-0"></i>
                                            <div>
                                                <span class="font-bold text-yellow-300">Порада новачку:</span> 
                                                <span>${emp.recommendation}</span>
                                                <span class="text-gray-400 ml-1 font-mono">(Поріг беззбитковості: ${emp.breakeven_wage.toFixed(4)} Coins/год)</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('');
                    }

                    bodyHtml = `
                        <div class="p-4 sm:p-5 border-t border-bordercolor bg-gray-950/50 space-y-5">
                            <!-- Top Row: Daily Balance + Upgrades & Limits -->
                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                <!-- Card 1: Daily Balance -->
                                <div class="glass-panel p-4 sm:p-5 rounded-xl border border-bordercolor space-y-3 shadow-md">
                                    <div class="flex items-center justify-between">
                                        <div class="flex items-center gap-2">
                                            <i class="fa-solid fa-scale-balanced text-yellow-400"></i>
                                            <h5 class="text-xs font-bold uppercase tracking-wider text-gray-300">Денний баланс фабрики (Daily Balance)</h5>
                                        </div>
                                        <span class="text-xs font-bold text-emerald-400 font-mono">+${netDaily.toFixed(2)} Coins/д</span>
                                    </div>

                                    <div class="space-y-1.5 text-xs divide-y divide-gray-800/80">
                                        <div class="flex justify-between py-1 text-gray-300">
                                            <span>Випуск продукції:</span>
                                            <span class="font-mono font-semibold text-white">${totalDailyPp.toFixed(1)} PP · ${totalDailyUnits.toFixed(2)} од.</span>
                                        </div>
                                        <div class="flex justify-between py-1 text-gray-300">
                                            <span>Ігровий прибуток робітників:</span>
                                            <span class="font-mono text-purple-300 font-semibold">+${(comp.in_game_profit || 0).toFixed(2)} Coins</span>
                                        </div>
                                        <div class="flex justify-between py-1 text-gray-300">
                                            <span>Сировина:</span>
                                            <span class="font-mono ${comp.raw_from_own ? 'text-emerald-400' : 'text-gray-400'} font-semibold">
                                                ${comp.raw_from_own ? 'Власна з ваших підприємств (економія)' : `-${(comp.raw_cost_daily || 0).toFixed(2)} Coins`}
                                            </span>
                                        </div>
                                        <div class="flex justify-between py-1 text-gray-300">
                                            <span>Вартість готового товару:</span>
                                            <span class="font-mono text-indigo-300 font-semibold">+${(comp.goods_value_daily || 0).toFixed(2)} Coins</span>
                                        </div>
                                        <div class="flex justify-between py-1 text-gray-300">
                                            <span>Зарплати персоналу:</span>
                                            <span class="font-mono text-rose-400 font-semibold">-${wagesDaily.toFixed(2)} Coins</span>
                                        </div>
                                        <div class="flex justify-between py-1 text-gray-300">
                                            <span>Витрати на менеджера:</span>
                                            <span class="font-mono text-gray-400 font-semibold">0.00 Coins</span>
                                        </div>
                                        <div class="flex justify-between py-1.5 font-bold text-white bg-gray-800/40 px-2 rounded-lg mt-1">
                                            <span class="text-emerald-400">ЧИСТИЙ ПРИБУТОК (NET):</span>
                                            <span class="font-mono text-emerald-400 text-sm">+${netDaily.toFixed(2)} Coins/добу</span>
                                        </div>
                                    </div>

                                    <div class="text-[11px] text-gray-400 flex items-center justify-between pt-1">
                                        <span>З вашою працею: <strong class="text-yellow-300">+${withSelfDaily.toFixed(2)} Coins</strong></span>
                                        <span class="text-[10px] text-emerald-400">💡 ${balanceTip}</span>
                                    </div>
                                </div>

                                <!-- Card 2: Upgrades & Limits -->
                                <div class="glass-panel p-4 sm:p-5 rounded-xl border border-bordercolor space-y-3 shadow-md flex flex-col justify-between">
                                    <div class="flex items-center gap-2">
                                        <i class="fa-solid fa-gears text-blue-400"></i>
                                        <h5 class="text-xs font-bold uppercase tracking-wider text-gray-300">Покращення та ліміти</h5>
                                    </div>

                                    <div class="grid grid-cols-3 gap-2 text-xs">
                                        <div class="bg-gray-800/60 p-2.5 rounded-lg border border-gray-700/50">
                                            <div class="text-[10px] text-gray-400 font-bold uppercase">Авто-двигун</div>
                                            <div class="font-bold text-white text-sm mt-0.5">${comp.engine_level || 0} рівень</div>
                                            <div class="text-[10px] text-emerald-400 font-mono">+${comp.engine_daily_pp || 0} PP/добу</div>
                                        </div>
                                        <div class="bg-gray-800/60 p-2.5 rounded-lg border border-gray-700/50">
                                            <div class="text-[10px] text-gray-400 font-bold uppercase">Склад</div>
                                            <div class="font-bold text-white text-sm mt-0.5">${comp.storage_level || 0} рівень</div>
                                            <div class="text-[10px] text-gray-400 font-mono">до ${(comp.storage_level || 0) * 200} од.</div>
                                        </div>
                                        <div class="bg-gray-800/60 p-2.5 rounded-lg border border-gray-700/50">
                                            <div class="text-[10px] text-gray-400 font-bold uppercase">Кімната відпочинку</div>
                                            <div class="font-bold text-white text-sm mt-0.5">${comp.break_room_level || 0} рівень</div>
                                            <div class="text-[10px] text-sky-400 font-mono">до ${comp.staff_cap || 1} робітників</div>
                                        </div>
                                    </div>

                                    <!-- Regional Taxes -->
                                    <div class="bg-gray-800/40 p-2.5 rounded-lg border border-gray-700/40 text-xs flex items-center justify-between">
                                        <span class="text-gray-300"><i class="fa-solid fa-receipt text-amber-400 mr-1.5"></i>Податки регіону:</span>
                                        <span class="font-mono text-gray-200">прибутковий <strong class="text-amber-300">${incomeTax}%</strong> · ринок ${(comp.taxes && comp.taxes.market) || 0}% · менеджер ${(comp.taxes && comp.taxes.manager) || 0}%</span>
                                    </div>

                                    <!-- Looking for Manager -->
                                    <div class="bg-gray-800/40 p-2.5 rounded-lg border border-gray-700/40 text-xs flex items-center justify-between">
                                        <span class="text-gray-300"><i class="fa-solid fa-user-tie text-indigo-400 mr-1.5"></i>Пошук менеджера:</span>
                                        <span class="font-mono text-indigo-300">0.013/год за очко навички (до 0.143/год)</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Employees Section Header -->
                            <div class="flex items-center justify-between pt-2">
                                <div class="flex items-center gap-2">
                                    <i class="fa-solid fa-users text-blue-400"></i>
                                    <h5 class="text-xs font-bold uppercase tracking-wider text-gray-200">
                                        Працівники фабрики (${comp.staff_count} з ${comp.staff_cap})
                                    </h5>
                                </div>
                                <span class="text-[11px] text-gray-400">Очки (PP), зарплата та чистий дохід розраховані за добу.</span>
                            </div>

                            <!-- Employees Cards List -->
                            <div class="space-y-3">
                                ${employeesCardsHtml}
                            </div>
                        </div>
                    `;
                }

                card.innerHTML = headerHtml + bodyHtml;
                container.appendChild(card);
            });
        }

        function renderRelocationCards() {
            const container = document.getElementById('relocationCards');
            container.innerHTML = '';

            const relocates = currentData.employees_flat.filter(e => e.status === 'RELOCATE' && e.relocation_target);

            if (relocates.length === 0) {
                container.innerHTML = `
                    <div class="col-span-2 glass-panel p-8 text-center text-gray-400 rounded-xl shadow-lg">
                        <i class="fa-solid fa-circle-check text-emerald-400 text-3xl mb-2"></i>
                        <p class="text-sm font-medium text-white">Всі працівники оптимально розміщені на своїх фабриках!</p>
                        <p class="text-xs text-gray-500 mt-1">Немає вигідних кандидатів на переведення без втрати значної лояльності.</p>
                    </div>
                `;
                return;
            }

            relocates.forEach(emp => {
                const t = emp.relocation_target;
                const card = document.createElement('div');
                card.className = 'glass-panel p-5 rounded-xl space-y-4 border border-blue-500/40 relative overflow-hidden shadow-lg';

                card.innerHTML = `
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-8 rounded-lg bg-blue-600/30 text-blue-400 flex items-center justify-center font-bold">
                                <i class="fa-solid fa-user"></i>
                            </div>
                            <div>
                                <h4 class="font-bold text-white text-sm">${emp.name}</h4>
                                <div class="text-[10px] text-gray-400">Prod: ${emp.hourly_pp.toFixed(2)} PP/год | Спеціалізація: ${emp.spec_days} дн.</div>
                            </div>
                        </div>
                        <span class="px-2.5 py-1 rounded bg-blue-900/60 text-blue-300 text-xs font-bold border border-blue-600">
                            +${t.daily_gain.toFixed(2)} Coins/добу
                        </span>
                    </div>

                    <div class="grid grid-cols-2 gap-3 text-xs bg-gray-900/80 p-3 rounded-lg border border-bordercolor">
                        <div>
                            <span class="text-[10px] text-gray-400 uppercase font-semibold">Поточна фабрика</span>
                            <div class="font-bold text-gray-200 mt-1">${emp.company_name}</div>
                            <div class="text-indigo-400 font-mono text-[10px]">${emp.item_code.toUpperCase()}</div>
                            <div class="text-gray-400 font-mono mt-1">+${(t.current_hourly_profit * 24).toFixed(2)} Coins/добу</div>
                        </div>
                        <div class="border-l border-bordercolor pl-3">
                            <span class="text-[10px] text-blue-400 uppercase font-semibold">Цільова фабрика 🚀</span>
                            <div class="font-bold text-white mt-1">${t.target_company_name}</div>
                            <div class="text-blue-300 font-mono text-[10px]">${t.target_item.toUpperCase()}</div>
                            <div class="text-emerald-400 font-mono font-bold mt-1">+${(t.simulated_hourly_profit * 24).toFixed(2)} Coins/добу</div>
                        </div>
                    </div>

                    <p class="text-xs text-gray-300 leading-relaxed bg-blue-950/30 p-2.5 rounded border border-blue-900/40">
                        💡 <strong class="text-white">Чому це вигідно:</strong> На фабриці "${t.target_company_name}" ресурс ${t.target_item.toUpperCase()} має вищу маржинальність. Оскільки працівник відпрацював на поточному місці лише ${emp.spec_days} дні(в), втрата прогресу спеціалізації незначна та компенсується з перших годин.
                    </p>
                `;
                container.appendChild(card);
            });
        }

        function renderOptimizer() {
            const container = document.getElementById('optimizerTable');
            container.innerHTML = `
                <table class="w-full text-left text-xs">
                    <thead class="bg-gray-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-bordercolor">
                        <tr>
                            <th class="p-3">Фабрика</th>
                            <th class="p-3">Товар</th>
                            <th class="p-3 text-right">Ціна товару</th>
                            <th class="p-3 text-right">Витрати сировини</th>
                            <th class="p-3 text-right">Чиста маржа / 1 PP</th>
                            <th class="p-3 text-right">Поточна середня ставка</th>
                            <th class="p-3 text-right text-yellow-400">Break-even (0% маржі)</th>
                            <th class="p-3 text-right text-emerald-400">Реком. ставка (20% маржі)</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-bordercolor">
                        ${currentData.companies.map(c => `
                            <tr class="hover:bg-hoverbg/50">
                                <td class="p-3 font-semibold text-white">${c.name}</td>
                                <td class="p-3 font-mono text-indigo-400">${c.item_code.toUpperCase()}</td>
                                <td class="p-3 text-right font-mono">${currentData.economics_by_item[c.item_code].market_price.toFixed(4)}</td>
                                <td class="p-3 text-right font-mono text-gray-400">${currentData.economics_by_item[c.item_code].raw_cost.toFixed(4)}</td>
                                <td class="p-3 text-right font-mono text-white font-bold">${c.margin_per_pp.toFixed(5)}</td>
                                <td class="p-3 text-right font-mono text-gray-300">${c.avg_wage.toFixed(4)}</td>
                                <td class="p-3 text-right font-mono font-bold text-yellow-400">&le; ${c.margin_per_pp.toFixed(4)} / PP</td>
                                <td class="p-3 text-right font-mono font-bold text-emerald-400">&le; ${(c.margin_per_pp * 0.8).toFixed(4)} / PP</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }

        function switchTab(t) {
            ['workers', 'companies', 'relocation', 'optimizer'].forEach(tabName => {
                const btn = document.getElementById(`tab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
                const content = document.getElementById(`content${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
                if (tabName === t) {
                    btn.className = 'pb-3 tab-active flex items-center gap-2 whitespace-nowrap';
                    content.classList.remove('hidden');
                } else {
                    btn.className = 'pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap';
                    content.classList.add('hidden');
                }
            });
        }

        // Export Report to Clipboard
        function copyReportToClipboard() {
            if (!currentData) return;
            const u = currentData.user;
            const s = currentData.summary;

            let text = `🏰 *WarEra Workforce Intel Report* — ${u.username} (Lv.${u.level})\n`;
            text += `🏭 Фабрик: ${s.total_companies} | 👥 Персонал: ${s.total_workforce}\n`;
            text += `💰 Чистий прибуток: ${s.total_hourly_profit >= 0 ? '+' : ''}${s.total_hourly_profit.toFixed(4)}/год (${s.total_daily_profit >= 0 ? '+' : ''}${s.total_daily_profit.toFixed(2)} Coins/добу)\n`;
            text += `📊 Статуси: 💎 Ядро: ${s.keep_count} | 🔄 Переведення: ${s.relocate_count} | ⚠️ Слабкі/Пенсія: ${s.underperformer_count} | 🚨 Збиткові: ${s.toxic_count}\n\n`;

            const alerts = currentData.employees_flat.filter(e => e.status !== 'KEEP');
            if (alerts.length > 0) {
                text += `⚠️ *Рекомендації до уваги:*\n`;
                alerts.forEach(e => {
                    text += `• [${e.status}] ${e.name} (${e.company_name}): ${e.recommendation}\n`;
                });
            } else {
                text += `✅ Всі працівники оптимально розподілені, фабрики працюють без збитків!\n`;
            }

            navigator.clipboard.writeText(text).then(() => {
                showToast('Звіт скопійовано в буфер обміну!');
            });
        }

        // Download JSON Report
        function downloadJsonReport() {
            if (!currentData) return;
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentData, null, 2));
            const dlAnchor = document.createElement('a');
            dlAnchor.setAttribute("href", dataStr);
            dlAnchor.setAttribute("download", `warera_workforce_${currentData.user.username}.json`);
            dlAnchor.click();
            dlAnchor.remove();
            showToast('JSON звіт збережено!');
        }

        // Initialize on page load
        window.addEventListener('DOMContentLoaded', () => {
            updateApiKeyBadgeUI();
            renderRecentChips();

            // Check if nick passed in query string
            const params = new URLSearchParams(window.location.search);
            const nickParam = params.get('nick');
            if (nickParam) {
                document.getElementById('userSearchInput').value = nickParam;
            }

            fetchData();
        });
    </script>
</body>
</html>
"""


class WorkerDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Extract API key if user provided personal token via header or query
        user_key = self.headers.get("X-User-API-Key") or query.get("apiKey", [None])[0]
        analyzer = WarEraWorkerAnalyzer(api_key=user_key) if user_key else WarEraWorkerAnalyzer()

        if path == "/" or path == "/index.html" or path == "/workers":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        elif path == "/api/analyze":
            nick = query.get("nick", [None])[0]
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                data = loop.run_until_complete(analyzer.analyze_user(nick))
                loop.close()

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/prices":
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                prices = loop.run_until_complete(analyzer.get_market_prices())
                loop.close()

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(prices, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-API-Key")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_dashboard(host: str = "0.0.0.0", port: int = 8085):
    server = HTTPServer((host, port), WorkerDashboardHandler)
    print(f"\n🚀 [WarEra Workforce Dashboard] запущено на http://{host}:{port}")
    print(f"👉 Відкрийте у браузері: http://localhost:{port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nДашборд зупинено.")
        server.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WarEra Workforce Dashboard")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Хост веб-сервера")
    parser.add_argument("--port", type=int, default=8085, help="Порт веб-сервера")
    args = parser.parse_args()
    start_dashboard(host=args.host, port=args.port)

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

        <!-- Top Stat Cards -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div class="glass-panel p-4 rounded-xl relative overflow-hidden shadow-lg">
                <div class="text-xs text-gray-400 flex items-center justify-between">
                    <span>Чистий прибуток</span>
                    <i class="fa-solid fa-coins text-yellow-400"></i>
                </div>
                <div class="mt-2 flex items-baseline gap-2">
                    <span id="statDailyProfit" class="text-2xl font-black text-green-400">--</span>
                    <span class="text-xs text-gray-400">Coins/добу</span>
                </div>
                <div id="statHourlyProfit" class="text-xs text-gray-400 mt-1">-- Coins/год</div>
            </div>

            <div class="glass-panel p-4 rounded-xl relative overflow-hidden shadow-lg">
                <div class="text-xs text-gray-400 flex items-center justify-between">
                    <span>Підприємства</span>
                    <i class="fa-solid fa-building text-blue-400"></i>
                </div>
                <div class="mt-2 flex items-baseline gap-2">
                    <span id="statCompaniesCount" class="text-2xl font-black text-white">--</span>
                    <span class="text-xs text-gray-400">фабрик</span>
                </div>
                <div id="statStaffCount" class="text-xs text-gray-400 mt-1">Персонал: -- чол</div>
            </div>

            <div class="glass-panel p-4 rounded-xl relative overflow-hidden shadow-lg">
                <div class="text-xs text-gray-400 flex items-center justify-between">
                    <span>Кадрові рокіровки</span>
                    <i class="fa-solid fa-shuffle text-indigo-400"></i>
                </div>
                <div class="mt-2 flex items-baseline gap-2">
                    <span id="statRelocateCount" class="text-2xl font-black text-blue-400">--</span>
                    <span class="text-xs text-gray-400">кандидатів</span>
                </div>
                <div class="text-xs text-blue-400/80 mt-1">на прибутковіші фабрики</div>
            </div>

            <div class="glass-panel p-4 rounded-xl relative overflow-hidden shadow-lg">
                <div class="text-xs text-gray-400 flex items-center justify-between">
                    <span>Ризики / Пенсія</span>
                    <i class="fa-solid fa-clock-rotate-left text-amber-400"></i>
                </div>
                <div class="mt-2 flex items-baseline gap-2">
                    <span id="statRiskCount" class="text-2xl font-black text-amber-400">--</span>
                    <span class="text-xs text-gray-400">потребують уваги</span>
                </div>
                <div id="statToxicCount" class="text-xs text-red-400 mt-1">Збиткових: 0</div>
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
            <button onclick="switchTab('workers')" id="tabWorkers" class="pb-3 tab-active flex items-center gap-2 whitespace-nowrap">
                <i class="fa-solid fa-users"></i>
                <span>Працівники фабрик</span>
            </button>
            <button onclick="switchTab('companies')" id="tabCompanies" class="pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap">
                <i class="fa-solid fa-industry"></i>
                <span>Огляд підприємств</span>
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

        <!-- TAB 1: WORKERS TABLE -->
        <div id="contentWorkers" class="space-y-4">
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

        <!-- TAB 2: COMPANIES CARDS -->
        <div id="contentCompanies" class="hidden grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <!-- Dynamically populated -->
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
            document.getElementById('playerProdSkill').innerHTML = `<i class="fa-solid fa-bolt text-yellow-400 mr-1"></i>Prod Skill: Lv.${u.production_skill.level || 0} (${u.production_skill.value || 0} PP)`;
            document.getElementById('playerCountry').innerHTML = `<i class="fa-solid fa-globe text-blue-400 mr-1"></i>Країна: ${u.country.slice(-6)}`;

            // Top Stats
            document.getElementById('statDailyProfit').innerText = (s.total_daily_profit >= 0 ? '+' : '') + s.total_daily_profit.toFixed(2);
            document.getElementById('statDailyProfit').className = s.total_daily_profit >= 0 ? 'text-2xl font-black text-green-400' : 'text-2xl font-black text-red-400';
            document.getElementById('statHourlyProfit').innerText = `${(s.total_hourly_profit >= 0 ? '+' : '') + s.total_hourly_profit.toFixed(4)} Coins/год`;

            document.getElementById('statCompaniesCount').innerText = s.total_companies;
            document.getElementById('statStaffCount').innerText = `Персонал: ${s.total_workforce} чол`;

            document.getElementById('statRelocateCount').innerText = s.relocate_count;
            document.getElementById('statRiskCount').innerText = s.underperformer_count + s.toxic_count;
            document.getElementById('statToxicCount').innerText = `Збиткових: ${s.toxic_count}`;

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
                    alertMsg.innerText = 'Сервер WarEra відхилив токен. Оновіть його в грі або видаліть для використання автоматичного ключа спільноти.';
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
            container.innerHTML = '';

            currentData.companies.forEach(comp => {
                const card = document.createElement('div');
                card.className = 'glass-panel p-5 rounded-xl space-y-4 hover:border-gray-600 transition-all shadow-lg flex flex-col justify-between';

                const profitClass = comp.daily_net_profit >= 0 ? 'text-emerald-400' : 'text-red-400';

                card.innerHTML = `
                    <div class="space-y-2">
                        <div class="flex items-start justify-between gap-2">
                            <div>
                                <h4 class="text-base font-bold text-white">${comp.name}</h4>
                                <span class="text-xs px-2 py-0.5 rounded bg-indigo-900/40 text-indigo-300 border border-indigo-700/50 font-mono uppercase">${comp.item_code}</span>
                            </div>
                            <span class="text-xs px-2.5 py-1 rounded-full ${comp.staff_count >= comp.staff_cap ? 'bg-amber-900/40 text-amber-300 border border-amber-700/50' : 'bg-emerald-900/40 text-emerald-300 border border-emerald-700/50'}">
                                ${comp.staff_count} / ${comp.staff_cap} місць
                            </span>
                        </div>

                        <div class="grid grid-cols-2 gap-2 text-xs pt-2">
                            <div class="bg-gray-800/60 p-2 rounded-lg">
                                <div class="text-gray-400 text-[10px]">Випуск (PP/год)</div>
                                <div class="font-bold text-white text-sm mt-0.5">${comp.hourly_pp.toFixed(2)} PP</div>
                                <div class="text-[10px] text-gray-400">${comp.hourly_units.toFixed(2)} од/год</div>
                            </div>
                            <div class="bg-gray-800/60 p-2 rounded-lg">
                                <div class="text-gray-400 text-[10px]">Маржа ресурсу</div>
                                <div class="font-bold text-yellow-400 text-sm mt-0.5">${comp.margin_per_pp.toFixed(5)}</div>
                                <div class="text-[10px] text-gray-400">Coins за 1 PP</div>
                            </div>
                        </div>

                        <div class="space-y-1 text-xs pt-1">
                            <div class="flex justify-between text-gray-300">
                                <span>Зарплатний фонд:</span>
                                <span class="font-mono text-gray-200">${comp.hourly_wage_cost.toFixed(4)}/год (${(comp.hourly_wage_cost*24).toFixed(2)}/д)</span>
                            </div>
                            <div class="flex justify-between text-gray-300">
                                <span>Середня ставка:</span>
                                <span class="font-mono text-gray-200">${comp.avg_wage.toFixed(4)}/год</span>
                            </div>
                            <div class="flex justify-between text-gray-300">
                                <span>Рекоменд. макс. ставка:</span>
                                <span class="font-mono text-yellow-400">&le; ${comp.recommended_max_wage.toFixed(4)}</span>
                            </div>
                        </div>
                    </div>

                    <div class="border-t border-bordercolor pt-3 flex items-center justify-between">
                        <span class="text-xs text-gray-400 font-medium">Чистий прибуток:</span>
                        <div class="text-right">
                            <span class="text-base font-black ${profitClass}">${comp.daily_net_profit >= 0 ? '+' : ''}${comp.daily_net_profit.toFixed(2)}</span>
                            <span class="text-xs text-gray-400">Coins/добу</span>
                        </div>
                    </div>
                `;
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

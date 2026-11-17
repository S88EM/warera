"""
Interactive Web Dashboard for WarEra Equipment Market Scanner.
Provides real-time visualization of market bargains, anomalies, stat rolls,
filters by rarity/slot, direct links to game market, and live scanner controls.
Compatible with Home Assistant Ingress and standalone desktop/Raspberry Pi mode.
"""

import asyncio
import json
import os
import sys
import time
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Dict, Any, Optional, List
from urllib.parse import parse_qs, urlparse

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from equipment_data import EQUIPMENT_METADATA, ALL_QUALITIES, QUALITY_TIERS

# Reference to the running EquipmentScannerApp instance
_app_instance: Optional[Any] = None
_loop_instance: Optional[asyncio.AbstractEventLoop] = None


def set_app_instance(app: Any, loop: Optional[asyncio.AbstractEventLoop] = None):
    global _app_instance, _loop_instance
    _app_instance = app
    _loop_instance = loop or getattr(app, "event_loop", None)


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="uk" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WarEra Market Scanner — Вигідні ціни та демпінг</title>
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
                    }
                }
            }
        }

    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0B0F19; }
        ::-webkit-scrollbar-thumb { background: #1F2937; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #374151; }
        @keyframes pulse-slow {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        .animate-pulse-slow { animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    </style>
</head>
<body class="bg-darkbg text-gray-100 min-h-screen flex flex-col">

    <!-- Top Navigation Bar -->
    <header class="border-b border-bordercolor bg-cardbg/90 backdrop-blur sticky top-0 z-40">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-2xl p-2 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 rounded-xl border border-cyan-500/30">⚔️</span>
                <div>
                    <div class="flex items-center space-x-2">
                        <h1 class="text-base sm:text-lg font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                            WarEra Market Scanner
                        </h1>
                        <span id="versionBadge" class="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
                            v--
                        </span>
                    </div>
                    <p class="text-xs text-gray-400 hidden sm:block">Пошук вигідних цін, демпінгу та топ-ролів спорядження</p>
                </div>
            </div>

            <div class="flex items-center space-x-2 sm:space-x-3">
                <!-- Live Pulse Status Badge -->
                <div id="statusPill" class="flex items-center space-x-2 text-xs bg-emerald-950/60 text-emerald-400 px-3 py-1.5 rounded-full border border-emerald-800">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span id="statusText" class="font-medium">Сканує</span>
                    <span class="text-emerald-600">|</span>
                    <span id="pricingModeText" class="font-mono text-[11px]">⚡ Live</span>
                </div>

                <!-- Unified View Switcher (100% Ingress Safe - No Page Reload) -->
                <div class="flex items-center bg-gray-900/90 p-0.5 rounded-lg border border-gray-700">
                    <button id="navBtnMarket" onclick="switchMainView('market')" class="px-2.5 py-1.5 rounded-md bg-blue-600 text-white font-medium text-xs flex items-center space-x-1.5 transition shadow">
                        <i class="fa-solid fa-shield-halved text-amber-400"></i>
                        <span class="hidden sm:inline">⚔️ Спорядження</span>
                    </button>
                    <button id="navBtnWorkers" onclick="switchMainView('workers')" class="px-2.5 py-1.5 rounded-md text-gray-400 hover:text-white font-medium text-xs flex items-center space-x-1.5 transition">
                        <i class="fa-solid fa-industry text-blue-400"></i>
                        <span class="hidden sm:inline">🏭 Фабрики & Кадри</span>
                    </button>
                    <a href="./clan" target="_blank" class="px-2.5 py-1.5 rounded-md text-indigo-300 hover:text-white hover:bg-indigo-900/50 font-medium text-xs flex items-center space-x-1.5 transition" title="Окрема публічна сторінка Штабу Клану для сокланів (без логіну)">
                        <i class="fa-solid fa-users-viewfinder text-indigo-400"></i>
                        <span class="hidden sm:inline">🛡️ Штаб Клану</span>
                    </a>
                </div>

                <!-- Immediate Scan Button -->
                <button id="btnScanNow" onclick="triggerScan()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 active:scale-95 text-xs font-semibold rounded-lg shadow transition flex items-center space-x-1.5" title="Сканувати ринок прямо зараз">
                    <i class="fa-solid fa-arrows-rotate" id="scanIcon"></i>
                    <span class="hidden sm:inline">Сканувати</span>
                </button>

                <!-- Pause / Resume Button -->
                <button id="btnTogglePause" onclick="togglePause()" class="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-semibold rounded-lg border border-bordercolor shadow transition flex items-center space-x-1.5">
                    <i class="fa-solid fa-pause" id="pauseIcon"></i>
                    <span id="pauseBtnText" class="hidden sm:inline">Пауза</span>
                </button>

                <!-- Settings Button -->
                <button onclick="openSettingsModal()" class="p-2 bg-gray-800 hover:bg-gray-700 text-xs font-semibold rounded-lg border border-bordercolor shadow transition text-gray-300 hover:text-white" title="Налаштування сканера">
                    <i class="fa-solid fa-gear"></i>
                </button>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 flex-1 w-full">

        <!-- VIEW 1: MARKET SCANNER (Active by default) -->
        <div id="viewMarket" class="space-y-6">

        <!-- KPI Summary Cards -->
        <section class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div class="bg-cardbg p-4 sm:p-5 rounded-xl border border-bordercolor shadow flex items-center justify-between">
                <div>
                    <div class="text-[11px] sm:text-xs text-gray-400 uppercase tracking-wider font-semibold">Знайдено аномалій</div>
                    <div class="text-xl sm:text-2xl font-bold font-mono text-emerald-400 mt-1" id="statAnomalies">0</div>
                    <div class="text-[11px] text-gray-500 mt-0.5" id="statActiveDeals">0 активних на ринку</div>
                </div>
                <div class="w-10 h-10 sm:w-12 sm:h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center text-xl sm:text-2xl text-emerald-400 border border-emerald-500/20">
                    🎯
                </div>
            </div>

            <div class="bg-cardbg p-4 sm:p-5 rounded-xl border border-bordercolor shadow flex items-center justify-between">
                <div>
                    <div class="text-[11px] sm:text-xs text-gray-400 uppercase tracking-wider font-semibold">Краща знижка</div>
                    <div class="text-xl sm:text-2xl font-bold font-mono text-cyan-400 mt-1" id="statBestDiscount">--%</div>
                    <div class="text-[11px] text-gray-500 mt-0.5 truncate max-w-[130px]" id="statBestDealName">Пошук...</div>
                </div>
                <div class="w-10 h-10 sm:w-12 sm:h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center text-xl sm:text-2xl text-cyan-400 border border-cyan-500/20">
                    🔥
                </div>
            </div>

            <div class="bg-cardbg p-4 sm:p-5 rounded-xl border border-bordercolor shadow flex items-center justify-between">
                <div>
                    <div class="text-[11px] sm:text-xs text-gray-400 uppercase tracking-wider font-semibold">Категорії в моніторингу</div>
                    <div class="text-xl sm:text-2xl font-bold font-mono text-purple-400 mt-1" id="statMonitoredCount">-- / 36</div>
                    <div class="text-[11px] text-gray-500 mt-0.5 truncate max-w-[130px]" id="statActiveRarities">Т3–Т6</div>
                </div>
                <div class="w-10 h-10 sm:w-12 sm:h-12 bg-purple-500/10 rounded-xl flex items-center justify-center text-xl sm:text-2xl text-purple-400 border border-purple-500/20">
                    💎
                </div>
            </div>

            <div class="bg-cardbg p-4 sm:p-5 rounded-xl border border-bordercolor shadow flex items-center justify-between">
                <div>
                    <div class="text-[11px] sm:text-xs text-gray-400 uppercase tracking-wider font-semibold">Швидкість сканера</div>
                    <div class="text-xl sm:text-2xl font-bold font-mono text-blue-400 mt-1" id="statSpeed">-- сек</div>
                    <div class="text-[11px] text-gray-500 mt-0.5" id="statCycleInfo">Цикл #0 • --:--:--</div>
                </div>
                <div class="w-10 h-10 sm:w-12 sm:h-12 bg-blue-500/10 rounded-xl flex items-center justify-center text-xl sm:text-2xl text-blue-400 border border-blue-500/20">
                    ⚡
                </div>
            </div>
        </section>

        <!-- Filter & Search Toolbar -->
        <section class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow space-y-3">
            <!-- Rarity Quick Filters -->
            <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <span class="text-xs text-gray-400 mr-1 font-semibold uppercase tracking-wider">Рідкість:</span>
                <button onclick="setRarityFilter('all')" id="btnRarity-all" class="px-2.5 py-1 text-xs rounded-lg font-medium border border-cyan-500 bg-cyan-950/60 text-cyan-300">
                    Всі
                </button>
                <button onclick="setRarityFilter('mythic')" id="btnRarity-mythic" class="px-2.5 py-1 text-xs rounded-lg font-medium border border-red-800 bg-red-950/30 text-red-400 hover:bg-red-950/60">
                    🔴 Mythic (VI)
                </button>
                <button onclick="setRarityFilter('legendary')" id="btnRarity-legendary" class="px-2.5 py-1 text-xs rounded-lg font-medium border border-yellow-800 bg-yellow-950/30 text-yellow-400 hover:bg-yellow-950/60">
                    🟡 Legendary (V)
                </button>
                <button onclick="setRarityFilter('epic')" id="btnRarity-epic" class="px-2.5 py-1 text-xs rounded-lg font-medium border border-purple-800 bg-purple-950/30 text-purple-400 hover:bg-purple-950/60">
                    🟣 Epic (IV)
                </button>
                <button onclick="setRarityFilter('rare')" id="btnRarity-rare" class="px-2.5 py-1 text-xs rounded-lg font-medium border border-blue-800 bg-blue-950/30 text-blue-400 hover:bg-blue-950/60">
                    🔵 Rare (III)
                </button>
                <button onclick="setRarityFilter('uncommon')" id="btnRarity-uncommon" class="px-2.5 py-1 text-xs rounded-lg font-medium border border-green-800 bg-green-950/30 text-green-400 hover:bg-green-950/60">
                    🟢 Uncommon (II)
                </button>
                <button onclick="setRarityFilter('common')" id="btnRarity-common" class="px-2.5 py-1 text-xs rounded-lg font-medium border border-gray-700 bg-gray-800 text-gray-400 hover:bg-gray-700">
                    ⚪ Common (I)
                </button>
            </div>

            <!-- Slots, Discount & Search row -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-bordercolor/60">
                <!-- Slot Selector -->
                <div>
                    <label class="block text-[11px] font-semibold text-gray-400 mb-1">Слот спорядження:</label>
                    <select id="slotFilter" onchange="renderDealsTable()" class="w-full bg-gray-800 border border-bordercolor rounded-lg px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500">
                        <option value="all">🛡️ Всі слоти</option>
                        <option value="weapon">⚔️ Зброя (Jet, Tank, Sniper...)</option>
                        <option value="helmet">🪖 Шоломи (Critical Damages)</option>
                        <option value="chest">🦺 Броня (Armor)</option>
                        <option value="pants">👖 Штани (Armor)</option>
                        <option value="boots">🥾 Чоботи (Dodge)</option>
                        <option value="gloves">🧤 Рукавиці (Precision)</option>
                    </select>
                </div>

                <!-- Min Discount Filter -->
                <div>
                    <label class="block text-[11px] font-semibold text-gray-400 mb-1">Мінімальна знижка:</label>
                    <select id="discountFilter" onchange="renderDealsTable()" class="w-full bg-gray-800 border border-bordercolor rounded-lg px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500">
                        <option value="0">Всі знайдені лоти</option>
                        <option value="5" selected>⚡ Знижка ≥ 5% (Стандарт)</option>
                        <option value="10">💎 Знижка ≥ 10%</option>
                        <option value="15">🔥 Знижка ≥ 15%</option>
                        <option value="20">🚀 Знижка ≥ 20%</option>
                        <option value="30">🏆 Знижка ≥ 30%</option>
                    </select>
                </div>

                <!-- God Roll Toggle -->
                <div class="flex items-end">
                    <label class="w-full h-8 flex items-center px-3 bg-gray-800/80 border border-bordercolor rounded-lg cursor-pointer hover:bg-gray-800 text-xs text-amber-300">
                        <input type="checkbox" id="godRollOnly" onchange="renderDealsTable()" class="w-4 h-4 rounded text-amber-500 bg-gray-700 border-gray-600 focus:ring-0 mr-2">
                        <span>🌟 Лише ТОП РОЛ (≥ <span id="lblGodRollThresh">80</span>%)</span>
                    </label>
                </div>

                <!-- Search Input -->
                <div>
                    <label class="block text-[11px] font-semibold text-gray-400 mb-1">Швидкий пошук:</label>
                    <div class="relative">
                        <input type="text" id="searchInput" oninput="renderDealsTable()" placeholder="Назва, код або стат (atk, crit...)" class="w-full bg-gray-800 border border-bordercolor rounded-lg pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500">
                        <i class="fa-solid fa-magnifying-glass absolute left-2.5 top-2.5 text-xs text-gray-500"></i>
                    </div>
                </div>
            </div>
        </section>

        <!-- Main Live Deals Table -->
        <section class="bg-cardbg rounded-xl border border-bordercolor shadow overflow-hidden">
            <div class="p-4 sm:p-5 border-b border-bordercolor flex items-center justify-between">
                <div>
                    <h2 class="text-base sm:text-lg font-bold text-white flex items-center space-x-2">
                        <span>🎯</span>
                        <span>Вигідні пропозиції ринку (Live Deals)</span>
                    </h2>
                    <p class="text-xs text-gray-400 mt-0.5">
                        Лоты, виставлені дешевше оціночної вартості з урахуванням статів та якості ролу
                    </p>
                </div>
                <div class="flex items-center space-x-2">
                    <span id="dealsCounterBadge" class="text-xs px-2.5 py-1 bg-blue-950 text-blue-400 rounded-lg border border-blue-800 font-mono">
                        0 лотів
                    </span>
                    <button onclick="clearDealsHistory()" class="px-2 py-1 text-xs text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded transition" title="Очистити список">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="bg-gray-800/50 text-gray-400 text-[11px] uppercase tracking-wider font-semibold border-b border-bordercolor">
                            <th class="p-3.5">Час</th>
                            <th class="p-3.5">Предмет</th>
                            <th class="p-3.5">Характеристики (Стати)</th>
                            <th class="p-3.5 text-center">Якість ролу</th>
                            <th class="p-3.5 text-right">Ціна лоту</th>
                            <th class="p-3.5 text-right">Оцінка ринку</th>
                            <th class="p-3.5 text-right">Знижка</th>
                            <th class="p-3.5 text-right">Вигода</th>
                            <th class="p-3.5 text-center">Дія</th>
                        </tr>
                    </thead>
                    <tbody id="dealsTableBody" class="divide-y divide-bordercolor">
                        <tr>
                            <td colspan="9" class="p-12 text-center text-gray-500">
                                <i class="fa-solid fa-circle-notch fa-spin text-2xl mb-3 text-blue-500"></i>
                                <div>Завантаження ринкових аномалій...</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Market Inspector Section (Inspect real order book for any item) -->
        <section class="bg-cardbg rounded-xl border border-bordercolor shadow overflow-hidden">
            <div class="p-4 sm:p-5 border-b border-bordercolor flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 class="text-base sm:text-lg font-bold text-white flex items-center space-x-2">
                        <span>🔍</span>
                        <span>Інспектор ордербуку (Live Order Book)</span>
                    </h2>
                    <p class="text-xs text-gray-400 mt-0.5">
                        Перегляд поточних активних пропозицій на ринку для вибраного предмета
                    </p>
                </div>
                <div class="flex items-center space-x-2">
                    <select id="marketInspectorSelect" onchange="loadMarketInspector()" class="bg-gray-800 border border-bordercolor rounded-lg px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500">
                        <optgroup label="Міфічні (Т6)">
                            <option value="jet">✈️ Винищувач (Jet)</option>
                            <option value="helmet6">🪖 Шолом VI</option>
                            <option value="chest6">🦺 Броня VI</option>
                            <option value="pants6">👖 Штани VI</option>
                            <option value="boots6">🥾 Чоботи VI</option>
                            <option value="gloves6">🧤 Рукавиці VI</option>
                        </optgroup>
                        <optgroup label="Легендарні (Т5)">
                            <option value="tank">🛡️ Танк (Tank)</option>
                            <option value="helmet5">🪖 Шолом V</option>
                            <option value="chest5">🦺 Броня V</option>
                            <option value="pants5">👖 Штани V</option>
                            <option value="boots5">🥾 Чоботи V</option>
                            <option value="gloves5">🧤 Рукавиці V</option>
                        </optgroup>
                        <optgroup label="Елітні (Т4)">
                            <option value="sniper">🎯 Снайперка (Sniper)</option>
                            <option value="helmet4">🪖 Шолом IV</option>
                            <option value="chest4">🦺 Броня IV</option>
                            <option value="pants4">👖 Штани IV</option>
                            <option value="boots4" selected>🥾 Чоботи IV</option>
                            <option value="gloves4">🧤 Рукавиці IV</option>
                        </optgroup>
                        <optgroup label="Поліпшені (Т3)">
                            <option value="rifle">🔫 Гвинтівка (Rifle)</option>
                            <option value="helmet3">🪖 Шолом III</option>
                            <option value="chest3">🦺 Броня III</option>
                            <option value="pants3">👖 Штани III</option>
                            <option value="boots3">🥾 Чоботи III</option>
                            <option value="gloves3">🧤 Рукавиці III</option>
                        </optgroup>
                    </select>
                    <button onclick="loadMarketInspector()" class="px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs rounded-lg text-gray-300">
                        <i class="fa-solid fa-rotate"></i>
                    </button>
                </div>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="bg-gray-800/50 text-gray-400 text-[11px] uppercase tracking-wider font-semibold border-b border-bordercolor">
                            <th class="p-3">#</th>
                            <th class="p-3">Ціна ордеру</th>
                            <th class="p-3">Характеристики (Стати)</th>
                            <th class="p-3 text-center">Рол якості</th>
                            <th class="p-3 text-center">Міцність</th>
                            <th class="p-3">Продавець (ID)</th>
                            <th class="p-3 text-center">Посилання</th>
                        </tr>
                    </thead>
                    <tbody id="marketInspectorBody" class="divide-y divide-bordercolor">
                        <tr>
                            <td colspan="7" class="p-6 text-center text-gray-500">
                                Оберіть предмет для перегляду відкритого стакана цін
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        </div>
        <!-- END VIEW 1: MARKET SCANNER -->

        <!-- VIEW 2: WORKFORCE & FACTORY INTELLIGENCE (100% Ingress Compatible) -->
        <div id="viewWorkers" class="space-y-6 hidden">

            <!-- Controls: Nickname Search, API Key, Export -->
            <div class="glass-panel p-4 rounded-xl flex flex-wrap items-center justify-between gap-3 border border-bordercolor shadow-lg">
                <div class="flex items-center gap-2 flex-wrap">
                    <div class="relative flex items-center">
                        <i class="fa-solid fa-user absolute left-3 text-gray-400 text-xs"></i>
                        <input id="workerSearchInput" type="text" placeholder="Нікнейм гравця..." value="Luc1fer"
                            onkeydown="if(event.key === 'Enter') fetchWorkerData()"
                            class="bg-gray-800/90 border border-bordercolor rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors w-40 sm:w-52">
                    </div>
                    <button onclick="fetchWorkerData()" id="btnWorkerAnalyze"
                        class="bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 shadow-md shadow-blue-600/30 transition-all">
                        <i class="fa-solid fa-arrows-rotate" id="workerRefreshIcon"></i>
                        <span>Аналіз</span>
                    </button>
                    <!-- Personal API Key Button -->
                    <button onclick="openWorkerApiKeyModal()" id="workerApiKeyBtn" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 border border-gray-700 text-xs text-gray-300 transition-colors">
                        <i class="fa-solid fa-key text-yellow-400" id="workerApiKeyIcon"></i>
                        <span id="workerApiKeyStatusText">Власний API-ключ</span>
                    </button>
                </div>

                <div class="flex items-center gap-2">
                    <button onclick="copyWorkerReportToClipboard()" title="Скопіювати звіт для Telegram / Discord"
                        class="px-2.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-gray-700 transition-colors flex items-center gap-1">
                        <i class="fa-solid fa-copy"></i>
                        <span>Копіювати звіт</span>
                    </button>
                    <button onclick="downloadWorkerJsonReport()" title="Завантажити JSON звіт"
                        class="px-2.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-gray-700 transition-colors flex items-center gap-1">
                        <i class="fa-solid fa-download"></i>
                        <span>JSON</span>
                    </button>
                </div>
            </div>

            <!-- Recent Search Chips -->
            <div id="workerRecentRow" class="flex items-center gap-2 text-xs text-gray-400 overflow-x-auto pb-1">
                <span class="text-gray-500 flex items-center gap-1"><i class="fa-solid fa-clock-rotate-left"></i> Нещодавні:</span>
                <div id="workerRecentChips" class="flex items-center gap-1.5"></div>
            </div>

            <!-- Top Stat Cards (Arcana-Style 9 Cards) -->
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-3.5">
                <!-- 1. Підприємства -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                        <span>Підприємства</span>
                        <i class="fa-solid fa-industry text-blue-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-white" id="statCompaniesCount">--</div>
                    <div class="text-xs text-gray-400 mt-1" id="statCompaniesSub">-- з робітниками · 0 з менеджером</div>
                </div>

                <!-- 2. Виробіток на добу -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                        <span>Виробіток</span>
                        <i class="fa-solid fa-bolt text-yellow-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-yellow-300" id="statTotalOutput">-- PP</div>
                    <div class="text-xs text-gray-400 mt-1" id="statOutputSub">очок виробітку на добу</div>
                </div>

                <!-- 3. Скрині з інструментами -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                        <span>Скрині з інструментами</span>
                        <i class="fa-solid fa-toolbox text-teal-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-teal-300" id="statToolboxes">--</div>
                    <div class="text-xs text-gray-400 mt-1">очікуваних знахідок на добу</div>
                </div>

                <!-- 4. Вартість товару -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                        <span>Вартість товару</span>
                        <i class="fa-solid fa-box-open text-indigo-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-indigo-300" id="statGoodsValue">--</div>
                    <div class="text-xs text-gray-400 mt-1">за ринковими цінами на добу</div>
                </div>

                <!-- 5. Зарплати персоналу -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                        <span>Зарплати персоналу</span>
                        <i class="fa-solid fa-money-bill-wave text-rose-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-rose-400" id="statWagesDaily">--</div>
                    <div class="text-xs text-gray-400 mt-1">витрат на добу за ставками</div>
                </div>

                <!-- 6. Менеджери -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                        <span>Менеджери</span>
                        <i class="fa-solid fa-user-tie text-purple-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-gray-300" id="statManagersDaily">0.00</div>
                    <div class="text-xs text-gray-400 mt-1">витрат на керуючих на добу</div>
                </div>

                <!-- 7. Ігровий прибуток -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                        <span>Ігровий прибуток</span>
                        <i class="fa-solid fa-gamepad text-purple-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-purple-300" id="statInGameProfit">--</div>
                    <div class="text-xs text-gray-400 mt-1">як показує панель Workforce</div>
                </div>

                <!-- 8. Чистий прибуток (NET) -->
                <div class="bg-cardbg p-4 rounded-xl border border-emerald-500/30 shadow-md bg-gradient-to-br from-emerald-950/20 to-cardbg hover:border-emerald-500/50 transition-all">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center justify-between">
                        <span>Чистий прибуток (NET)</span>
                        <i class="fa-solid fa-coins text-yellow-400"></i>
                    </div>
                    <div class="mt-2 text-2xl font-black text-emerald-400" id="statDailyProfit">--</div>
                    <div class="text-xs text-gray-400 mt-1" id="statDailyProfitWithSelf">-- з власною працею</div>
                </div>

                <!-- 9. Робоча сила -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
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
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-bold uppercase tracking-wider text-gray-300">Країни з найнижчими податками</span>
                            <span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-700/40" title="Будуйте фабрики в цих країнах, щоб зберігати 100% прибутку">0% Податку</span>
                        </div>
                        <i class="fa-solid fa-earth-americas text-blue-400"></i>
                    </div>
                    <div id="workerLowestTaxList" class="flex flex-wrap gap-2 text-xs">
                        <span class="text-gray-500 text-xs">Завантаження країн...</span>
                    </div>
                    <div class="text-[11px] text-gray-400 mt-2.5 flex items-center gap-1.5">
                        <i class="fa-solid fa-circle-info text-blue-400 shrink-0"></i>
                        <span>💡 Новачкам: Регіональні податки сплачуються з прибутку. Фабрики в зонах 0% приносять максимум!</span>
                    </div>
                </div>

                <!-- Best Products Right Now -->
                <div class="bg-cardbg p-4 rounded-xl border border-bordercolor shadow-md">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-bold uppercase tracking-wider text-gray-300">Найприбутковіші товари прямо зараз</span>
                            <span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700/40" title="Товари з найвищою віддачею Coins на 100 очок виробітку">Топ ринку</span>
                        </div>
                        <i class="fa-solid fa-arrow-trend-up text-amber-400"></i>
                    </div>
                    <div id="workerBestProductsList" class="flex flex-wrap gap-2 text-xs">
                        <span class="text-gray-500 text-xs">Завантаження аналітики ринку...</span>
                    </div>
                    <div class="text-[11px] text-gray-400 mt-2.5 flex items-center gap-1.5">
                        <i class="fa-solid fa-circle-info text-amber-400 shrink-0"></i>
                        <span>💡 Новачкам: Показує, який товар генерує найбільше Coins за 100 очок виробітку робітників.</span>
                    </div>
                </div>
            </div>

            <!-- Player Profile Banner -->
            <div id="workerPlayerBanner" class="bg-cardbg p-4 rounded-xl flex flex-wrap items-center justify-between gap-4 border-l-4 border-l-blue-500 shadow-lg border border-bordercolor">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 rounded-full bg-blue-900/60 flex items-center justify-center text-xl font-bold text-blue-300 border border-blue-500/30">
                        <span id="workerPlayerAvatarLetter">?</span>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <span id="workerPlayerUsername" class="text-lg font-bold text-white">Завантаження...</span>
                            <span id="workerPlayerLevel" class="text-xs px-2 py-0.5 rounded bg-gray-800 text-yellow-400 border border-bordercolor font-semibold">Lv.--</span>
                        </div>
                        <div class="text-xs text-gray-400 flex items-center gap-3 mt-1 flex-wrap">
                            <span id="workerPlayerCountry"><i class="fa-solid fa-globe text-blue-400 mr-1"></i>Країна: --</span>
                            <span id="workerPlayerProdSkill"><i class="fa-solid fa-bolt text-yellow-400 mr-1"></i>Prod Skill: --</span>
                        </div>
                    </div>
                </div>
                <!-- Category Filter Pills -->
                <div class="flex items-center gap-1.5 flex-wrap text-xs">
                    <button onclick="setWorkerFilter('ALL')" id="wfilterALL" class="px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium transition-colors">Всі (<span id="wcntAll">0</span>)</button>
                    <button onclick="setWorkerFilter('KEEP')" id="wfilterKEEP" class="px-3 py-1.5 rounded-lg bg-gray-800 text-emerald-400 hover:bg-gray-700 transition-colors">💎 Утримувати (<span id="wcntKeep">0</span>)</button>
                    <button onclick="setWorkerFilter('RELOCATE')" id="wfilterRELOCATE" class="px-3 py-1.5 rounded-lg bg-gray-800 text-blue-400 hover:bg-gray-700 transition-colors">🔄 Перевести (<span id="wcntRelocate">0</span>)</button>
                    <button onclick="setWorkerFilter('LOW_MORALE')" id="wfilterLOW_MORALE" class="px-3 py-1.5 rounded-lg bg-gray-800 text-amber-400 hover:bg-gray-700 transition-colors">⚠️ Низький настрій (<span id="wcntMorale">0</span>)</button>
                    <button onclick="setWorkerFilter('RETIREMENT')" id="wfilterRETIREMENT" class="px-3 py-1.5 rounded-lg bg-gray-800 text-purple-400 hover:bg-gray-700 transition-colors">⏳ Скоро пенсія (<span id="wcntRetire">0</span>)</button>
                    <button onclick="setWorkerFilter('TOXIC')" id="wfilterTOXIC" class="px-3 py-1.5 rounded-lg bg-gray-800 text-red-400 hover:bg-gray-700 transition-colors">🚨 Звільнити (<span id="wcntToxic">0</span>)</button>
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
                <button onclick="openWorkerApiKeyModal()" class="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow transition whitespace-nowrap ml-3">
                    <i class="fa-solid fa-key mr-1"></i> Оновити ключ
                </button>
            </div>

            <!-- Sub-Tabs Navigation -->
            <div class="flex items-center border-b border-bordercolor gap-6 text-sm overflow-x-auto">
                <button onclick="switchWorkerSubTab('companies')" id="wtabCompanies" class="pb-3 tab-active flex items-center gap-2 whitespace-nowrap text-blue-400 font-semibold">
                    <i class="fa-solid fa-industry"></i>
                    <span>Огляд підприємств</span>
                </button>
                <button onclick="switchWorkerSubTab('workers')" id="wtabWorkers" class="pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap">
                    <i class="fa-solid fa-users"></i>
                    <span>Працівники фабрик</span>
                </button>
                <button onclick="switchWorkerSubTab('relocation')" id="wtabRelocation" class="pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap">
                    <i class="fa-solid fa-arrows-split-up-and-left"></i>
                    <span>Матриця переведень</span>
                </button>
                <button onclick="switchWorkerSubTab('optimizer')" id="wtabOptimizer" class="pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap">
                    <i class="fa-solid fa-calculator"></i>
                    <span>Калькулятор зарплат</span>
                </button>
            </div>

            <!-- SUB-TAB 1: COMPANIES CARDS (Default active) -->
            <div id="wcontentCompanies" class="space-y-4"></div>

            <!-- SUB-TAB 2: WORKERS TABLE -->
            <div id="wcontentWorkers" class="hidden space-y-4">
                <div class="bg-cardbg rounded-xl overflow-hidden shadow-xl border border-bordercolor">
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-gray-900/90 text-gray-400 uppercase text-[10px] tracking-wider border-b border-bordercolor">
                                <tr>
                                    <th class="p-3">Статус</th>
                                    <th class="p-3 cursor-pointer hover:text-white" onclick="sortWorkerList('name')">Працівник <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                    <th class="p-3 cursor-pointer hover:text-white" onclick="sortWorkerList('company')">Фабрика / Товар <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                    <th class="p-3 text-right cursor-pointer hover:text-white" onclick="sortWorkerList('pp')">Виробіток <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                    <th class="p-3 text-right cursor-pointer hover:text-white" onclick="sortWorkerList('wage')">Зарплата <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                    <th class="p-3 text-right cursor-pointer hover:text-white" onclick="sortWorkerList('profit')">Чистий прибуток <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                    <th class="p-3 text-right">Break-even Wage</th>
                                    <th class="p-3 text-center cursor-pointer hover:text-white" onclick="sortWorkerList('spec')">Стаж / Бонус <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                    <th class="p-3 text-center cursor-pointer hover:text-white" onclick="sortWorkerList('retire')">Пенсія / Ризик <i class="fa-solid fa-sort ml-1 text-gray-600"></i></th>
                                    <th class="p-3">Рекомендація</th>
                                </tr>
                            </thead>
                            <tbody id="workerTableBody" class="divide-y divide-bordercolor">
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

            <!-- SUB-TAB 3: RELOCATION MATRIX -->
            <div id="wcontentRelocation" class="hidden space-y-4">
                <div class="bg-cardbg p-5 rounded-xl space-y-3 border-l-4 border-l-blue-500 shadow-lg border border-bordercolor">
                    <h3 class="text-base font-bold text-white flex items-center gap-2">
                        <i class="fa-solid fa-arrows-turn-to-dots text-blue-400"></i>
                        Розумний симулятор переведень між фабриками
                    </h3>
                    <p class="text-xs text-gray-300 leading-relaxed">
                        Правило економіки WarEra: якщо працівник має високу базову продуктивність, але ще не накопичив високий бонус спеціалізації (&le; 3 дні), переведення його на фабрику з вищою маржею на 1 PP дасть більше чистого прибутку, ніж збереження на менш рентабельній фабриці.
                    </p>
                </div>
                <div id="workerRelocationCards" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
            </div>

            <!-- SUB-TAB 4: WAGE OPTIMIZER & BREAK-EVEN -->
            <div id="wcontentOptimizer" class="hidden space-y-4">
                <div class="bg-cardbg p-5 rounded-xl space-y-4 shadow-lg border border-bordercolor">
                    <h3 class="text-base font-bold text-white flex items-center gap-2">
                        <i class="fa-solid fa-sliders text-indigo-400"></i>
                        Оптимізатор ставок заробітної плати (Break-even & Target Margin)
                    </h3>
                    <p class="text-xs text-gray-400">
                        Максимально допустима ставка зарплати (<span class="text-yellow-400">Break-even Wage</span>) показує межу, вище якої працівник починає приносити прямий збиток власнику фабрики.
                    </p>
                    <div id="workerOptimizerTable" class="overflow-x-auto"></div>
                </div>
            </div>

        </div>
        <!-- END VIEW 2: WORKFORCE -->

    </main>

    <!-- Settings Modal -->
    <div id="settingsModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="bg-cardbg rounded-2xl border border-bordercolor shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div class="p-5 border-b border-bordercolor flex items-center justify-between">
                <div class="flex items-center space-x-2">
                    <span class="text-xl">⚙️</span>
                    <h3 class="font-bold text-white text-base">Налаштування сканера WarEra</h3>
                </div>
                <button onclick="closeSettingsModal()" class="text-gray-400 hover:text-white">
                    <i class="fa-solid fa-xmark text-lg"></i>
                </button>
            </div>

            <div class="p-5 space-y-4 text-xs">
                <!-- Pricing mode -->
                <div>
                    <label class="block font-semibold text-gray-300 mb-1.5">Метод оцінки вартості (Pricing Mode):</label>
                    <div class="grid grid-cols-2 gap-2">
                        <button id="optModeLive" onclick="setPricingMode('live')" class="p-2.5 rounded-xl border text-left font-medium transition flex flex-col space-y-1">
                            <span class="font-bold">⚡ Реальний час (Live)</span>
                            <span class="text-[10px] text-gray-400">Порівняння статів з відкритими ордерами</span>
                        </button>
                        <button id="optModeHistory" onclick="setPricingMode('history')" class="p-2.5 rounded-xl border text-left font-medium transition flex flex-col space-y-1">
                            <span class="font-bold">📜 3-денна історія (DB)</span>
                            <span class="text-[10px] text-gray-400">Медіана угод з локальної бази SQLite</span>
                        </button>
                    </div>
                </div>

                <!-- Scan Interval -->
                <div>
                    <label class="block font-semibold text-gray-300 mb-1.5">Частота сканування:</label>
                    <div class="grid grid-cols-5 gap-1.5 mb-1.5">
                        <button onclick="setScanInterval(1)" id="btnInterval-1" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">1 сек</button>
                        <button onclick="setScanInterval(2)" id="btnInterval-2" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">2 сек</button>
                        <button onclick="setScanInterval(3)" id="btnInterval-3" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">3 сек</button>
                        <button onclick="setScanInterval(5)" id="btnInterval-5" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">5 сек</button>
                        <button onclick="setScanInterval(10)" id="btnInterval-10" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">10 сек</button>
                    </div>
                    <div class="grid grid-cols-4 gap-1.5">
                        <button onclick="setScanInterval(15)" id="btnInterval-15" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">15 сек</button>
                        <button onclick="setScanInterval(20)" id="btnInterval-20" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">20 сек</button>
                        <button onclick="setScanInterval(25)" id="btnInterval-25" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">25 сек</button>
                        <button onclick="setScanInterval(30)" id="btnInterval-30" class="py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center">30 сек</button>
                    </div>
                </div>

                <!-- Thresholds -->
                <div class="grid grid-cols-2 gap-3 pt-2">
                    <div>
                        <label class="block font-semibold text-gray-300 mb-1">Мін. знижка для алерту (%):</label>
                        <input type="number" id="settingMinDiscount" min="1" max="50" step="0.5" class="w-full bg-gray-800 border border-bordercolor rounded-lg px-3 py-1.5 text-gray-100 font-mono">
                    </div>
                    <div>
                        <label class="block font-semibold text-gray-300 mb-1">Поріг ТОП РОЛ (%):</label>
                        <input type="number" id="settingGodRoll" min="50" max="99" step="1" class="w-full bg-gray-800 border border-bordercolor rounded-lg px-3 py-1.5 text-gray-100 font-mono">
                    </div>
                </div>

                <!-- Active Qualities checkboxes -->
                <div class="pt-2 border-t border-bordercolor">
                    <label class="block font-semibold text-gray-300 mb-1.5">Категорії спорядження в сканері:</label>
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        <label class="flex items-center space-x-2 p-1.5 rounded bg-gray-800/60 border border-bordercolor cursor-pointer text-red-400">
                            <input type="checkbox" id="chkQuality-mythic" onchange="toggleQualityBackend('mythic')" class="rounded bg-gray-700 border-gray-600 text-red-500">
                            <span>🔴 Mythic (VI)</span>
                        </label>
                        <label class="flex items-center space-x-2 p-1.5 rounded bg-gray-800/60 border border-bordercolor cursor-pointer text-yellow-400">
                            <input type="checkbox" id="chkQuality-legendary" onchange="toggleQualityBackend('legendary')" class="rounded bg-gray-700 border-gray-600 text-yellow-500">
                            <span>🟡 Legendary (V)</span>
                        </label>
                        <label class="flex items-center space-x-2 p-1.5 rounded bg-gray-800/60 border border-bordercolor cursor-pointer text-purple-400">
                            <input type="checkbox" id="chkQuality-epic" onchange="toggleQualityBackend('epic')" class="rounded bg-gray-700 border-gray-600 text-purple-500">
                            <span>🟣 Epic (IV)</span>
                        </label>
                        <label class="flex items-center space-x-2 p-1.5 rounded bg-gray-800/60 border border-bordercolor cursor-pointer text-blue-400">
                            <input type="checkbox" id="chkQuality-rare" onchange="toggleQualityBackend('rare')" class="rounded bg-gray-700 border-gray-600 text-blue-500">
                            <span>🔵 Rare (III)</span>
                        </label>
                        <label class="flex items-center space-x-2 p-1.5 rounded bg-gray-800/60 border border-bordercolor cursor-pointer text-green-400">
                            <input type="checkbox" id="chkQuality-uncommon" onchange="toggleQualityBackend('uncommon')" class="rounded bg-gray-700 border-gray-600 text-green-500">
                            <span>🟢 Uncommon (II)</span>
                        </label>
                        <label class="flex items-center space-x-2 p-1.5 rounded bg-gray-800/60 border border-bordercolor cursor-pointer text-gray-400">
                            <input type="checkbox" id="chkQuality-common" onchange="toggleQualityBackend('common')" class="rounded bg-gray-700 border-gray-600 text-gray-500">
                            <span>⚪ Common (I)</span>
                        </label>
                    </div>
                </div>
            </div>

            <div class="p-4 bg-gray-900 border-t border-bordercolor flex items-center justify-between">
                <button onclick="saveThresholds()" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg shadow text-xs transition">
                    Зберегти налаштування
                </button>
                <button onclick="closeSettingsModal()" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 font-semibold rounded-lg text-xs transition">
                    Закрити
                </button>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="border-t border-bordercolor/60 py-4 text-center text-xs text-gray-500">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <div>WarEra Market Scanner Suite • Ingress & Autonomous Engine</div>
            <div class="flex items-center space-x-3 text-[11px]">
                <span id="footerPulse">🟢 Підключено до сканера</span>
                <a href="https://app.warera.io/market/equipments" target="_blank" class="text-blue-400 hover:underline">
                    WarEra Market ↗
                </a>
            </div>
        </div>
    </footer>

    <!-- Client-side Logic -->
    <script>
        // State
        let currentStatus = {};
        let rawDeals = [];
        let selectedRarity = 'all';
        let isPaused = false;
        let isPolling = true;

        // Auto-detect Ingress base URL
        const BASE_PATH = window.location.pathname.replace(/\/+$/, '');
        window.BASE_PATH = BASE_PATH;

        function getApiUrl(endpoint) {
            const cleanEndpoint = endpoint.replace(/^\/+/, '');
            return BASE_PATH ? `${BASE_PATH}/${cleanEndpoint}` : `/${cleanEndpoint}`;
        }
        window.getApiUrl = getApiUrl;

        // Rarity styling helpers
        const RARITY_MAP = {
            'mythic': { label: 'Mythic VI', color: 'text-red-400', border: 'border-red-800', bg: 'bg-red-950/40', dot: '🔴' },
            'legendary': { label: 'Legendary V', color: 'text-yellow-400', border: 'border-yellow-800', bg: 'bg-yellow-950/40', dot: '🟡' },
            'epic': { label: 'Epic IV', color: 'text-purple-400', border: 'border-purple-800', bg: 'bg-purple-950/40', dot: '🟣' },
            'rare': { label: 'Rare III', color: 'text-blue-400', border: 'border-blue-800', bg: 'bg-blue-950/40', dot: '🔵' },
            'uncommon': { label: 'Uncommon II', color: 'text-green-400', border: 'border-green-800', bg: 'bg-green-950/40', dot: '🟢' },
            'common': { label: 'Common I', color: 'text-gray-400', border: 'border-gray-700', bg: 'bg-gray-800', dot: '⚪' },
        };

        const SLOT_ICONS = {
            'weapon': '⚔️',
            'helmet': '🪖',
            'chest': '🦺',
            'pants': '👖',
            'boots': '🥾',
            'gloves': '🧤'
        };

        function getSlotByItemCode(code) {
            if (!code) return 'weapon';
            if (code.startsWith('helmet')) return 'helmet';
            if (code.startsWith('chest')) return 'chest';
            if (code.startsWith('pants')) return 'pants';
            if (code.startsWith('boots')) return 'boots';
            if (code.startsWith('gloves')) return 'gloves';
            return 'weapon';
        }

        // Fetch Scanner Status
        async function fetchStatus() {
            try {
                const res = await fetch(getApiUrl('api/status'));
                if (!res.ok) return;
                currentStatus = await res.json();
                updateStatusUI();
            } catch (e) {
                console.warn('Status poll error:', e);
            }
        }

        // Fetch Live Deals
        async function fetchDeals() {
            try {
                const res = await fetch(getApiUrl('api/deals'));
                if (!res.ok) return;
                const data = await res.json();
                rawDeals = data.deals || [];
                renderDealsTable();
            } catch (e) {
                console.warn('Deals poll error:', e);
            }
        }

        function updateStatusUI() {
            if (!currentStatus) return;

            document.getElementById('versionBadge').textContent = `v${currentStatus.version || 'b.0001.15'}`;
            document.getElementById('statAnomalies').textContent = currentStatus.total_alerts || 0;
            document.getElementById('statActiveDeals').textContent = `${currentStatus.active_deals_count || 0} активних на ринку`;
            document.getElementById('statBestDiscount').textContent = currentStatus.best_discount ? `-${currentStatus.best_discount}%` : '--%';
            document.getElementById('statBestDealName').textContent = currentStatus.best_deal_item || 'Пошук...';
            document.getElementById('statMonitoredCount').textContent = `${currentStatus.monitored_items_count || 0} / 36`;
            
            const activeQ = currentStatus.active_qualities || [];
            document.getElementById('statActiveRarities').textContent = activeQ.map(q => q.charAt(0).toUpperCase() + q.slice(1)).join(', ') || '--';
            document.getElementById('statSpeed').textContent = `${currentStatus.scan_interval || 1} сек`;
            document.getElementById('statCycleInfo').textContent = `Цикл #${currentStatus.cycle_count || 0} • ${currentStatus.last_scan_time || '--:--:--'}`;

            // Mode text
            const modeIsLive = (currentStatus.pricing_mode || 'live').toLowerCase() === 'live';
            document.getElementById('pricingModeText').textContent = modeIsLive ? '⚡ Live' : '📜 Історія';

            // Pause status
            isPaused = !!currentStatus.paused;
            const statusPill = document.getElementById('statusPill');
            const statusText = document.getElementById('statusText');
            const pauseIcon = document.getElementById('pauseIcon');
            const pauseBtnText = document.getElementById('pauseBtnText');

            if (isPaused) {
                statusPill.className = 'flex items-center space-x-2 text-xs bg-amber-950/60 text-amber-400 px-3 py-1.5 rounded-full border border-amber-800';
                statusText.textContent = 'Пауза';
                pauseIcon.className = 'fa-solid fa-play text-emerald-400';
                pauseBtnText.textContent = 'Запустити';
            } else {
                statusPill.className = 'flex items-center space-x-2 text-xs bg-emerald-950/60 text-emerald-400 px-3 py-1.5 rounded-full border border-emerald-800';
                statusText.textContent = 'Сканує';
                pauseIcon.className = 'fa-solid fa-pause text-amber-400';
                pauseBtnText.textContent = 'Пауза';
            }

            // Update modal fields
            document.getElementById('lblGodRollThresh').textContent = currentStatus.god_roll_threshold || 80;
            document.getElementById('settingMinDiscount').value = currentStatus.min_discount || 5.0;
            document.getElementById('settingGodRoll').value = currentStatus.god_roll_threshold || 80.0;

            // Update interval buttons highlight
            [1, 2, 3, 5, 10, 15, 20, 25, 30].forEach(sec => {
                const btn = document.getElementById(`btnInterval-${sec}`);
                if (btn) {
                    if (currentStatus.scan_interval === sec) {
                        btn.className = 'py-1.5 rounded-lg border border-blue-500 bg-blue-900/60 text-blue-300 font-mono font-bold text-center';
                    } else {
                        btn.className = 'py-1.5 rounded-lg border border-bordercolor bg-gray-800 text-gray-300 hover:bg-gray-700 font-mono text-center';
                    }
                }
            });

            // Update mode buttons highlight
            const optLive = document.getElementById('optModeLive');
            const optHist = document.getElementById('optModeHistory');
            if (modeIsLive) {
                optLive.className = 'p-2.5 rounded-xl border border-cyan-500 bg-cyan-950/50 text-cyan-300 font-medium transition flex flex-col space-y-1';
                optHist.className = 'p-2.5 rounded-xl border border-bordercolor bg-gray-800/80 text-gray-400 hover:bg-gray-800 font-medium transition flex flex-col space-y-1';
            } else {
                optHist.className = 'p-2.5 rounded-xl border border-amber-500 bg-amber-950/50 text-amber-300 font-medium transition flex flex-col space-y-1';
                optLive.className = 'p-2.5 rounded-xl border border-bordercolor bg-gray-800/80 text-gray-400 hover:bg-gray-800 font-medium transition flex flex-col space-y-1';
            }

            // Update quality checkboxes
            ['mythic', 'legendary', 'epic', 'rare', 'uncommon', 'common'].forEach(q => {
                const chk = document.getElementById(`chkQuality-${q}`);
                if (chk) chk.checked = activeQ.includes(q);
            });
        }

        // Render Deals Table with Active Filters
        function renderDealsTable() {
            const tbody = document.getElementById('dealsTableBody');
            const slotFilter = document.getElementById('slotFilter').value;
            const minDiscount = parseFloat(document.getElementById('discountFilter').value) || 0;
            const godRollOnly = document.getElementById('godRollOnly').checked;
            const search = document.getElementById('searchInput').value.toLowerCase().trim();

            const filtered = rawDeals.filter(deal => {
                // Rarity filter
                if (selectedRarity !== 'all' && deal.rarity !== selectedRarity) return false;

                // Slot filter
                const slot = getSlotByItemCode(deal.item_code);
                if (slotFilter !== 'all' && slot !== slotFilter) return false;

                // Discount threshold
                if (deal.discount_pct < minDiscount) return false;

                // God roll only
                if (godRollOnly && !deal.is_god_roll) return false;

                // Text search
                if (search) {
                    const name = (deal.item_name || '').toLowerCase();
                    const code = (deal.item_code || '').toLowerCase();
                    const skillsStr = JSON.stringify(deal.skills || {}).toLowerCase();
                    if (!name.includes(search) && !code.includes(search) && !skillsStr.includes(search)) {
                        return false;
                    }
                }

                return true;
            });

            document.getElementById('dealsCounterBadge').textContent = `${filtered.length} лотів`;

            if (filtered.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="9" class="p-12 text-center text-gray-500">
                            <div class="text-3xl mb-2">🔍</div>
                            <div class="text-sm font-semibold text-gray-300">Аномалій за вибраними фільтрами не знайдено</div>
                            <div class="text-xs text-gray-500 mt-1">Сканер перевіряє ринок кожні ${currentStatus.scan_interval || 1} сек. Нові демпінгові лоти з'являться тут миттєво.</div>
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = filtered.map((d, index) => {
                const rStyle = RARITY_MAP[d.rarity] || RARITY_MAP['common'];
                const slotIcon = SLOT_ICONS[getSlotByItemCode(d.item_code)] || '🛡️';
                const skillsHtml = formatSkillsPills(d.skills);
                const rollPct = Math.round(d.roll_quality || 50);
                const rollBadge = d.is_god_roll 
                    ? `<span class="ml-1.5 px-1.5 py-0.5 text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded font-bold whitespace-nowrap">🌟 ТОП РОЛ</span>`
                    : '';

                const activeMarker = d.is_active 
                    ? `<span class="inline-block w-2 h-2 rounded-full bg-emerald-400 mr-1.5" title="Зараз активний на ринку"></span>`
                    : `<span class="inline-block w-2 h-2 rounded-full bg-gray-500 mr-1.5" title="Попередньо виявлений лот"></span>`;

                return `
                    <tr class="hover:bg-hoverbg/50 transition">
                        <td class="p-3.5 text-xs text-gray-400 font-mono whitespace-nowrap">
                            ${activeMarker}${d.timestamp || '--:--'}
                        </td>
                        <td class="p-3.5">
                            <div class="flex items-center space-x-2">
                                <span class="text-lg">${slotIcon}</span>
                                <div>
                                    <div class="font-bold text-white flex items-center space-x-1.5">
                                        <span>${d.item_name || d.item_code}</span>
                                    </div>
                                    <div class="flex items-center space-x-1.5 mt-0.5">
                                        <span class="text-[10px] px-1.5 py-0.2 rounded border ${rStyle.border} ${rStyle.bg} ${rStyle.color} font-medium">
                                            ${rStyle.label}
                                        </span>
                                        <span class="text-[10px] text-gray-500 font-mono">${d.item_code}</span>
                                    </div>
                                </div>
                            </div>
                        </td>
                        <td class="p-3.5">
                            <div class="flex flex-wrap gap-1 max-w-[280px]">
                                ${skillsHtml}
                            </div>
                        </td>
                        <td class="p-3.5 text-center whitespace-nowrap">
                            <div class="inline-flex items-center">
                                <div class="w-16 bg-gray-800 rounded-full h-2 mr-2 overflow-hidden border border-bordercolor">
                                    <div class="h-2 rounded-full ${rollPct >= 80 ? 'bg-amber-400' : rollPct >= 65 ? 'bg-cyan-400' : 'bg-blue-500'}" style="width: ${rollPct}%"></div>
                                </div>
                                <span class="font-mono text-xs font-semibold ${rollPct >= 80 ? 'text-amber-400' : 'text-gray-300'}">${rollPct}%</span>
                                ${rollBadge}
                            </div>
                        </td>
                        <td class="p-3.5 text-right font-mono font-bold text-white text-sm whitespace-nowrap">
                            ${Number(d.price).toFixed(2)}
                        </td>
                        <td class="p-3.5 text-right font-mono text-gray-400 text-xs whitespace-nowrap">
                            <div>${Number(d.reference_price).toFixed(2)}</div>
                            <div class="text-[10px] text-gray-500">${d.notes ? d.notes.slice(0, 16) : 'медіана'}</div>
                        </td>
                        <td class="p-3.5 text-right whitespace-nowrap">
                            <span class="px-2 py-1 bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 rounded-md font-mono font-bold text-xs">
                                -${d.discount_pct}%
                            </span>
                        </td>
                        <td class="p-3.5 text-right font-mono font-bold text-emerald-400 text-xs whitespace-nowrap">
                            +${Number(d.potential_profit).toFixed(2)}
                        </td>
                        <td class="p-3.5 text-center whitespace-nowrap">
                            <a href="${d.url || `https://app.warera.io/market/equipments?item=${d.item_code}`}" target="_blank" class="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow inline-flex items-center space-x-1 transition">
                                <span>Купити</span>
                                <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                            </a>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function formatSkillsPills(skills) {
            if (!skills || typeof skills !== 'object' || Object.keys(skills).length === 0) {
                return '<span class="text-xs text-gray-500">Без статів</span>';
            }

            const labels = {
                'attack': { name: 'Atk', color: 'text-red-300 bg-red-950/40 border-red-900/60' },
                'criticalChance': { name: 'Crit', color: 'text-amber-300 bg-amber-950/40 border-amber-900/60', suffix: '%' },
                'armor': { name: 'Armor', color: 'text-blue-300 bg-blue-950/40 border-blue-900/60' },
                'dodge': { name: 'Dodge', color: 'text-emerald-300 bg-emerald-950/40 border-emerald-900/60' },
                'precision': { name: 'Prec', color: 'text-purple-300 bg-purple-950/40 border-purple-900/60' },
                'criticalDamages': { name: 'CritDmg', color: 'text-orange-300 bg-orange-950/40 border-orange-900/60', suffix: '%' }
            };

            return Object.entries(skills).map(([k, v]) => {
                const conf = labels[k] || { name: k, color: 'text-gray-300 bg-gray-800 border-gray-700' };
                const suff = conf.suffix || '';
                return `
                    <span class="text-[11px] font-mono px-1.5 py-0.5 rounded border ${conf.color} font-semibold">
                        ${conf.name} ${v}${suff}
                    </span>
                `;
            }).join('');
        }

        // Rarity Filter Click
        function setRarityFilter(rarity) {
            selectedRarity = rarity;
            ['all', 'mythic', 'legendary', 'epic', 'rare', 'uncommon', 'common'].forEach(r => {
                const btn = document.getElementById(`btnRarity-${r}`);
                if (!btn) return;
                if (r === rarity) {
                    btn.classList.add('ring-2', 'ring-cyan-400', 'font-bold');
                } else {
                    btn.classList.remove('ring-2', 'ring-cyan-400', 'font-bold');
                }
            });
            renderDealsTable();
        }

        // Trigger manual scan immediately
        async function triggerScan() {
            const icon = document.getElementById('scanIcon');
            icon.classList.add('fa-spin');
            try {
                await fetch(getApiUrl('api/scan'), { method: 'POST' });
                await fetchStatus();
                await fetchDeals();
            } catch (e) {
                console.error(e);
            } finally {
                setTimeout(() => icon.classList.remove('fa-spin'), 1000);
            }
        }

        // Pause/Resume scanner
        async function togglePause() {
            const action = isPaused ? 'resume' : 'pause';
            try {
                await fetch(getApiUrl('api/control'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action })
                });
                await fetchStatus();
            } catch (e) {
                console.error(e);
            }
        }

        // Change interval
        async function setScanInterval(sec) {
            try {
                await fetch(getApiUrl('api/control'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'set_interval', interval: sec })
                });
                await fetchStatus();
            } catch (e) {
                console.error(e);
            }
        }

        // Change pricing mode
        async function setPricingMode(mode) {
            try {
                await fetch(getApiUrl('api/control'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'set_mode', mode: mode })
                });
                await fetchStatus();
            } catch (e) {
                console.error(e);
            }
        }

        // Toggle Quality Backend
        async function toggleQualityBackend(q) {
            try {
                await fetch(getApiUrl('api/control'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'toggle_quality', quality: q })
                });
                await fetchStatus();
            } catch (e) {
                console.error(e);
            }
        }

        // Save Thresholds
        async function saveThresholds() {
            const minD = parseFloat(document.getElementById('settingMinDiscount').value) || 5.0;
            const godR = parseFloat(document.getElementById('settingGodRoll').value) || 80.0;
            try {
                await fetch(getApiUrl('api/control'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'set_thresholds', min_discount: minD, god_roll: godR })
                });
                closeSettingsModal();
                await fetchStatus();
                await fetchDeals();
            } catch (e) {
                console.error(e);
            }
        }

        // Clear Deals History
        async function clearDealsHistory() {
            if (!confirm('Очистити список виявлених лотів на екрані?')) return;
            try {
                await fetch(getApiUrl('api/control'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'clear_deals' })
                });
                rawDeals = [];
                renderDealsTable();
                await fetchStatus();
            } catch (e) {
                console.error(e);
            }
        }

        // Market Inspector Loader
        async function loadMarketInspector() {
            const select = document.getElementById('marketInspectorSelect');
            const itemCode = select.value;
            const tbody = document.getElementById('marketInspectorBody');

            tbody.innerHTML = `
                <tr><td colspan="7" class="p-6 text-center text-gray-500">
                    <i class="fa-solid fa-circle-notch fa-spin text-xl text-blue-500 mb-2"></i>
                    <div>Опитування стакану ордерів для ${itemCode}...</div>
                </td></tr>
            `;

            try {
                const res = await fetch(getApiUrl(`api/market?item=${itemCode}`));
                if (!res.ok) return;
                const data = await res.json();
                const offers = data.offers || [];

                if (offers.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-gray-500">Немає зафіксованих ордерів для ${itemCode}.</td></tr>`;
                    return;
                }

                tbody.innerHTML = offers.map((off, idx) => {
                    const price = Number(off.price || 0).toFixed(2);
                    const skills = off.item ? off.item.skills : (off.skills || {});
                    const state = off.item ? off.item.state : (off.state || 100);
                    const userId = off.userId || off.user_id || 'unknown';
                    const skillsPills = formatSkillsPills(skills);

                    return `
                        <tr class="hover:bg-hoverbg/50 transition">
                            <td class="p-3 text-xs text-gray-400 font-mono">#${idx + 1}</td>
                            <td class="p-3 font-mono font-bold text-white">${price}</td>
                            <td class="p-3"><div class="flex flex-wrap gap-1">${skillsPills}</div></td>
                            <td class="p-3 text-center font-mono text-xs text-gray-300">--</td>
                            <td class="p-3 text-center font-mono text-xs text-gray-400">${state}%</td>
                            <td class="p-3 font-mono text-xs text-gray-400 truncate max-w-[120px]">${userId.slice(0, 10)}...</td>
                            <td class="p-3 text-center">
                                <a href="https://app.warera.io/market/equipments?item=${itemCode}" target="_blank" class="text-blue-400 hover:text-blue-300 text-xs">
                                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                                </a>
                            </td>
                        </tr>
                    `;
                }).join('');
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-red-400">Помилка завантаження: ${e}</td></tr>`;
            }
        }

        // Modal Controls
        function openSettingsModal() {
            document.getElementById('settingsModal').classList.remove('hidden');
        }
        function closeSettingsModal() {
            document.getElementById('settingsModal').classList.add('hidden');
        }

        // Initial Loop
        fetchStatus();
        fetchDeals();

        // Periodic Refresh (every 2.5 seconds)
        setInterval(() => {
            if (isPolling) {
                fetchStatus();
                fetchDeals();
            }
        }, 2500);

        // =====================================================================
        // UNIFIED VIEW SWITCHER & WORKFORCE INTELLIGENCE (INGRESS COMPATIBLE)
        // =====================================================================
        let currentMainView = 'market';
        let workerDataLoaded = false;
        let workerCurrentData = null;
        let workerCurrentFilter = 'ALL';
        let workerSortField = 'profit';
        let workerSortAsc = false;

        const LS_WORKER_KEY = 'warera_user_api_key';
        const LS_WORKER_RECENTS = 'warera_recent_nicks';

        function switchMainView(view) {
            currentMainView = view;
            const btnMarket = document.getElementById('navBtnMarket');
            const btnWorkers = document.getElementById('navBtnWorkers');
            const viewMarket = document.getElementById('viewMarket');
            const viewWorkers = document.getElementById('viewWorkers');

            if (view === 'workers') {
                viewMarket.classList.add('hidden');
                viewWorkers.classList.remove('hidden');
                btnWorkers.className = 'px-2.5 py-1.5 rounded-md bg-blue-600 text-white font-medium text-xs flex items-center space-x-1.5 transition shadow';
                btnMarket.className = 'px-2.5 py-1.5 rounded-md text-gray-400 hover:text-white font-medium text-xs flex items-center space-x-1.5 transition';
                if (!workerDataLoaded) {
                    fetchWorkerData();
                }
            } else {
                viewWorkers.classList.add('hidden');
                viewMarket.classList.remove('hidden');
                btnMarket.className = 'px-2.5 py-1.5 rounded-md bg-blue-600 text-white font-medium text-xs flex items-center space-x-1.5 transition shadow';
                btnWorkers.className = 'px-2.5 py-1.5 rounded-md text-gray-400 hover:text-white font-medium text-xs flex items-center space-x-1.5 transition';
            }
        }

        function getWorkerUserApiKey() {
            return localStorage.getItem(LS_WORKER_KEY) || '';
        }

        function updateWorkerApiKeyUI() {
            const key = getWorkerUserApiKey();
            const badgeText = document.getElementById('workerApiKeyStatusText');
            const icon = document.getElementById('workerApiKeyIcon');
            if (!badgeText) return;

            const auth = (workerCurrentData && workerCurrentData.auth) || {};
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

        function openWorkerApiKeyModal() {
            document.getElementById('workerModalApiKeyInput').value = getWorkerUserApiKey();
            document.getElementById('workerApiKeyModal').classList.remove('hidden');
        }

        function closeWorkerApiKeyModal() {
            document.getElementById('workerApiKeyModal').classList.add('hidden');
        }

        function toggleWorkerApiKeyVisibility() {
            const input = document.getElementById('workerModalApiKeyInput');
            const icon = document.getElementById('workerApiKeyEyeIcon');
            if (input.type === 'password') {
                input.type = 'text';
                icon.className = 'fa-solid fa-eye-slash';
            } else {
                input.type = 'password';
                icon.className = 'fa-solid fa-eye';
            }
        }

        function saveWorkerApiKey() {
            const key = document.getElementById('workerModalApiKeyInput').value.trim();
            if (key) {
                localStorage.setItem(LS_WORKER_KEY, key);
                showWorkerToast('API ключ збережено в браузері!');
            } else {
                localStorage.removeItem(LS_WORKER_KEY);
                showWorkerToast('Використовується системний ключ.');
            }
            updateWorkerApiKeyUI();
            closeWorkerApiKeyModal();
            fetchWorkerData();
        }

        function clearWorkerApiKey() {
            localStorage.removeItem(LS_WORKER_KEY);
            document.getElementById('workerModalApiKeyInput').value = '';
            updateWorkerApiKeyUI();
            closeWorkerApiKeyModal();
            showWorkerToast('Ключ очищено. Використовується публічний режим.');
            fetchWorkerData();
        }

        function getWorkerRecentSearches() {
            try {
                return JSON.parse(localStorage.getItem(LS_WORKER_RECENTS)) || ['Luc1fer'];
            } catch {
                return ['Luc1fer'];
            }
        }

        function addWorkerRecentSearch(nick) {
            if (!nick) return;
            let recents = getWorkerRecentSearches().filter(n => n.toLowerCase() !== nick.toLowerCase());
            recents.unshift(nick);
            if (recents.length > 6) recents = recents.slice(0, 6);
            localStorage.setItem(LS_WORKER_RECENTS, JSON.stringify(recents));
            renderWorkerRecentChips();
        }

        function renderWorkerRecentChips() {
            const container = document.getElementById('workerRecentChips');
            if (!container) return;
            container.innerHTML = '';
            const recents = getWorkerRecentSearches();
            recents.forEach(nick => {
                const chip = document.createElement('button');
                chip.className = 'px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 text-[11px] text-gray-300 border border-gray-700 transition-colors flex items-center gap-1';
                chip.innerHTML = `<span>${nick}</span>`;
                chip.onclick = () => {
                    document.getElementById('workerSearchInput').value = nick;
                    fetchWorkerData();
                };
                container.appendChild(chip);
            });
        }

        function showWorkerToast(msg) {
            const toast = document.getElementById('workerToast');
            if (!toast) return;
            document.getElementById('workerToastMsg').innerText = msg;
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
            renderWorkerCompanies();
        }

        function toggleAllWorkerCompanies(expand) {
            if (!workerCurrentData || !workerCurrentData.companies) return;
            if (expand) {
                workerCurrentData.companies.forEach(c => workerExpandedCompanies.add(c.company_id));
            } else {
                workerExpandedCompanies.clear();
            }
            renderWorkerCompanies();
        }

        async function fetchWorkerData() {
            const input = document.getElementById('workerSearchInput');
            const nick = (input ? input.value.trim() : '') || 'Luc1fer';
            addWorkerRecentSearch(nick);

            const refreshIcon = document.getElementById('workerRefreshIcon');
            if (refreshIcon) refreshIcon.classList.add('fa-spin');

            const headers = {};
            const userKey = getWorkerUserApiKey();
            if (userKey) {
                headers['X-User-API-Key'] = userKey;
            }

            try {
                // Ingress-safe URL resolution
                const apiUrl = getApiUrl(`api/analyze?nick=${encodeURIComponent(nick)}`);
                const res = await fetch(apiUrl, { headers });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.error || 'Помилка завантаження даних');
                }
                workerCurrentData = await res.json();
                workerDataLoaded = true;
                if (workerCurrentData.companies && workerCurrentData.companies.length > 0 && workerExpandedCompanies.size === 0) {
                    workerExpandedCompanies.add(workerCurrentData.companies[0].company_id);
                }
                renderWorkerAll();
            } catch (err) {
                showWorkerToast(`Помилка: ${err.message}`);
            } finally {
                if (refreshIcon) refreshIcon.classList.remove('fa-spin');
            }
        }

        function renderWorkerAll() {
            if (!workerCurrentData) return;
            const u = workerCurrentData.user;
            const s = workerCurrentData.summary;

            // Player Profile Banner
            document.getElementById('workerPlayerUsername').innerText = u.username;
            document.getElementById('workerPlayerAvatarLetter').innerText = u.username.charAt(0).toUpperCase();
            document.getElementById('workerPlayerLevel').innerText = `Lv.${u.level}`;
            const flag = getCountryFlag(u.country_code);
            document.getElementById('workerPlayerCountry').innerHTML = `<span class="mr-1">${flag}</span>${u.country_name || 'Україна'}`;
            
            const prodSkill = u.production_skill || {};
            const mgmtPts = u.management_pts || 0;
            const mgmtBonus = u.management_bonus_pct || 0;
            document.getElementById('workerPlayerProdSkill').innerHTML = `
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
            const taxListEl = document.getElementById('workerLowestTaxList');
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
            const prodListEl = document.getElementById('workerBestProductsList');
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

            // Counts for category filter pills
            document.getElementById('wcntAll').innerText = s.total_workforce || 0;
            document.getElementById('wcntKeep').innerText = s.keep_count || 0;
            document.getElementById('wcntRelocate').innerText = s.relocate_count || 0;
            if (document.getElementById('wcntMorale')) document.getElementById('wcntMorale').innerText = s.low_morale_count !== undefined ? s.low_morale_count : 0;
            if (document.getElementById('wcntRetire')) document.getElementById('wcntRetire').innerText = s.retire_count !== undefined ? s.retire_count : 0;
            document.getElementById('wcntToxic').innerText = s.toxic_count || 0;

            // Auth Alert Banner
            const auth = workerCurrentData.auth || {};
            const alertBanner = document.getElementById('workerAuthAlertBanner');
            const alertTitle = document.getElementById('workerAuthAlertTitle');
            const alertMsg = document.getElementById('workerAuthAlertMsg');
            
            if (alertBanner) {
                if (auth.auth_failed && !auth.is_community_key) {
                    alertBanner.className = 'bg-rose-950/60 border border-rose-500/60 rounded-xl p-3.5 flex items-center justify-between text-rose-200 shadow-lg';
                    alertTitle.innerText = 'Помилка авторизації WarEra API (401 Unauthorized)';
                    alertMsg.innerText = 'Сервер WarEra відхилив токен. Перевірте його в грі або використовуйте автоматичний ключ спільноти.';
                } else if (workerCurrentData.employees_flat.length === 0 && workerCurrentData.companies.length > 0) {
                    alertBanner.className = 'bg-blue-950/50 border border-blue-500/50 rounded-xl p-3.5 flex items-center justify-between text-blue-200';
                    alertTitle.innerText = 'На фабриках немає робітників';
                    alertMsg.innerText = `На фабриках гравця ${u.username} наразі немає найнятих працівників.`;
                } else {
                    alertBanner.classList.add('hidden');
                }
            }
            updateWorkerApiKeyUI();

            renderWorkerTable();
            renderWorkerCompanies();
            renderWorkerRelocation();
            renderWorkerOptimizer();
        }

        function setWorkerFilter(f) {
            workerCurrentFilter = f;
            ['ALL', 'KEEP', 'RELOCATE', 'LOW_MORALE', 'RETIREMENT', 'TOXIC'].forEach(id => {
                const el = document.getElementById(`wfilter${id}`);
                if (!el) return;
                if (id === f) {
                    el.className = 'px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium transition-colors shadow-lg';
                } else {
                    const colorClass = (id === 'KEEP') ? 'text-emerald-400' :
                                       (id === 'RELOCATE') ? 'text-blue-400' :
                                       (id === 'LOW_MORALE') ? 'text-amber-400' :
                                       (id === 'RETIREMENT') ? 'text-purple-400' :
                                       (id === 'TOXIC') ? 'text-red-400' : 'text-gray-300';
                    el.className = `px-3 py-1.5 rounded-lg bg-gray-800 ${colorClass} hover:bg-gray-700 transition-colors`;
                }
            });
            renderWorkerTable();
            renderWorkerCompanies();
        }

        function sortWorkerList(field) {
            if (workerSortField === field) {
                workerSortAsc = !workerSortAsc;
            } else {
                workerSortField = field;
                workerSortAsc = false;
            }
            renderWorkerTable();
        }

        function renderWorkerTable() {
            const tbody = document.getElementById('workerTableBody');
            if (!tbody || !workerCurrentData) return;
            tbody.innerHTML = '';

            let list = [...workerCurrentData.employees_flat];
            if (workerCurrentFilter !== 'ALL') {
                list = list.filter(e => e.status === workerCurrentFilter);
            }

            list.sort((a, b) => {
                let vA, vB;
                if (workerSortField === 'name') { vA = a.name; vB = b.name; }
                else if (workerSortField === 'company') { vA = a.company_name; vB = b.company_name; }
                else if (workerSortField === 'pp') { vA = a.hourly_pp; vB = b.hourly_pp; }
                else if (workerSortField === 'wage') { vA = a.wage; vB = b.wage; }
                else if (workerSortField === 'spec') { vA = a.spec_days; vB = b.spec_days; }
                else if (workerSortField === 'retire') { vA = a.retire_in_days; vB = b.retire_in_days; }
                else { vA = a.hourly_net_profit; vB = b.hourly_net_profit; }

                if (vA < vB) return workerSortAsc ? -1 : 1;
                if (vA > vB) return workerSortAsc ? 1 : -1;
                return 0;
            });

            if (list.length === 0) {
                const auth = workerCurrentData.auth || {};
                let emptyMsg = 'Немає працівників у цій категорії';
                if (auth.auth_failed) {
                    emptyMsg = '⚠️ Не вдалося завантажити робітників через помилку авторизації API (401 Unauthorized). <button onclick="openWorkerApiKeyModal()" class="ml-1 underline font-semibold text-rose-300 hover:text-white">Оновити API-ключ</button>';
                } else if (!auth.key_present) {
                    emptyMsg = 'ℹ️ Для відображення робітників фабрик введіть ваш API-ключ з гри. <button onclick="openWorkerApiKeyModal()" class="ml-1 underline font-semibold text-amber-300 hover:text-white">Ввести ключ</button>';
                } else if (workerCurrentData.employees_flat.length === 0) {
                    emptyMsg = 'На фабриках цього гравця наразі немає найнятих працівників або ростер робітників приватний.';
                }
                tbody.innerHTML = `<tr><td colspan="10" class="p-8 text-center text-gray-400">${emptyMsg}</td></tr>`;
                return;
            }

            list.forEach(emp => {
                let statusBadge = '<span class="px-2 py-1 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-700/60 font-semibold text-[10px]"><i class="fa-solid fa-gem mr-1"></i>УТРИМУВАТИ</span>';
                if (emp.status === 'TOXIC') {
                    statusBadge = '<span class="px-2 py-1 rounded bg-rose-900/60 text-rose-300 border border-rose-700/60 font-semibold text-[10px]"><i class="fa-solid fa-ban mr-1"></i>ЗВІЛЬНИТИ</span>';
                } else if (emp.status === 'RELOCATE') {
                    statusBadge = '<span class="px-2 py-1 rounded bg-blue-900/60 text-blue-300 border border-blue-700/60 font-semibold text-[10px]"><i class="fa-solid fa-shuffle mr-1"></i>ПЕРЕВЕСТИ</span>';
                } else if (emp.status === 'LOW_MORALE') {
                    statusBadge = '<span class="px-2 py-1 rounded bg-amber-900/60 text-amber-300 border border-amber-700/60 font-semibold text-[10px]"><i class="fa-solid fa-triangle-exclamation mr-1"></i>НАСТРІЙ</span>';
                } else if (emp.status === 'RETIREMENT') {
                    statusBadge = '<span class="px-2 py-1 rounded bg-purple-900/60 text-purple-300 border border-purple-700/60 font-semibold text-[10px]"><i class="fa-solid fa-hourglass-half mr-1"></i>ПЕНСІЯ</span>';
                } else if (emp.status === 'UNDERPERFORMER') {
                    statusBadge = '<span class="px-2 py-1 rounded bg-amber-900/60 text-amber-300 border border-amber-700/60 font-semibold text-[10px]"><i class="fa-solid fa-triangle-exclamation mr-1"></i>СЛАБКИЙ</span>';
                }

                const profitClass = emp.hourly_net_profit >= 0 ? 'text-emerald-400 font-semibold' : 'text-red-400 font-bold';
                const retireClass = emp.retire_in_days <= 4 ? 'text-amber-400 font-bold animate-pulse' : 'text-gray-300';

                const tr = document.createElement('tr');
                tr.className = 'hover:bg-hoverbg/60 transition-colors';
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
                    <td class="p-3 text-right font-mono text-yellow-400/90 whitespace-nowrap">
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

        function renderWorkerCompanies() {
            const container = document.getElementById('wcontentCompanies');
            if (!container || !workerCurrentData) return;
            container.innerHTML = '';

            const comps = workerCurrentData.companies || [];
            if (comps.length === 0) {
                container.innerHTML = `<div class="p-8 text-center text-gray-400 bg-cardbg rounded-xl border border-bordercolor">Підприємств не знайдено.</div>`;
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
                card.className = 'bg-cardbg rounded-2xl border border-bordercolor overflow-hidden shadow-lg transition-all hover:border-gray-600/80';

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

                    // Employees list cards (filtered if filter active)
                    let empList = comp.employees || [];
                    if (workerCurrentFilter !== 'ALL') {
                        empList = empList.filter(e => e.status === workerCurrentFilter);
                    }

                    let employeesCardsHtml = '';
                    if (!comp.employees || comp.employees.length === 0) {
                        employeesCardsHtml = `
                            <div class="p-6 text-center text-gray-400 bg-gray-900/50 rounded-xl border border-gray-800">
                                <i class="fa-solid fa-user-slash text-xl mb-2 text-gray-500"></i>
                                <div>На цьому підприємстві наразі немає найнятих працівників.</div>
                                <div class="text-xs text-gray-500 mt-1">Кімната відпочинку ${comp.break_room_level} ур. дозволяє найняти до ${comp.staff_cap} робітників.</div>
                            </div>
                        `;
                    } else if (empList.length === 0) {
                        employeesCardsHtml = `
                            <div class="p-4 text-center text-gray-400 bg-gray-900/40 rounded-xl border border-gray-800 text-xs">
                                Немає працівників за обраним фільтром на цій фабриці (всього працює: ${comp.employees.length}).
                            </div>
                        `;
                    } else {
                        employeesCardsHtml = empList.map(emp => {
                            let statusBadge = '';
                            if (emp.status === 'KEEP') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/70 text-emerald-300 border border-emerald-700/50">💎 Утримувати</span>`;
                            } else if (emp.status === 'RELOCATE') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-950/70 text-blue-300 border border-blue-700/50">🔄 Перевести</span>`;
                            } else if (emp.status === 'LOW_MORALE') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950/70 text-amber-300 border border-amber-700/50">⚠️ Низький настрій</span>`;
                            } else if (emp.status === 'RETIREMENT') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-950/70 text-purple-300 border border-purple-700/50">⏳ Скоро пенсія</span>`;
                            } else if (emp.status === 'UNDERPERFORMER') {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950/70 text-amber-300 border border-amber-700/50">⚠️ Слабкий</span>`;
                            } else {
                                statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950/70 text-rose-300 border border-rose-700/50">🚨 Звільнити</span>`;
                            }

                            const pensionBadge = emp.retire_in_days <= 30 
                                ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950/40 text-purple-300 border border-purple-700/40" title="Робітника на пенсії можна утримувати й надалі, якщо він приносить прибуток"><i class="fa-solid fa-hourglass-half mr-1"></i>Пенсія: ${emp.retire_in_days} дн. (можна утримувати)</span>` 
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
                                <div class="bg-cardbg p-4 sm:p-5 rounded-xl border border-bordercolor space-y-3 shadow-md">
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
                                <div class="bg-cardbg p-4 sm:p-5 rounded-xl border border-bordercolor space-y-3 shadow-md flex flex-col justify-between">
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

        function renderWorkerRelocation() {
            const container = document.getElementById('workerRelocationCards');
            if (!container || !workerCurrentData) return;
            container.innerHTML = '';

            const relocates = workerCurrentData.employees_flat.filter(e => e.status === 'RELOCATE' && e.relocation_target);

            if (relocates.length === 0) {
                container.innerHTML = `
                    <div class="col-span-2 bg-cardbg p-8 text-center text-gray-400 rounded-xl shadow-lg border border-bordercolor">
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
                card.className = 'bg-cardbg p-5 rounded-xl space-y-4 border border-blue-500/40 relative overflow-hidden shadow-lg';
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

        function renderWorkerOptimizer() {
            const container = document.getElementById('workerOptimizerTable');
            if (!container || !workerCurrentData) return;
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
                        ${workerCurrentData.companies.map(c => `
                            <tr class="hover:bg-hoverbg/50">
                                <td class="p-3 font-semibold text-white">${c.name}</td>
                                <td class="p-3 font-mono text-indigo-400">${c.item_code.toUpperCase()}</td>
                                <td class="p-3 text-right font-mono">${workerCurrentData.economics_by_item[c.item_code].market_price.toFixed(4)}</td>
                                <td class="p-3 text-right font-mono text-gray-400">${workerCurrentData.economics_by_item[c.item_code].raw_cost.toFixed(4)}</td>
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

        function switchWorkerSubTab(t) {
            ['workers', 'companies', 'relocation', 'optimizer'].forEach(tabName => {
                const btn = document.getElementById(`wtab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
                const content = document.getElementById(`wcontent${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
                if (!btn || !content) return;
                if (tabName === t) {
                    btn.className = 'pb-3 tab-active flex items-center gap-2 whitespace-nowrap text-blue-400 font-semibold';
                    content.classList.remove('hidden');
                } else {
                    btn.className = 'pb-3 text-gray-400 hover:text-gray-200 flex items-center gap-2 transition-colors whitespace-nowrap';
                    content.classList.add('hidden');
                }
            });
        }

        function copyWorkerReportToClipboard() {
            if (!workerCurrentData) return;
            const u = workerCurrentData.user;
            const s = workerCurrentData.summary;

            let text = `🏰 *WarEra Workforce Intel Report* — ${u.username} (Lv.${u.level})\n`;
            text += `🏭 Фабрик: ${s.total_companies} | 👥 Персонал: ${s.total_workforce}\n`;
            text += `💰 Чистий прибуток: ${s.total_hourly_profit >= 0 ? '+' : ''}${s.total_hourly_profit.toFixed(4)}/год (${s.total_daily_profit >= 0 ? '+' : ''}${s.total_daily_profit.toFixed(2)} Coins/добу)\n`;
            text += `📊 Статуси: 💎 Утримувати: ${s.keep_count} | 🔄 Перевести: ${s.relocate_count} | ⚠️ Низький настрій: ${s.low_morale_count || 0} | ⏳ Скоро пенсія: ${s.retire_count || 0} | 🚨 Звільнити: ${s.toxic_count}\n\n`;

            const alerts = workerCurrentData.employees_flat.filter(e => e.status !== 'KEEP');
            if (alerts.length > 0) {
                text += `⚠️ *Рекомендації до уваги:*\n`;
                alerts.forEach(e => {
                    text += `• [${e.status}] ${e.name} (${e.company_name}): ${e.recommendation}\n`;
                });
            } else {
                text += `✅ Всі працівники оптимально розподілені, фабрики працюють без збитків!\n`;
            }

            navigator.clipboard.writeText(text).then(() => {
                showWorkerToast('Звіт скопійовано в буфер обміну!');
            });
        }

        function downloadWorkerJsonReport() {
            if (!workerCurrentData) return;
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(workerCurrentData, null, 2));
            const dlAnchor = document.createElement('a');
            dlAnchor.setAttribute("href", dataStr);
            dlAnchor.setAttribute("download", `warera_workforce_${workerCurrentData.user.username}.json`);
            dlAnchor.click();
            dlAnchor.remove();
            showWorkerToast('JSON звіт збережено!');
        }

        // Initialize view & recents
        window.addEventListener('DOMContentLoaded', () => {
            updateWorkerApiKeyUI();
            renderWorkerRecentChips();
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('view') === 'workers' || window.location.pathname.endsWith('/workers')) {
                switchMainView('workers');
            }
        });

    </script>

    <!-- Worker API Key Modal -->
    <div id="workerApiKeyModal" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-cardbg p-6 rounded-2xl max-w-lg w-full space-y-4 shadow-2xl border border-gray-700">
            <div class="flex items-center justify-between">
                <h3 class="text-base font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-key text-yellow-400"></i>
                    Особистий API-ключ WarEra
                </h3>
                <button onclick="closeWorkerApiKeyModal()" class="text-gray-400 hover:text-white text-lg">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            <p class="text-xs text-gray-300 leading-relaxed">
                Якщо ви хочете аналізувати приватні дані власних фабрик, введіть ваш персональний токен (<span class="text-blue-400">app.warera.io &rarr; Профіль &rarr; API Token</span>).
            </p>
            <div class="space-y-1.5">
                <label class="text-[11px] text-gray-400 font-semibold uppercase">API Token (wae_...):</label>
                <div class="relative">
                    <input id="workerModalApiKeyInput" type="password" placeholder="wae_xxxxxxxxxxxxxxxxxxxxxxxx..."
                        class="w-full bg-gray-900 border border-bordercolor rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono">
                    <button type="button" onclick="toggleWorkerApiKeyVisibility()" class="absolute right-3 top-2.5 text-gray-400 hover:text-white text-xs">
                        <i class="fa-solid fa-eye" id="workerApiKeyEyeIcon"></i>
                    </button>
                </div>
                <p class="text-[10px] text-emerald-400 flex items-center gap-1 mt-1">
                    <i class="fa-solid fa-shield-halved"></i> Зберігається тільки у вашому браузері (localStorage).
                </p>
            </div>
            <div class="flex items-center justify-end gap-2 pt-2 border-t border-bordercolor">
                <button onclick="clearWorkerApiKey()" class="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-red-400 text-xs font-medium transition-colors">
                    Видалити / Скинути
                </button>
                <button onclick="saveWorkerApiKey()" class="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition-all">
                    Зберегти ключ
                </button>
            </div>
        </div>
    </div>

    <!-- Generic Toast -->
    <div id="workerToast" class="fixed bottom-5 right-5 z-50 transform translate-y-20 opacity-0 transition-all duration-300 bg-gray-900 border border-blue-500 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs">
        <i class="fa-solid fa-circle-check text-emerald-400 text-base"></i>
        <span id="workerToastMsg">Повідомлення</span>
    </div>

</body>
</html>
"""


class EquipmentDashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default request logging to avoid terminal clutter
        pass

    def _send_json(self, data: Any, status: int = HTTPStatus.OK):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path.rstrip("/")

        # Status endpoint
        if clean_path.endswith("/api/status"):
            if _app_instance:
                status = _app_instance.get_status()
            else:
                status = {
                    "version": config.APP_VERSION,
                    "running": False,
                    "paused": True,
                    "scan_interval": config.EQUIPMENT_SCAN_INTERVAL,
                    "pricing_mode": config.PRICING_MODE,
                    "cycles": 0,
                    "total_alerts": 0,
                    "active_deals_count": 0,
                    "history_deals_count": 0,
                    "best_discount": 0.0,
                    "best_deal_item": "--",
                    "last_scan_time": "--:--:--",
                    "active_qualities": config.EQUIPMENT_QUALITIES,
                    "monitored_items_count": len(config.EQUIPMENT_TO_MONITOR),
                    "min_discount": config.EQUIPMENT_MIN_DISCOUNT,
                    "god_roll_threshold": config.EQUIPMENT_GOD_ROLL_THRESHOLD,
                }
            self._send_json(status)
            return

        # Deals endpoint
        if clean_path.endswith("/api/deals"):
            deals = _app_instance.get_deals() if _app_instance else []
            self._send_json({"status": "ok", "deals": deals, "count": len(deals)})
            return

        # Market offers inspector endpoint
        if clean_path.endswith("/api/market"):
            query_params = parse_qs(parsed.query)
            item_code = query_params.get("item", ["boots4"])[0]
            offers = []
            if _app_instance:
                offers = _app_instance.get_market_offers(item_code)
            self._send_json({"status": "ok", "item": item_code, "offers": offers})
            return

        # Workforce & Factory Intelligence routes
        if clean_path.endswith("/workers") or clean_path.endswith("/workforce"):
            import worker_dashboard
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(worker_dashboard.DASHBOARD_HTML.encode("utf-8"))
            return

        if clean_path.endswith("/api/analyze"):
            from worker_analyzer import WarEraWorkerAnalyzer
            query_params = parse_qs(parsed.query)
            nick = query_params.get("nick", [None])[0]
            user_key = self.headers.get("X-User-API-Key") or query_params.get("apiKey", [None])[0]
            analyzer = WarEraWorkerAnalyzer(api_key=user_key) if user_key else WarEraWorkerAnalyzer()
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                data = loop.run_until_complete(analyzer.analyze_user(nick))
                loop.close()
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # Clan & Military Unit (MU) Intelligence routes (Public, Zero-Auth)
        if clean_path.endswith("/clan") or clean_path.endswith("/clan.html"):
            import clan_dashboard
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(clan_dashboard.CLAN_DASHBOARD_HTML.encode("utf-8"))
            return

        if clean_path.endswith("/api/clan"):
            from clan_analyzer import WarEraClanAnalyzer
            query_params = parse_qs(parsed.query)
            mu_id = query_params.get("mu", [None])[0] or query_params.get("nick", [None])[0]
            user_key = self.headers.get("X-User-API-Key") or query_params.get("apiKey", [None])[0]
            analyzer = WarEraClanAnalyzer(api_key=user_key) if user_key else WarEraClanAnalyzer()
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                data = loop.run_until_complete(analyzer.analyze_clan(mu_id))
                loop.close()
                self._send_json(data)
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # Serve SPA HTML for root or any Ingress subpath
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path.rstrip("/")

        # Manual Scan endpoint
        if clean_path.endswith("/api/scan"):
            if _app_instance:
                if _loop_instance and _loop_instance.is_running():
                    asyncio.run_coroutine_threadsafe(_app_instance.trigger_manual_scan(), _loop_instance)
                else:
                    _app_instance.wake_event.set()
                self._send_json({"status": "ok", "message": "Сканування запущено"})
            else:
                self._send_json({"status": "error", "message": "Сканер не підключено"}, HTTPStatus.SERVICE_UNAVAILABLE)
            return

        # Control actions endpoint
        if clean_path.endswith("/api/control"):
            content_length = int(self.headers.get("Content-Length", 0))
            body_raw = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                body = json.loads(body_raw)
            except Exception:
                body = {}

            action = body.get("action", "")

            if not _app_instance:
                self._send_json({"status": "error", "message": "Сканер не підключено"}, HTTPStatus.SERVICE_UNAVAILABLE)
                return

            if action == "pause":
                _app_instance.pause()
            elif action == "resume":
                _app_instance.resume()
            elif action == "set_interval":
                sec = int(body.get("interval", 1))
                _app_instance.set_scan_interval(sec)
            elif action == "set_mode":
                mode = str(body.get("mode", "live"))
                _app_instance.set_pricing_mode(mode)
            elif action == "toggle_quality":
                q = str(body.get("quality", "mythic"))
                _app_instance.toggle_quality(q)
            elif action == "set_thresholds":
                if "min_discount" in body:
                    _app_instance.set_min_discount_pct(float(body["min_discount"]))
                if "god_roll" in body:
                    _app_instance.set_god_roll_threshold(float(body["god_roll"]))
            elif action == "clear_deals":
                _app_instance.clear_deals()

            self._send_json({
                "status": "ok",
                "action": action,
                "current_status": _app_instance.get_status()
            })
            return

        self._send_json({"status": "error", "message": "Невідомий маршрут"}, HTTPStatus.NOT_FOUND)


def start_dashboard(host: str = "0.0.0.0", port: int = 8080, app_instance: Optional[Any] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
    """Starts the Web Dashboard HTTP server in a separate background daemon thread."""
    if app_instance is not None:
        set_app_instance(app_instance, loop)

    def _serve():
        try:
            server = HTTPServer((host, port), EquipmentDashboardHandler)
            print(f"\n[🚀 Web Dashboard] Активний за адресою: http://{host}:{port} (Ingress port {port})")
            server.serve_forever()
        except Exception as e:
            print(f"[Web Dashboard] Помилка або сервер зупинено: {e}")

    thread = Thread(target=_serve, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    print(f"Starting standalone WarEra Equipment Dashboard on port {config.WEB_DASHBOARD_PORT}...")
    server = HTTPServer((config.WEB_DASHBOARD_HOST, config.WEB_DASHBOARD_PORT), EquipmentDashboardHandler)
    try:
        print(f"Open: http://localhost:{config.WEB_DASHBOARD_PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

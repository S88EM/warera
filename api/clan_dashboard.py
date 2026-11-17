"""
WarEra Clan & Military Unit (MU) Standalone Dashboard
Public, zero-auth page for clan mates and commanders.
Features:
- Live War/Eco/Hybrid build categorization
- Live Pill status ('cocain' +60% buff / ready / cooldown -60%)
- Theoretical daily damage with minimum Full Epic (Purple IV) gear, armor, dodge
- Inactive / AFK monitor (>24h offline)
- One-click Discord/Telegram report copy
"""

CLAN_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="uk" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WarEra · Штаб Клану (Combat Intelligence)</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        darkbg: '#0a0d14',
                        cardbg: '#111622',
                        hoverbg: '#1a2234',
                        bordercolor: '#212c42'
                    }
                }
            }
        }
    </script>
    <!-- FontAwesome 6 -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Font: Inter -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0a0d14; color: #f3f4f6; }
        .glass-panel { background: rgba(17, 22, 34, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(33, 44, 66, 0.8); }
        .tab-btn.active { background: #2563eb; color: #ffffff; font-weight: 600; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0a0d14; }
        ::-webkit-scrollbar-thumb { background: #212c42; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3b82f6; }
    </style>
</head>
<body class="min-h-screen flex flex-col antialiased selection:bg-blue-600 selection:text-white">

    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-40 bg-darkbg/95 backdrop-blur border-b border-bordercolor px-4 py-3">
        <div class="max-w-7xl mx-auto flex items-center justify-between gap-3">
            <div class="flex items-center gap-3">
                <a href="./" class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-800 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 hover:opacity-90 transition-opacity">
                    <i class="fa-solid fa-shield-halved text-lg"></i>
                </a>
                <div>
                    <div class="flex items-center gap-2">
                        <span class="font-extrabold text-white text-base tracking-tight" id="headerClanTitle">WarEra · Штаб Клану</span>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/60 uppercase tracking-wider flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span> Live Intel
                        </span>
                    </div>
                    <div class="text-xs text-gray-400">Бойова готовність, білди, статус таблетки та розрахунок залпу</div>
                </div>
            </div>

            <!-- Header Actions -->
            <div class="flex items-center gap-2 flex-wrap">
                <a href="./" class="px-3 py-1.5 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-gray-300 text-xs font-medium border border-bordercolor transition-colors flex items-center gap-1.5">
                    <i class="fa-solid fa-arrow-left text-gray-400"></i> Сканер ринку
                </a>
                <button onclick="copyDiscordReport()" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all flex items-center gap-1.5">
                    <i class="fa-solid fa-copy"></i> Скопіювати звіт
                </button>
                <button onclick="loadClanData(true)" class="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs border border-bordercolor transition-colors" title="Оновити дані">
                    <i class="fa-solid fa-rotate" id="refreshIcon"></i>
                </button>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">

        <!-- Clan Hero Header Banner -->
        <section class="glass-panel rounded-2xl p-5 border border-bordercolor shadow-xl relative overflow-hidden">
            <div class="absolute -right-10 -bottom-10 opacity-5 pointer-events-none text-9xl">
                <i class="fa-solid fa-shield-halved"></i>
            </div>
            
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-5 relative z-10">
                <!-- Clan Branding -->
                <div class="flex items-center gap-4">
                    <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-950 to-cardbg border-2 border-indigo-500/40 p-1 flex items-center justify-center shrink-0 shadow-lg overflow-hidden">
                        <img id="clanAvatar" src="https://media.warera.io/avatars/mu/mu-69af3162a583a3b5f9941e71-1790698677633-kmc5qgys.png" alt="MU Logo" class="w-full h-full object-cover rounded-xl" onerror="this.src=''; this.parentElement.innerHTML='<i class=\'fa-solid fa-shield text-2xl text-indigo-400\'></i>';">
                    </div>
                    <div>
                        <div class="flex items-center gap-2.5 flex-wrap">
                            <h1 id="clanName" class="text-2xl font-black text-white tracking-tight">Завантаження клану...</h1>
                            <span id="clanTierBadge" class="px-2 py-0.5 rounded text-xs font-bold bg-blue-950 text-blue-300 border border-blue-700/60 uppercase">Platinum</span>
                            <span class="px-2 py-0.5 rounded text-xs font-mono bg-purple-950 text-purple-300 border border-purple-700/60" id="clanRankBadge">Ранг #--</span>
                        </div>
                        <div class="text-xs text-gray-400 flex items-center gap-3 mt-1.5 flex-wrap">
                            <span id="clanUpgrades"><i class="fa-solid fa-landmark text-indigo-400 mr-1"></i>Штаб: -- ур. · Казарми: -- ур.</span>
                            <span>·</span>
                            <span id="clanWealth"><i class="fa-solid fa-coins text-yellow-400 mr-1"></i>Казна підрозділу: -- Coins</span>
                            <span>·</span>
                            <span class="text-emerald-400 font-semibold"><i class="fa-solid fa-unlock text-[10px] mr-1"></i>Публічний доступ для сокланів</span>
                        </div>
                    </div>
                </div>

                <!-- Live Salvo Highlight Card -->
                <div class="bg-gradient-to-br from-rose-950/40 to-cardbg p-3.5 rounded-xl border border-rose-500/30 flex items-center gap-4 shrink-0 shadow-lg">
                    <div class="w-12 h-12 rounded-xl bg-rose-600/20 border border-rose-500/30 flex items-center justify-center text-rose-400 text-2xl shrink-0">
                        <i class="fa-solid fa-crosshairs"></i>
                    </div>
                    <div>
                        <div class="text-[11px] font-bold uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
                            <span>Загальний залп клану на добу</span>
                            <i class="fa-solid fa-circle-question text-gray-400 cursor-pointer" title="Теоретичний щоденний дамаг усіх вар-бійців під таблеткою з мінімальним фіол-сетом (з урахуванням броні та увороту)"></i>
                        </div>
                        <div class="text-xl sm:text-2xl font-black text-white mt-0.5" id="statClanSalvo">--</div>
                        <div class="text-[11px] text-gray-400">під таблеткою + мін. фіол-сет IV</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 4 Key Stat Summary Cards -->
        <section class="grid grid-cols-2 md:grid-cols-4 gap-3.5">
            <!-- 1. Вар білди -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Бойові білди (War)</span>
                    <i class="fa-solid fa-swords text-emerald-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-emerald-400" id="statWarCount">--</div>
                <div class="text-xs text-gray-400 mt-1" id="statWarSub">-- бійців клану (≥70% вар)</div>
            </div>

            <!-- 2. Таблетка (Бойова готовність) -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Під таблеткою (+60%)</span>
                    <i class="fa-solid fa-capsules text-purple-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-purple-300" id="statPillActive">--</div>
                <div class="text-xs text-gray-400 mt-1" id="statPillSub">-- готові прийняти наказ</div>
            </div>

            <!-- 3. Еко-тил / Гібриди -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Еко-тил & Гібриди</span>
                    <i class="fa-solid fa-tractor text-amber-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-amber-300" id="statEcoCount">--</div>
                <div class="text-xs text-gray-400 mt-1" id="statEcoSub">-- еко / -- гібриди</div>
            </div>

            <!-- 4. Активність / AFK -->
            <div class="glass-panel p-4 rounded-xl border border-bordercolor shadow-md hover:border-gray-600 transition-all">
                <div class="text-[11px] font-bold uppercase tracking-wider text-gray-400 flex items-center justify-between">
                    <span>Детектор онлайну</span>
                    <i class="fa-solid fa-clock text-blue-400"></i>
                </div>
                <div class="mt-2 text-2xl font-black text-blue-400" id="statOnlineCount">--</div>
                <div class="text-xs text-gray-400 mt-1" id="statAfkSub">-- інактив (>24 год)</div>
            </div>
        </section>

        <!-- Beginner Tip / Rule Banner -->
        <section class="bg-blue-950/30 border border-blue-500/40 rounded-xl p-3.5 text-xs text-blue-200 flex items-center gap-3">
            <i class="fa-solid fa-circle-info text-blue-400 text-lg shrink-0"></i>
            <div>
                <span class="font-bold text-white">Як розраховується бойова міць бійців:</span> 
                Теоретичний дамаг розраховано під <b>таблеткою (+60% атаки)</b> з мінімальним <b>фулл-фіол сетом IV</b> (або фактичним, якщо вдягнено краще). Враховано <b>уворот</b> (удари з 0 витратою HP) та <b>броню</b> (зменшення втрати HP), що збільшує кількість ударів на добу у 3–4 рази!
            </div>
        </section>

        <!-- Controls, Filter Tabs & Search -->
        <section class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 flex-wrap">
            <!-- Filter Pills -->
            <div class="flex items-center gap-1.5 flex-wrap text-xs">
                <button onclick="setFilter('ALL')" id="filterALL" class="tab-btn px-3 py-1.5 rounded-lg active transition-colors">Всі (<span id="cntAll">0</span>)</button>
                <button onclick="setFilter('WAR')" id="filterWAR" class="tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-emerald-400 hover:bg-gray-700 transition-colors">⚔️ Вар (<span id="cntWar">0</span>)</button>
                <button onclick="setFilter('PILL_ACTIVE')" id="filterPILL_ACTIVE" class="tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-purple-400 hover:bg-gray-700 transition-colors">💊 П'є зараз (<span id="cntPillActive">0</span>)</button>
                <button onclick="setFilter('PILL_READY')" id="filterPILL_READY" class="tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-blue-400 hover:bg-gray-700 transition-colors">⚪ Готовий (<span id="cntPillReady">0</span>)</button>
                <button onclick="setFilter('PILL_COOLDOWN')" id="filterPILL_COOLDOWN" class="tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-rose-400 hover:bg-gray-700 transition-colors">⏳ Відкат (<span id="cntPillCooldown">0</span>)</button>
                <button onclick="setFilter('HYBRID')" id="filterHYBRID" class="tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-sky-400 hover:bg-gray-700 transition-colors">⚖️ Гібриди (<span id="cntHybrid">0</span>)</button>
                <button onclick="setFilter('ECO')" id="filterECO" class="tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-amber-400 hover:bg-gray-700 transition-colors">🚜 Еко (<span id="cntEco">0</span>)</button>
                <button onclick="setFilter('AFK')" id="filterAFK" class="tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-gray-400 hover:bg-gray-700 transition-colors">💤 Інактив (<span id="cntAfk">0</span>)</button>
            </div>

            <!-- Search box -->
            <div class="relative min-w-[200px]">
                <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-gray-400 text-xs"></i>
                <input type="text" id="memberSearchInput" oninput="renderMembersTable()" placeholder="Пошук бійця за ніком..." class="w-full bg-cardbg border border-bordercolor rounded-lg pl-8 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 transition-colors">
            </div>
        </section>

        <!-- Clan Roster Table -->
        <section class="glass-panel rounded-2xl border border-bordercolor shadow-xl overflow-hidden">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse text-xs">
                    <thead>
                        <tr class="bg-cardbg/80 border-b border-bordercolor text-gray-400 font-semibold select-none">
                            <th class="p-3 cursor-pointer hover:text-white transition-colors" onclick="sortRoster('name')">Боєць <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors" onclick="sortRoster('role')">Роль <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors" onclick="sortRoster('build')">Білд <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors" onclick="sortRoster('pill')">Таблетка (Cocain) <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors" onclick="sortRoster('defense')" title="Ефективна броня та уворот з урахуванням фіол-сету та софткапу">Захист (Фіол) <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors" onclick="sortRoster('hits')" title="Кількість ударів на добу з пулу здоров'я з урахуванням зниження втрати HP">Ударів/добу <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors text-right" onclick="sortRoster('damage')">Очікуваний дамаг/день <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors text-right" onclick="sortRoster('weekly')">Дамаг тижня <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                            <th class="p-3 cursor-pointer hover:text-white transition-colors" onclick="sortRoster('online')">Онлайн <i class="fa-solid fa-sort ml-1 text-[10px]"></i></th>
                        </tr>
                    </thead>
                    <tbody id="clanTableBody" class="divide-y divide-bordercolor/60">
                        <tr>
                            <td colspan="9" class="p-8 text-center text-gray-400">
                                <i class="fa-solid fa-spinner fa-spin text-xl mb-2 text-blue-500"></i>
                                <div>Завантаження бойового складу клану...</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="border-t border-bordercolor bg-darkbg/90 py-4 px-6 text-center text-xs text-gray-500">
        WarEra Clan Combat Intelligence · Black Mace · Дані синхронізовано з грою
    </footer>

    <!-- Toast Notification -->
    <div id="toast" class="fixed bottom-5 right-5 z-50 transform translate-y-20 opacity-0 transition-all duration-300 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold flex items-center gap-2"></div>

    <script>
        let clanData = null;
        let currentFilter = 'ALL';
        let sortField = 'damage';
        let sortAsc = false;

        function showToast(msg, isSuccess = true) {
            const toast = document.getElementById('toast');
            toast.className = `fixed bottom-5 right-5 z-50 transform translate-y-0 opacity-100 transition-all duration-300 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold flex items-center gap-2 ${
                isSuccess ? 'bg-emerald-950 text-emerald-200 border border-emerald-600/50' : 'bg-rose-950 text-rose-200 border border-rose-600/50'
            }`;
            toast.innerHTML = `<i class="fa-solid ${isSuccess ? 'fa-check-circle text-emerald-400' : 'fa-circle-exclamation text-rose-400'}"></i> ${msg}`;
            setTimeout(() => {
                toast.classList.add('translate-y-20', 'opacity-0');
            }, 3000);
        }

        async function loadClanData(isManual = false) {
            const icon = document.getElementById('refreshIcon');
            if (icon) icon.classList.add('fa-spin');

            try {
                const urlParams = new URLSearchParams(window.location.search);
                const muParam = urlParams.get('mu') || '';
                const basePath = window.location.pathname.replace(/\/(clan(\.html)?|\index\.html)?\/?$/, '');
                const cleanEndpoint = `api/clan${muParam ? `?mu=${encodeURIComponent(muParam)}` : ''}`;
                const apiUrl = basePath ? `${basePath}/${cleanEndpoint}` : `./${cleanEndpoint}`;

                const resp = await fetch(apiUrl);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

                const contentType = resp.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                    const textSample = await resp.text();
                    throw new Error(`Сервер повернув HTML замість JSON. Перевірте оновлення бекенду.`);
                }

                const data = await resp.json();

                if (data.status !== 'ok') {
                    throw new Error(data.message || 'Не вдалося завантажити дані підрозділу');
                }

                clanData = data;
                renderClanHeader();
                renderMembersTable();
                if (isManual) showToast('Дані клану оновлено!');
            } catch (err) {
                console.error('Failed to load clan data:', err);
                showToast(`Помилка: ${err.message}`, false);
            } finally {
                if (icon) icon.classList.remove('fa-spin');
            }
        }

        function formatNumber(num) {
            if (num === undefined || num === null) return '0';
            return num.toLocaleString('uk-UA');
        }

        function formatMillions(num) {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(2) + 'M';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'k';
            }
            return num.toString();
        }

        function renderClanHeader() {
            if (!clanData) return;
            const mu = clanData.mu;
            const s = clanData.summary;

            document.getElementById('clanName').innerText = mu.name || 'Black Mace';
            document.getElementById('headerClanTitle').innerText = `${mu.name || 'Black Mace'} · Штаб`;
            if (mu.avatar_url) {
                document.getElementById('clanAvatar').src = mu.avatar_url;
            }
            document.getElementById('clanTierBadge').innerText = (mu.weekly_tier || 'Platinum').toUpperCase();
            document.getElementById('clanRankBadge').innerText = `Ранг #${mu.weekly_rank || '--'}`;
            document.getElementById('clanUpgrades').innerHTML = `<i class="fa-solid fa-landmark text-indigo-400 mr-1"></i>Штаб: ${mu.headquarters_level} ур. · Казарми: ${mu.dormitories_level} ур.`;
            document.getElementById('clanWealth').innerHTML = `<i class="fa-solid fa-coins text-yellow-400 mr-1"></i>Казна підрозділу: ${formatNumber(Math.round(mu.wealth))} Coins`;

            // Salvo Highlight
            const minM = (s.clan_daily_salvo_min / 1000000).toFixed(1);
            const maxM = (s.clan_daily_salvo_max / 1000000).toFixed(1);
            document.getElementById('statClanSalvo').innerText = `~${minM}M – ${maxM}M`;

            // KPI Cards
            document.getElementById('statWarCount').innerText = s.war_count;
            document.getElementById('statWarSub').innerText = `${Math.round((s.war_count / s.total_members) * 100)}% складу клану (≥70% вар)`;

            document.getElementById('statPillActive').innerText = `${s.pill_active_count} бійців`;
            document.getElementById('statPillSub').innerText = `${s.pill_ready_count} готові прийняти наказ`;

            document.getElementById('statEcoCount').innerText = `${s.eco_count} / ${s.hybrid_count}`;
            document.getElementById('statEcoSub').innerText = `${s.eco_count} еко-акаунтів · ${s.hybrid_count} гібрид`;

            const onlineCount = s.total_members - s.afk_count;
            document.getElementById('statOnlineCount').innerText = `${onlineCount} / ${s.total_members}`;
            document.getElementById('statAfkSub').innerText = `${s.afk_count} інактив (>24 год)`;

            // Counts for filter pills
            document.getElementById('cntAll').innerText = s.total_members;
            document.getElementById('cntWar').innerText = s.war_count;
            document.getElementById('cntPillActive').innerText = s.pill_active_count;
            document.getElementById('cntPillReady').innerText = s.pill_ready_count;
            document.getElementById('cntPillCooldown').innerText = s.pill_cooldown_count;
            document.getElementById('cntHybrid').innerText = s.hybrid_count;
            document.getElementById('cntEco').innerText = s.eco_count;
            document.getElementById('cntAfk').innerText = s.afk_count;
        }

        function setFilter(f) {
            currentFilter = f;
            ['ALL', 'WAR', 'PILL_ACTIVE', 'PILL_READY', 'PILL_COOLDOWN', 'HYBRID', 'ECO', 'AFK'].forEach(id => {
                const el = document.getElementById(`filter${id}`);
                if (!el) return;
                if (id === f) {
                    el.className = 'tab-btn px-3 py-1.5 rounded-lg active transition-colors shadow-lg';
                } else {
                    el.className = 'tab-btn px-3 py-1.5 rounded-lg bg-gray-800 text-gray-400 hover:bg-gray-700 transition-colors';
                }
            });
            renderMembersTable();
        }

        function sortRoster(field) {
            if (sortField === field) {
                sortAsc = !sortAsc;
            } else {
                sortField = field;
                sortAsc = false;
            }
            renderMembersTable();
        }

        function renderMembersTable() {
            const tbody = document.getElementById('clanTableBody');
            if (!tbody || !clanData) return;

            let list = [...clanData.members];

            // Filter
            if (currentFilter === 'WAR') {
                list = list.filter(m => m.build_type === 'WAR');
            } else if (currentFilter === 'ECO') {
                list = list.filter(m => m.build_type === 'ECO');
            } else if (currentFilter === 'HYBRID') {
                list = list.filter(m => m.build_type === 'HYBRID');
            } else if (currentFilter === 'PILL_ACTIVE') {
                list = list.filter(m => m.pill_status === 'ACTIVE');
            } else if (currentFilter === 'PILL_READY') {
                list = list.filter(m => m.pill_status === 'READY');
            } else if (currentFilter === 'PILL_COOLDOWN') {
                list = list.filter(m => m.pill_status === 'COOLDOWN');
            } else if (currentFilter === 'AFK') {
                list = list.filter(m => m.is_afk);
            }

            // Search query
            const q = (document.getElementById('memberSearchInput').value || '').trim().toLowerCase();
            if (q) {
                list = list.filter(m => m.username.toLowerCase().includes(q));
            }

            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-gray-400">Не знайдено бійців за вказаними критеріями</td></tr>`;
                return;
            }

            // Sort
            list.sort((a, b) => {
                let vA, vB;
                if (sortField === 'name') { vA = a.username; vB = b.username; }
                else if (sortField === 'role') { vA = a.clan_role; vB = b.clan_role; }
                else if (sortField === 'build') { vA = a.war_ratio; vB = b.war_ratio; }
                else if (sortField === 'pill') { vA = a.pill_status; vB = b.pill_status; }
                else if (sortField === 'defense') { vA = a.effective_armor + a.effective_dodge; vB = b.effective_armor + b.effective_dodge; }
                else if (sortField === 'hits') { vA = a.hits_per_day_max; vB = b.hits_per_day_max; }
                else if (sortField === 'weekly') { vA = a.weekly_damage; vB = b.weekly_damage; }
                else if (sortField === 'online') { vA = a.hours_offline; vB = b.hours_offline; }
                else { vA = a.theoretical_daily_dmg_max; vB = b.theoretical_daily_dmg_max; }

                if (vA < vB) return sortAsc ? -1 : 1;
                if (vA > vB) return sortAsc ? 1 : -1;
                return 0;
            });

            tbody.innerHTML = list.map(m => {
                // Online indicator
                let onlineDot = 'bg-emerald-400';
                if (m.hours_offline >= 24) {
                    onlineDot = 'bg-rose-500';
                } else if (m.hours_offline >= 3) {
                    onlineDot = 'bg-amber-400';
                }

                // Pill Badge
                let pillBadgeClass = 'bg-gray-800 text-gray-400 border-gray-700';
                if (m.pill_status === 'ACTIVE') {
                    pillBadgeClass = 'bg-purple-950/80 text-purple-300 border-purple-700/60 font-semibold';
                } else if (m.pill_status === 'READY') {
                    pillBadgeClass = 'bg-blue-950/80 text-blue-300 border-blue-700/60 font-semibold';
                } else if (m.pill_status === 'COOLDOWN') {
                    pillBadgeClass = 'bg-rose-950/80 text-rose-300 border-rose-700/60 font-semibold';
                }

                // Build Badge
                let buildBadgeClass = 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50';
                if (m.build_type === 'ECO') {
                    buildBadgeClass = 'bg-amber-950/60 text-amber-300 border-amber-700/50';
                } else if (m.build_type === 'HYBRID') {
                    buildBadgeClass = 'bg-sky-950/60 text-sky-300 border-sky-700/50';
                }

                // Role Badge
                let roleColor = 'text-gray-400';
                if (m.clan_role === 'LEADER') roleColor = 'text-yellow-400 font-bold';
                if (m.clan_role === 'COMMANDER') roleColor = 'text-rose-400 font-semibold';
                if (m.clan_role === 'MANAGER') roleColor = 'text-purple-400 font-semibold';

                const dmgMinM = formatMillions(m.theoretical_daily_dmg_min);
                const dmgMaxM = formatMillions(m.theoretical_daily_dmg_max);

                return `
                    <tr class="hover:bg-hoverbg/50 transition-colors">
                        <!-- Боєць -->
                        <td class="p-3 whitespace-nowrap">
                            <div class="flex items-center gap-2.5">
                                <div class="w-8 h-8 rounded-lg bg-gray-800 border border-gray-700 overflow-hidden shrink-0 flex items-center justify-center">
                                    ${m.avatar_url ? `<img src="${m.avatar_url}" class="w-full h-full object-cover">` : `<span class="text-xs font-bold text-gray-300">${m.username.charAt(0)}</span>`}
                                </div>
                                <div>
                                    <div class="font-bold text-white text-xs flex items-center gap-1.5">
                                        <span>${m.username}</span>
                                        <span class="text-[10px] px-1 rounded bg-gray-800 text-yellow-400 border border-bordercolor">Lv.${m.level}</span>
                                    </div>
                                    <div class="text-[10px] text-gray-400">Ранг ${m.military_rank}</div>
                                </div>
                            </div>
                        </td>

                        <!-- Роль у клані -->
                        <td class="p-3 whitespace-nowrap">
                            <span class="${roleColor} text-xs">${m.role_label}</span>
                        </td>

                        <!-- Білд -->
                        <td class="p-3 whitespace-nowrap">
                            <span class="px-2 py-0.5 rounded text-[11px] font-medium border ${buildBadgeClass}">
                                ${m.build_label}
                            </span>
                        </td>

                        <!-- Таблетка -->
                        <td class="p-3 whitespace-nowrap">
                            <span class="px-2 py-0.5 rounded text-[11px] border ${pillBadgeClass}" title="${m.pill_tip}">
                                ${m.pill_label}
                            </span>
                        </td>

                        <!-- Захист -->
                        <td class="p-3 whitespace-nowrap">
                            <div class="font-mono text-gray-200 text-xs">
                                <span class="text-blue-400" title="Броня">${m.effective_armor}%</span> / <span class="text-emerald-400" title="Уворот (0 витрат HP)">${m.effective_dodge}%</span>
                            </div>
                            <div class="text-[10px] text-gray-400">${m.hp_cost_per_hit} HP / удар</div>
                        </td>

                        <!-- Ударів на добу -->
                        <td class="p-3 whitespace-nowrap">
                            <div class="font-extrabold text-white text-xs">${m.hits_per_day_max} <span class="text-[10px] font-normal text-gray-400">уд.</span></div>
                            <div class="text-[10px] text-gray-400">${m.hits_per_day_natural} без їжі</div>
                        </td>

                        <!-- Очікуваний дамаг -->
                        <td class="p-3 whitespace-nowrap text-right">
                            <div class="font-black text-rose-400 text-sm">~${dmgMaxM}</div>
                            <div class="text-[10px] text-gray-400">мін: ${dmgMinM}</div>
                        </td>

                        <!-- Дамаг тижня -->
                        <td class="p-3 whitespace-nowrap text-right">
                            <div class="font-bold text-gray-200 text-xs">${formatMillions(m.weekly_damage)}</div>
                            <div class="text-[10px] text-gray-400">всього: ${formatMillions(m.total_damage)}</div>
                        </td>

                        <!-- Онлайн -->
                        <td class="p-3 whitespace-nowrap">
                            <div class="flex items-center gap-1.5">
                                <span class="w-2 h-2 rounded-full ${onlineDot} shrink-0"></span>
                                <span class="text-xs ${m.is_afk ? 'text-rose-400 font-semibold' : 'text-gray-300'}">${m.last_seen_label}</span>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function copyDiscordReport() {
            if (!clanData) return;
            const mu = clanData.mu;
            const s = clanData.summary;

            const minM = (s.clan_daily_salvo_min / 1000000).toFixed(1);
            const maxM = (s.clan_daily_salvo_max / 1000000).toFixed(1);

            let text = `⚔️ **WarEra Clan Intel Report — ${mu.name}**\n`;
            text += `👥 Склад: ${s.total_members} (⚔️ Вар: ${s.war_count} | 🚜 Еко: ${s.eco_count} | ⚖️ Гібрид: ${s.hybrid_count})\n`;
            text += `💊 Бойова готовність: ${s.pill_active_count} під таблеткою | ${s.pill_ready_count} готові пити | ${s.pill_cooldown_count} на відкаті\n`;
            text += `💥 **Очікуваний щоденний залп клану (фіол-сет + таблетка): ~${minM}M – ${maxM}M дамагу**\n\n`;
            
            text += `📋 **Топ бійців за очікуваним дамагом сьогодні:**\n`;
            const warMembers = clanData.members.filter(m => m.build_type !== 'ECO').slice(0, 10);
            warMembers.forEach((m, idx) => {
                const maxDmg = formatMillions(m.theoretical_daily_dmg_max);
                text += `${idx + 1}. **${m.username}** (Lv.${m.level}) — ${m.pill_label} | ~${maxDmg} дамагу (${m.last_seen_label})\n`;
            });

            if (s.afk_count > 0) {
                text += `\n⚠️ **Інактив (>24 год):**\n`;
                clanData.members.filter(m => m.is_afk).forEach(m => {
                    text += `• ${m.username} (офлайн ${m.last_seen_label})\n`;
                });
            }

            navigator.clipboard.writeText(text).then(() => {
                showToast('Бойовий звіт скопійовано! Вставте у чат Telegram/Discord.');
            }).catch(() => {
                showToast('Не вдалося скопіювати звіт', false);
            });
        }

        // Auto load on start
        window.addEventListener('DOMContentLoaded', () => {
            loadClanData(false);
        });
    </script>
</body>
</html>
"""

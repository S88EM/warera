        // State
        let currentStatus = {};
        let rawDeals = [];
        let selectedRarity = 'all';
        let isPaused = false;
        let isPolling = true;

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

        // Periodic Refresh (every 3.5 seconds, paused when tab is inactive)
        setInterval(() => {
            if (isPolling && document.visibilityState === 'visible') {
                fetchStatus();
                fetchDeals();
            }
        }, 3500);

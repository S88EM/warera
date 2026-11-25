        // In-game Item Icons (Case, Elite Case, Scrap)
        const ICON_CASE_REGULAR = "data:image/png;base64,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";
        const ICON_CASE_ELITE = "data:image/png;base64,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";
        const ICON_SCRAP = "data:image/png;base64,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";

        let clanData = null;
        const _initParams = new URLSearchParams(window.location.search);
        let currentFilter = _initParams.get('filter') || 'ALL';
        let sortField = _initParams.get('sort') || 'damage_fish';
        let sortAsc = _initParams.get('dir') === 'asc';
        let currentViewMode = _initParams.get('view') || localStorage.getItem('warera_clan_view') || (window.innerWidth < 768 ? 'cards' : 'table');
        let customBattleBonus = parseFloat(_initParams.get('buff') || localStorage.getItem('warera_battle_bonus') || '84');
        if (isNaN(customBattleBonus)) customBattleBonus = 84;

        let selectedMembers = new Set();
        let lastFetchTimestamp = 0;
        let previousPillStatuses = {};
        let recentlyChangedUsers = new Set();

        function syncStateToUrl() {
            try {
                const url = new URL(window.location.href);
                url.searchParams.set('buff', String(customBattleBonus));
                if (currentFilter && currentFilter !== 'ALL') url.searchParams.set('filter', currentFilter);
                else url.searchParams.delete('filter');
                if (sortField && sortField !== 'damage_fish') url.searchParams.set('sort', sortField);
                else url.searchParams.delete('sort');
                if (sortAsc) url.searchParams.set('dir', 'asc');
                else url.searchParams.delete('dir');
                if (currentViewMode) url.searchParams.set('view', currentViewMode);
                window.history.replaceState({}, '', url.toString());
            } catch (e) { /* ignore */ }
        }

        function updateFreshnessTimer() {
            const el = document.getElementById('liveFreshnessText');
            if (!el) return;
            if (!lastFetchTimestamp) {
                el.innerText = 'Оновлення...';
                return;
            }
            const sec = Math.max(0, Math.floor((Date.now() - lastFetchTimestamp) / 1000));
            if (sec < 60) el.innerText = `оновлено ${sec}с тому`;
            else el.innerText = `оновлено ${Math.floor(sec / 60)}хв тому`;
        }
        setInterval(updateFreshnessTimer, 1000);

        function updateTopBonusButtonsUI() {
            [50, 65, 84, 100].forEach(val => {
                const btn = document.getElementById(`topBonusBtn_${val}`);
                if (!btn) return;
                if (Math.abs(customBattleBonus - val) < 0.01) {
                    btn.className = 'px-2 py-1 rounded-md bg-amber-600/30 border border-amber-500 text-[11px] font-mono text-amber-300 font-bold transition';
                } else {
                    btn.className = 'px-2 py-1 rounded-md bg-gray-800 hover:bg-gray-700 border border-bordercolor text-[11px] font-mono text-gray-300 transition';
                }
            });
        }

        function updateClanSalvoStats() {
            if (!clanData || !clanData.members) return;
            const s = clanData.summary;

            // Realistic Available Salvo until 02:00:
            // - ACTIVE: actual in-hands + remaining regen until current pill ends
            // - READY: full 8h pill salvo
            // - COOLDOWN: full pill salvo ONLY if debuff expires before 02:00 (evening session); if after 02:00, 0
            const dynamicClanSalvo = clanData.members.reduce((acc, m) => {
                if (m.build_type === 'ECO') return acc;
                if (m.pill_status === 'ACTIVE') {
                    return acc + getCustomInstantFishSalvo(m) + getCustomRegenFishSalvo(m);
                }
                if (m.pill_status === 'READY') {
                    return acc + getCustomFishSalvo(m);
                }
                if (m.pill_status === 'COOLDOWN') {
                    return acc + (m.can_drink_before_reset ? getCustomFishSalvo(m) : 0);
                }
                return acc;
            }, 0);
            const elSalvo = document.getElementById('statClanSalvo');
            if (elSalvo) elSalvo.innerText = `~${formatMillions(dynamicClanSalvo || s.clan_pill_available_salvo || 0)}`;

            const dynamicInstantSalvo = clanData.members.reduce((acc, m) => acc + (m.pill_status === 'ACTIVE' ? getCustomInstantFishSalvo(m) : 0), 0);
            const elInstant = document.getElementById('statInstantSalvo');
            if (elInstant) elInstant.innerText = `~${formatMillions(dynamicInstantSalvo || s.clan_pill_instant_fish_salvo || s.clan_pill_instant_salvo || 0)}`;

            const dynamicRegenSalvo = clanData.members.reduce((acc, m) => acc + (m.pill_status === 'ACTIVE' ? getCustomRegenFishSalvo(m) : 0), 0);
            const elRegen = document.getElementById('statRegenSalvo');
            if (elRegen) elRegen.innerText = `~${formatMillions(dynamicRegenSalvo || s.clan_pill_regen_fish_salvo || s.clan_pill_regen_salvo || 0)}`;

            const readyMembers = clanData.members.filter(m => m.pill_status === 'READY');
            const readyCount = readyMembers.length;
            const dynamicReadySalvo = readyMembers.reduce((acc, m) => acc + getCustomFishSalvo(m), 0);
            const elReady = document.getElementById('statReadySalvo');
            if (elReady) elReady.innerText = `~${formatMillions(dynamicReadySalvo || s.clan_pill_ready_salvo || 0)}`;
            const elReadyCount = document.getElementById('statReadyCount');
            if (elReadyCount) elReadyCount.innerText = readyCount;
        }

        function updateCustomBattleBonus(val) {
            const num = parseFloat(val);
            customBattleBonus = isNaN(num) ? 0 : Math.max(0, num);
            localStorage.setItem('warera_battle_bonus', customBattleBonus.toString());
            updateTopBonusButtonsUI();
            syncStateToUrl();
            updateClanSalvoStats();
            renderMembersTable();
            updateSalvoPlannerBar();
        }

        function setBattleBonus(val) {
            const bInput = document.getElementById('battleBonusInput');
            if (bInput) bInput.value = val;
            updateCustomBattleBonus(val);
        }

        function getCustomFishSalvo(m) {
            const unbuffedHit = m.unbuffed_hit_dmg || (m.avg_dmg_per_hit ? Math.round(m.avg_dmg_per_hit / 1.50) : 0);
            const customMult = 1.0 + (customBattleBonus / 100.0);
            return Math.round((m.pill_fish_hits || 0) * unbuffedHit * customMult);
        }

        function getCustomSteakSalvo(m) {
            const unbuffedHit = m.unbuffed_hit_dmg || (m.avg_dmg_per_hit ? Math.round(m.avg_dmg_per_hit / 1.50) : 0);
            const customMult = 1.0 + (customBattleBonus / 100.0);
            return Math.round((m.pill_full_hits || 0) * unbuffedHit * customMult);
        }

        function getCustomInstantFishSalvo(m) {
            const unbuffedHit = m.unbuffed_hit_dmg || (m.avg_dmg_per_hit ? Math.round(m.avg_dmg_per_hit / 1.50) : 0);
            const customMult = 1.0 + (customBattleBonus / 100.0);
            return Math.round((m.pill_instant_fish_hits || m.pill_instant_hits || 0) * unbuffedHit * customMult);
        }

        function getCustomRegenFishSalvo(m) {
            const unbuffedHit = m.unbuffed_hit_dmg || (m.avg_dmg_per_hit ? Math.round(m.avg_dmg_per_hit / 1.50) : 0);
            const customMult = 1.0 + (customBattleBonus / 100.0);
            return Math.round((m.pill_regen_fish_hits || m.pill_regen_hits || 0) * unbuffedHit * customMult);
        }

        async function loadClanData(isManual = false) {
            const icon = document.getElementById('refreshIcon');
            if (icon) icon.classList.add('fa-spin');

            try {
                const urlParams = new URLSearchParams(window.location.search);
                const muParam = urlParams.get('mu') || '';
                const basePath = window.location.pathname.replace(/\/(clan(\.html)?|\index\.html)?\/?$/, '');
                const cleanEndpoint = `api/clan${muParam ? `?mu=${encodeURIComponent(muParam)}` : ''}`;
                const apiUrl = basePath ? `${basePath}/${cleanEndpoint}` : `/${cleanEndpoint}`;

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

                // Detect pill status changes since previous fetch
                const nextChanged = new Set();
                if (Object.keys(previousPillStatuses).length > 0 && Array.isArray(data.members)) {
                    data.members.forEach(m => {
                        const prev = previousPillStatuses[m.username];
                        if (prev && prev !== m.pill_status) {
                            nextChanged.add(m.username);
                        }
                    });
                }
                if (Array.isArray(data.members)) {
                    const nextMap = {};
                    data.members.forEach(m => { nextMap[m.username] = m.pill_status; });
                    previousPillStatuses = nextMap;
                }
                recentlyChangedUsers = nextChanged;
                lastFetchTimestamp = Date.now();
                updateFreshnessTimer();

                clanData = data;
                const bInput = document.getElementById('battleBonusInput');
                if (bInput) bInput.value = customBattleBonus;
                updateTopBonusButtonsUI();
                renderClanHeader();
                setFilter(currentFilter);
                if (isManual) showToast('Дані клану оновлено!');
            } catch (err) {
                console.error('Failed to load clan data:', err);
                showToast(`Помилка: ${err.message}`, false);
            } finally {
                if (icon) icon.classList.remove('fa-spin');
            }
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
            document.getElementById('clanUpgrades').innerHTML = `<i class="fa-solid fa-landmark text-gray-400 mr-1"></i>Штаб: ${mu.headquarters_level} рів. · Казарми: ${mu.dormitories_level} рів.`;
            document.getElementById('clanWealth').innerHTML = `<i class="fa-solid fa-coins text-yellow-400/90 mr-1"></i>Казна: ${formatNumber(Math.round(mu.wealth))} Coins`;

            // Salvo Highlight (Calculated with active custom battle bonus)
            updateClanSalvoStats();

            const todayClanM = formatMillions(s.clan_today_damage || 0);
            document.getElementById('statClanToday').innerText = `+${todayClanM}`;
            if (s.clan_yesterday_damage !== null && s.clan_yesterday_damage !== undefined) {
                document.getElementById('statClanYesterday').innerText = formatMillions(s.clan_yesterday_damage);
            } else {
                document.getElementById('statClanYesterday').innerText = 'з 02:00';
            }

            // KPI Cards
            document.getElementById('statWarCount').innerText = s.war_count;
            document.getElementById('statWarSub').innerText = `${Math.round((s.war_count / s.total_members) * 100)}% складу клану (≥70% вар)`;

            document.getElementById('statPillActive').innerText = `${s.pill_active_count} бійців`;
            document.getElementById('statPillSub').innerText = `${s.pill_ready_count} можуть пити таблетку`;

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

        function toggleKpiFilter(f) {
            setFilter(currentFilter === f ? 'ALL' : f);
        }

        function setFilter(f) {
            currentFilter = f || 'ALL';
            ['ALL', 'WAR', 'PILL_ACTIVE', 'PILL_READY', 'PILL_COOLDOWN', 'HYBRID', 'ECO', 'AFK'].forEach(id => {
                const el = document.getElementById(`filter${id}`);
                if (!el) return;
                if (id === currentFilter) {
                    el.className = 'tab-btn px-2.5 py-1 rounded-md active transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 shadow';
                } else {
                    el.className = 'tab-btn px-2.5 py-1 rounded-md bg-gray-800/80 text-gray-300 hover:bg-gray-700 transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5';
                }
            });
            ['WAR', 'PILL_ACTIVE', 'ECO', 'AFK'].forEach(id => {
                const card = document.getElementById(`kpiCard${id}`);
                if (!card) return;
                if (id === currentFilter) {
                    card.classList.add('ring-1', 'ring-blue-500', 'border-blue-500/70');
                } else {
                    card.classList.remove('ring-1', 'ring-blue-500', 'border-blue-500/70');
                }
            });
            syncStateToUrl();
            renderMembersTable();
        }

        function sortRoster(field) {
            if (sortField === field) {
                sortAsc = !sortAsc;
            } else {
                sortField = field;
                sortAsc = (field === 'name' || field === 'role');
            }
            updateSortControls();
            syncStateToUrl();
            renderMembersTable();
        }

        function changeSort(field) {
            sortField = field;
            sortAsc = (field === 'name' || field === 'role');
            updateSortControls();
            syncStateToUrl();
            renderMembersTable();
        }

        function toggleSortOrder() {
            sortAsc = !sortAsc;
            updateSortControls();
            syncStateToUrl();
            renderMembersTable();
        }

        function updateSortControls() {
            const icon = document.getElementById('sortOrderIcon');
            if (icon) {
                icon.className = sortAsc ? 'fa-solid fa-arrow-up-short-wide text-xs' : 'fa-solid fa-arrow-down-wide-short text-xs';
            }
            const select = document.getElementById('sortSelect');
            if (select && select.value !== sortField) {
                select.value = sortField;
            }
        }

        function setViewMode(mode) {
            currentViewMode = mode;
            localStorage.setItem('warera_clan_view', mode);
            syncStateToUrl();
            updateViewModeUI();
        }

        function updateViewModeUI() {
            const tableSec = document.getElementById('clanTableSection');
            const cardsSec = document.getElementById('clanCardsSection');
            const cardsBtn = document.getElementById('viewCardsBtn');
            const tableBtn = document.getElementById('viewTableBtn');

            const effectiveMode = (window.innerWidth < 768) ? 'cards' : currentViewMode;
            if (tableSec && cardsSec) {
                if (effectiveMode === 'cards') {
                    tableSec.classList.add('hidden');
                    cardsSec.classList.remove('hidden');
                } else {
                    tableSec.classList.remove('hidden');
                    cardsSec.classList.add('hidden');
                }
            }

            if (cardsBtn && tableBtn) {
                if (effectiveMode === 'cards') {
                    cardsBtn.className = 'view-btn px-2 py-1 rounded-md transition-colors flex items-center gap-1 active text-white shadow-sm';
                    tableBtn.className = 'view-btn px-2 py-1 rounded-md transition-colors flex items-center gap-1 text-gray-400 hover:text-white';
                } else {
                    tableBtn.className = 'view-btn px-2 py-1 rounded-md transition-colors flex items-center gap-1 active text-white shadow-sm';
                    cardsBtn.className = 'view-btn px-2 py-1 rounded-md transition-colors flex items-center gap-1 text-gray-400 hover:text-white';
                }
            }
        }
        window.addEventListener('resize', updateViewModeUI);

        function renderSparkline7d(history7d, targetDmg) {
            const vals = Array.isArray(history7d) && history7d.length === 7 ? history7d : [0, 0, 0, 0, 0, 0, 0];
            const maxVal = Math.max(1, ...vals, targetDmg || 0);
            const bars = vals.map((v, idx) => {
                const h = v > 0 ? Math.max(3, Math.round((v / maxVal) * 16)) : 2;
                const y = 18 - h;
                const x = idx * 8 + 1;
                let fill = '#334155';
                if (v > 0) {
                    fill = (targetDmg && v >= targetDmg) ? '#10b981' : '#38bdf8';
                }
                return `<rect x="${x}" y="${y}" width="5" height="${h}" rx="1" fill="${fill}"><title>День ${idx + 1}: ${formatMillions(v)}</title></rect>`;
            }).join('');
            return `<svg width="56" height="18" viewBox="0 0 56 18" class="inline-block align-middle opacity-90" aria-label="7-денна активність">${bars}</svg>`;
        }

        function toggleMemberSelection(username, checked) {
            if (checked) selectedMembers.add(username);
            else selectedMembers.delete(username);
            updateSalvoPlannerBar();
        }

        function toggleSelectAll(checked) {
            if (!clanData || !clanData.members) return;
            const visible = getFilteredAndSortedMembers();
            visible.forEach(m => {
                if (checked) selectedMembers.add(m.username);
                else selectedMembers.delete(m.username);
            });
            renderMembersTable();
            updateSalvoPlannerBar();
        }

        function clearSelectedMembers() {
            selectedMembers.clear();
            const allCb = document.getElementById('selectAllCheckbox');
            if (allCb) allCb.checked = false;
            renderMembersTable();
            updateSalvoPlannerBar();
        }

        function updateSalvoPlannerBar() {
            const bar = document.getElementById('salvoPlannerBar');
            if (!bar) return;
            if (!clanData || selectedMembers.size === 0) {
                bar.classList.add('hidden');
                return;
            }
            const picked = clanData.members.filter(m => selectedMembers.has(m.username));
            const totalFish = picked.reduce((acc, m) => acc + (m.build_type === 'ECO' ? 0 : getCustomFishSalvo(m)), 0);
            const totalInstant = picked.reduce((acc, m) => acc + (m.pill_status === 'ACTIVE' ? getCustomInstantFishSalvo(m) : 0), 0);

            document.getElementById('salvoSelectedCount').innerText = picked.length;
            document.getElementById('salvoSelectedFish').innerText = `~${formatMillions(totalFish)}`;
            document.getElementById('salvoSelectedInstant').innerText = `~${formatMillions(totalInstant)}`;
            bar.classList.remove('hidden');
        }

        function copySelectedSalvoPing() {
            if (!clanData || selectedMembers.size === 0) return;
            const picked = clanData.members.filter(m => selectedMembers.has(m.username));
            const totalFish = picked.reduce((acc, m) => acc + (m.build_type === 'ECO' ? 0 : getCustomFishSalvo(m)), 0);
            const totalInstant = picked.reduce((acc, m) => acc + (m.pill_status === 'ACTIVE' ? getCustomInstantFishSalvo(m) : 0), 0);
            const pings = picked.map(m => `@${m.username}`).join(' ');
            const msg = `⚔️ **Залп під баф +${customBattleBonus}%** (${picked.length} бійців)\n💥 Повний залп 8г (риба): **~${formatMillions(totalFish)}** · В руках: **~${formatMillions(totalInstant)}**\n${pings}`;
            navigator.clipboard.writeText(msg).then(() => {
                showToast(`Скопійовано пінг для ${picked.length} бійців!`);
            }).catch(() => {
                showToast('Не вдалося скопіювати в буфер обміну', false);
            });
        }

        function renderTableRow(m) {
            const fishSalvo = getCustomFishSalvo(m);
            const steakSalvo = getCustomSteakSalvo(m);
            const isSelected = selectedMembers.has(m.username);
            const isRecentlyChanged = recentlyChangedUsers.has(m.username);

            let onlineDot = 'bg-emerald-400';
            if (m.hours_offline >= 24) onlineDot = 'bg-rose-500';
            else if (m.hours_offline >= 3) onlineDot = 'bg-amber-400';

            let pillBadgeClass = 'bg-gray-800 text-gray-400 border-gray-700';
            if (m.pill_status === 'ACTIVE') pillBadgeClass = 'bg-purple-950/80 text-purple-300 border-purple-700/60 font-semibold';
            else if (m.pill_status === 'READY') pillBadgeClass = 'bg-blue-950/80 text-blue-300 border-blue-700/60 font-semibold';
            else if (m.pill_status === 'COOLDOWN') pillBadgeClass = 'bg-rose-950/80 text-rose-300 border-rose-700/60 font-semibold';

            let buildBadgeClass = 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50';
            if (m.build_type === 'ECO') buildBadgeClass = 'bg-amber-950/60 text-amber-300 border-amber-700/50';
            else if (m.build_type === 'HYBRID') buildBadgeClass = 'bg-sky-950/60 text-sky-300 border-sky-700/50';

            let roleColor = 'text-gray-400';
            if (m.clan_role === 'LEADER') roleColor = 'text-yellow-400 font-bold';
            if (m.clan_role === 'COMMANDER') roleColor = 'text-rose-400 font-semibold';
            if (m.clan_role === 'MANAGER') roleColor = 'text-purple-400 font-semibold';

            const pillPct = m.pill_status === 'ACTIVE' ? Math.max(0, Math.min(100, Math.round(((m.pill_remaining_hours || 0) / 8.0) * 100))) : 0;
            const rowHighlight = isRecentlyChanged ? 'bg-amber-950/15 ring-1 ring-inset ring-amber-400/50' : '';

            return `
                <tr class="hover:bg-hoverbg/50 transition-colors group ${rowHighlight}">
                    <!-- Checkbox -->
                    <td class="p-3 text-center">
                        <input type="checkbox" ${isSelected ? 'checked' : ''} data-user="${encodeURIComponent(m.username)}" onchange="toggleMemberSelection(decodeURIComponent(this.dataset.user), this.checked)" class="rounded border-gray-600 bg-darkbg text-blue-500 focus:ring-0 cursor-pointer">
                    </td>

                    <!-- Боєць · Роль · Онлайн (Sticky column) -->
                    <td class="p-3 whitespace-nowrap sticky left-0 bg-[#111622] group-hover:bg-[#1a2234] z-10 border-r border-bordercolor/60 shadow-[2px_0_5px_rgba(0,0,0,0.4)]">
                        <div class="flex items-center gap-2.5">
                            <div class="relative shrink-0">
                                <div class="w-8 h-8 rounded-lg bg-gray-800 border border-gray-700 overflow-hidden flex items-center justify-center">
                                    ${m.avatar_url ? `<img src="${m.avatar_url}" class="w-full h-full object-cover">` : `<span class="text-xs font-bold text-gray-300">${m.username.charAt(0)}</span>`}
                                </div>
                                <span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ${onlineDot} border-2 border-[#111622]" title="${m.last_seen_label}"></span>
                            </div>
                            <div>
                                <div class="font-bold text-white text-xs flex items-center gap-1.5">
                                    <span>${m.username}</span>
                                    <span class="text-[10px] px-1 rounded bg-gray-800 text-yellow-400 border border-bordercolor font-mono">Lv.${m.level}</span>
                                    <button data-user="${encodeURIComponent(m.username)}" onclick="event.stopPropagation(); openTargetCalculator(decodeURIComponent(this.dataset.user))" class="px-1.5 py-0.5 rounded-md bg-blue-500/20 hover:bg-blue-500/40 border border-blue-500/40 text-blue-300 hover:text-white text-[10px] font-bold transition-all ml-0.5 flex items-center gap-1" title="Калькулятор спорядження">
                                        <i class="fa-solid fa-crosshairs text-[9px]"></i>
                                        <span class="hidden xl:inline">Ціль</span>
                                    </button>
                                </div>
                                <div class="text-[10px] text-gray-400 flex items-center gap-1.5 mt-0.5">
                                    <span class="${roleColor}">${m.role_label}</span>
                                    <span>·</span>
                                    <span>Ранг ${m.military_rank}</span>
                                    ${m.prestige ? `<span class="text-[9px] px-1 rounded bg-purple-950/80 text-purple-300 border border-purple-700/50 font-mono">P${m.prestige}</span>` : ''}
                                    <span>·</span>
                                    <span class="${m.is_afk ? 'text-rose-400 font-semibold' : 'text-gray-400'}">${m.last_seen_label}</span>
                                </div>
                            </div>
                        </div>
                    </td>

                    <!-- Білд · 7д тренд -->
                    <td class="p-3 whitespace-nowrap">
                        <div class="flex flex-col gap-1">
                            <span class="px-2 py-0.5 rounded text-[11px] font-medium border w-fit ${buildBadgeClass}">
                                ${m.build_label}
                            </span>
                            <div class="flex items-center gap-1.5">
                                ${renderSparkline7d(m.history_7d, m.target_damage)}
                                <span class="text-[9px] text-gray-500 font-mono">7д</span>
                            </div>
                        </div>
                    </td>

                    <!-- Таблетка (Cocaine) -->
                    <td class="p-3 whitespace-nowrap">
                        <div class="flex items-center gap-1.5">
                            <span class="px-2 py-0.5 rounded text-[11px] border ${pillBadgeClass}" title="${m.pill_tip}">
                                ${m.pill_label}
                            </span>
                            ${isRecentlyChanged ? '<span class="text-[9px] px-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold">Нове</span>' : ''}
                        </div>
                        ${m.build_type === 'ECO' ? `
                            <div class="text-[10px] text-gray-500 mt-1">економічний білд</div>
                        ` : `
                            <div class="text-[10px] text-gray-300 font-medium flex items-center gap-1 mt-1">
                                <i class="fa-regular fa-clock text-[9px] text-gray-400"></i>
                                <span title="${m.pill_remaining_tip || m.pill_time_label}">${m.pill_time_label}</span>
                                ${m.pill_status === 'COOLDOWN' && !m.can_drink_before_reset ? `
                                    <span class="text-[9px] px-1 rounded bg-rose-950 text-rose-300 border border-rose-800/60 font-mono">після 02:00</span>
                                ` : (m.pill_status === 'COOLDOWN' && m.can_drink_before_reset ? `
                                    <span class="text-[9px] px-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/60 font-mono">до 02:00</span>
                                ` : '')}
                            </div>
                            ${m.pill_status === 'ACTIVE' ? `
                                <div class="w-28 bg-gray-800 rounded-full h-1 mt-1 overflow-hidden">
                                    <div class="bg-purple-400 h-1 rounded-full" style="width: ${pillPct}%"></div>
                                </div>
                                <div class="text-[10px] font-bold mt-0.5">
                                    ${(m.pill_remaining_hours <= 0.2) ? `
                                        <span class="text-amber-400 font-extrabold">Баф закінчується</span>
                                    ` : `
                                        <span class="text-rose-400 font-bold" title="В руках прямо зараз"><i class="fa-solid fa-fire text-[9px] mr-0.5"></i>~${formatMillions(getCustomInstantFishSalvo(m))}</span>
                                        <span class="text-gray-500 font-normal">|</span>
                                        <span class="text-amber-400 font-medium" title="Дозріє регеном"><i class="fa-regular fa-hourglass-half text-[9px] mr-0.5"></i>~${formatMillions(getCustomRegenFishSalvo(m))}</span>
                                    `}
                                </div>
                            ` : ''}
                        `}
                    </td>

                    <!-- Урон (Сьогодні / Вчора) -->
                    <td class="p-3 whitespace-nowrap text-right">
                        <div class="font-bold text-xs ${m.today_damage > 0 ? 'text-emerald-400 font-extrabold' : 'text-gray-400'}" title="Сьогодні: ${formatNumber(m.today_damage)}">
                            ${m.today_damage > 0 ? `+${formatMillions(m.today_damage)}` : '0'}
                        </div>
                        <div class="text-[10px] text-gray-400 font-mono" title="${m.has_yesterday ? `Вчора: ${formatNumber(m.yesterday_damage)}` : 'Очікує знімку'}">
                            вчора: ${m.has_yesterday ? formatMillions(m.yesterday_damage) : '—'}
                        </div>
                        ${m.target_damage ? `
                            <div data-user="${encodeURIComponent(m.username)}" class="mt-1.5 flex flex-col items-end cursor-pointer group/tg p-1 -mr-1 rounded-lg hover:bg-blue-500/10 transition-all" onclick="event.stopPropagation(); openTargetCalculator(decodeURIComponent(this.dataset.user))" title="Змінити ціль">
                                <div class="flex items-center gap-1 mb-0.5 text-[10px] font-mono">
                                    <span class="text-emerald-400 font-bold">${formatMillions(m.target_damage)}</span>
                                    <span class="text-gray-400">(${m.target_progress_pct}%)</span>
                                </div>
                                <div class="w-24 bg-gray-700/60 rounded-full h-1.5 overflow-hidden">
                                    <div class="bg-gradient-to-r from-emerald-500 to-teal-400 h-1.5 rounded-full" style="width: ${Math.min(100, m.target_progress_pct)}%"></div>
                                </div>
                                ${m.saved_strategy_label ? `
                                    <div class="mt-0.5 flex items-center gap-1 text-[9px] text-purple-300 font-mono">
                                        <i class="fa-solid fa-lock text-[8px] text-purple-400"></i>
                                        <span class="truncate max-w-[110px]">${m.saved_strategy_label.replace(/^[🔥🛡️🗡️🔫🎯\s]+/, '')}</span>
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}
                    </td>

                    <!-- Залп 8г · Тиждень -->
                    <td class="p-3 whitespace-nowrap text-right">
                        ${m.build_type === 'ECO' ? `
                            <div class="text-gray-500 font-mono text-xs">—</div>
                            <div class="text-[10px] text-gray-500">тиждень: ${formatMillions(m.weekly_damage)}</div>
                        ` : `
                            <div class="flex flex-col items-end font-mono">
                                <div class="text-xs sm:text-sm font-bold text-sky-400" title="Залп на смаженій рибі (+${customBattleBonus}%)">
                                    ~${formatMillions(fishSalvo)}
                                </div>
                                <div class="text-[10px] text-rose-300/80 font-semibold" title="Залп на стейках (+${customBattleBonus}%)">
                                    стейк: ~${formatMillions(steakSalvo)}
                                </div>
                                <div class="text-[10px] text-gray-400 mt-0.5" title="Усього: ${formatMillions(m.total_damage)}">
                                    тиж: ${formatMillions(m.weekly_damage)}
                                </div>
                            </div>
                        `}
                    </td>
                </tr>
            `;
        }

        function renderMemberCard(m) {
            const fishSalvo = getCustomFishSalvo(m);
            const steakSalvo = getCustomSteakSalvo(m);
            const isSelected = selectedMembers.has(m.username);
            const isRecentlyChanged = recentlyChangedUsers.has(m.username);

            let onlineDot = 'bg-emerald-400';
            if (m.hours_offline >= 24) onlineDot = 'bg-rose-500';
            else if (m.hours_offline >= 3) onlineDot = 'bg-amber-400';

            let pillBadgeClass = 'bg-gray-800 text-gray-400 border-gray-700';
            if (m.pill_status === 'ACTIVE') pillBadgeClass = 'bg-purple-950/80 text-purple-300 border-purple-700/60 font-semibold';
            else if (m.pill_status === 'READY') pillBadgeClass = 'bg-blue-950/80 text-blue-300 border-blue-700/60 font-semibold';
            else if (m.pill_status === 'COOLDOWN') pillBadgeClass = 'bg-rose-950/80 text-rose-300 border-rose-700/60 font-semibold';

            return `
                <div class="glass-panel rounded-2xl border ${isRecentlyChanged ? 'border-amber-400/60 bg-amber-950/15' : 'border-bordercolor/80'} p-3 shadow-lg flex flex-col gap-2.5">
                    <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center gap-2.5 min-w-0">
                            <input type="checkbox" ${isSelected ? 'checked' : ''} data-user="${encodeURIComponent(m.username)}" onchange="toggleMemberSelection(decodeURIComponent(this.dataset.user), this.checked)" class="rounded border-gray-600 bg-darkbg text-blue-500 focus:ring-0 cursor-pointer shrink-0">
                            <div class="relative shrink-0">
                                <div class="w-9 h-9 rounded-xl bg-gray-800 border border-gray-700 overflow-hidden flex items-center justify-center">
                                    ${m.avatar_url ? `<img src="${m.avatar_url}" class="w-full h-full object-cover">` : `<span class="text-xs font-bold text-gray-300">${m.username.charAt(0)}</span>`}
                                </div>
                                <span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ${onlineDot} border-2 border-cardbg"></span>
                            </div>
                            <div class="min-w-0">
                                <div class="flex items-center gap-1.5">
                                    <span class="font-extrabold text-white text-sm truncate">${m.username}</span>
                                    <span class="text-[10px] px-1 rounded bg-gray-800 text-yellow-400 border border-bordercolor font-mono">Lv.${m.level}</span>
                                </div>
                                <div class="text-[10px] text-gray-400 truncate">${m.role_label} · ${m.build_label} · ${m.last_seen_label}</div>
                            </div>
                        </div>
                        <button data-user="${encodeURIComponent(m.username)}" onclick="event.stopPropagation(); openTargetCalculator(decodeURIComponent(this.dataset.user))" class="px-2.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 border border-blue-500/40 text-blue-300 text-xs font-bold shrink-0 flex items-center gap-1">
                            <i class="fa-solid fa-crosshairs text-[10px]"></i> Ціль
                        </button>
                    </div>

                    <!-- 3 Key Combat Fields: Pill Status, Salvo 8h, Today / 7d -->
                    <div class="grid grid-cols-3 gap-2 bg-darkbg/80 rounded-xl p-2 border border-bordercolor/60 text-center">
                        <div>
                            <div class="text-[9px] uppercase font-bold text-gray-400 mb-0.5">Таблетка</div>
                            <span class="px-1.5 py-0.5 rounded text-[10px] border inline-block ${pillBadgeClass}">${m.pill_label}</span>
                            <div class="text-[9px] text-gray-400 mt-0.5">${m.pill_time_label || '—'}</div>
                        </div>
                        <div class="border-x border-bordercolor/40 px-1">
                            <div class="text-[9px] uppercase font-bold text-gray-400 mb-0.5">Залп (8 год)</div>
                            ${m.build_type === 'ECO'
                                ? `<div class="text-xs font-bold font-mono text-gray-500">—</div>`
                                : `
                                    <div class="text-xs font-bold font-mono text-sky-400">🐟 ~${formatMillions(fishSalvo)}</div>
                                    <div class="text-[10px] font-mono text-rose-300/80">🥩 ~${formatMillions(steakSalvo)}</div>
                                    ${m.pill_status === 'ACTIVE' ? `<div class="text-[9px] font-mono text-purple-300">в руках ~${formatMillions(getCustomInstantFishSalvo(m))}</div>` : ''}
                                `
                            }
                        </div>
                        <div>
                            <div class="text-[9px] uppercase font-bold text-gray-400 mb-0.5">Сьогодні / Вчора</div>
                            <div class="text-xs font-bold text-emerald-400 font-mono">${m.today_damage > 0 ? `+${formatMillions(m.today_damage)}` : '0'}</div>
                            <div class="text-[9px] text-gray-400 font-mono">Вчора: ${m.has_yesterday ? formatMillions(m.yesterday_damage) : '—'}</div>
                            <div class="mt-0.5">${renderSparkline7d(m.history_7d, m.target_damage)}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        function getFilteredAndSortedMembers() {
            if (!clanData || !clanData.members) return [];
            let list = [...clanData.members];

            if (currentFilter === 'WAR') list = list.filter(m => m.build_type === 'WAR');
            else if (currentFilter === 'ECO') list = list.filter(m => m.build_type === 'ECO');
            else if (currentFilter === 'HYBRID') list = list.filter(m => m.build_type === 'HYBRID');
            else if (currentFilter === 'PILL_ACTIVE') list = list.filter(m => m.pill_status === 'ACTIVE');
            else if (currentFilter === 'PILL_READY') list = list.filter(m => m.pill_status === 'READY');
            else if (currentFilter === 'PILL_COOLDOWN') list = list.filter(m => m.pill_status === 'COOLDOWN');
            else if (currentFilter === 'AFK') list = list.filter(m => m.is_afk);

            const q = (document.getElementById('memberSearchInput').value || '').trim().toLowerCase();
            if (q) list = list.filter(m => m.username.toLowerCase().includes(q));

            list.sort((a, b) => {
                let vA, vB;
                if (sortField === 'name') { vA = a.username; vB = b.username; }
                else if (sortField === 'role') { vA = a.clan_role; vB = b.clan_role; }
                else if (sortField === 'build') { vA = a.war_ratio; vB = b.war_ratio; }
                else if (sortField === 'pill') { vA = a.pill_status; vB = b.pill_status; }
                else if (sortField === 'today') { vA = a.today_damage || 0; vB = b.today_damage || 0; }
                else if (sortField === 'yesterday') { vA = a.yesterday_damage || 0; vB = b.yesterday_damage || 0; }
                else if (sortField === 'weekly') { vA = a.weekly_damage; vB = b.weekly_damage; }
                else if (sortField === 'online') { vA = a.hours_offline; vB = b.hours_offline; }
                else if (sortField === 'damage_fish') { vA = getCustomFishSalvo(a); vB = getCustomFishSalvo(b); }
                else if (sortField === 'damage') { vA = getCustomSteakSalvo(a); vB = getCustomSteakSalvo(b); }
                else { vA = getCustomFishSalvo(a); vB = getCustomFishSalvo(b); }

                if (vA < vB) return sortAsc ? -1 : 1;
                if (vA > vB) return sortAsc ? 1 : -1;
                return 0;
            });
            return list;
        }

        function renderMembersTable() {
            const tbody = document.getElementById('clanTableBody');
            const cardsContainer = document.getElementById('clanCardsSection');
            if (!tbody || !clanData) return;

            const list = getFilteredAndSortedMembers();
            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-gray-400">Не знайдено бійців за вказаними критеріями</td></tr>`;
                if (cardsContainer) {
                    cardsContainer.innerHTML = `<div class="glass-panel p-8 rounded-2xl border border-bordercolor text-center text-gray-400">Не знайдено бійців за вказаними критеріями</div>`;
                }
                updateViewModeUI();
                updateSortControls();
                return;
            }

            tbody.innerHTML = list.map(m => renderTableRow(m)).join('');
            if (cardsContainer) {
                cardsContainer.innerHTML = list.map(m => renderMemberCard(m)).join('');
            }

            updateViewModeUI();
            updateSortControls();
            updateSalvoPlannerBar();
        }

        function copyDiscordReport() {
            if (!clanData) return;
            const mu = clanData.mu;
            const s = clanData.summary;

            const minM = (s.clan_daily_salvo_min / 1000000).toFixed(1);
            const maxM = (s.clan_daily_salvo_max / 1000000).toFixed(1);

            let text = `⚔️ **WarEra Clan Intel Report — ${mu.name}**\n`;
            text += `👥 Склад: ${s.total_members} (⚔️ Вар: ${s.war_count} | 🚜 Еко: ${s.eco_count} | ⚖️ Гібрид: ${s.hybrid_count})\n`;
            text += `💊 Бойова готовність: ${s.pill_active_count} під бафом (+60%) | ${s.pill_ready_count} готові пити | ${s.pill_cooldown_count} під дебафом\n`;
            const clanFishSalvo = clanData.members.reduce((acc, m) => {
                if (m.build_type === 'ECO') return acc;
                if (m.pill_status === 'ACTIVE') return acc + getCustomInstantFishSalvo(m) + getCustomRegenFishSalvo(m);
                if (m.pill_status === 'READY') return acc + getCustomFishSalvo(m);
                if (m.pill_status === 'COOLDOWN') return acc + (m.can_drink_before_reset ? getCustomFishSalvo(m) : 0);
                return acc;
            }, 0);
            text += `💥 **Залп клану до 02:00 (+${customBattleBonus}% баф): ~${formatMillions(clanFishSalvo)} урону**\n`;
            const dynamicInstantSalvo = clanData.members.reduce((acc, m) => acc + (m.pill_status === 'ACTIVE' ? getCustomInstantFishSalvo(m) : 0), 0);
            const dynamicRegenSalvo = clanData.members.reduce((acc, m) => acc + (m.pill_status === 'ACTIVE' ? getCustomRegenFishSalvo(m) : 0), 0);
            text += `🔥 **Залишок активних бійців (+${customBattleBonus}%):** В руках: ~${formatMillions(dynamicInstantSalvo)} | Реген: ~${formatMillions(dynamicRegenSalvo)}\n`;
            const readyMembers = clanData.members.filter(m => m.pill_status === 'READY');
            const dynamicReadySalvo = readyMembers.reduce((acc, m) => acc + getCustomFishSalvo(m), 0);
            text += `💊 **Можуть пити зараз (${readyMembers.length} бійців): ~${formatMillions(dynamicReadySalvo)} урону (+${customBattleBonus}%)\n`;
            const eveningMembers = clanData.members.filter(m => m.pill_status === 'COOLDOWN' && m.can_drink_before_reset);
            if (eveningMembers.length > 0) {
                const eveningSalvo = eveningMembers.reduce((acc, m) => acc + getCustomFishSalvo(m), 0);
                text += `⏳ **Зможуть пити ввечері до 02:00 (${eveningMembers.length} бійців): ~${formatMillions(eveningSalvo)} урону**\n`;
            }
            text += `⚡ **Реальний факт сьогодні (з 02:00): +${formatMillions(s.clan_today_damage || 0)} урону**\n`;
            if (s.clan_yesterday_damage) {
                text += `📅 **Факт за вчора: ${formatMillions(s.clan_yesterday_damage)} урону**\n`;
            }
            text += `\n`;
            
            text += `📋 **Топ бійців (Залп 🐟 Риба / 🥩 Стейк | Факт сьогодні):**\n`;
            const warMembers = clanData.members.filter(m => m.build_type !== 'ECO').slice(0, 10);
            warMembers.forEach((m, idx) => {
                const fishDmg = formatMillions(getCustomFishSalvo(m));
                const steakDmg = formatMillions(getCustomSteakSalvo(m));
                const todayDmg = m.today_damage > 0 ? `+${formatMillions(m.today_damage)}` : '0';
                text += `${idx + 1}. **${m.username}** — 🐟 ~${fishDmg} / 🥩 ~${steakDmg} | Факт: ${todayDmg} (${m.pill_time_label})\n`;
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
            const bInput = document.getElementById('battleBonusInput');
            if (bInput) bInput.value = customBattleBonus;
            loadClanData(false);
        });

        window.addEventListener('resize', () => {
            if (!localStorage.getItem('warera_clan_view')) {
                const autoMode = window.innerWidth < 768 ? 'cards' : 'table';
                if (autoMode !== currentViewMode) {
                    setViewMode(autoMode);
                }
            }
        });

        // ================= TARGET DAMAGE & GEAR CALCULATOR MODAL LOGIC =================
        let activeCalcMember = null;
        let activeCalcData = null;
        let activeCalcTarget = 2000000;
        let activeCalcAmmo = 'auto';
        let activeCalcFood = 'auto';
        let activeCalcWeapon = 'auto';
        let activeCalcBonus = 84;
        let activeSelectedStrat = null;
        let activeIsBuildLocked = false;
        let calcTargetDebounce = null;
        let calcBonusDebounce = null;
        let activeCalcPrestige = 0;
        let activeCalcRankBonus = 0;
        let calcPrestigeDebounce = null;
        let calcRankBonusDebounce = null;

        function getPillBadgeClass(status) {
            if (status === 'ACTIVE') return 'bg-purple-950/80 text-purple-300 border-purple-700/60 font-semibold';
            if (status === 'READY') return 'bg-blue-950/80 text-blue-300 border-blue-700/60 font-semibold';
            if (status === 'COOLDOWN') return 'bg-rose-950/80 text-rose-300 border-rose-700/60 font-semibold';
            return 'bg-gray-800 text-gray-400 border-gray-700';
        }

        function updateCalcTargetHint(rawDmg) {
            const hint = document.getElementById('calcTargetHint');
            if (hint) {
                if (!rawDmg || isNaN(rawDmg) || rawDmg <= 0) {
                    hint.innerText = '= введіть число (напр. 3.4)';
                    hint.className = 'text-[11px] font-mono text-amber-400 font-bold';
                } else {
                    hint.innerText = `= ${formatNumber(rawDmg)} урону (${formatMillions(rawDmg)})`;
                    hint.className = 'text-[11px] font-mono text-emerald-400 font-bold';
                }
            }
        }

        function onCalcTargetInput(val) {
            const cleanStr = String(val).replace(',', '.').trim();
            const parsed = parseFloat(cleanStr);
            if (isNaN(parsed) || parsed <= 0) {
                updateCalcTargetHint(0);
                return;
            }
            const targetVal = Math.round(parsed * 1000000);
            updateCalcTargetHint(targetVal);

            clearTimeout(calcTargetDebounce);
            calcTargetDebounce = setTimeout(() => {
                activeCalcTarget = targetVal;
                activeIsBuildLocked = false;
                fetchCalculatorPlan(true);
            }, 350);
        }

        function setCalcTarget(valInMillions) {
            const cleanStr = String(valInMillions).replace(',', '.').trim();
            const parsed = parseFloat(cleanStr);
            const numM = isNaN(parsed) ? 1 : Math.max(0.1, parsed);
            activeCalcTarget = Math.round(numM * 1000000);
            activeIsBuildLocked = false;
            const input = document.getElementById('calcTargetInput');
            if (input) input.value = numM;
            updateCalcTargetHint(activeCalcTarget);
            fetchCalculatorPlan(true);
        }

        function updateBonusPresetButtonsUI() {
            [50, 65, 84, 100].forEach(p => {
                const btn = document.getElementById(`bonusPresetBtn_${p}`);
                if (!btn) return;
                if (Math.abs(activeCalcBonus - p) < 0.1) {
                    btn.className = 'px-2 py-2 rounded-xl bg-amber-600 text-white font-mono text-[11px] border border-amber-400 font-bold shadow';
                } else {
                    btn.className = 'px-2 py-2 rounded-xl bg-gray-800 text-gray-300 font-mono text-[11px] border border-bordercolor hover:bg-gray-700';
                }
            });
        }

        function onCalcBonusInput(val) {
            const cleanStr = String(val).replace(',', '.').trim();
            const parsed = parseFloat(cleanStr);
            if (isNaN(parsed) || parsed < 0) return;
            activeCalcBonus = parsed;
            updateBonusPresetButtonsUI();

            clearTimeout(calcBonusDebounce);
            calcBonusDebounce = setTimeout(() => {
                fetchCalculatorPlan();
            }, 350);
        }

        function setCalcBonus(val) {
            const cleanStr = String(val).replace(',', '.').trim();
            const parsed = parseFloat(cleanStr);
            activeCalcBonus = isNaN(parsed) ? 50 : Math.max(0, parsed);
            const input = document.getElementById('calcBonusInput');
            if (input) input.value = activeCalcBonus;
            updateBonusPresetButtonsUI();
            fetchCalculatorPlan();
        }

        function onCalcPrestigeInput(val) {
            const parsed = parseInt(val, 10);
            activeCalcPrestige = isNaN(parsed) ? 0 : Math.max(0, parsed);
            const badge = document.getElementById('calcPrestigeBadge');
            if (badge) badge.innerText = `⭐ Престиж: ${activeCalcPrestige}`;
            const prestigeAutoLabel = document.getElementById('calcPrestigeAutoLabel');
            if (prestigeAutoLabel && activeCalcMember) {
                const diff = activeCalcPrestige !== (activeCalcMember.prestige || 0);
                prestigeAutoLabel.innerText = diff ? `⚠️ симуляція` : `✓ з гри: ${activeCalcMember.prestige || 0}`;
                prestigeAutoLabel.className = diff ? `text-[10px] text-amber-400 font-mono font-semibold` : `text-[10px] text-purple-400 font-mono font-semibold`;
            }

            clearTimeout(calcPrestigeDebounce);
            calcPrestigeDebounce = setTimeout(() => {
                fetchCalculatorPlan();
            }, 350);
        }

        function onCalcRankBonusInput(val) {
            const cleanStr = String(val).replace(',', '.').trim();
            const parsed = parseFloat(cleanStr);
            activeCalcRankBonus = isNaN(parsed) ? 0 : Math.max(0, parsed);
            const rankEl = document.getElementById('calcUserRank');
            if (rankEl && activeCalcMember) {
                rankEl.innerText = `Ранг ${activeCalcMember.military_rank || 0} (+${activeCalcRankBonus}%)`;
            }
            const rankAutoLabel = document.getElementById('calcRankAutoLabel');
            if (rankAutoLabel && activeCalcMember) {
                const diff = Math.abs(activeCalcRankBonus - (activeCalcMember.rank_bonus_pct || 0)) > 0.01;
                rankAutoLabel.innerText = diff ? `⚠️ симуляція` : `✓ з гри: +${activeCalcMember.rank_bonus_pct || 0}%`;
                rankAutoLabel.className = diff ? `text-[10px] text-amber-400 font-mono font-semibold` : `text-[10px] text-emerald-400 font-mono font-semibold`;
            }

            clearTimeout(calcRankBonusDebounce);
            calcRankBonusDebounce = setTimeout(() => {
                fetchCalculatorPlan();
            }, 350);
        }

        function openTargetCalculator(username) {
            if (!clanData || !clanData.members) return;
            const m = clanData.members.find(x => x.username.toLowerCase() === (username || '').toLowerCase());
            if (!m) {
                showToast('Бійця не знайдено', false);
                return;
            }

            activeCalcMember = m;
            activeCalcTarget = Number(m.target_damage) || 2000000;
            activeCalcAmmo = m.target_ammo || 'auto';
            activeCalcFood = m.target_food || (m.target_use_fish ? 'cookedFish' : 'auto');
            activeCalcWeapon = m.target_weapon || 'auto';
            activeCalcBonus = (typeof m.target_battle_bonus === 'number') ? m.target_battle_bonus : ((typeof customBattleBonus === 'number' && !isNaN(customBattleBonus)) ? customBattleBonus : 84);
            activeCalcPrestige = (typeof m.target_prestige === 'number') ? m.target_prestige : (m.prestige || (m.leveling && m.leveling.prestige) || 0);
            activeCalcRankBonus = (typeof m.target_rank_bonus === 'number') ? m.target_rank_bonus : ((typeof m.rank_bonus_pct === 'number') ? m.rank_bonus_pct : (m.skills?.attack?.militaryRankPercent || 0));
            activeIsBuildLocked = !!m.is_build_locked;
            activeSelectedStrat = m.saved_build || null;

            // Populate header details safely
            const nameEl = document.getElementById('calcUserName');
            if (nameEl) nameEl.innerText = m.username;
            const lvlEl = document.getElementById('calcUserLevel');
            if (lvlEl) lvlEl.innerText = `Lv.${m.level}`;
            const rankEl = document.getElementById('calcUserRank');
            if (rankEl) rankEl.innerText = `Ранг ${m.military_rank || 0} (+${activeCalcRankBonus}%)`;
            const prestigeBadge = document.getElementById('calcPrestigeBadge');
            if (prestigeBadge) prestigeBadge.innerText = `⭐ Престиж: ${activeCalcPrestige}`;
            const avatarImg = document.getElementById('calcUserAvatar');
            if (avatarImg) avatarImg.src = m.avatar_url || 'https://media.warera.io/images/itemsv2/sniper.png';

            // Badges
            const pillBadge = document.getElementById('calcPillBadge');
            if (pillBadge) {
                pillBadge.innerText = m.pill_label || '💊 Таблетка';
                pillBadge.className = `px-2 py-0.5 rounded text-[10px] border ${getPillBadgeClass(m.pill_status)}`;
            }
            const hungerBadge = document.getElementById('calcHungerBadge');
            if (hungerBadge) hungerBadge.innerText = `🥪 Голод: ${m.hunger_curr || 0}/${m.hunger_max || 0}`;
            const healthBadge = document.getElementById('calcHealthBadge');
            if (healthBadge) healthBadge.innerText = `❤️ HP: ${Math.round(m.health_curr || 0)}/${Math.round(m.health_max || 0)}`;

            // Target input (in Millions)
            const input = document.getElementById('calcTargetInput');
            if (input) input.value = activeCalcTarget ? (activeCalcTarget / 1000000) : 4;
            updateCalcTargetHint(activeCalcTarget);

            // Battle bonus input
            const bonusInput = document.getElementById('calcBonusInput');
            if (bonusInput) bonusInput.value = activeCalcBonus;
            updateBonusPresetButtonsUI();

            // Prestige and Rank inputs
            const prestigeInput = document.getElementById('calcPrestigeInput');
            if (prestigeInput) prestigeInput.value = activeCalcPrestige;

            const rankBonusInput = document.getElementById('calcRankBonusInput');
            if (rankBonusInput) rankBonusInput.value = activeCalcRankBonus;

            const rankAutoLabel = document.getElementById('calcRankAutoLabel');
            if (rankAutoLabel) {
                rankAutoLabel.innerText = `✓ з гри: +${activeCalcRankBonus}%`;
                rankAutoLabel.className = 'text-[10px] text-emerald-400 font-mono font-semibold';
            }

            const prestigeAutoLabel = document.getElementById('calcPrestigeAutoLabel');
            if (prestigeAutoLabel) {
                prestigeAutoLabel.innerText = `✓ з гри: ${activeCalcPrestige}`;
                prestigeAutoLabel.className = 'text-[10px] text-purple-400 font-mono font-semibold';
            }

            // Reset ammo, food, and weapon buttons
            updateAmmoSelectorUI();
            updateFoodSelectorUI();
            updateWeaponSelectorUI();

            // Show modal & lock background scroll / pull-to-refresh
            setCalcMobileTab('build');
            document.body.style.overflow = 'hidden';
            document.body.style.overscrollBehaviorY = 'contain';
            const modal = document.getElementById('targetCalcModal');
            if (modal) modal.classList.remove('hidden');

            // Fetch live plan
            fetchCalculatorPlan();
        }

        function closeTargetCalculator() {
            const modal = document.getElementById('targetCalcModal');
            if (modal) modal.classList.add('hidden');
            document.body.style.overflow = '';
            document.body.style.overscrollBehaviorY = '';
        }

        function setCalcAmmo(ammoKey) {
            activeCalcAmmo = ammoKey;
            activeIsBuildLocked = false;
            updateAmmoSelectorUI();
            fetchCalculatorPlan(true);
        }

        function updateAmmoSelectorUI() {
            ['auto', 'lightAmmo', 'ammo', 'heavyAmmo'].forEach(k => {
                const btn = document.getElementById(`ammoBtn_${k}`);
                if (!btn) return;
                if (k === activeCalcAmmo) {
                    btn.className = 'px-2 py-1 rounded-lg bg-blue-600 text-white font-mono text-[10px] border border-blue-400 font-bold shadow-md';
                } else {
                    btn.className = 'px-2 py-1 rounded-lg bg-gray-800 text-gray-300 font-mono text-[10px] border border-bordercolor hover:bg-gray-700';
                }
            });
        }

        function setCalcFood(foodKey) {
            activeCalcFood = foodKey;
            activeIsBuildLocked = false;
            updateFoodSelectorUI();
            fetchCalculatorPlan(true);
        }

        function updateFoodSelectorUI() {
            ['auto', 'steak', 'cookedFish'].forEach(k => {
                const btn = document.getElementById(`foodBtn_${k}`);
                if (!btn) return;
                if (k === activeCalcFood) {
                    if (k === 'steak') {
                        btn.className = 'px-2 py-1 rounded-lg bg-rose-600 text-white font-mono text-[10px] border border-rose-400 font-bold shadow-md';
                    } else if (k === 'cookedFish') {
                        btn.className = 'px-2 py-1 rounded-lg bg-sky-600 text-white font-mono text-[10px] border border-sky-400 font-bold shadow-md';
                    } else {
                        btn.className = 'px-2 py-1 rounded-lg bg-blue-600 text-white font-mono text-[10px] border border-blue-400 font-bold shadow-md';
                    }
                } else {
                    btn.className = 'px-2 py-1 rounded-lg bg-gray-800 text-gray-300 font-mono text-[10px] border border-bordercolor hover:bg-gray-700';
                }
            });
        }

        function setCalcWeapon(weaponKey) {
            activeCalcWeapon = weaponKey;
            activeIsBuildLocked = false;
            updateWeaponSelectorUI();
            fetchCalculatorPlan(true);
        }

        function updateWeaponSelectorUI() {
            ['auto', 'sniper', 'tank', 'rifle'].forEach(k => {
                const btn = document.getElementById(`weaponBtn_${k}`);
                if (!btn) return;
                if (k === activeCalcWeapon) {
                    btn.className = 'px-2 py-1 rounded-lg bg-blue-600 text-white font-mono text-[10px] border border-blue-400 font-bold shadow-md';
                } else {
                    btn.className = 'px-2 py-1 rounded-lg bg-gray-800 text-gray-300 font-mono text-[10px] border border-bordercolor hover:bg-gray-700';
                }
            });
        }

        async function fetchCalculatorPlan(forceUnlock = false) {
            if (!activeCalcMember) return;
            const stratBody = document.getElementById('calcStrategiesBody');
            const banner = document.getElementById('calcStatusBanner');
            const optimalCard = document.getElementById('calcOptimalCard');
            const slotsGrid = document.getElementById('calcGearSlotsGrid');

            if (optimalCard) {
                optimalCard.innerHTML = `
                    <div class="glass-panel p-6 rounded-2xl border border-blue-500/30 text-center space-y-2 bg-darkbg/60">
                        <div class="text-blue-400 text-sm font-bold flex items-center justify-center gap-2">
                            <i class="fa-solid fa-spinner fa-spin"></i>
                            <span>Підбираємо найвигідніший бойовий комплект під ціль...</span>
                        </div>
                        <div class="text-[11px] text-gray-400">Аналізуємо ціни ринку, знос зброї, ухилення та ліміт голоду...</div>
                    </div>
                `;
            }
            if (stratBody) {
                stratBody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-gray-400"><i class="fa-solid fa-spinner fa-spin text-blue-500 mr-2"></i> Завантаження варіантів...</td></tr>`;
            }
            if (banner) {
                banner.innerHTML = `<span class="text-gray-400"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Оцінка зносу та дефіциту...</span>`;
            }

            try {
                const basePath = window.location.pathname.replace(/\/(clan(\.html)?|\index\.html)?\/?$/, '');
                const lockQuery = forceUnlock ? '&unlock=1' : (activeIsBuildLocked ? '&locked=1' : '');
                const url = `${basePath ? `${basePath}/` : '/'}api/calculator?nick=${encodeURIComponent(activeCalcMember.username)}&target=${activeCalcTarget}&ammo=${activeCalcAmmo}&food=${activeCalcFood}&bonus=${activeCalcBonus}&prestige=${activeCalcPrestige}&rank_bonus=${activeCalcRankBonus}&weapon=${activeCalcWeapon}${lockQuery}`;

                const resp = await fetch(url);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();

                if (data.status !== 'ok' || !data.result) {
                    throw new Error(data.message || 'Не вдалося прорахувати план');
                }

                activeCalcData = data.result;
                activeIsBuildLocked = !!activeCalcData.is_build_locked;
                activeSelectedStrat = activeCalcData.best_strategy;
                renderCalculatorUI(activeCalcData);

                // Auto-lock freshly calculated build so reopening the modal keeps the exact same build
                if (!activeIsBuildLocked && activeSelectedStrat) {
                    await saveCurrentTarget(false, true);
                }
            } catch (err) {
                console.error('Calculator fetch error:', err);
                if (optimalCard) {
                    optimalCard.innerHTML = `
                        <div class="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-center text-rose-300 text-xs">
                            <i class="fa-solid fa-triangle-exclamation mr-1.5"></i> Помилка: ${err.message}
                        </div>
                    `;
                }
            }
        }

        function renderCalculatorUI(result) {
            const p = result.player;
            const t = result.target;
            const best = result.best_strategy;
            if (!activeSelectedStrat) activeSelectedStrat = best;

            // Updated time
            const timeSpan = document.getElementById('calcUpdatedTime');
            if (timeSpan && result.updated_at) {
                const dt = new Date(result.updated_at);
                timeSpan.innerText = `🟢 ціни ринку оновлено: ${dt.toLocaleTimeString()}`;
            }

            // Status Banner (without redundant 'Білд закріплено' badge)
            const banner = document.getElementById('calcStatusBanner');
            if (banner) {
                const deficitStr = t.deficit_damage > 0 ? `Залишилося: <b class="text-white font-mono">+${formatNumber(t.deficit_damage)}</b>` : `<b class="text-emerald-400 font-mono">Ціль уже виконана!</b>`;
                const pillTimeStr = p.has_active_pill ? `Таблетка: <b class="text-amber-400 font-mono">${p.pill_remaining_hours} год</b>` : `Нова таблетка: <b class="text-blue-400 font-mono">8.0 год</b>`;
                banner.innerHTML = `
                    <div class="flex items-center gap-2 flex-wrap">
                        <span>Сьогодні: <b class="text-emerald-400 font-mono">+${formatNumber(p.today_damage)}</b></span>
                        <span class="text-gray-500">·</span>
                        <span>${deficitStr}</span>
                    </div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <span>${pillTimeStr}</span>
                        <span class="text-gray-500">·</span>
                        <span>Голод: <b class="text-sky-400 font-mono">${(p && p.available_hunger !== undefined) ? p.available_hunger : (best && best.available_hunger !== undefined ? best.available_hunger : 0)} од.</b></span>
                    </div>
                `;
            }

            // Update mobile tab budget badge
            const mobBudget = document.getElementById('calcMobileBudgetBadge');
            if (mobBudget && best) {
                const activeStrat = activeSelectedStrat || best;
                mobBudget.innerText = `(${formatNumber(activeStrat.grand_total_cost)} Coins)`;
            }

            // Render Hero Card (Only the best profitable strategy!)
            const optimalCard = document.getElementById('calcOptimalCard');
            if (optimalCard && best) {
                const isSelectedBest = !activeSelectedStrat || activeSelectedStrat.strategy_key === best.strategy_key;
                const stratToShow = isSelectedBest ? best : activeSelectedStrat;
                const isSaved = !!(stratToShow.is_saved_build || (activeIsBuildLocked && activeSelectedStrat && (activeSelectedStrat.strategy_key === stratToShow.strategy_key || activeSelectedStrat.label === stratToShow.label)));

                let stratBadge = '';
                let lockActionBtn = '';
                if (isSaved) {
                    stratBadge = `<span class="px-2 py-0.5 rounded-full bg-purple-500/25 text-purple-200 border border-purple-500/60 text-[10px] font-black uppercase tracking-wide flex items-center gap-1 shadow-sm">
                        <i class="fa-solid fa-lock text-purple-400"></i> ЗБЕРЕЖЕНИЙ БІЛД
                    </span>`;
                    lockActionBtn = `
                        <button onclick="unlockCurrentBuild()" class="px-2 py-0.5 rounded-lg bg-gray-800 hover:bg-rose-950/70 text-gray-300 hover:text-rose-200 border border-bordercolor hover:border-rose-500/50 text-[10px] font-bold flex items-center gap-1 transition-all shadow-sm active:scale-95" title="Скинути збережений білд і повернутися до авто-підбору">
                            <i class="fa-solid fa-unlock text-[9px]"></i> <span>Скинути</span>
                        </button>
                    `;
                } else if (stratToShow.is_best_value) {
                    stratBadge = `<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 text-[10px] font-black uppercase tracking-wide">
                        🏆 НАЙВИГІДНІШИЙ ВАРІАНТ
                    </span>`;
                    lockActionBtn = `
                        <button onclick="saveCurrentBuild()" class="px-2 py-0.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-[10px] font-bold flex items-center gap-1 shadow-sm shadow-purple-500/20 transition-all active:scale-95" title="Зберегти цей білд, щоб він не мінявся після ударів">
                            <i class="fa-solid fa-bookmark text-[9px]"></i> <span>Зберегти цей білд</span>
                        </button>
                    `;
                } else {
                    stratBadge = `<span class="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/50 text-[10px] font-black uppercase tracking-wide">
                        ⚙️ ОБРАНИЙ ВАРІАНТ
                    </span>`;
                    lockActionBtn = `
                        <button onclick="saveCurrentBuild()" class="px-2 py-0.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-[10px] font-bold flex items-center gap-1 shadow-sm shadow-purple-500/20 transition-all active:scale-95" title="Зберегти цей білд, щоб він не мінявся після ударів">
                            <i class="fa-solid fa-bookmark text-[9px]"></i> <span>Зберегти цей білд</span>
                        </button>
                    `;
                }

                const cp = result.consumable_prices || {};
                const case1Price = cp.case1 ? Number(cp.case1).toFixed(2) : '3.89';
                const case2Price = cp.case2 ? Number(cp.case2).toFixed(2) : '26.92';

                optimalCard.innerHTML = `
                    <div class="glass-panel p-4 sm:p-5 rounded-2xl border-2 ${isSaved ? 'border-purple-500/60 bg-gradient-to-r from-purple-950/40 via-[#0e131f] to-indigo-950/30' : (stratToShow.is_best_value ? 'border-emerald-500/60 bg-gradient-to-r from-emerald-950/40 via-[#0e131f] to-blue-950/30' : 'border-blue-500/60 bg-[#0e131f]')} shadow-xl space-y-3.5">
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-bordercolor/60 pb-3">
                            <div class="flex items-start sm:items-center gap-3">
                                <div class="w-12 h-12 rounded-2xl ${isSaved ? 'bg-purple-500/15 border-2 border-purple-500/50 text-purple-400' : (stratToShow.is_best_value ? 'bg-emerald-500/15 border-2 border-emerald-500/40 text-emerald-400' : 'bg-blue-500/15 border-2 border-blue-500/40 text-blue-400')} flex items-center justify-center text-2xl shrink-0 shadow-inner">
                                    ${isSaved ? '🛡️' : (stratToShow.is_best_value ? '🏆' : '⚙️')}
                                </div>
                                <div>
                                    <div class="flex items-center gap-2 flex-wrap">
                                        ${stratBadge}
                                        ${lockActionBtn}
                                        <span class="text-xs text-gray-400">під ціль <b class="text-white font-mono">${formatMillions(t.target_damage)}</b> <span class="text-amber-400 font-mono font-bold">(+${t.battle_bonus ?? activeCalcBonus}% баф)</span></span>
                                    </div>
                                    <h3 class="text-base sm:text-lg font-black text-white mt-1 flex items-center gap-2 flex-wrap">
                                        <span>${stratToShow.label}</span>
                                        <span class="text-xs font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-700/40">
                                            ${stratToShow.food_icon} ${stratToShow.food_name}
                                        </span>
                                    </h3>
                                </div>
                            </div>
                            <div class="text-left sm:text-right bg-darkbg/60 p-2.5 rounded-xl border border-bordercolor/40 sm:border-0 sm:bg-transparent sm:p-0">
                                <div class="text-[10px] uppercase font-bold text-gray-400 tracking-wider">На закупівлю:</div>
                                <div class="text-xl sm:text-2xl font-black text-emerald-400 font-mono tracking-tight">${formatNumber(stratToShow.grand_total_cost)} Coins</div>
                                ${stratToShow.initial_grand_total && p.today_damage > 0 && stratToShow.initial_grand_total > stratToShow.grand_total_cost + 10 ? `<div class="text-[10px] text-gray-400 font-mono mt-0.5">Повний план: ${formatNumber(stratToShow.initial_grand_total)} Coins</div>` : ''}
                                <div class="text-[11px] font-bold font-mono mt-0.5 whitespace-nowrap ${stratToShow.net_profit >= 0 ? 'text-emerald-400' : 'text-amber-400'}">
                                    ${stratToShow.net_profit >= 0 ? `💰 Чистий профіт: +${formatNumber(stratToShow.net_profit)}` : `📉 Чисті витрати: ${formatNumber(Math.abs(stratToShow.net_profit))}`} Coins
                                </div>
                                <div class="text-[9px] text-gray-400 mt-0.5">без урахування баунті та дропу з битв</div>
                                <div class="text-[10px] text-sky-400 font-mono mt-0.5">🔥 ~${formatNumber(Math.abs(stratToShow.cost_per_m_dmg || 0))} Coins / 1M (чистими)</div>
                                ${stratToShow.savings_vs_best > 0 ? `<div class="text-[10px] text-amber-400 font-mono mt-0.5">+${formatNumber(stratToShow.savings_vs_best)} Coins дорожче за топ</div>` : '<div class="text-[10px] text-emerald-400/80 font-mono mt-0.5">Економічний оптимум</div>'}
                            </div>
                        </div>

                        <!-- 6 Stat Metrics: 3x2 on desktop, 2x3 on mobile (lightweight, no heavy borders) -->
                        <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-3 gap-y-2 bg-darkbg/60 rounded-xl p-2.5 text-xs">
                            <div>
                                <div class="text-[10px] uppercase font-bold text-gray-400">Патрони</div>
                                <div class="font-bold text-white mt-0.5 truncate">${stratToShow.ammo_badge}</div>
                                <div class="text-[10px] text-gray-400 font-mono">${formatNumber(stratToShow.ammo_units_needed)} постр.</div>
                            </div>

                            <div>
                                <div class="text-[10px] uppercase font-bold text-gray-400">Удари</div>
                                <div class="font-bold text-white mt-0.5 font-mono">${formatNumber(stratToShow.hits_needed)} уд.</div>
                                <div class="text-[10px] text-emerald-400 font-mono">~${formatNumber(stratToShow.avg_dmg_per_hit)}/уд.</div>
                            </div>

                            <div title="1 зброя = 100 ударів без ухилення">
                                <div class="text-[10px] uppercase font-bold text-gray-400">Зброя</div>
                                <div class="font-bold text-amber-400 mt-0.5 font-mono">${stratToShow.weapons_burned} шт</div>
                                <div class="text-[10px] text-gray-400 font-mono">${(isSaved && p.today_damage > 0) ? `на ${formatNumber(stratToShow.hits_needed)} уд.` : '100 уд/ган'}</div>
                            </div>

                            <div title="Броня захищена ухиленням ${stratToShow.eff_dodge}%">
                                <div class="text-[10px] uppercase font-bold text-gray-400">Броня</div>
                                <div class="font-bold text-indigo-300 mt-0.5 font-mono">${stratToShow.armor_sets_burned} компл.</div>
                                <div class="text-[10px] text-gray-400 font-mono">ухил. ${stratToShow.eff_dodge}%</div>
                            </div>

                            <div>
                                <div class="text-[10px] uppercase font-bold text-gray-400">Їжа / Голод</div>
                                <div class="font-bold ${stratToShow.can_reach_in_session ? 'text-sky-300' : 'text-rose-400'} mt-0.5 font-mono">${stratToShow.food_units_needed} шт</div>
                                <div class="text-[10px] text-gray-400 font-mono">${stratToShow.available_hunger ? `${stratToShow.food_units_needed} / ${stratToShow.available_hunger} од. голоду` : `${stratToShow.hunger_usage_pct}% шкали`}</div>
                            </div>

                            <div>
                                <div class="text-[10px] uppercase font-bold text-gray-400">Ліміт сесії</div>
                                <div class="font-bold ${stratToShow.can_reach_in_session ? (stratToShow.reach_status === 'soft_cap' ? 'text-amber-300' : 'text-emerald-400') : 'text-rose-400'} mt-0.5">
                                    ${stratToShow.reach_badge || (stratToShow.can_reach_in_session ? '✅ Досяжно' : '❌ Переліміт')}
                                </div>
                                <div class="text-[10px] text-gray-400 font-mono">${stratToShow.reach_note || (stratToShow.can_reach_in_session ? 'Вкладається в 1 сесію (8 год)' : 'Не вміститься в 1 сесію')}</div>
                            </div>
                        </div>

                        <!-- Combined 1-Line Return (Cases + Scrap) -->
                        <div class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-xl bg-darkbg/70 border border-bordercolor/50 text-xs" title="Кейс ~${case1Price} Coins, Елітний ~${case2Price} Coins">
                            <span class="text-gray-300 font-semibold">
                                Повернення: <b class="text-emerald-400 font-mono">+${formatNumber(Math.round((stratToShow.total_cases_value || 0) + (stratToShow.scrap_value || 0)))} Coins</b>
                            </span>
                            <span class="text-[11px] text-gray-400 font-mono">
                                Кейси +${formatNumber(stratToShow.total_cases_value || 0)} (${stratToShow.expected_case1 || 0} зв. + ${stratToShow.expected_case2 || 0} ел.) · Брухт +${formatNumber(stratToShow.scrap_value || 0)}
                            </span>
                        </div>
                    </div>
                `;
            }

            // Populate alternative strategies table in collapsed details
            const tbody = document.getElementById('calcStrategiesBody');
            if (tbody) {
                tbody.innerHTML = result.strategies.map((s, idx) => {
                    const isSelected = activeSelectedStrat && activeSelectedStrat.strategy_key === s.strategy_key;
                    const isBest = s.is_best_value;
                    const canReach = s.can_reach_in_session;

                    let statusBadge = '';
                    if (s.is_saved_build) {
                        statusBadge = `<span class="px-2 py-0.5 rounded-full bg-purple-500/25 text-purple-200 border border-purple-500/60 text-[10px] font-black flex items-center justify-center gap-1"><i class="fa-solid fa-lock text-[9px] text-purple-400"></i> ЗБЕРЕЖЕНИЙ</span>`;
                    } else if (isBest) {
                        statusBadge = `<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 text-[10px] font-black">🏆 НАЙВИГІДНІШИЙ</span>`;
                    } else if (s.reach_badge) {
                        const badgeColor = s.reach_status === 'ok' ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : (s.reach_status === 'soft_cap' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/30');
                        statusBadge = `<span class="px-1.5 py-0.5 rounded ${badgeColor} text-[10px] font-bold">${s.reach_badge}</span>`;
                    } else if (canReach) {
                        statusBadge = `<span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border-blue-500/30 text-[10px]">✅ Досяжно</span>`;
                    } else {
                        statusBadge = `<span class="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border-rose-500/30 text-[10px]" title="Не вистачить шкали голоду за 1 сесію таблетки">❌ Ліміт голоду</span>`;
                    }

                    const rowBg = isSelected 
                        ? 'bg-blue-600/20 border-l-4 border-l-blue-400 border-bordercolor/80' 
                        : (isBest ? 'bg-emerald-950/20 hover:bg-emerald-950/40' : 'hover:bg-cardbg/80');

                    return `
                        <tr class="${rowBg} cursor-pointer transition-all" onclick="selectStrategyRow('${s.strategy_key}')">
                            <td class="p-2.5 font-sans">
                                <div class="font-bold text-white text-xs flex items-center gap-1.5">
                                    <span>${s.label}</span>
                                </div>
                                <div class="text-[10px] text-gray-400 flex items-center gap-1 mt-0.5">
                                    <span>${s.food_icon} ${s.food_name}</span>
                                    <span>•</span>
                                    <span>${formatNumber(s.avg_dmg_per_hit || s.avg_damage_per_hit || s.sim_dmg || 0)} урону/удар</span>
                                </div>
                            </td>
                            <td class="p-2.5 text-center">
                                <span class="px-1.5 py-0.5 rounded bg-gray-800 text-[10px] border border-bordercolor text-gray-300 font-bold" title="${s.ammo_name} (${s.ammo_price} Coins/шт)">
                                    ${s.ammo_badge}
                                </span>
                            </td>
                            <td class="p-2.5 text-center font-bold text-gray-200">
                                ${formatNumber(s.hits_needed)}
                            </td>
                            <td class="p-2.5 text-center" title="1 пушка = 100 ударів без ухилення">
                                <span class="text-amber-400 font-bold">${s.weapons_burned} шт</span>
                            </td>
                            <td class="p-2.5 text-center" title="Захищено ухиленням ${s.eff_dodge}%">
                                <span class="text-indigo-300 font-bold">${s.armor_sets_burned} компл.</span>
                            </td>
                            <td class="p-2.5 text-center">
                                <div class="font-bold ${canReach ? 'text-sky-300' : 'text-rose-400'}">${s.food_units_needed} шт</div>
                                <div class="text-[9px] text-gray-500 font-mono">${s.hunger_usage_pct}% ліміту</div>
                            </td>
                            <td class="p-2.5 text-right font-black text-xs ${isBest ? 'text-emerald-400 text-sm' : 'text-gray-200'}">
                                <div>${formatNumber(s.grand_total_cost)} Coins</div>
                                <div class="text-[9px] font-mono font-semibold ${s.net_profit >= 0 ? 'text-emerald-400' : 'text-amber-400'}">
                                    ${s.net_profit >= 0 ? 'Профіт +' : 'Мінус '}${formatNumber(s.net_profit)} Coins
                                </div>
                                ${s.savings_vs_best > 0 ? `<div class="text-[9px] text-gray-500 font-normal">+${formatNumber(s.savings_vs_best)} Coins</div>` : ''}
                            </td>
                            <td class="p-2.5 text-center font-sans">
                                ${statusBadge}
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            const mobileAltList = document.getElementById('calcStrategiesMobileList');
            if (mobileAltList && Array.isArray(result.strategies)) {
                mobileAltList.innerHTML = result.strategies.map(s => {
                    const isSelected = activeSelectedStrat && activeSelectedStrat.strategy_key === s.strategy_key;
                    const isBest = s.is_best_value;
                    const canReach = s.can_reach_in_session;
                    let statusBadge = canReach
                        ? '<span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-bold">✅ Досяжно</span>'
                        : '<span class="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[10px] font-bold">❌ Ліміт</span>';
                    if (s.is_saved_build) statusBadge = '<span class="px-1.5 py-0.5 rounded bg-purple-500/25 text-purple-200 border border-purple-500/50 text-[10px] font-bold">🔒 Збережений</span>';
                    else if (isBest) statusBadge = '<span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold">🏆 Топ</span>';
                    else if (s.reach_badge) statusBadge = `<span class="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 text-[10px] font-bold">${s.reach_badge}</span>`;

                    return `
                        <div onclick="selectStrategyRow('${s.strategy_key}')" class="p-2.5 rounded-xl border ${isSelected ? 'border-blue-500 bg-blue-950/25' : 'border-bordercolor/70 bg-darkbg/60'} cursor-pointer space-y-1.5 transition">
                            <div class="flex items-center justify-between gap-2">
                                <span class="font-bold text-white text-xs truncate">${s.label}</span>
                                <span class="shrink-0">${statusBadge}</span>
                            </div>
                            <div class="text-[10px] text-gray-400 font-mono flex items-center justify-between gap-2 flex-wrap">
                                <span>${s.food_name} · ${formatNumber(s.hits_needed)} уд. · ${s.weapons_burned} збр. · ${s.armor_sets_burned} бр.</span>
                                <span class="${canReach ? 'text-sky-300' : 'text-rose-400'}">${s.food_units_needed} шт (${s.hunger_usage_pct}%)</span>
                            </div>
                            <div class="flex items-center justify-between pt-1 border-t border-bordercolor/40 font-mono text-xs">
                                <span class="font-black ${isBest ? 'text-emerald-400' : 'text-white'}">${formatNumber(s.grand_total_cost)} Coins</span>
                                <span class="text-[10px] font-semibold ${s.net_profit >= 0 ? 'text-emerald-400' : 'text-amber-400'}">
                                    ${s.net_profit >= 0 ? 'Профіт +' : 'Мінус '}${formatNumber(s.net_profit)} Coins
                                </span>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            renderShoppingList(activeSelectedStrat || best);
        }

        function selectStrategyRow(stratKey) {
            if (!activeCalcData || !activeCalcData.strategies) return;
            const strat = activeCalcData.strategies.find(s => s.strategy_key === stratKey);
            if (!strat) return;
            activeSelectedStrat = strat;
            renderCalculatorUI(activeCalcData);
        }

        function setCalcMobileTab(tab) {
            const left = document.getElementById('calcLeftCol');
            const right = document.getElementById('calcRightCol');
            const btnBuild = document.getElementById('calcTabBtn_build');
            const btnSettings = document.getElementById('calcTabBtn_settings');
            if (!left || !right) return;
            if (tab === 'settings') {
                left.classList.remove('hidden');
                right.classList.add('hidden', 'lg:block');
                if (btnSettings) btnSettings.className = 'py-2.5 px-3 text-white border-b-2 border-blue-500 bg-blue-600/10 flex items-center justify-center gap-1.5 transition';
                if (btnBuild) btnBuild.className = 'py-2.5 px-3 text-gray-400 border-b-2 border-transparent flex items-center justify-center gap-1.5 transition';
            } else {
                right.classList.remove('hidden');
                left.classList.add('hidden', 'lg:block');
                if (btnBuild) btnBuild.className = 'py-2.5 px-3 text-white border-b-2 border-blue-500 bg-blue-600/10 flex items-center justify-center gap-1.5 transition';
                if (btnSettings) btnSettings.className = 'py-2.5 px-3 text-gray-400 border-b-2 border-transparent flex items-center justify-center gap-1.5 transition';
            }
        }

        function renderShoppingList(strat) {
            if (!strat) return;

            const lblEl = document.getElementById('calcSelectedStratLabel');
            if (lblEl) lblEl.innerText = `${strat.label} (${strat.food_name})`;
            const grandEl = document.getElementById('calcSelectedGrandTotal');
            if (grandEl) grandEl.innerHTML = `${formatNumber(strat.grand_total_cost)} Coins`;

            const grid = document.getElementById('calcGearSlotsGrid');
            if (grid) {
                const slots = strat.build_slots || [];
                if (slots.length === 0) {
                    if (strat.is_naked) {
                        grid.innerHTML = `
                            <div class="col-span-full p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 text-center space-y-1">
                                <div class="text-amber-400 font-bold text-sm">⚠️ Боєць не має надітої зброї (Голий)</div>
                                <div class="text-gray-300 text-xs">Для бою необхідно одягнути зброю в грі або обрати комплект із покупкою (Золота середина чи Т4).</div>
                            </div>
                        `;
                    } else {
                        grid.innerHTML = `
                            <div class="col-span-full p-4 rounded-xl bg-darkbg/60 border border-emerald-500/30 text-center space-y-1">
                                <div class="text-emerald-400 font-bold text-sm">🛡 Використовується поточний надітий шмот бійця</div>
                                <div class="text-gray-400 text-xs">Жодних нових витрат на покупку спорядження не потрібно! (0.00 Coins)</div>
                            </div>
                        `;
                    }
                } else {
                    grid.innerHTML = slots.map(item => {
                        const isEquipped = item.already_equipped;
                        const rarity = (item.rarity || 'epic').toLowerCase();

                        // Rarity styling matching WarEra Wiki Builder
                        let cardBorder = 'border-bordercolor';
                        let cardBg = 'bg-cardbg/80';
                        let cardGlow = '';
                        let tierPill = '';

                        const isConsumable = item.is_consumable || item.slot === 'ammo' || item.slot === 'food';

                        if (isConsumable) {
                            tierPill = ''; // No tier pill for ammo & food!
                            if (item.slot === 'ammo') {
                                if (item.item_code === 'lightAmmo') {
                                    cardBorder = 'border-emerald-500/70';
                                    cardBg = 'bg-gradient-to-b from-[#0a2016] via-[#07160f] to-[#040c08]';
                                    cardGlow = 'shadow-[0_4px_16px_rgba(16,185,129,0.25)]';
                                } else if (item.item_code === 'heavyAmmo') {
                                    cardBorder = 'border-purple-500/70';
                                    cardBg = 'bg-gradient-to-b from-[#1b0f2a] via-[#130b1e] to-[#0b0611]';
                                    cardGlow = 'shadow-[0_4px_16px_rgba(168,85,247,0.25)]';
                                } else {
                                    // standard blue ammo
                                    cardBorder = 'border-blue-500/70';
                                    cardBg = 'bg-gradient-to-b from-[#0c182c] via-[#091120] to-[#050b14]';
                                    cardGlow = 'shadow-[0_4px_16px_rgba(59,130,246,0.25)]';
                                }
                            } else {
                                // Food styling: User requested Steak = Blue background, Fish = Purple background!
                                if (item.item_code === 'cookedFish' || item.item_code === 'fish') {
                                    cardBorder = 'border-purple-500/70';
                                    cardBg = 'bg-gradient-to-b from-[#1b0f2a] via-[#130b1e] to-[#0b0611]';
                                    cardGlow = 'shadow-[0_4px_16px_rgba(168,85,247,0.25)]';
                                } else {
                                    // steak
                                    cardBorder = 'border-blue-500/70';
                                    cardBg = 'bg-gradient-to-b from-[#0c182c] via-[#091120] to-[#050b14]';
                                    cardGlow = 'shadow-[0_4px_16px_rgba(59,130,246,0.25)]';
                                }
                            }
                        } else if (rarity === 'mythic' || item.tier === 6) {
                            cardBorder = 'border-rose-500/60';
                            cardBg = 'bg-gradient-to-r from-[#260a12] to-[#110609]';
                            tierPill = '<span class="absolute -top-1 -right-1 text-[9px] px-1 rounded bg-rose-950 text-rose-300 border border-rose-500/60 font-bold leading-tight">T6</span>';
                        } else if (rarity === 'legendary' || item.tier === 5) {
                            cardBorder = 'border-amber-500/60';
                            cardBg = 'bg-gradient-to-r from-[#261b07] to-[#120d04]';
                            tierPill = '<span class="absolute -top-1 -right-1 text-[9px] px-1 rounded bg-amber-950 text-amber-300 border border-amber-500/60 font-bold leading-tight">T5</span>';
                        } else if (rarity === 'epic' || item.tier === 4) {
                            cardBorder = 'border-purple-500/60';
                            cardBg = 'bg-gradient-to-r from-[#1b0f2a] to-[#0e0816]';
                            tierPill = '<span class="absolute -top-1 -right-1 text-[9px] px-1 rounded bg-purple-950 text-purple-300 border border-purple-500/60 font-bold leading-tight">T4</span>';
                        } else if (rarity === 'rare' || item.tier === 3) {
                            cardBorder = 'border-blue-500/60';
                            cardBg = 'bg-gradient-to-r from-[#0c182c] to-[#070d18]';
                            tierPill = '<span class="absolute -top-1 -right-1 text-[9px] px-1 rounded bg-blue-950 text-blue-300 border border-blue-500/60 font-bold leading-tight">T3</span>';
                        } else if (rarity === 'uncommon' || item.tier === 2) {
                            cardBorder = 'border-emerald-500/60';
                            cardBg = 'bg-gradient-to-r from-[#0a2016] to-[#06110c]';
                            tierPill = '<span class="absolute -top-1 -right-1 text-[9px] px-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/60 font-bold leading-tight">T2</span>';
                        }

                        const cleanName = (item.name || '').replace(/\s*\([^)]*\)\s*$/, '').trim();
                        const compactStats = (item.target_stats || '—')
                            .replace(/Атака/g, 'Атк')
                            .replace(/Крит\.?\s*урон/gi, 'Крит ур.')
                            .replace(/Крит-урон/gi, 'Крит ур.')
                            .replace(/Ухилення/g, 'Ухил')
                            .replace(/Влучність/g, 'Влуч.')
                            .replace(/\s*•\s*/g, ' · ');

                        const fallbackSrc = item.slot === 'food'
                            ? 'https://media.warera.io/images/itemsv2/steak.png'
                            : (item.slot === 'ammo'
                                ? 'https://media.warera.io/images/itemsv2/lightAmmo.png'
                                : 'https://media.warera.io/images/itemsv2/sniper.png');

                        let priceHtml = '';
                        if (isEquipped) {
                            priceHtml = `<div class="text-right shrink-0"><div class="text-[11px] font-bold text-emerald-400">На тобі</div><div class="text-[10px] text-gray-400 font-mono">0 Coins</div></div>`;
                        } else if (item.item_code === 'knife' && strat.is_naked) {
                            priceHtml = `<a href="https://app.warera.io/market/equipments" target="_blank" class="px-2.5 py-1 rounded-lg bg-rose-950/70 border border-rose-500/50 text-rose-300 text-[10px] font-bold whitespace-nowrap shrink-0">Купити</a>`;
                        } else {
                            const buyPriceLabel = item.total_price > 0 ? `${formatNumber(item.total_price)}` : `${item.unit_price}`;
                            priceHtml = `
                                <a href="${item.url}" target="_blank" class="px-2.5 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 border border-blue-500/40 text-right shrink-0 transition block group" title="Купити ${cleanName} (${item.qty_needed} шт)">
                                    <div class="font-mono text-[11px] font-bold text-emerald-300 group-hover:text-white whitespace-nowrap">${buyPriceLabel} Coins</div>
                                    <div class="font-mono text-[10px] text-gray-300 group-hover:text-white">×${item.qty_needed} <i class="fa-solid fa-arrow-up-right-from-square text-[8px] ml-0.5"></i></div>
                                </a>
                            `;
                        }

                        return `
                            <div class="px-3 py-2 rounded-xl border ${cardBorder} ${cardBg} flex items-center gap-3 min-h-[60px] hover:border-gray-400 transition-all">
                                <div class="relative w-10 h-10 rounded-lg bg-black/40 border border-white/10 flex items-center justify-center shrink-0 p-1">
                                    <img src="${item.image_url}" class="max-h-full max-w-full object-contain" onerror="this.onerror=null; this.src='${fallbackSrc}';">
                                    ${tierPill}
                                </div>
                                <div class="min-w-0 flex-1">
                                    <div class="font-bold text-white text-xs truncate" title="${item.name}">${cleanName}</div>
                                    <div class="text-[11px] font-mono text-sky-300 truncate mt-0.5" title="${item.target_stats || ''}">${compactStats}</div>
                                </div>
                                ${priceHtml}
                            </div>
                        `;
                    }).join('');
                }
            }

            // Pill status strip (Ammo and Food are already shown in the 8-slot grid above)
            const consGrid = document.getElementById('calcConsumablesGrid');
            if (consGrid) {
                const needPill = strat.pill_cost > 0;
                consGrid.innerHTML = `
                    <div class="glass-panel px-3.5 py-2.5 rounded-xl border ${needPill ? 'border-rose-500/30 bg-rose-950/15' : 'border-emerald-500/30 bg-emerald-950/15'} flex items-center justify-between gap-3">
                        <div class="flex items-center gap-2.5 min-w-0">
                            <span class="text-base">💊</span>
                            <div class="min-w-0">
                                <div class="text-xs font-bold ${needPill ? 'text-white' : 'text-emerald-300'}">
                                    Таблетка (Cocaine): ${needPill ? 'потрібно докупити (1 шт на 8 год, +60%)' : 'вже активна на бійці'}
                                </div>
                            </div>
                        </div>
                        <div class="font-mono font-bold text-xs ${needPill ? 'text-rose-300' : 'text-emerald-400'} shrink-0">
                            ${needPill ? `${strat.pill_cost} Coins` : '0.00 Coins'}
                        </div>
                    </div>
                `;
            }
        }

        async function saveCurrentTarget(andClose = true, silent = false) {
            if (!activeCalcMember) return;
            const btn = document.getElementById('btnSaveTarget');
            if (btn) btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Збереження...`;

            try {
                const basePath = window.location.pathname.replace(/\/(clan(\.html)?|\index\.html)?\/?$/, '');
                const postUrl = `${basePath ? `${basePath}/` : '/'}api/clan/targets`;

                // Prepare saved_build payload
                const stratToSave = activeSelectedStrat || (activeCalcData && activeCalcData.best_strategy);
                let savedBuildPayload = null;
                if (stratToSave) {
                    savedBuildPayload = Object.assign({}, stratToSave);
                    if (!savedBuildPayload.initial_target_damage) {
                        savedBuildPayload.initial_target_damage = activeCalcTarget;
                        savedBuildPayload.initial_grand_total = stratToSave.grand_total_cost;
                        savedBuildPayload.initial_hits = stratToSave.hits_needed;
                    }
                }

                const resp = await fetch(postUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: activeCalcMember.username,
                        user_id: activeCalcMember.user_id || '',
                        target_damage: activeCalcTarget,
                        gear_tier: stratToSave ? (stratToSave.tier_name || `t${stratToSave.tier_num || 5}`) : 'epic',
                        use_pill: true,
                        use_fish: stratToSave ? stratToSave.food_key === 'cookedFish' : true,
                        battle_bonus: activeCalcBonus,
                        weapon: activeCalcWeapon,
                        food: activeCalcFood,
                        ammo: activeCalcAmmo,
                        prestige: activeCalcPrestige,
                        rank_bonus: activeCalcRankBonus,
                        saved_strategy_key: stratToSave ? stratToSave.strategy_key : null,
                        saved_strategy_label: stratToSave ? stratToSave.label : null,
                        saved_build: savedBuildPayload,
                        is_build_locked: true,
                    })
                });

                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();

                if (data.status !== 'ok') throw new Error(data.message || 'Помилка збереження');

                // Update local memory in clanData so table progress bar renders immediately!
                activeCalcMember.target_damage = activeCalcTarget;
                activeCalcMember.target_battle_bonus = activeCalcBonus;
                activeCalcMember.target_weapon = activeCalcWeapon;
                activeCalcMember.target_food = activeCalcFood;
                activeCalcMember.target_ammo = activeCalcAmmo;
                activeCalcMember.target_prestige = activeCalcPrestige;
                activeCalcMember.target_rank_bonus = activeCalcRankBonus;
                activeCalcMember.saved_strategy_key = stratToSave ? stratToSave.strategy_key : null;
                activeCalcMember.saved_strategy_label = stratToSave ? stratToSave.label : null;
                activeCalcMember.saved_build = savedBuildPayload;
                activeCalcMember.is_build_locked = true;
                activeIsBuildLocked = true;

                const todayVal = Number(activeCalcMember.today_damage || 0);
                activeCalcMember.target_progress_pct = Math.round(Math.min(100.0, (todayVal / activeCalcTarget) * 100.0) * 10) / 10;

                renderMembersTable();
                if (!silent) {
                    const stratLabel = stratToSave ? ` та білд "${stratToSave.label}"` : '';
                    showToast(`Ціль ${formatMillions(activeCalcTarget)}${stratLabel} збережено!`);
                }

                if (andClose) {
                    closeTargetCalculator();
                } else if (activeCalcData) {
                    if (stratToSave) stratToSave.is_saved_build = true;
                    renderCalculatorUI(activeCalcData);
                }
            } catch (err) {
                console.error('Save target error:', err);
                if (!silent) showToast(`Помилка: ${err.message}`, false);
            } finally {
                if (btn) btn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Зберегти ціль`;
            }
        }

        async function saveCurrentBuild() {
            await saveCurrentTarget(false);
        }

        async function unlockCurrentBuild() {
            if (!activeCalcMember) return;
            try {
                const basePath = window.location.pathname.replace(/\/(clan(\.html)?|\index\.html)?\/?$/, '');
                const postUrl = `${basePath ? `${basePath}/` : '/'}api/clan/targets`;

                const resp = await fetch(postUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: activeCalcMember.username,
                        clear_build: true,
                    })
                });

                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                if (data.status !== 'ok') throw new Error(data.message || 'Помилка скидання');

                activeCalcMember.is_build_locked = false;
                activeCalcMember.saved_build = null;
                activeCalcMember.saved_strategy_key = null;
                activeCalcMember.saved_strategy_label = null;
                activeIsBuildLocked = false;
                activeSelectedStrat = null;

                renderMembersTable();
                showToast(`Закріплення білду скинуто. Увімкнено авто-підбір.`);
                await fetchCalculatorPlan(true);
            } catch (err) {
                console.error('Unlock build error:', err);
                showToast(`Помилка: ${err.message}`, false);
            }
        }
    

        let allBattles = [];
        let autoRefreshTimer = null;

        function setFilterSniperOnly() {
            document.getElementById('timingFilter').value = 'sniper';
            applyFilters();
        }

        async function fetchData(manual = false) {
            const icon = document.getElementById('refreshIcon');
            if (icon) icon.classList.add('fa-spin');

            try {
                const basePath = window.location.pathname.replace(/\/(battles(\.html)?|sniper(\.html)?|index\.html)?\/?$/, '');
                const apiUrl = basePath ? `${basePath}/api/battles` : '/api/battles';
                const res = await fetch(apiUrl);
                if (!res.ok) throw new Error('Помилка сервера: ' + res.status);
                allBattles = await res.json();
                renderKPIs();
                applyFilters();
                if (manual) showToast('Дані битв успішно оновлено!');
            } catch (err) {
                console.error(err);
                if (manual) showToast('Не вдалося завантажити дані: ' + err.message);
            } finally {
                if (icon) icon.classList.remove('fa-spin');
            }
        }

        function renderKPIs() {
            document.getElementById('statTotalBattles').textContent = allBattles.length;

            const purpleBattles = allBattles.filter(b => b.roundCutoff.has_purple || b.battleCutoff.has_purple);
            document.getElementById('statPurpleBattles').textContent = purpleBattles.length;

            let lowestDmg = Infinity;
            let lowestLoc = 'Немає активних';
            let sniperCount = 0;

            allBattles.forEach(b => {
                if (b.timing && b.timing.isSniperWindow) {
                    sniperCount++;
                }
                if (b.bestPurpleMinDamage !== null && b.bestPurpleMinDamage < lowestDmg) {
                    lowestDmg = b.bestPurpleMinDamage;
                    lowestLoc = `${b.region.name} (${formatDmg(lowestDmg)} dmg)`;
                }
            });

            document.getElementById('statSniperCount').textContent = sniperCount;

            const banner = document.getElementById('sniperAlertBanner');
            if (sniperCount > 0) {
                document.getElementById('sniperAlertCount').textContent = sniperCount;
                banner.classList.remove('hidden');
            } else {
                banner.classList.add('hidden');
            }

            if (lowestDmg !== Infinity) {
                document.getElementById('statMinPurpleDmg').textContent = formatDmg(lowestDmg);
                document.getElementById('statMinPurpleLoc').textContent = lowestLoc;
            } else {
                document.getElementById('statMinPurpleDmg').textContent = '—';
                document.getElementById('statMinPurpleLoc').textContent = 'Немає фіолу';
            }
        }

        function applyFilters() {
            const search = document.getElementById('searchInput').value.toLowerCase().trim();
            const dmgFilter = document.getElementById('dmgFilter').value;
            const typeFilter = document.getElementById('typeFilter').value;
            const timingFilter = document.getElementById('timingFilter').value;
            const bountyFilter = document.getElementById('bountyFilter') ? document.getElementById('bountyFilter').value : 'all';

            const filtered = allBattles.filter(b => {
                // Search filter
                if (search) {
                    const matchReg = b.region.name.toLowerCase().includes(search);
                    const matchAtt = b.attacker.name.toLowerCase().includes(search);
                    const matchDef = b.defender.name.toLowerCase().includes(search);
                    if (!matchReg && !matchAtt && !matchDef) return false;
                }

                // Bounty / Contract filter
                if (bountyFilter === 'bounties_only' && !b.hasBounty) return false;

                // Type filter
                if (typeFilter !== 'all' && b.type !== typeFilter) return false;

                // Timing filter
                if (timingFilter === 'sniper') {
                    if (!b.timing || !b.timing.isSniperWindow) return false;
                } else if (timingFilter === 'closing_soon') {
                    if (!b.timing || b.timing.minutesLeft > 35) return false;
                }

                // Damage filter
                if (dmgFilter === 'purple_only') {
                    if (!b.roundCutoff.has_purple && !b.battleCutoff.has_purple) return false;
                } else if (dmgFilter !== 'all') {
                    const maxAllowed = parseInt(dmgFilter, 10);
                    if (b.bestPurpleMinDamage === null || b.bestPurpleMinDamage > maxAllowed) return false;
                }

                return true;
            });

            document.getElementById('filteredCount').textContent = `Показано ${filtered.length} з ${allBattles.length} битв`;
            renderBattlesList(filtered);
        }

        function renderBattlesList(battles) {
            const container = document.getElementById('battlesContainer');
            if (!battles.length) {
                container.innerHTML = `
                    <div class="glass-panel rounded-2xl p-8 text-center text-gray-400">
                        <i class="fa-solid fa-ghost text-3xl mb-2 text-gray-500"></i>
                        <p class="text-sm">Жодна битва не відповідає вибраним фільтрам.</p>
                        <p class="text-xs text-gray-500 mt-1">Спробуйте скинути фільтр часу на «Всі етапи раунду».</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = battles.map((b, idx) => {
                const rc = b.roundCutoff;
                const bc = b.battleCutoff;
                const tm = b.timing || {};

                let typeBadge = '';
                if (b.type === 'war') {
                    typeBadge = `<span class="px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 border border-red-500/20 text-[11px] font-semibold"><i class="fa-solid fa-swords mr-1"></i>Війна</span>`;
                } else if (b.type === 'tournament') {
                    typeBadge = `<span class="px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[11px] font-semibold"><i class="fa-solid fa-trophy mr-1"></i>Турнір</span>`;
                } else {
                    typeBadge = `<span class="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[11px] font-semibold"><i class="fa-solid fa-shield mr-1"></i>Повстання</span>`;
                }

                // Bounty Contract Badge
                const bountyBadge = b.hasBounty
                    ? `<span class="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[11px] font-bold flex items-center gap-1 shadow-sm"><i class="fa-solid fa-coins text-amber-400"></i>Баунті: ${b.maxBountyRate} / 1k</span>`
                    : '';

                // Timing Badge
                let timeBadge = '';
                if (tm.isSniperWindow) {
                    timeBadge = `
                        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-xs font-bold pulse-subtle">
                            <i class="fa-solid fa-bullseye"></i>
                            <span>Снайперське вікно: ${tm.formattedEta}</span>
                        </div>
                    `;
                } else if (tm.status === 'urgent') {
                    timeBadge = `
                        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40 text-xs font-bold">
                            <i class="fa-solid fa-bolt"></i>
                            <span>Фінал: ${tm.formattedEta}</span>
                        </div>
                    `;
                } else if (tm.status === 'closing_soon') {
                    timeBadge = `
                        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-500/15 text-blue-400 border border-blue-500/30 text-xs font-medium">
                            <i class="fa-regular fa-clock"></i>
                            <span>До кінця: ${tm.formattedEta}</span>
                        </div>
                    `;
                } else {
                    timeBadge = `
                        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-darkbg text-gray-400 border border-bordercolor text-xs font-medium" title="Дані попередні. Точний поріг стабілізується за 15-20 хв до кінця">
                            <i class="fa-regular fa-clock text-gray-500"></i>
                            <span>${tm.formattedEta} (попередні дані)</span>
                        </div>
                    `;
                }

                const attPts = b.attacker.roundPoints;
                const defPts = b.defender.roundPoints;
                const maxPts = b.round.pointsToWin || 300;
                const attPercent = Math.min(100, Math.round((attPts / maxPts) * 100));
                const defPercent = Math.min(100, Math.round((defPts / maxPts) * 100));

                // Round Cutoff Block
                let roundBlock = '';
                if (rc.has_purple) {
                    const isUltraCheap = rc.min_damage_for_purple < 100000;
                    const badgeClass = isUltraCheap ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300' : 'bg-cardbg border-bordercolor text-purple-300';
                    const fireTag = isUltraCheap ? `<span class="ml-1.5 px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">🔥 ТОП ЛОТ</span>` : '';

                    roundBlock = `
                        <div class="p-3 rounded-xl border ${badgeClass} space-y-1">
                            <div class="flex items-center justify-between">
                                <span class="text-[11px] uppercase tracking-wider text-gray-400 font-semibold flex items-center gap-1">
                                    <i class="fa-solid fa-bullseye text-purple-400"></i> Раунд: Поріг фіолу
                                </span>
                                ${fireTag}
                            </div>
                            <div class="flex items-baseline justify-between">
                                <span class="text-xl font-black text-white">${formatDmg(rc.min_damage_for_purple)} <span class="text-xs font-normal text-gray-400">dmg</span></span>
                                <span class="text-xs font-medium text-purple-400">Ранг #${rc.cutoff_rank}</span>
                            </div>
                            <div class="flex items-center justify-between text-xs text-gray-400 pt-1 border-t border-bordercolor/50">
                                <span class="truncate font-medium text-gray-300">🎁 ${rc.last_purple_item.name}</span>
                                <span class="truncate text-gray-400">👤 ${rc.last_purple_player.username}</span>
                            </div>
                            <div class="text-[10px] text-gray-400 pt-0.5">
                                В пулі: <strong class="text-purple-400">${rc.total_purple_plus_items}</strong> фіол/кращих речей &bull; Запас: <span class="text-gray-300">+${formatDmg(rc.gap_to_next)}</span>
                            </div>
                        </div>
                    `;
                } else {
                    roundBlock = `
                        <div class="p-3 rounded-xl border border-bordercolor/40 bg-darkbg/40 text-gray-500 flex flex-col justify-center items-center h-full min-h-[90px]">
                            <span class="text-xs">В поточному раунді ще немає фіолу</span>
                            <span class="text-[10px] text-gray-600">Потрібно більше загального дамагу</span>
                        </div>
                    `;
                }

                // Battle Cutoff Block
                let battleBlock = '';
                if (bc.has_purple) {
                    battleBlock = `
                        <div class="p-3 rounded-xl border border-bordercolor bg-cardbg space-y-1">
                            <div class="flex items-center justify-between">
                                <span class="text-[11px] uppercase tracking-wider text-gray-400 font-semibold flex items-center gap-1">
                                    <i class="fa-solid fa-trophy text-amber-400"></i> Битва: Поріг фіолу
                                </span>
                                <span class="text-xs font-medium text-amber-400">Ранг #${bc.cutoff_rank}</span>
                            </div>
                            <div class="flex items-baseline justify-between">
                                <span class="text-xl font-black text-white">${formatDmg(bc.min_damage_for_purple)} <span class="text-xs font-normal text-gray-400">dmg</span></span>
                                <span class="text-xs text-gray-400">по всій битві</span>
                            </div>
                            <div class="flex items-center justify-between text-xs text-gray-400 pt-1 border-t border-bordercolor/50">
                                <span class="truncate font-medium text-gray-300">🎁 ${bc.last_purple_item.name}</span>
                                <span class="truncate text-gray-400">👤 ${bc.last_purple_player.username}</span>
                            </div>
                            <div class="text-[10px] text-gray-400 pt-0.5">
                                В пулі битви: <strong class="text-amber-400">${bc.total_purple_plus_items}</strong> топових речей
                            </div>
                        </div>
                    `;
                } else {
                    battleBlock = `
                        <div class="p-3 rounded-xl border border-bordercolor/40 bg-darkbg/40 text-gray-500 flex flex-col justify-center items-center h-full min-h-[90px]">
                            <span class="text-xs">В заліку битви ще немає фіолу</span>
                        </div>
                    `;
                }

                return `
                    <div class="glass-panel rounded-2xl p-4 sm:p-5 hover:border-purple-500/40 transition duration-200">
                        <!-- Card Header -->
                        <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-bordercolor">
                            <div class="flex items-center gap-2.5">
                                <h3 class="text-base font-bold text-white flex items-center gap-2">
                                    <span>${b.region.name}</span>
                                </h3>
                                ${typeBadge}
                                ${bountyBadge}
                                <span class="text-xs text-gray-400 font-medium">Раунд #${b.round.number}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                ${timeBadge}
                                <button onclick="openModal('${b.battleId}', 'round')" class="px-2.5 py-1 rounded-lg bg-darkbg hover:bg-hoverbg border border-bordercolor text-xs text-gray-300 hover:text-white transition flex items-center gap-1.5">
                                    <i class="fa-solid fa-list-ol text-purple-400"></i> Рейтинг
                                </button>
                                <a href="${b.wareraUrl}" target="_blank" class="px-3 py-1 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-600/30 transition flex items-center gap-1.5">
                                    <i class="fa-solid fa-arrow-up-right-from-square"></i> На WarEra
                                </a>
                            </div>
                        </div>

                        <!-- Card Body -->
                        <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 pt-4">
                            <!-- Left: Combatants & Progress (5 cols) -->
                            <div class="lg:col-span-5 space-y-3">
                                <!-- Attacker vs Defender -->
                                <div>
                                    <div class="flex items-center justify-between text-xs font-semibold">
                                        <div class="flex items-center gap-1.5 text-red-400">
                                            <i class="fa-solid fa-sword"></i>
                                            <span>${b.attacker.name}</span>
                                        </div>
                                        <div class="text-gray-400 font-mono text-sm">
                                            <span class="${attPts > defPts ? 'text-emerald-400 font-bold' : 'text-gray-300'}">${attPts}</span> : <span class="${defPts > attPts ? 'text-emerald-400 font-bold' : 'text-gray-300'}">${defPts}</span>
                                            <span class="text-xs font-normal text-gray-500">/ 300</span>
                                        </div>
                                        <div class="flex items-center gap-1.5 text-blue-400">
                                            <span>${b.defender.name}</span>
                                            <i class="fa-solid fa-shield"></i>
                                        </div>
                                    </div>
                                    ${b.hasBounty ? `
                                        <div class="flex items-center justify-between pt-1">
                                            <div>${b.attacker.bounty ? `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-bold"><i class="fa-solid fa-coins text-[9px] text-amber-400"></i> ${b.attacker.bounty.ratePer1k} / 1k <span class="text-gray-400 font-normal">(${b.attacker.bounty.pool}g)</span></span>` : ''}</div>
                                            <div>${b.defender.bounty ? `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-bold"><i class="fa-solid fa-coins text-[9px] text-amber-400"></i> ${b.defender.bounty.ratePer1k} / 1k <span class="text-gray-400 font-normal">(${b.defender.bounty.pool}g)</span></span>` : ''}</div>
                                        </div>
                                    ` : ''}
                                </div>

                                <!-- Dual Progress Bar -->
                                <div class="w-full h-2.5 bg-darkbg rounded-full overflow-hidden flex border border-bordercolor">
                                    <div class="bg-red-500 transition-all duration-300" style="width: ${attPercent}%"></div>
                                    <div class="flex-1 bg-transparent"></div>
                                    <div class="bg-blue-500 transition-all duration-300" style="width: ${defPercent}%"></div>
                                </div>

                                <div class="flex items-center justify-between text-[11px] text-gray-400">
                                    <span>У раунді: <strong class="text-gray-200">${formatDmg(b.round.totalDamage)} dmg</strong></span>
                                    <span>Тік: <strong>#${b.round.currentTick || '—'}</strong></span>
                                </div>
                            </div>

                            <!-- Right: Cutoff Cards (7 cols) -->
                            <div class="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-3">
                                ${roundBlock}
                                ${battleBlock}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function openModal(battleId, scope) {
            const b = allBattles.find(x => x.battleId === battleId);
            if (!b) return;

            const cutoffData = scope === 'round' ? b.roundCutoff : b.battleCutoff;
            const title = scope === 'round' ? `Раунд #${b.round.number} — ${b.region.name}` : `Битва — ${b.region.name}`;

            document.getElementById('modalTitle').textContent = `⚔️ ${title}`;
            document.getElementById('modalSubtitle').textContent = `Повний розподіл дропу серед топ гравців (всього учасників з дамагом: ${cutoffData.ranks_count})`;

            const list = cutoffData.full_ranks || [];
            const listEl = document.getElementById('modalRanksList');

            if (!list.length) {
                listEl.innerHTML = `<p class="text-sm text-gray-500 text-center py-6">Дані про ранг відсутні</p>`;
            } else {
                listEl.innerHTML = list.map(r => {
                    const isPurple = r.item_info.is_purple_plus;
                    const badgeClass = isPurple ? 'item-badge-epic' : (r.item_info.tier === 3 ? 'item-badge-rare' : (r.item_info.tier === 2 ? 'item-badge-uncommon' : 'item-badge-none'));
                    const isCutoff = r.rank === cutoffData.cutoff_rank;
                    const borderStyle = isCutoff ? 'border-2 border-purple-500 bg-purple-950/20' : 'border border-bordercolor bg-darkbg';

                    return `
                        <div class="p-2.5 rounded-xl ${borderStyle} flex items-center justify-between gap-3 text-xs">
                            <div class="flex items-center gap-2.5 min-w-0">
                                <span class="w-6 text-center font-bold text-gray-400">#${r.rank}</span>
                                <div>
                                    <div class="font-semibold text-white truncate">${r.user_id ? r.user_id.slice(0, 8) + '...' : 'Unknown'}</div>
                                    <div class="text-[11px] text-gray-400">${formatDmg(r.damage)} dmg</div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                ${isCutoff ? '<span class="px-1.5 py-0.5 rounded bg-purple-500 text-white font-bold text-[10px]">ПОРІГ</span>' : ''}
                                <span class="px-2 py-1 rounded-lg ${badgeClass} text-xs font-semibold whitespace-nowrap">
                                    🎁 ${r.item_info.name}
                                </span>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            document.getElementById('rankingModal').classList.remove('hidden');
        }

        function closeModal() {
            document.getElementById('rankingModal').classList.add('hidden');
        }

        window.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });
        document.getElementById('rankingModal').addEventListener('click', e => {
            if (e.target === document.getElementById('rankingModal')) closeModal();
        });

        window.addEventListener('DOMContentLoaded', () => {
            fetchData();
            autoRefreshTimer = setInterval(() => {
                if (document.visibilityState === 'visible') {
                    fetchData(false);
                }
            }, 30000);
        });
    

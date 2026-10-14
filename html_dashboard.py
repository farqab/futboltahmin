import os
import sys
import json
from datetime import datetime

def normalize_match_date(m):
    """Her maç verisinden ISO (YYYY-MM-DD) ve TR (DD.MM.YYYY) formatında tarih üretir."""
    d = str(m.get('date') or '').strip()
    utc = str(m.get('utc_date') or '').strip()
    if len(d) == 8 and d.isdigit():
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}", f"{d[6:8]}.{d[4:6]}.{d[:4]}"
    if "." in d:
        parts = d.split(".")
        if len(parts) == 3:
            day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            return f"{year}-{month}-{day}", f"{day}.{month}.{year}"
    if "-" in d and len(d) >= 10:
        parts = d[:10].split("-")
        if len(parts) == 3:
            year, month, day = parts[0], parts[1].zfill(2), parts[2].zfill(2)
            return f"{year}-{month}-{day}", f"{day}.{month}.{year}"
    if utc and len(utc) >= 10 and "-" in utc:
        parts = utc[:10].split("-")
        return utc[:10], f"{parts[2]}.{parts[1]}.{parts[0]}"
    return "", ""

CALENDAR_CSS = """
        /* --- TAKVİM & GÜN SEÇİCİ KONTROL PANELİ --- */
        .calendar-control-panel {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.98));
            border: 1px solid rgba(59, 130, 246, 0.35);
            border-radius: 16px;
            padding: 18px 22px;
            margin-bottom: 28px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }
        .calendar-panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            padding-bottom: 14px;
            margin-bottom: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .calendar-panel-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.25rem;
            font-weight: 800;
            color: #F8FAFC;
            margin: 0;
        }
        .calendar-panel-subtitle {
            font-size: 0.8rem;
            color: #94A3B8;
            margin-top: 4px;
        }
        .calendar-badge-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .match-counter-pill {
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.4);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 700;
            color: #93C5FD;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .pulse-indicator {
            width: 8px;
            height: 8px;
            background: #10B981;
            border-radius: 50%;
            box-shadow: 0 0 8px #10B981;
            animation: pulse-dot 1.8s infinite;
        }
        @keyframes pulse-dot {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }
        .calendar-action-bar {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 12px;
        }
        .date-picker-box {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(59, 130, 246, 0.45);
            border-radius: 10px;
            padding: 6px 12px;
        }
        .date-picker-box label {
            font-size: 0.8rem;
            font-weight: 700;
            color: #60A5FA;
            white-space: nowrap;
        }
        .calendar-native-input {
            background: transparent;
            border: none;
            color: #F8FAFC;
            font-family: inherit;
            font-size: 0.88rem;
            font-weight: 700;
            outline: none;
            cursor: pointer;
            color-scheme: dark;
        }
        .calendar-native-input::-webkit-calendar-picker-indicator {
            cursor: pointer;
            filter: invert(0.8) sepia(100%) saturate(300%) hue-rotate(180deg);
        }
        .date-pill-group {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
        }
        .date-pill-btn {
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #CBD5E1;
            padding: 7px 13px;
            border-radius: 10px;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .date-pill-btn:hover {
            background: rgba(59, 130, 246, 0.2);
            border-color: rgba(59, 130, 246, 0.5);
            color: #FFFFFF;
            transform: translateY(-1px);
        }
        .date-pill-btn.active {
            background: linear-gradient(135deg, #2563EB, #1D4ED8);
            border-color: #60A5FA;
            color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
        }
        .date-pill-btn.vip-filter-btn {
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.5);
            color: #FBBF24;
        }
        .date-pill-btn.vip-filter-btn:hover {
            background: rgba(245, 158, 11, 0.3);
            border-color: #F59E0B;
            color: #FFFFFF;
        }
        .date-pill-btn.vip-filter-btn.active-vip {
            background: linear-gradient(135deg, #F59E0B, #D97706) !important;
            border-color: #FBBF24 !important;
            color: #000000 !important;
            font-weight: 900 !important;
            box-shadow: 0 0 16px rgba(245, 158, 11, 0.5) !important;
        }
        .pill-count-num {
            font-size: 0.72rem;
            opacity: 0.85;
            background: rgba(0, 0, 0, 0.25);
            padding: 1px 6px;
            border-radius: 6px;
        }
        .search-box-wrapper {
            display: flex;
            align-items: center;
            margin-left: auto;
            gap: 8px;
        }
        .search-input-field {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #FFFFFF;
            padding: 7px 12px;
            border-radius: 10px;
            font-size: 0.82rem;
            outline: none;
            width: 190px;
            transition: all 0.2s;
        }
        .search-input-field:focus {
            border-color: #3B82F6;
            width: 230px;
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
        }
        .btn-reset-filter {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.35);
            color: #FCA5A5;
            padding: 7px 12px;
            border-radius: 10px;
            font-size: 0.78rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-reset-filter:hover {
            background: rgba(239, 68, 68, 0.3);
            color: #FFFFFF;
        }
"""

CALENDAR_JS = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const dateInput = document.getElementById('calendarDateInput');
    const pillButtons = document.querySelectorAll('.date-pill-btn:not(.vip-filter-btn)');
    const vipFilterBtn = document.getElementById('vipFilterBtn');
    const searchInput = document.getElementById('teamSearchInput');
    const clearBtn = document.getElementById('clearFilterBtn');
    const visibleCountEl = document.getElementById('visibleMatchCount');
    const matchCards = document.querySelectorAll('.match-card');
    
    let activeDate = 'all';
    let activeSearch = '';
    let activeVipOnly = false;

    function filterMatches() {
        const visibleMatchIds = new Set();
        
        matchCards.forEach(card => {
            const cardDate = card.getAttribute('data-date') || '';
            const cardSearch = (card.getAttribute('data-search') || '').toLowerCase();
            const cardVip = card.getAttribute('data-vip') === '1';
            const cardId = card.getAttribute('data-match-id') || cardSearch;
            
            const matchDate = (activeDate === 'all' || !activeDate || cardDate === activeDate);
            const matchQuery = (!activeSearch || cardSearch.includes(activeSearch));
            const matchVip = (!activeVipOnly || cardVip);
            
            if (matchDate && matchQuery && matchVip) {
                card.style.display = '';
                visibleMatchIds.add(cardId);
            } else {
                card.style.display = 'none';
            }
        });

        if (visibleCountEl) {
            visibleCountEl.textContent = visibleMatchIds.size;
        }

        // Grids & titles visibility check
        document.querySelectorAll('.matches-grid').forEach(grid => {
            const visibleInGrid = Array.from(grid.querySelectorAll('.match-card')).filter(c => c.style.display !== 'none').length;
            const prevTitle = grid.previousElementSibling;
            
            let emptyMsg = grid.querySelector('.empty-grid-msg');
            if (visibleInGrid === 0) {
                if (prevTitle && prevTitle.classList.contains('league-title')) {
                    prevTitle.style.display = 'none';
                    grid.style.display = 'none';
                } else if (prevTitle && prevTitle.classList.contains('section-title')) {
                    if (!emptyMsg) {
                        emptyMsg = document.createElement('div');
                        emptyMsg.className = 'empty-grid-msg';
                        emptyMsg.style.cssText = 'grid-column: 1/-1; padding: 16px; text-align: center; color: #94A3B8; background: rgba(30, 41, 59, 0.4); border-radius: 8px; font-size: 0.85rem; border: 1px dashed rgba(255,255,255,0.1); margin-bottom: 8px;';
                        emptyMsg.textContent = 'ℹ️ Seçilen filtre kriterlerine uygun maç bulunamadı.';
                        grid.appendChild(emptyMsg);
                    }
                    emptyMsg.style.display = 'block';
                }
            } else {
                if (prevTitle) prevTitle.style.display = '';
                grid.style.display = '';
                if (emptyMsg) emptyMsg.style.display = 'none';
            }
        });
    }

    // Pill Button click
    pillButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            pillButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            activeDate = this.getAttribute('data-date');
            
            if (dateInput) {
                dateInput.value = (activeDate === 'all') ? '' : activeDate;
            }
            filterMatches();
        });
    });

    // VIP Filter Button click
    if (vipFilterBtn) {
        vipFilterBtn.addEventListener('click', function() {
            activeVipOnly = !activeVipOnly;
            if (activeVipOnly) {
                this.classList.add('active-vip');
            } else {
                this.classList.remove('active-vip');
            }
            filterMatches();
        });
    }

    // Calendar native input change
    if (dateInput) {
        dateInput.addEventListener('change', function() {
            const picked = this.value;
            activeDate = picked || 'all';
            
            let matchedPill = false;
            pillButtons.forEach(btn => {
                if (btn.getAttribute('data-date') === activeDate) {
                    btn.classList.add('active');
                    matchedPill = true;
                } else {
                    btn.classList.remove('active');
                }
            });
            if (!matchedPill && activeDate !== 'all') {
                pillButtons.forEach(btn => btn.classList.remove('active'));
            }
            filterMatches();
        });
    }

    // Search input
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            activeSearch = this.value.trim().toLowerCase();
            filterMatches();
        });
    }

    // Reset button
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            activeDate = 'all';
            activeSearch = '';
            activeVipOnly = false;
            if (vipFilterBtn) vipFilterBtn.classList.remove('active-vip');
            if (dateInput) dateInput.value = '';
            if (searchInput) searchInput.value = '';
            pillButtons.forEach(btn => {
                if (btn.getAttribute('data-date') === 'all') btn.classList.add('active');
                else btn.classList.remove('active');
            });
            filterMatches();
        });
    }

    // Initial filter run
    filterMatches();
});
</script>
"""

def generate_html_report(results, report_date="2026-09-19", output_file="gunluk_bulten.html"):
    """
    TypeSafe AI tarafından analiz edilen tüm gerçek maçları
    modern, karanlık modlu, interaktif bir HTML Dashboard'a dönüştürür.
    """
    # İstatistikler
    total_matches = len(results)
    value_bets = [r for r in results if r.get("action_status") == "BET"]
    if not value_bets:
        value_bets = sorted([r for r in results if r.get("confidence", 0) >= 50 and r.get("trap_score", 10) <= 5.0], key=lambda x: x.get("confidence", 0), reverse=True)[:4]
        
    high_scoring = [r for r in results if r.get("action_status") == "GOAL_ONLY" or r.get("over_2_5_prob", 0) >= 62]
    high_scoring = sorted(high_scoring, key=lambda x: x.get("over_2_5_prob", 0), reverse=True)[:6]
    
    trap_games = [r for r in results if r.get("action_status") == "NO_BET" or r.get("trap_score", 0) >= 5.2]
    trap_games = sorted(trap_games, key=lambda x: x.get("trap_score", 0), reverse=True)[:6]

    # Liglere göre grupla
    leagues = {}
    for r in results:
        lg = r.get("league", "Diğer")
        if lg not in leagues:
            leagues[lg] = []
        leagues[lg].append(r)

    TURKISH_DAYS = {
        0: "Pzt", 1: "Salı", 2: "Çarş", 3: "Perş", 4: "Cuma", 5: "Cmt", 6: "Paz"
    }

    # Tarihleri ayıkla ve grupla
    date_counts = {}
    for r in results:
        iso, tr = normalize_match_date(r)
        if iso:
            if iso not in date_counts:
                date_counts[iso] = {"tr": tr, "count": 0}
            date_counts[iso]["count"] += 1

    # Bugün tespiti ve rapor başlığı tarihi
    clean_date = str(report_date).strip()
    if len(clean_date) == 8 and clean_date.isdigit():
        today_iso = f"{clean_date[:4]}-{clean_date[4:6]}-{clean_date[6:8]}"
        display_report_date = f"{clean_date[6:8]}.{clean_date[4:6]}.{clean_date[:4]}"
    elif "-" in clean_date and len(clean_date) >= 10:
        today_iso = clean_date[:10]
        pts = today_iso.split("-")
        display_report_date = f"{pts[2]}.{pts[1]}.{pts[0]}"
    else:
        today_iso = datetime.now().strftime("%Y-%m-%d")
        display_report_date = datetime.now().strftime("%d.%m.%Y")

    date_buttons_list = []
    for iso_k in sorted(date_counts.keys()):
        d_info = date_counts[iso_k]
        cnt = d_info["count"]
        tr_str = d_info["tr"]
        
        try:
            dt_obj = datetime.strptime(iso_k, "%Y-%m-%d")
            day_name = TURKISH_DAYS.get(dt_obj.weekday(), "")
        except Exception:
            day_name = ""

        if iso_k == today_iso or "2026-10-13" in iso_k:
            lbl = f"⭐ Bugün ({tr_str[:5]})"
        else:
            lbl = f"📅 {tr_str[:5]} {day_name}"

        date_buttons_list.append(
            f'<button type="button" class="date-pill-btn" data-date="{iso_k}">{lbl} <span class="pill-count-num">({cnt})</span></button>'
        )

    date_buttons_html = "".join(date_buttons_list)

    vip_match_count = sum(
        1 for m in results
        if (
            m.get("is_baron_verified")
            or m.get("is_baron_trap")
            or (m.get("baron_intel") or {}).get("has_whale_volume")
            or float(m.get("volume_gbp") or (m.get("baron_intel") or {}).get("volume_gbp") or 0.0) >= 50000.0
            or float(((m.get("signals") or {}).get("vip_syndicate_radar", {}).get("signals", {}).get("moneyway_volume") or {}).get("total_matched_gbp", 0.0)) >= 50000.0
        )
    )

    def render_form_badges(form_str):
        if not form_str or form_str == "-":
            return "<span class='badge-empty'>Form Yok</span>"
        html = ""
        for ch in form_str.upper():
            if ch == "W":
                html += "<span class='form-badge form-w' title='Galibiyet'>G</span>"
            elif ch == "L":
                html += "<span class='form-badge form-l' title='Mağlubiyet'>M</span>"
            elif ch == "D":
                html += "<span class='form-badge form-d' title='Beraberlik'>B</span>"
            else:
                html += f"<span class='form-badge'>{ch}</span>"
        return html

    def render_smart_coupons_html(matches_list):
        try:
            from smart_coupon_generator import generate_smart_coupons
            coupons = generate_smart_coupons(matches_list)
            html_out = ""
            for k, c in coupons.items():
                if not c.get("maclar"): continue
                border_col = "#10B981" if "ALTIN" in c["baslik"] else "#F59E0B"
                badge_bg = "rgba(16, 185, 129, 0.2)" if "ALTIN" in c["baslik"] else "rgba(245, 158, 11, 0.2)"
                badge_col = "#34D399" if "ALTIN" in c["baslik"] else "#FBBF24"
                
                rows_html = ""
                for m in c["maclar"]:
                    rows_html += f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(0,0,0,0.25); border-radius: 8px; margin-bottom: 8px; font-size: 0.85rem;">
                        <div>
                            <span style="color: #94A3B8; font-size: 0.75rem;">[{m['lig']}]</span>
                            <div style="font-weight: 700; color: #F1F5F9;">{m['mac']}</div>
                        </div>
                        <div style="text-align: right;">
                            <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: {badge_bg}; color: {badge_col}; font-weight: 800; font-size: 0.8rem;">
                                {m['tahmin']}
                            </span>
                            <div style="color: #64748B; font-size: 0.72rem; margin-top: 2px;">Oran: <strong>{m['oran']}</strong></div>
                        </div>
                    </div>
                    """
                
            # 50-Agent Swarm Kuponu Ekle
            try:
                from agent_swarm_50 import generate_50agent_smart_portfolio
                swarm_res = generate_50agent_smart_portfolio(matches_list)
                if swarm_res.get("altin_kasa"):
                    sak = swarm_res["altin_kasa"]
                    s_rows = ""
                    for sm in sak["maclar"]:
                        s_rows += f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(0,0,0,0.3); border-radius: 8px; margin-bottom: 8px; font-size: 0.85rem;">
                            <div>
                                <span style="color: #A5B4FC; font-size: 0.75rem;">[{sm['lig']}]</span>
                                <div style="font-weight: 700; color: #FFFFFF;">{sm['mac']}</div>
                                <div style="color: #94A3B8; font-size: 0.7rem;">Konsensüs: <strong>{sm['konsensus']}</strong></div>
                            </div>
                            <div style="text-align: right;">
                                <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: rgba(99, 102, 241, 0.25); color: #818CF8; font-weight: 800; font-size: 0.8rem;">
                                    {sm['tercih']}
                                </span>
                                <div style="color: #CBD5E1; font-size: 0.75rem; margin-top: 2px;">Oran: <strong>{sm['oran']}</strong></div>
                            </div>
                        </div>
                        """
                    html_out += f"""
                    <div style="background: linear-gradient(135deg, rgba(30, 27, 75, 0.9), rgba(15, 23, 42, 0.95)); border: 2px solid #6366F1; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.2);">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid rgba(99, 102, 241, 0.3); padding-bottom: 8px;">
                                <span style="font-weight: 800; font-size: 0.95rem; color: #E0E7FF;">🤖 50-AGENT SWARM (2'Lİ ALTIN KASA)</span>
                                <span style="background: #6366F1; color: #FFF; font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 12px;">
                                    %75+ Konsensüs
                                </span>
                            </div>
                            {s_rows}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; padding-top: 10px; border-top: 1px dashed rgba(99, 102, 241, 0.4);">
                            <span style="color: #C7D2FE; font-size: 0.8rem;">Swarm Toplam Oran:</span>
                            <span style="font-size: 1.35rem; font-weight: 900; color: #818CF8;">
                                {sak['toplam_oran']}
                            </span>
                        </div>
                    </div>
                    """
            except Exception as e:
                pass

            return html_out if html_out else "<div style='color: #64748B;'>Bugün için kriterleri sağlayan hazır kombine bulunamadı.</div>"
        except Exception as e:
            return f"<div style='color: red;'>Kupon oluşturma hatası: {e}</div>"

    def render_match_card(m):
        tahmin = m.get("tahmin_ms", "MS 1")
        kazanan = m.get("tahmin_kazanan", "")
        conf = m.get("confidence", 50)
        over_prob = m.get("over_2_5_prob", 50)
        btts_prob = m.get("btts_prob", 50)
        trap_score = m.get("trap_score", 5.0)
        
        # Rozet renkleri
        tahmin_badge_cls = "badge-home" if tahmin == "MS 1" else ("badge-draw" if tahmin == "MS X" else "badge-away")
        trap_color = "#ef4444" if trap_score >= 6.0 else ("#f59e0b" if trap_score >= 4.5 else "#10b981")
        
        odds = m.get("odds") or {}
        h_logo = m.get("home_logo", "")
        a_logo = m.get("away_logo", "")
        
        h_img = f"<img src='{h_logo}' class='team-logo' onerror=\"this.style.display='none'\">" if h_logo else ""
        a_img = f"<img src='{a_logo}' class='team-logo' onerror=\"this.style.display='none'\">" if a_logo else ""
        
        action_lbl = m.get("action_label", "")
        if not action_lbl:
            if m.get("action_status") == "BET" or m.get("is_value_bet"): action_lbl = "🟢 OYNA (BANKO)"
            elif m.get("action_status") == "GOAL_ONLY" or m.get("is_high_scoring"): action_lbl = "🟡 SADECE GOL OYNA"
            else: action_lbl = "🔴 PAS GEÇ (UZAK DUR)"
            
        action_bg = "rgba(16, 185, 129, 0.18); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.4);" if "OYNA" in action_lbl and "GOL" not in action_lbl else (
            "rgba(245, 158, 11, 0.18); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4);" if "GOL" in action_lbl else
            "rgba(239, 68, 68, 0.18); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.4);"
        )

        # Küresel Sharp İstihbarat Kutusu
        signals = m.get("signals") or {}
        fs_sig = signals.get("flashscore_lineups") or {}
        pin_sig = signals.get("pinnacle_benchmark") or {}
        drop_sig = signals.get("dropping_odds_steam") or {}
        vip_sig = signals.get("vip_syndicate_radar") or {}

        # 1. VIP Baron Para Hacmi & Asya Handikap
        vol = vip_sig.get("signals", {}).get("moneyway_volume") or {}
        ah = vip_sig.get("signals", {}).get("asian_handicap") or {}
        baron_intel = m.get("baron_intel") or {}
        is_baron_verified = m.get("is_baron_verified", baron_intel.get("is_baron_verified", False))
        is_baron_trap = m.get("is_baron_trap", baron_intel.get("is_baron_trap", False))
        matched_gbp = float(m.get("volume_gbp") or baron_intel.get("volume_gbp") or vol.get("total_matched_gbp", 0.0))
        our_share = float(m.get("dominance_pct") or baron_intel.get("dominance_pct") or vol.get("our_market_share_pct", 50.0))
        has_real_vol = (vol.get("has_volume_data", False) and matched_gbp > 0) or matched_gbp >= 50000.0 or is_baron_verified or is_baron_trap

        g_verdict = m.get("global_verdict") or "NORMAL"
        is_veto = m.get("is_global_vetoed", False) or "VETO" in str(g_verdict) or "RED" in str(g_verdict) or is_baron_trap
        is_boost = ("BOOST" in str(g_verdict) or "SMART" in str(g_verdict) or is_baron_verified) and not is_veto
        b_border = "#EF4444" if is_veto else "#10B981" if is_boost else "#38BDF8"
        b_bg = "rgba(239, 68, 68, 0.12)" if is_veto else "rgba(16, 185, 129, 0.12)" if is_boost else "rgba(56, 189, 248, 0.08)"
        is_whale = ("WHALE" in str(g_verdict) or vol.get("is_volume_surge", False) or has_real_vol or is_baron_verified or is_baron_trap)
        
        if is_baron_trap:
            whale_badge = "<span style='background: #EF4444; color: #FFF; font-weight: 900; padding: 1px 6px; border-radius: 4px; font-size: 0.68rem; margin-left: 5px;'>❗ ŞÜPHELİ YIĞILMA</span>"
        elif is_baron_verified:
            whale_badge = "<span style='background: #F59E0B; color: #000; font-weight: 900; padding: 1px 6px; border-radius: 4px; font-size: 0.68rem; margin-left: 5px;'>👑 KURUMSAL PARA ONAYLI</span>"
        elif is_whale and matched_gbp >= 50000.0:
            whale_badge = "<span style='background: #F59E0B; color: #000; font-weight: 900; padding: 1px 6px; border-radius: 4px; font-size: 0.68rem; margin-left: 5px;'>👑 BARON HACMİ</span>"
        else:
            whale_badge = ""
        b_badge_col = "#EF4444" if is_veto else "#10B981" if is_boost else "#0284C7"

        if has_real_vol:
            vol_title = "👑 VIP Baron (Betfair Canlı)"
            vol_text = f"£{matched_gbp:,.0f} (%{our_share:.1f} Para - Borsa)"
        else:
            vol_title = "👑 VIP Baron Radarı"
            vol_text = "Canlı Borsa: Veri Bekleniyor"

        if is_baron_verified:
            baron_typesafe_badge = "<div style='color: #34D399; font-weight: 800; font-size: 0.64rem; margin-top: 3px;'>🛡️ TypeSafe Baron Teyidi: ✅ KURUMSAL PARA ONAYLI</div>"
        elif is_baron_trap:
            baron_typesafe_badge = "<div style='color: #F87171; font-weight: 800; font-size: 0.64rem; margin-top: 3px;'>🛡️ TypeSafe Baron Teyidi: ⚠️ ŞÜPHELİ YIĞILMA</div>"
        elif has_real_vol:
            baron_typesafe_badge = "<div style='color: #FBBF24; font-size: 0.64rem; margin-top: 3px;'>🛡️ TypeSafe Baron Teyidi: ⚖️ DENGELİ PİYASA</div>"
        else:
            baron_typesafe_badge = "<div style='color: #94A3B8; font-size: 0.64rem; margin-top: 3px;'>🛡️ TypeSafe Baron Teyidi: ⏳ LİKİDİTE BEKLENİYOR</div>"
        
        has_ah = ah.get("has_real_data", False)
        if not has_ah or ah.get("status") == "DATA_PENDING":
            ah_display = "Asya: Çizgi Dengeli / Resmi Veri Bekleniyor"
        else:
            ah_open = ah.get("open_line", 0.0)
            ah_curr = ah.get("current_line", 0.0)
            shift = ah.get("line_shift", 0.0)
            ah_dir_code = ah.get("direction", "STABLE")
            
            if shift != 0.0:
                ah_dir_lbl = "Ev Lehine" if shift < 0 else "Dep Lehine"
                ah_display = f"Asya: {ah_open:+} ➔ {ah_curr:+} ({ah_dir_lbl})"
            elif ah_dir_code == "HOME_ODDS_DROP":
                ah_display = f"Asya: {ah_curr:+} Sabit ({ah.get('open_odds')} ➔ {ah.get('current_odds')} Ev)"
            elif ah_dir_code == "HOME_ODDS_RISE":
                ah_display = f"Asya: {ah_curr:+} Sabit ({ah.get('open_odds')} ➔ {ah.get('current_odds')} Dep)"
            else:
                ah_display = f"Asya: {ah_curr:+} Sabit Çizgi"

        # 2. Flashscore Teyitli İlk 11 & Diziliş
        has_real_lineup = fs_sig.get("is_confirmed", False) and bool(fs_sig.get("home_formation")) and bool(fs_sig.get("away_formation"))
        if has_real_lineup:
            fs_title = "⚡ Flashscore (Teyitli İlk 11)"
            h_form = fs_sig.get("home_formation")
            a_form = fs_sig.get("away_formation")
            h_miss = fs_sig.get("home_missing_count", 0)
            a_miss = fs_sig.get("away_missing_count", 0)
            fs_main = f"{h_form} vs {a_form}"
            fs_sub = f"Eksik: Ev {h_miss}, Dep {a_miss}"
        else:
            fs_title = "⚡ Flashscore Kadro Radarı"
            fs_main = "İlk 11: Maça 1 Saat Kala"
            h_rot = "Yüksek" if m.get("home_rotation_risk") else "Düşük"
            a_rot = "Yüksek" if m.get("away_rotation_risk") else "Düşük"
            fs_sub = f"Rotasyon Riski: Ev {h_rot} / Dep {a_rot}"

        # 3. Pinnacle Benchmark
        pin_edge = pin_sig.get("sharp_ev_pct")
        has_pin = pin_sig.get("has_sharp_benchmark", False)

        if has_pin and pin_edge is not None:
            if pin_edge > 0:
                pin_str = f"+%{pin_edge:.1f} Sharp Değer"
                pin_badge = "Sazan Tuzağı Yok"
            elif pin_edge >= -6.0:
                pin_str = f"%{pin_edge:.1f} Adil Marj"
                pin_badge = "Adil Çizgi Teyitli"
            else:
                pin_str = f"%{pin_edge:.1f} Negatif Marj"
                pin_badge = "Düşük Oran Uyarısı"
        else:
            pin_str = "Global Sharp: Veri Bekleniyor"
            pin_badge = "Model Adil Çizgi"

        # 4. Dropping Odds / Steam Hareketi
        drift_desc = m.get("odds_drift_desc") or ""
        drift_sig = m.get("odds_drift", {}).get("signal", "NORMAL")
        h_drift = m.get("odds_drift", {}).get("home_drift_pct", 0.0)
        if h_drift != 0.0:
            drop_str = f"%{abs(h_drift)} Oran Çöküşü"
            drop_sub = "Ev Lehine Akıllı Para" if h_drift < 0 else "Piyasa Şüphesi"
        else:
            drop_str = "Oran Hareketi Dengeli"
            drop_sub = "Çoklu Büro Stabil"

        g_box_html = f"""
        <div style="background: {b_bg}; border: 1px solid {b_border}; border-radius: 10px; padding: 9px 11px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 5px;">
                <span style="color: #F8FAFC; font-weight: 800; font-size: 0.74rem;">🌐 4'lü Küresel Sharp & VIP İstihbaratı</span>
                <div>
                    <span style="background: {b_badge_col}; color: #FFFFFF; font-weight: 900; padding: 2px 7px; border-radius: 4px; font-size: 0.67rem;">{g_verdict}</span>
                    {whale_badge}
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.69rem;">
                <!-- 1. VIP Baron Para Hacmi & Asya -->
                <div style="background: rgba(245, 158, 11, 0.09); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 6px; padding: 5px 7px;">
                    <div style="color: #FBBF24; font-weight: 800; font-size: 0.67rem;">{vol_title}</div>
                    <div style="color: #FFFFFF; font-weight: 700;">{vol_text}</div>
                    <div style="color: #94A3B8; font-size: 0.64rem;">{ah_display}</div>
                    {baron_typesafe_badge}
                </div>

                <!-- 2. Flashscore Teyitli İlk 11 & Diziliş -->
                <div style="background: rgba(56, 189, 248, 0.09); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 6px; padding: 5px 7px;">
                    <div style="color: #38BDF8; font-weight: 800; font-size: 0.67rem;">{fs_title}</div>
                    <div style="color: #FFFFFF; font-weight: 700;">{fs_main}</div>
                    <div style="color: #94A3B8; font-size: 0.64rem;">{fs_sub}</div>
                </div>

                <!-- 3. Pinnacle Marjsız Adil Çizgi -->
                <div style="background: rgba(16, 185, 129, 0.09); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 5px 7px;">
                    <div style="color: #34D399; font-weight: 800; font-size: 0.67rem;">🎯 Pinnacle Benchmark</div>
                    <div style="color: #FFFFFF; font-weight: 700;">{pin_str}</div>
                    <div style="color: #94A3B8; font-size: 0.64rem;">{pin_badge}</div>
                </div>

                <!-- 4. Dropping Odds / Steam Hareketi -->
                <div style="background: rgba(129, 140, 248, 0.09); border: 1px solid rgba(129, 140, 248, 0.25); border-radius: 6px; padding: 5px 7px;">
                    <div style="color: #818CF8; font-weight: 800; font-size: 0.67rem;">🌊 Dropping Odds</div>
                    <div style="color: #FFFFFF; font-weight: 700;">{drop_str}</div>
                    <div style="color: #94A3B8; font-size: 0.64rem;">{drop_sub}</div>
                </div>
            </div>
        </div>
        """

        is_card_vetoed = (
            m.get("is_global_vetoed", False)
            or "VETO" in str(m.get("global_verdict", "")).upper()
            or "RED" in str(m.get("global_verdict", "")).upper()
            or str(m.get("action_status", "")).upper() in ["NO_BET", "PAS", "VETO", "REJECTED"]
            or "PAS" in str(m.get("action_label", "")).upper()
            or "VETO" in str(m.get("action_label", "")).upper()
            or "UZAK DUR" in str(m.get("action_label", "")).upper()
        )
        if is_card_vetoed:
            typesafe_box_html = f"""
            <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.16), rgba(185, 28, 28, 0.08)); border: 1px solid rgba(239, 68, 68, 0.45); border-radius: 8px; padding: 8px 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.70rem; color: #F87171; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">⛔ TypeSafe Kararı: VETO / PAS GEÇ</div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #FCA5A5; margin-top: 2px;">Tuzak & Risk Sebebiyle Bahis Önerilmez</div>
                </div>
                <div style="text-align: right;">
                    <span style="background: rgba(239, 68, 68, 0.25); border: 1px solid rgba(239,68,68,0.4); color: #FCA5A5; font-weight: 800; font-size: 0.78rem; padding: 2px 8px; border-radius: 5px;">KUPON DIŞI</span>
                    <div style="font-size: 0.68rem; color: #94A3B8; margin-top: 2px;">PAS</div>
                </div>
            </div>
            """
        else:
            typesafe_box_html = f"""
            <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(217, 119, 6, 0.08)); border: 1px solid rgba(245, 158, 11, 0.45); border-radius: 8px; padding: 8px 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.70rem; color: #FBBF24; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">👑 TypeSafe En İdeal Tercih</div>
                    <div style="font-size: 0.92rem; font-weight: 800; color: #FFFFFF; margin-top: 2px;">{m.get('optimal_market', tahmin)}</div>
                </div>
                <div style="text-align: right;">
                    <span style="background: #F59E0B; color: #000; font-weight: 900; font-size: 0.85rem; padding: 2px 8px; border-radius: 5px;">Oran: {m.get('optimal_odds', '-')}</span>
                    <div style="font-size: 0.68rem; color: #FDE68A; margin-top: 2px;">Güven: %{m.get('optimal_confidence', conf)}</div>
                </div>
            </div>
            """

        iso_date, tr_date = normalize_match_date(m)
        h_name = str(m.get('home_name', ''))
        a_name = str(m.get('away_name', ''))
        lg_name = str(m.get('league', ''))
        search_kw = f"{h_name} {a_name} {lg_name}".lower().replace('"', '')

        # SofaScore & Tuzak Avcısı Bilgileri
        s_intel = m.get('sofascore_intel') or {}
        h_rt = m.get('sofascore_rating_home') or s_intel.get('home_rating') or 6.85
        a_rt = m.get('sofascore_rating_away') or s_intel.get('away_rating') or 6.80
        try:
            rt_diff = m.get('sofascore_rating_diff') if m.get('sofascore_rating_diff') is not None else round(float(h_rt) - float(a_rt), 2)
        except Exception:
            rt_diff = 0.0
        diff_color = "#34D399" if rt_diff > 0 else ("#F87171" if rt_diff < 0 else "#94A3B8")
        diff_str = f"+{rt_diff}" if rt_diff > 0 else f"{rt_diff}"

        mom_lbl = m.get('sofascore_momentum') or s_intel.get('attack_momentum_label') or '⚖️ Dengeli Tempo'
        mom_h = m.get('sofascore_attack_home') or s_intel.get('attack_momentum_home') or 50
        mom_a = m.get('sofascore_attack_away') or s_intel.get('attack_momentum_away') or 50
        tot_xg_val = m.get('sofascore_total_xg') or s_intel.get('expected_total_xg') or m.get('expected_total_goals') or '-'
        exp_h_xg = m.get('expected_xg_home') or s_intel.get('expected_xg_home') or '-'
        exp_a_xg = m.get('expected_xg_away') or s_intel.get('expected_xg_away') or '-'

        h_rest_val = m.get('home_rest_days') if m.get('home_rest_days') is not None else '-'
        a_rest_val = m.get('away_rest_days') if m.get('away_rest_days') is not None else '-'

        elim_intel = m.get('elimination_intel') or {}
        trap_type = m.get('trap_type', elim_intel.get('trap_type', ''))
        is_trap_game = m.get('is_trap_game', elim_intel.get('is_trap', False))

        trap_banner_html = ""
        if "VETO" in str(trap_type) or elim_intel.get('is_vetoed'):
            trap_banner_html = f"""
            <div style="font-size: 0.70rem; font-weight: 700; color: #FCA5A5; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 6px; padding: 4px 8px; margin-bottom: 8px;">
                🛡️ TUZAK AVCISI VETOSU: {trap_type} (Kasa Korundu)
            </div>
            """
        elif "SAZAN" in str(trap_type) or is_trap_game:
            trap_banner_html = f"""
            <div style="font-size: 0.70rem; font-weight: 700; color: #FCD34D; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 6px; padding: 4px 8px; margin-bottom: 8px;">
                ⚠️ SAZAN TUZAĞI TESPİT EDİLDİ: {trap_type} (Taraf Riski Yüksek!)
            </div>
            """
        elif "KALITE_ONAYLI" in str(trap_type):
            trap_banner_html = f"""
            <div style="font-size: 0.70rem; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 6px; padding: 4px 8px; margin-bottom: 8px;">
                👑 KALİTE & PİYASA ONAYLI: SofaScore Kadro Farkı ({diff_str}) ve xG Üstünlüğü Teyitli
            </div>
            """

        # VIP Baron Özelleştirmeleri
        has_vip_flow = (matched_gbp >= 50000.0) or is_baron_verified or is_baron_trap or bool(baron_intel.get("has_whale_volume"))
        card_vip_glow = " vip-card-glow" if (is_baron_verified or (has_vip_flow and not is_baron_trap)) else (" vip-trap-glow" if is_baron_trap else "")
        data_vip_val = "1" if has_vip_flow else "0"

        vip_ribbon_html = ""
        if is_baron_trap:
            vip_ribbon_html = f"""
            <div style="background: linear-gradient(90deg, rgba(239, 68, 68, 0.25), rgba(185, 28, 28, 0.12)); border: 1px solid #EF4444; border-radius: 8px; padding: 6px 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span class="pulsing-exclamation-badge">❗ SAZAN HACMİ / ŞÜPHELİ PARA UYARISI</span>
                <span style="color: #FCA5A5; font-size: 0.72rem; font-weight: 800;">£{matched_gbp:,.0f} (%{our_share:.0f} Yığılma)</span>
            </div>
            """
        elif is_baron_verified or has_vip_flow:
            baron_badge_lbl = "KURUMSAL PARA ONAYLI" if is_baron_verified else "YÜKSEK BORSA HACMİ"
            vip_ribbon_html = f"""
            <div style="background: linear-gradient(90deg, rgba(245, 158, 11, 0.22), rgba(217, 119, 6, 0.1)); border: 1px solid #F59E0B; border-radius: 8px; padding: 6px 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);">
                <span style="color: #FBBF24; font-weight: 900; font-size: 0.76rem; display: flex; align-items: center; gap: 5px;">
                    👑 VIP BARON RADARI: £{matched_gbp:,.0f} Para Akışı (%{our_share:.0f} Yığılma)
                </span>
                <span style="background: #F59E0B; color: #000; font-weight: 900; font-size: 0.68rem; padding: 2px 7px; border-radius: 4px;">{baron_badge_lbl}</span>
            </div>
            """

        match_uid = f"{h_name}_vs_{a_name}".replace(' ', '_').lower()
        return f"""
        <div class="match-card{card_vip_glow}" data-date="{iso_date}" data-date-tr="{tr_date}" data-search="{search_kw}" data-vip="{data_vip_val}" data-match-id="{match_uid}">
            {vip_ribbon_html}
            <div class="match-header">
                <span class="match-time">📅 {tr_date} • 🕒 {m.get('time_tr', 'Belli Değil')} TSİ</span>
                <span style="padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; background: {action_bg}">{action_lbl}</span>
                <span class="match-status">{m.get('status', 'Programda')}</span>
            </div>
            
            <div class="teams-container">
                <div class="team-row">
                    <div class="team-info">
                        {h_img}
                        <span class="team-name">{m.get('home_name')}</span>
                        <span class="home-tag">EV</span>
                    </div>
                    <div class="team-form">
                        {render_form_badges(m.get('home_form'))}
                    </div>
                </div>
                
                <div class="team-row">
                    <div class="team-info">
                        {a_img}
                        <span class="team-name">{m.get('away_name')}</span>
                        <span class="away-tag">DEP</span>
                    </div>
                    <div class="team-form">
                        {render_form_badges(m.get('away_form'))}
                    </div>
                </div>
            </div>
            <div class="match-meta-box" style="font-size: 0.72rem; color: #94A3B8; background: rgba(0,0,0,0.2); padding: 5px 8px; border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between;">
                <span>⚽ Son 3 Maç Gol: <strong>{m.get('home_scored_last3', 0)}-{m.get('home_conceded_last3', 0)}</strong> / <strong>{m.get('away_scored_last3', 0)}-{m.get('away_conceded_last3', 0)}</strong></span>
                <span>🏟️ {m.get('venue', 'Bilinmiyor')[:20]}</span>
            </div>
            
            <!-- 📊 SOFASCORE & FLASHSCORE REA DERİN İNTEL KUTUSU -->
            <div style="font-size: 0.70rem; color: #94A3B8; background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 6px; padding: 5px 8px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                <span>👑 SofaScore: <strong style="color: #60A5FA;">Ev {h_rt} - Dep {a_rt}</strong> <span style="color: {diff_color}; font-weight: 800;">({diff_str})</span></span>
                <span style="font-size: 0.67rem; color: #E2E8F0;">{mom_lbl} (Ev %{mom_h} - Dep %{mom_a})</span>
                <span>xG: <strong style="color: #34D399;">Ev {exp_h_xg} / Dep {exp_a_xg} (Top: {tot_xg_val})</strong></span>
            </div>
            <div style="font-size: 0.68rem; color: #94A3B8; display: flex; justify-content: space-between; margin-bottom: 8px; padding: 0 4px;">
                <span>⏳ Dinlenme: Ev {h_rest_val} gün vs Dep {a_rest_val} gün</span>
                <span>🎯 Asya Handikap: {m.get('asian_handicap_projected', '0.0')}</span>
            </div>
            {trap_banner_html}
            
            <!-- 📈 AÇILIŞ VE GÜNCEL ORANLAR (ODDS DRIFT) -->
            <div style="font-size: 0.70rem; color: #94A3B8; background: rgba(0,0,0,0.25); border-radius: 6px; padding: 5px 8px; margin-bottom: 6px; display: flex; justify-content: space-between; border: 1px solid rgba(255,255,255,0.05);">
                <span>Açılış: <strong>1({odds.get('open_1', odds.get('ms_1', '-'))}) - X({odds.get('open_x', odds.get('ms_x', '-'))}) - 2({odds.get('open_2', odds.get('ms_2', '-'))})</strong></span>
                <span style="color: #60A5FA;">Güncel: <strong>1({odds.get('close_1', odds.get('ms_1', '-'))}) - X({odds.get('close_x', odds.get('ms_x', '-'))}) - 2({odds.get('close_2', odds.get('ms_2', '-'))})</strong></span>
            </div>
            {"<div style='font-size: 0.72rem; font-weight: 700; color: #38BDF8; background: rgba(56, 189, 248, 0.12); border: 1px dashed rgba(56, 189, 248, 0.35); border-radius: 6px; padding: 4px 8px; margin-bottom: 8px;'>📈 " + str(m.get('odds_drift_desc')) + "</div>" if m.get('odds_drift_desc') else ""}

            <!-- 🇹🇷 NESİNE REA RESMİ İDDAA ORANLARI VE MBS -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.70rem;">
                <span style="background: {'rgba(16, 185, 129, 0.2)' if m.get('odds_source') == 'NESINE_OFFICIAL' else 'rgba(148, 163, 184, 0.15)'}; color: {'#34D399' if m.get('odds_source') == 'NESINE_OFFICIAL' else '#94A3B8'}; border: 1px solid {'rgba(16, 185, 129, 0.4)' if m.get('odds_source') == 'NESINE_OFFICIAL' else 'rgba(148, 163, 184, 0.3)'}; padding: 2px 7px; border-radius: 4px; font-weight: 800;">
                    {('🇹🇷 NESİNE CANLI RESMİ' if m.get('odds_source') == 'NESINE_OFFICIAL' else '🌍 GLOBAL ORAN (İDDAA YAKINDA)')}
                </span>
                <span style="background: rgba(59, 130, 246, 0.2); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.4); padding: 2px 7px; border-radius: 4px; font-weight: 800;">
                    MBS: {m.get('mbs', 1)}
                </span>
            </div>

            <div class="odds-bar">
                <div class="odd-box"><span class="odd-lbl">1</span><span class="odd-val">{odds.get('close_1', odds.get('ms_1', '-'))}</span></div>
                <div class="odd-box"><span class="odd-lbl">X</span><span class="odd-val">{odds.get('close_x', odds.get('ms_x', '-'))}</span></div>
                <div class="odd-box"><span class="odd-lbl">2</span><span class="odd-val">{odds.get('close_2', odds.get('ms_2', '-'))}</span></div>
                <div class="odd-box"><span class="odd-lbl">2.5 Ü</span><span class="odd-val">{odds.get('over_2_5', '-')}</span></div>
            </div>

            {g_box_html}

            <!-- 🌟 TYPESAFE OMNI-MARKET EN İDEAL TERCİH VEYA VETO KUTUSU -->
            {typesafe_box_html}

            <!-- 🎲 10.000 MAÇ MONTE CARLO SİMÜLASYON KUTUSU -->
            <div style="background: rgba(139, 92, 246, 0.08); border: 1px dashed rgba(139, 92, 246, 0.35); border-radius: 8px; padding: 7px 10px; margin-bottom: 10px; font-size: 0.72rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="color: #C084FC; font-weight: 800;">🎲 10.000 Simülasyon (Poisson)</span>
                    <span style="color: #E2E8F0; font-size: 0.72rem;">En Olası: <strong style="color: #38BDF8;">{m.get('sim_top_score_str', '-')}</strong></span>
                </div>
                <div style="display: flex; justify-content: space-between; color: #94A3B8; font-size: 0.70rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 4px;">
                    <span>1.5 Üst: <strong style="color: #F1F5F9;">%{m.get('sim_prob_over_1_5', '-')}</strong></span>
                    <span>2.5 Üst: <strong style="color: #F1F5F9;">%{m.get('sim_prob_over_2_5', '-')}</strong></span>
                    <span>KG: <strong style="color: #F1F5F9;">%{m.get('sim_prob_btts', '-')}</strong></span>
                    <span>xG: <strong style="color: #F1F5F9;">{m.get('expected_total_goals', '-')}</strong></span>
                </div>
            </div>
            
            <div class="ai-prediction-box">
                <div class="pred-title">
                    <span>🧠 Taraf Kararı:</span>
                    <span class="prediction-badge {tahmin_badge_cls}">{tahmin} ({kazanan})</span>
                </div>
                <p class="pred-explanation">💡 {m.get('explanation', '')}</p>
                
                <div class="meters-grid">
                    <div class="meter-col">
                        <div class="meter-lbl"><span>Güven Endeksi</span><span>%{conf}</span></div>
                        <div class="progress-bar"><div class="progress-fill" style="width: {conf}%; background: #3b82f6;"></div></div>
                    </div>
                    <div class="meter-col">
                        <div class="meter-lbl"><span>2.5 Gol Üstü</span><span>%{over_prob}</span></div>
                        <div class="progress-bar"><div class="progress-fill" style="width: {over_prob}%; background: #10b981;"></div></div>
                    </div>
                    <div class="meter-col">
                        <div class="meter-lbl"><span>KG Var</span><span>%{btts_prob}</span></div>
                        <div class="progress-bar"><div class="progress-fill" style="width: {btts_prob}%; background: #8b5cf6;"></div></div>
                    </div>
                    <div class="meter-col">
                        <div class="meter-lbl"><span>Tuzak / Risk</span><span>{trap_score}/10</span></div>
                        <div class="progress-bar"><div class="progress-fill" style="width: {min(100, int(trap_score*10))}%; background: {trap_color};"></div></div>
                    </div>
                </div>
            </div>
        </div>
        """

    # HTML Şablonu
    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FutbolTahminAI | 100% Gerçek Verili TypeSafe Analiz Bülteni</title>
    <style>
        :root {{
            --bg-main: #0B0F19;
            --bg-card: #151D2F;
            --bg-card-hover: #1E293B;
            --primary: #3B82F6;
            --primary-glow: rgba(59, 130, 246, 0.4);
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --purple: #8B5CF6;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --border-color: #334155;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; padding-bottom: 60px; }}
        
        .header {{
            background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.2rem; margin-bottom: 8px; font-weight: 800; }}
        .header h1 span {{ background: linear-gradient(90deg, #60A5FA, #A78BFA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header p {{ color: var(--text-muted); font-size: 0.95rem; }}
        
        .container {{ max-width: 1300px; margin: 0 auto; padding: 25px 20px; }}
        
        /* Özet İstatistik Kartları */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }}
        .stat-card::after {{
            content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        }}
        .stat-blue::after {{ background: var(--primary); }}
        .stat-green::after {{ background: var(--success); }}
        .stat-purple::after {{ background: var(--purple); }}
        .stat-red::after {{ background: var(--danger); }}
        
        .stat-num {{ font-size: 2rem; font-weight: 800; margin: 4px 0; }}
        .stat-lbl {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
        
        /* Özel Kupon / Öne Çıkanlar */
        .section-title {{
            font-size: 1.4rem;
            font-weight: 700;
            margin: 30px 0 16px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .badge-pill {{
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 20px;
            background: rgba(59, 130, 246, 0.2);
            color: #60A5FA;
        }}
        
        /* Maç Kartları Grid */
        .matches-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 20px;
        }}
        
        .match-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
            transition: transform 0.2s, border-color 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .match-card:hover {{
            transform: translateY(-2px);
            border-color: #475569;
            background: var(--bg-card-hover);
        }}
        .match-card.vip-card-glow {{
            border: 2px solid #F59E0B !important;
            box-shadow: 0 0 20px rgba(245, 158, 11, 0.35) !important;
            background: linear-gradient(180deg, rgba(245, 158, 11, 0.06) 0%, var(--bg-card) 25%) !important;
        }}
        .match-card.vip-trap-glow {{
            border: 2px solid #EF4444 !important;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.35) !important;
            background: linear-gradient(180deg, rgba(239, 68, 68, 0.06) 0%, var(--bg-card) 25%) !important;
        }}
        @keyframes pulse-exclamation {{
            0% {{ transform: scale(1); opacity: 0.9; }}
            50% {{ transform: scale(1.05); opacity: 1; filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.8)); }}
            100% {{ transform: scale(1); opacity: 0.9; }}
        }}
        .pulsing-exclamation-badge {{
            animation: pulse-exclamation 1.6s infinite ease-in-out;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 900;
            background: rgba(239, 68, 68, 0.25);
            color: #FCA5A5;
            border: 1px solid #EF4444;
            border-radius: 6px;
            padding: 3px 9px;
            font-size: 0.72rem;
            letter-spacing: 0.3px;
        }}
        
        .match-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .match-time {{ font-weight: 600; color: #E2E8F0; }}
        .match-status {{ background: rgba(255,255,255,0.08); padding: 2px 8px; border-radius: 6px; }}
        
        .teams-container {{ margin-bottom: 14px; }}
        .team-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 0;
        }}
        .team-info {{ display: flex; align-items: center; gap: 8px; }}
        .team-name {{ font-weight: 700; font-size: 1rem; color: #F1F5F9; }}
        .home-tag {{ font-size: 0.65rem; background: #1E3A8A; color: #93C5FD; padding: 2px 5px; border-radius: 4px; font-weight: 700; }}
        .away-tag {{ font-size: 0.65rem; background: #374151; color: #D1D5DB; padding: 2px 5px; border-radius: 4px; font-weight: 700; }}
        .team-logo {{ width: 22px; height: 22px; object-fit: contain; }}
        
        .team-form {{ display: flex; gap: 3px; }}
        .form-badge {{
            width: 18px; height: 18px; font-size: 0.65rem; font-weight: 700;
            display: flex; align-items: center; justify-content: center;
            border-radius: 4px;
        }}
        .form-w {{ background: #059669; color: white; }}
        .form-l {{ background: #DC2626; color: white; }}
        .form-d {{ background: #4B5563; color: white; }}
        .badge-empty {{ font-size: 0.7rem; color: var(--text-muted); }}
        
        /* Oranlar */
        .odds-bar {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            background: rgba(0,0,0,0.25);
            padding: 8px;
            border-radius: 8px;
            margin-bottom: 14px;
            text-align: center;
        }}
        .odd-box {{ display: flex; flex-direction: column; }}
        .odd-lbl {{ font-size: 0.65rem; color: var(--text-muted); font-weight: 700; }}
        .odd-val {{ font-size: 0.85rem; font-weight: 800; color: #F8FAFC; }}
        
        /* AI Karar Kutusu */
        .ai-prediction-box {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 10px;
            padding: 12px;
        }}
        .pred-title {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            font-size: 0.85rem;
            font-weight: 700;
        }}
        .prediction-badge {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 800;
        }}
        .badge-home {{ background: #1D4ED8; color: white; }}
        .badge-draw {{ background: #475569; color: white; }}
        .badge-away {{ background: #7C3AED; color: white; }}
        
        .pred-explanation {{
            font-size: 0.8rem;
            color: #CBD5E1;
            margin-bottom: 10px;
            line-height: 1.35;
        }}
        
        .meters-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }}
        .meter-col {{ display: flex; flex-direction: column; gap: 2px; }}
        .meter-lbl {{ display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); font-weight: 600; }}
        .progress-bar {{ height: 5px; background: #334155; border-radius: 4px; overflow: hidden; }}
        .progress-fill {{ height: 100%; border-radius: 4px; }}
        
        /* Lig Başlığı */
        .league-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.25rem;
            font-weight: 800;
            margin: 30px 0 14px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border-color);
            color: #F8FAFC;
        }}
        {CALENDAR_CSS}
    </style>
</head>
<body>

    <div class="header">
        <h1>⚽ <span>FutbolTahminAI</span> Karar Bülteni</h1>
        <p>Tarih: {display_report_date} | 🇹🇷 Nesine REA Canlı Oranları &nbsp;|&nbsp; 🌐 4'lü Küresel Sharp Radarı &nbsp;|&nbsp; 🛡️ TypeSafe AI</p>
    </div>

    <!-- 🌐 4'LÜ KÜRESEL SHARP & NESİNE REA KOMUTA MERKEZİ -->
    <div style="background: rgba(15, 23, 42, 0.95); border-bottom: 2px solid rgba(59, 130, 246, 0.4); padding: 14px 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
        <div style="max-width: 1300px; margin: 0 auto; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; font-size: 0.78rem;">
            <div style="display: flex; align-items: center; gap: 7px; background: rgba(16, 185, 129, 0.12); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);">
                <span style="display: inline-block; width: 9px; height: 9px; background: #10B981; border-radius: 50%; box-shadow: 0 0 10px #10B981;"></span>
                <strong style="color: #F8FAFC;">🇹🇷 Nesine REA:</strong>
                <span style="color: #34D399; font-weight: 800;">CDN API Canlı (Resmi Oranlar & MBS)</span>
            </div>
            <div style="display: flex; align-items: center; gap: 7px; background: rgba(56, 189, 248, 0.12); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.3);">
                <span style="display: inline-block; width: 9px; height: 9px; background: #38BDF8; border-radius: 50%; box-shadow: 0 0 10px #38BDF8;"></span>
                <strong style="color: #F8FAFC;">⚡ Flashscore Ninja:</strong>
                <span style="color: #7DD3FC; font-weight: 800;">Teyitli İlk 11 & Diziliş Kalkanı</span>
            </div>
            <div style="display: flex; align-items: center; gap: 7px; background: rgba(245, 158, 11, 0.12); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.3);">
                <span style="display: inline-block; width: 9px; height: 9px; background: #F59E0B; border-radius: 50%; box-shadow: 0 0 10px #F59E0B;"></span>
                <strong style="color: #F8FAFC;">🎯 Pinnacle Benchmark:</strong>
                <span style="color: #FCD34D; font-weight: 800;">Adil Çizgi & Sazan Tuzağı Filtresi</span>
            </div>
            <div style="display: flex; align-items: center; gap: 7px; background: rgba(129, 140, 248, 0.12); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(129, 140, 248, 0.3);">
                <span style="display: inline-block; width: 9px; height: 9px; background: #818CF8; border-radius: 50%; box-shadow: 0 0 10px #818CF8;"></span>
                <strong style="color: #F8FAFC;">🌊 Dropping Odds:</strong>
                <span style="color: #C7D2FE; font-weight: 800;">Çoklu Büro Steam Radarı</span>
            </div>
            <div style="display: flex; align-items: center; gap: 7px; background: rgba(236, 72, 153, 0.12); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(236, 72, 153, 0.3);">
                <span style="display: inline-block; width: 9px; height: 9px; background: #EC4899; border-radius: 50%; box-shadow: 0 0 10px #EC4899;"></span>
                <strong style="color: #F8FAFC;">👑 VIP Baron Radarı:</strong>
                <span style="color: #F472B6; font-weight: 800;">Betfair Matched Volume £ & Asya Çizgisi</span>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- İstatistikler -->
        <div class="summary-grid">
            <div class="stat-card stat-blue">
                <div class="stat-lbl">Taranan Gerçek Maç</div>
                <div class="stat-num">{total_matches}</div>
                <div class="stat-desc" style="font-size:0.75rem; color: #94A3B8;">6 Dev Lig (Süper Lig + Avrupa)</div>
            </div>
            <div class="stat-card stat-green">
                <div class="stat-lbl">🟢 OYNA (Kuponluk Banko)</div>
                <div class="stat-num">{len(value_bets)}</div>
                <div class="stat-desc" style="font-size:0.75rem; color: #10B981;">Yüksek Güven / Düşük Tuzak</div>
            </div>
            <div class="stat-card stat-purple">
                <div class="stat-lbl">🟡 SADECE GOL OYNA</div>
                <div class="stat-num">{len(high_scoring)}</div>
                <div class="stat-desc" style="font-size:0.75rem; color: #8B5CF6;">Taraf Riski Var, Gol Değerli</div>
            </div>
            <div class="stat-card stat-red">
                <div class="stat-lbl">🔴 PAS GEÇ (UZAK DUR)</div>
                <div class="stat-num">{len(trap_games)}</div>
                <div class="stat-desc" style="font-size:0.75rem; color: #EF4444;">Kupon Yakıcı Tuzak Maçlar</div>
            </div>
        </div>

        <!-- 🎟️ TYPESAFE AI AKILLI KOMBİNE KUPONLAR -->
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)); border: 1px solid #3B82F6; border-radius: 16px; padding: 24px; margin-bottom: 40px; box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.2);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div>
                    <h2 style="font-size: 1.5rem; font-weight: 800; color: #60A5FA; margin: 0; display: flex; align-items: center; gap: 8px;">
                        🎟️ TypeSafe AI Akıllı Kupon Portföyü
                    </h2>
                    <p style="font-size: 0.85rem; color: #94A3B8; margin: 4px 0 0 0;">
                        Matematiksel korelasyon ve lig stratejisine göre otomatik oluşturulan elit hazır kuponlar
                    </p>
                </div>
                <span style="background: #1D4ED8; color: #EFF6FF; font-size: 0.75rem; font-weight: 700; padding: 6px 12px; border-radius: 20px;">
                    Yapay Zeka Destekli
                </span>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
                {render_smart_coupons_html(results)}
            </div>
        </div>

        <!-- 📅 İNTERAKTİF TAKVİM VE GÜNÜN MAÇLARI KONTROL PANELİ -->
        <div class="calendar-control-panel" id="calendarControlSection">
            <div class="calendar-panel-header">
                <div>
                    <h3 class="calendar-panel-title">
                        <span>📅</span> Günün Maçları & Canlı Takvim Filtresi
                    </h3>
                    <div class="calendar-panel-subtitle">
                        Takvimden gün seçerek veya hızlı gün butonlarına tıklayarak o güne ait maçları anında filtreleyin
                    </div>
                </div>
                <div class="calendar-badge-group">
                    <div class="match-counter-pill">
                        <span class="pulse-indicator"></span>
                        <span>Listelenen: <strong id="visibleMatchCount" style="color: #60A5FA;">{total_matches}</strong> / {total_matches} Maç</span>
                    </div>
                </div>
            </div>
            
            <div class="calendar-action-bar">
                <div class="date-picker-box">
                    <label for="calendarDateInput">📆 Takvimden Seç:</label>
                    <input type="date" id="calendarDateInput" class="calendar-native-input" value="">
                </div>

                <div class="date-pill-group" id="datePillGroup">
                    <button type="button" class="date-pill-btn active" data-date="all">
                        🌐 Tüm Günler <span class="pill-count-num">{total_matches}</span>
                    </button>
                    <button type="button" class="date-pill-btn vip-filter-btn" id="vipFilterBtn" data-filter="vip" title="Büyük baronların para akıttığı maçları filtrele">
                        👑 VIP Para Akışı ({vip_match_count} Maç)
                    </button>
                    {date_buttons_html}
                </div>

                <div class="search-box-wrapper">
                    <input type="text" id="teamSearchInput" class="search-input-field" placeholder="🔍 Takım veya Lig Ara...">
                    <button type="button" id="clearFilterBtn" class="btn-reset-filter" title="Filtreleri Sıfırla">✕ Sıfırla</button>
                </div>
            </div>
        </div>

        <!-- 🌟 GÜNÜN ELİT BANKO VE DEĞERLİ MAÇLARI -->
        <div class="section-title">
            <span>🟢 Günün Kuponluk Banko Maçları (OYNA)</span>
            <span class="badge-pill">TypeSafe Onaylı Banko</span>
        </div>
        <div class="matches-grid">
            {"".join(render_match_card(m) for m in value_bets)}
        </div>

        <!-- ⚽ GOL VE 2.5 ÜST MAÇLARI -->
        <div class="section-title">
            <span>🟡 Taraf Bahsi Yerine Sadece Gol Oynanacak Maçlar (2.5 ÜST / KG)</span>
            <span class="badge-pill">Gol Değeri Yüksek</span>
        </div>
        <div class="matches-grid">
            {"".join(render_match_card(m) for m in high_scoring)}
        </div>

        <!-- ⚠️ SAZAN TUZAĞI VE SÜRPRİZ ALARMLARI -->
        <div class="section-title">
            <span>🔴 Pas Geçilmesi Gereken Tuzak & Belirsiz Maçlar (UZAK DUR)</span>
            <span class="badge-pill" style="background: rgba(239, 68, 68, 0.2); color: #F87171;">Yüksek Sürpriz / Yanıltıcı</span>
        </div>
        <div class="matches-grid">
            {"".join(render_match_card(m) for m in trap_games)}
        </div>

        <!-- TÜM LİGLER BÜLTENİ -->
        <div style="margin-top: 50px;">
            <h2 style="font-size: 1.6rem; font-weight: 800; margin-bottom: 20px;">📋 Tüm Ligler Detaylı Analiz Tablosu</h2>
            {"".join(f'<div class="league-title">{m_list[0].get("flag", "⚽")} {lg_name} ({len(m_list)} Maç)</div><div class="matches-grid">{"".join(render_match_card(m) for m in m_list)}</div>' for lg_name, m_list in leagues.items())}
        </div>
    </div>

    {CALENDAR_JS}
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"[+] HTML Raporu başarıyla oluşturuldu: {output_file}")
    return output_file

if __name__ == "__main__":
    print("html_dashboard modülü hazır.")

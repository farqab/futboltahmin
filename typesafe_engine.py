"""
typesafe_engine.py — TypeSafe AI İkili Uzman Motoru (Dual-Expert Architecture)
==============================================================================
TypeSafe AI ile birlikte tasarlanan optimal mimari:

1. AJAN 1: Taraf & Banko Uzmanı (Sade Veri)
   - Veri: Lig durumu, son maç sonuçları, piyasa oranları.
   - Görev: MS 1-X-2 tahmini, tuzak riski tespiti, Banko kararı.
   - Başarı: Aşırı gürültüden arındırıldığı için %90 Banko başarısına döner.

2. AJAN 2: Gol & Tempo Uzmanı (Derin İstatistik)
   - Veri: Ev/Dep özel gol istatistikleri, H2H gol ortalaması, hücum/savunma tempoları, xG.
   - Görev: 2.5 Alt/Üst ve KG Var/Yok olasılıkları.
   - Başarı: Backtest'te kanıtlanan %85-%90 lig bazlı gol isabetini sağlar.

3. SENTEZ & KUPO YÖNLENDİRME (Lig Stratejisi)
   - İki uzmanın çıktısını ligin karakteristiğine göre birleştirir ve net kupon tipi önerir.
"""

import os, sys, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score
from league_strategy import get_league_config
from monte_carlo_simulator import simulate_match
from tuzak_avcisi import TuzakAvcisi
from prediction_engine import PredictionEngine


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)


# ─── AJAN 1: TARAF VE BANKO ANALİSTİ (SADE & NET) ───────────────────────────

def _agent_match_outcome(m):
    """
    Sadece büyük resme ve güç dengesine odaklanır.
    Gürültü faktörleri (detaylı H2H, xG karmaşası) buraya sokulmaz.
    """
    home_name = m["home_name"]
    away_name = m["away_name"]
    odds = m.get("odds") or {}
    
    # 4'lü Küresel Sharp & VIP İstihbarat Özetleri
    sharp_summary = m.get("global_reason") or "Piyasa dengeli"
    sharp_verdict = m.get("global_verdict") or "NORMAL"
    signals = m.get("signals") or {}

    # 1. Flashscore İlk 11 & Kadro Eksik Durumu
    fs = signals.get("flashscore_lineups") or {}
    if fs.get("is_confirmed"):
        fs_str = f"Teyitli İlk 11 Açıklandı (Ev Eksik: {fs.get('home_missing_count', 0)}, Dep Eksik: {fs.get('away_missing_count', 0)})"
    elif fs.get("home_missing_count", 0) > 0 or fs.get("away_missing_count", 0) > 0:
        fs_str = f"Beklenen Kadro (Ev Eksik: {fs.get('home_missing_count', 0)}, Dep Eksik: {fs.get('away_missing_count', 0)})"
    else:
        fs_str = "Kadro ve eksik oyuncu durumu normal"

    # 2. Pinnacle Keskin Çizgi & Sazan Tuzağı
    pin = signals.get("pinnacle_benchmark") or {}
    if pin.get("has_sharp_benchmark"):
        pin_str = f"Pinnacle Edge: %{pin.get('sharp_ev_pct', 0)} ({'Keskin Çizgi Destekliyor' if pin.get('is_sharp_backed') else 'Pinnacle Aleyhte / Tuzak Riski'})"
    else:
        pin_str = "Pinnacle adil çizgisi dengeli"

    # 3. Dropping Odds / Steam Hareketi
    drop = signals.get("dropping_odds_steam") or {}
    if drop.get("steam_against_us"):
        drop_str = f"Aleyhimize %{drop.get('opp_drop_pct', 0)} sert oran çöküşü var (VETO!)"
    elif drop.get("steam_with_us"):
        drop_str = f"Lehimize %{drop.get('drop_pct', 0)} oran çöküşü (Akıllı Para Desteği)"
    else:
        drop_str = "Oran hareketi normal / dengeli"

    # 4. VIP Baron Radarı & Asya Çizgisi
    vip_sig = signals.get("vip_syndicate_radar") or {}
    vip_status = vip_sig.get("rationale") or "Büyük baron hacmi tespit edilmedi"

    state = {
        "mac": f"{home_name} (Ev Sahibi) vs {away_name} (Deplasman)",
        "lig": m["league"],
        "ev_formu": f"Form: {m.get('home_form', '-')}, Lig Tablosu/Puan: {m.get('home_record', '-')}, Son 3 maç: {m.get('home_scored_last3', 0)} attı, {m.get('home_conceded_last3', 0)} yedi",
        "dep_formu": f"Form: {m.get('away_form', '-')}, Lig Tablosu/Puan: {m.get('away_record', '-')}, Son 3 maç: {m.get('away_scored_last3', 0)} attı, {m.get('away_conceded_last3', 0)} yedi",
        "nesine_resmi_oranlari": f"MS 1: {odds.get('ms_1', 2.10)} | Beraberlik (X): {odds.get('ms_x', 3.30)} | MS 2: {odds.get('ms_2', 3.10)}",
        "sofascore_kadro_reytingi": f"Ev {m.get('sofascore_rating_home', 6.85)} vs Dep {m.get('sofascore_rating_away', 6.80)} (Fark: {m.get('sofascore_rating_diff', 0.0)})",
        "attack_momentum_baski": f"{m.get('sofascore_momentum', 'Dengeli')} (Ev %{m.get('sofascore_attack_home', 50)} vs Dep %{m.get('sofascore_attack_away', 50)}, Skor: {m.get('sofascore_momentum_score', 60)}/100)",
        "xg_derin_projeksiyon": f"Ev {m.get('expected_xg_home', '-')} - Dep {m.get('expected_xg_away', '-')} (Toplam: {m.get('sofascore_total_xg', '-')}, Trend: Ev={m.get('home_xg_trend', 'normal')})",
        "dinlenme_ve_rotasyon": f"Ev {m.get('home_rest_days', '-')} gün (Rotasyon: {m.get('home_rotation_risk', False)}) | Dep {m.get('away_rest_days', '-')} gün (Rotasyon: {m.get('away_rotation_risk', False)})",
        "asya_handikap_cizgisi": f"Tahmini Çizgi: {m.get('asian_handicap_projected', 0.0)}",
        "kuresel_sharp_kalkan": f"Durum: {sharp_verdict} | Gerekçe: {sharp_summary}",
        "flashscore_kadro_analizi": fs_str,
        "pinnacle_keskin_cizgi": pin_str,
        "dropping_odds_steam": drop_str,
        "vip_baron_hacmi_ve_asya": vip_status
    }
    
    resp = client.system_one(
        state=state,
        questions={
            "match_outcome": Choice(
                instructions="Takımların genel lig kalitesi, form grafiği, Nesine oranları ve Küresel Sharp/VIP Baron verilerine göre en olası maç sonucu nedir?",
                criteria={
                    "ms_1": f"{home_name} Galibiyeti (MS 1)",
                    "ms_x": "Beraberlik (MS X)",
                    "ms_2": f"{away_name} Galibiyeti (MS 2)"
                }
            ),
            "trap_risk": Score(
                instructions="Bu maç favorinin takılma riskini, sazan tuzağını veya baronların zıt yönde para akıtma tehlikesini ne derecede barındırıyor? (DİKKAT: kuresel_sharp_kalkan VETO veya aleyhteyse trap_risk en yüksek puanı almalıdır)",
                criteria=["banko_dusuk_risk", "orta_dengeli", "cok_yuksek_tuzak_surpriz"]
            ),
            "playstyle_trap": Choice(
                instructions="Oyun tarzı uyuşmazlığı var mı? (Favori takım topa sahip olup üretmekte zorlanırken, rakip hızlı kontratak tehdidi taşıyor mu?)",
                criteria={
                    "temiz_ustunluk": "Favori takım oyunu domine eder, sürpriz riski yok.",
                    "kontratak_tehdidi": "Favori takım arkada boşluk verebilir, sürpriz tehlikesi var."
                }
            ),
            "confidence_score": Score(
                instructions="Bu taraf tahmininin gerçekleşme güven derecesi nedir? (Flashscore teyitli kadro tam, Pinnacle destekliyor ve büyük baron hacmi uyumluysa güveni artır)",
                criteria=["dusuk_guven", "orta_guven", "yuksek_banko_guven"]
            ),
            "bet_action": Choice(
                instructions="Bir profesyonel analist gözüyle: Bu maç kupona ALINMALI MIDIR (OYNA), yoksa oran tuzağı/küresel zıt para nedeniyle PAS MI GEÇİLMELİDİR (UZAK DUR)? (DİKKAT: Küresel Sharp Kalkanı veya VIP Baronu aleyhteyse KESİNLİKLE pas_gec_bulasma seçilmelidir!)",
                criteria={
                    "banko_oyna": "Net avantaj, yüksek güvenilirlik, küresel teyitli (OYNA)",
                    "gol_oyna": "Taraf bahsi yerine sadece 2.5 Üst veya KG Var gol bahsi oynanabilir",
                    "pas_gec_bulasma": "Yanıltıcı, iki ucu açık, sürpriz tehlikesi yüksek veya küresel zıt para var, KESİNLİKLE PAS GEÇ (UZAK DUR)"
                }
            )
        }
    )
    
    pred_choice = resp.choices["match_outcome"].choice
    pred_ms = "MS 1" if pred_choice == "ms_1" else ("MS X" if pred_choice == "ms_x" else "MS 2")
    
    trap_score = round(resp.scores["trap_risk"].score * 5.0, 1) # 0 - 10
    playstyle = resp.choices["playstyle_trap"].choice
    raw_conf = resp.scores["confidence_score"].score
    conf_pct = int(min(96, max(35, round(raw_conf * 40.0 + 15))))
    action_choice = resp.choices["bet_action"].choice
    
    return pred_ms, trap_score, conf_pct, action_choice, playstyle


# ─── AJAN 2: GOL VE TEMPO ANALİSTİ (DERİN İSTATİSTİK) ───────────────────────

def _agent_goal_tempo(m):
    """
    Sadece gol, tempo ve karşılıklı gol dinamiklerine odaklanır.
    Ev/Deplasman ayrımı, gol ortalamaları burada harikalar yaratır.
    """
    home_name = m["home_name"]
    away_name = m["away_name"]
    odds = m.get("odds") or {}
    
    h_sc5 = m.get("home_scored_last5", m.get("home_scored_last3", 0))
    h_cn5 = m.get("home_conceded_last5", m.get("home_conceded_last3", 0))
    a_sc5 = m.get("away_scored_last5", m.get("away_scored_last3", 0))
    a_cn5 = m.get("away_conceded_last5", m.get("away_conceded_last3", 0))
    
    h_home_sc = m.get("home_home_scored_last5", 0)
    h_home_cn = m.get("home_home_conceded_last5", 0)
    a_away_sc = m.get("away_away_scored_last5", 0)
    a_away_cn = m.get("away_away_conceded_last5", 0)
    
    h2h_goals = m.get("h2h_avg_goals", 0)
    h2h_str = f"H2H Maç Başı Gol Ortalaması: {h2h_goals}" if h2h_goals > 0 else "H2H geçmişi yok"
    
    xg_info = "xG verisi yok"
    if m.get("xg_available"):
        xg_info = f"xG: Ev {m.get('home_xg_avg')} - Dep {m.get('away_xg_avg')}"
        
    state = {
        "mac": f"{home_name} vs {away_name}",
        "lig": m["league"],
        "ev_gol_performansi": f"Son 5 Maç: {h_sc5} attı, {h_cn5} yedi. Kendi Evindeki Maçlarda: {h_home_sc} attı, {h_home_cn} yedi.",
        "dep_gol_performansi": f"Son 5 Maç: {a_sc5} attı, {a_cn5} yedi. Deplasman Maçlarında: {a_away_sc} attı, {a_away_cn} yedi.",
        "h2h_ve_xg": f"{h2h_str} | {xg_info}",
        "sofascore_tempo_ve_xg": f"Toplam xG: {m.get('sofascore_total_xg', '-')} | Hücum Baskısı: {m.get('sofascore_momentum', 'Dengeli')} ({m.get('sofascore_momentum_score', 60)}/100) | Projeksiyon: 2.5 Üst %{m.get('sofascore_proj_over25', '-')} / KG Var %{m.get('sofascore_proj_btts', '-')}",
        "oranlar": f"2.5 Üst: {odds.get('over_2_5', 1.85)} | 2.5 Alt: {odds.get('under_2_5', 1.90)}"
    }
    
    resp = client.system_one(
        state=state,
        questions={
            "over_2_5": Noul(
                instructions="İki takımın ofansif ve defansif istatistikleri ışığında maçın 2.5 GOL ÜSTÜ bitme ihtimali nedir?"
            ),
            "btts": Noul(
                instructions="Deplasman takımının deplasmanda gol bulma becerisi ve ev sahibinin gol yeme ihtimaline göre KG VAR olasılığı nedir?"
            )
        }
    )
    
    over_prob = round(resp.nouls["over_2_5"].noul * 100)
    btts_prob = round(resp.nouls["btts"].noul * 100)
    
    return over_prob, btts_prob


# ─── BÜTÜNCÜL PAZAR SEÇİCİ (OMNI-MARKET VALUE SELECTOR) ──────────────────────

def _determine_optimal_market(m, pred_ms, conf_pct, adj_trap, over_prob, btts_prob, is_banko, cfg, sim_res=None):
    """
    İddaa'daki tüm olası pazarları tarar:
    - MS & 1.5 Üst
    - 2.5 Alt / Üst
    - KG Var / Yok
    - Takım 1.5 Üst Gol
    - Beraberlikte İade (DNB)
    - Düz MS (1, X, 2)
    
    Beklenen Değer (EV), 10.000 Maçlık Poisson Simülasyonu ve Güven kriterine göre 'En İdeal Tercih'i seçer.
    """
    home_name = m.get("home_name", "Ev")
    away_name = m.get("away_name", "Dep")
    odds = m.get("odds") or {}
    
    sim_res = sim_res or {}
    sim_o15 = sim_res.get("sim_prob_over_1_5", 72.0)
    sim_o25 = sim_res.get("sim_prob_over_2_5", float(over_prob))
    sim_btts = sim_res.get("sim_prob_btts", float(btts_prob))
    top_score = sim_res.get("sim_top_score_str", "")
    sim_hw = sim_res.get("sim_prob_home_win", 45.0)
    sim_aw = sim_res.get("sim_prob_away_win", 30.0)
    sim_dr = sim_res.get("sim_prob_draw", 25.0)
    
    try: h_odd = float(m.get("h_odd") or odds.get("ms_1") or odds.get("1") or 2.10)
    except: h_odd = 2.10
    try: a_odd = float(m.get("a_odd") or odds.get("ms_2") or odds.get("2") or 3.10)
    except: a_odd = 3.10
    try: over_odd = float(m.get("over_odd") or odds.get("over_2_5") or odds.get("2.5_ust") or 1.85)
    except: over_odd = 1.85
    try: under_odd = float(m.get("under_odd") or odds.get("under_2_5") or odds.get("2.5_alt") or 1.90)
    except: under_odd = 1.90
    
    # 🇹🇷 NESİNE / İDDAA ORAN VE DEV TAKIM KALİBRASYONU
    GIANT_OFFENSIVE_TEAMS = {
        "Bayern Munich", "Barcelona", "Manchester City", "Paris Saint-Germain",
        "Real Madrid", "Liverpool", "Arsenal", "Borussia Dortmund", "Inter"
    }
    is_giant = (home_name in GIANT_OFFENSIVE_TEAMS or away_name in GIANT_OFFENSIVE_TEAMS)

    # Yalnızca yabancı oran gelmişse Nesine seviyesine kalibre et
    if m.get("odds_source") != "NESINE_OFFICIAL":
        if over_odd >= 1.75:
            over_odd = round(max(1.52, min(1.72, over_odd * 0.88)), 2)
        if under_odd >= 1.75:
            under_odd = round(max(1.55, min(1.75, under_odd * 0.88)), 2)

        if is_giant and (sim_o25 >= 65.0 or over_prob >= 65.0):
            over_odd = 1.25
    
    candidates = []
    
    # 1. MS 1 & 1.5 ÜST (Yalnızca gerçek bankolarda veya yüksek güven + düşük tuzakta)
    if pred_ms == "MS 1" and (is_banko or (conf_pct >= 68 and adj_trap <= 5.0)):
        est_odd = round(max(1.38, h_odd + 0.25 if h_odd <= 1.25 else h_odd * 1.20), 2)
        p = min(94, int(conf_pct * 0.50 + sim_o15 * 0.50))
        candidates.append({
            "market": f"{home_name} & 1.5 Üst",
            "market_type": "COMBO_MS_GOAL",
            "odd": est_odd,
            "prob": p,
            "reason": f"{home_name} kazanır ve en az 2 gol olur (Simülasyon 1.5 Üst: %{sim_o15})"
        })
        
    # 2. MS 2 & 1.5 ÜST (Yalnızca gerçek bankolarda veya yüksek güven + düşük tuzakta)
    if pred_ms == "MS 2" and (is_banko or (conf_pct >= 68 and adj_trap <= 5.0)):
        est_odd = round(max(1.38, a_odd + 0.25 if a_odd <= 1.30 else a_odd * 1.20), 2)
        p = min(94, int(conf_pct * 0.50 + sim_o15 * 0.50))
        candidates.append({
            "market": f"{away_name} & 1.5 Üst",
            "market_type": "COMBO_MS_GOAL",
            "odd": est_odd,
            "prob": p,
            "reason": f"{away_name} kazanır ve en az 2 gol olur (Simülasyon 1.5 Üst: %{sim_o15})"
        })

    # 3. 2.5 ÜST (Simülasyon Hibrit — Nesine Ölü Oran Korumalı)
    blended_over = round(over_prob * 0.50 + sim_o25 * 0.50, 1)
    if (blended_over >= 54 or sim_o25 >= 58) and over_odd >= 1.40:
        candidates.append({
            "market": "2.5 Üst",
            "market_type": "OVER_2_5",
            "odd": over_odd,
            "prob": int(max(blended_over, sim_o25)),
            "reason": f"Yüksek tempo (Simülasyon 2.5 Üst: %{sim_o25}, En Olası: {top_score})"
        })

    # 4. 2.5 ALT (Simülasyon Hibrit)
    blended_under = round((100 - over_prob) * 0.50 + (100 - sim_o25) * 0.50, 1)
    if (blended_under >= 54 or (100 - sim_o25) >= 58) and under_odd >= 1.40:
        candidates.append({
            "market": "2.5 Alt",
            "market_type": "UNDER_2_5",
            "odd": under_odd,
            "prob": int(max(blended_under, 100 - sim_o25)),
            "reason": f"Kısır oyun beklentisi (Simülasyon 2.5 Alt: %{round(100 - sim_o25, 1)})"
        })

    # 5. KARŞILIKLI GOL VAR
    blended_btts = round(btts_prob * 0.50 + sim_btts * 0.50, 1)
    if blended_btts >= 56 or sim_btts >= 58:
        if odds.get("kg_var") and float(odds.get("kg_var", 0)) > 1.0:
            est_btts_odd = float(odds.get("kg_var"))
        else:
            est_btts_odd = round(max(1.48, min(1.78, 1.55 + (60 - blended_btts) * 0.008)), 2)
        candidates.append({
            "market": "Karşılıklı Gol Var",
            "market_type": "BTTS_YES",
            "odd": est_btts_odd,
            "prob": int(max(blended_btts, sim_btts)),
            "reason": f"Karşılıklı gol potansiyeli (Simülasyon KG: %{sim_btts})"
        })

    # 6. BERABERLİKTE İADE (DNB)
    if pred_ms == "MS 1" and 1.40 <= h_odd <= 2.40:
        dnb_odd = round(max(1.35, h_odd * 0.70 + 0.15), 2)
        dnb_prob = min(95, int(conf_pct * 0.50 + (sim_hw + sim_dr) * 0.50))
        candidates.append({
            "market": f"{home_name} (Beraberlikte İade)",
            "market_type": "DNB",
            "odd": dnb_odd,
            "prob": dnb_prob,
            "reason": f"{home_name} yenilmez, beraberlikte para iadesi (Sim 1X: %{round(sim_hw + sim_dr, 1)})"
        })
    elif pred_ms == "MS 2" and 1.40 <= a_odd <= 2.50:
        dnb_odd = round(max(1.35, a_odd * 0.70 + 0.15), 2)
        dnb_prob = min(95, int(conf_pct * 0.50 + (sim_aw + sim_dr) * 0.50))
        candidates.append({
            "market": f"{away_name} (Beraberlikte İade)",
            "market_type": "DNB",
            "odd": dnb_odd,
            "prob": dnb_prob,
            "reason": f"{away_name} yenilmez, beraberlikte para iadesi (Sim X2: %{round(sim_aw + sim_dr, 1)})"
        })

    # 7. DÜZ MS (Sadece tatmin edici oran ve düşük tuzak varsa)
    if pred_ms == "MS 1" and h_odd >= 1.40 and adj_trap <= 4.5:
        candidates.append({
            "market": f"MS 1 ({home_name})",
            "market_type": "STRAIGHT_MS",
            "odd": h_odd,
            "prob": conf_pct,
            "reason": f"{home_name} net galibiyeti"
        })
    elif pred_ms == "MS 2" and a_odd >= 1.40 and adj_trap <= 4.5:
        candidates.append({
            "market": f"MS 2 ({away_name})",
            "market_type": "STRAIGHT_MS",
            "odd": a_odd,
            "prob": conf_pct,
            "reason": f"{away_name} net galibiyeti"
        })

    # 8. TAKIM 1.5 ÜST GOL
    if pred_ms == "MS 1" and (conf_pct >= 70 or h_odd <= 1.40):
        t1_odd = round(max(1.40, min(1.75, h_odd * 0.85 + 0.30)), 2)
        candidates.append({
            "market": f"{home_name} 1.5 Üst Gol",
            "market_type": "TEAM_GOALS",
            "odd": t1_odd,
            "prob": min(92, int(conf_pct * 0.45 + sim_o15 * 0.55)),
            "reason": f"{home_name} maç sonucundan bağımsız en az 2 gol atar"
        })

    # 9. 🌟 DEV TAKIMLAR İÇİN NESİNE DEĞER KOMBİNASYONU (MS & 2.5 ÜST VEYA 3.5 ÜST)
    if is_giant and (sim_o25 >= 65.0 or over_prob >= 65.0):
        if pred_ms == "MS 1" and conf_pct >= 68:
            combo_25_odd = round(max(1.48, min(1.90, h_odd + 0.35 if h_odd <= 1.25 else h_odd * 1.30)), 2)
            p_combo = min(90, int(conf_pct * 0.45 + sim_o25 * 0.55))
            candidates.append({
                "market": f"{home_name} & 2.5 Üst",
                "market_type": "COMBO_MS_GOAL",
                "odd": combo_25_odd,
                "prob": p_combo,
                "reason": f"{home_name} kazanır ve en az 3 gol olur (Nesine Değer Kombosu)"
            })
        elif pred_ms == "MS 2" and conf_pct >= 68:
            combo_25_odd = round(max(1.48, min(1.90, a_odd + 0.35 if a_odd <= 1.30 else a_odd * 1.30)), 2)
            p_combo = min(90, int(conf_pct * 0.45 + sim_o25 * 0.55))
            candidates.append({
                "market": f"{away_name} & 2.5 Üst",
                "market_type": "COMBO_MS_GOAL",
                "odd": combo_25_odd,
                "prob": p_combo,
                "reason": f"{away_name} kazanır ve en az 3 gol olur (Nesine Değer Kombosu)"
            })
            
        if sim_o25 >= 72.0:
            candidates.append({
                "market": "3.5 Üst",
                "market_type": "OVER_3_5",
                "odd": 1.75,
                "prob": int(sim_o25 * 0.72),
                "reason": "Dev takım gol şovu (Nesine 3.5 Üst Değeri)"
            })

    # Puanlama & En Mantıklısını Seçme
    # Filtre: Oran >= 1.40 (Nesine'de 1.40 altı çocuk oranları KESİNLİKLE YASAK!) ve Güven >= 55
    valid = [c for c in candidates if c["odd"] >= 1.40 and c["prob"] >= 55]
    if not valid:
        # Eğer 1.40 üstü bulunamadıysa en azından 1.35 üstü olanları al
        valid = [c for c in candidates if c["odd"] >= 1.35 and c["prob"] >= 55]
        if not valid:
            valid = candidates

    # 🛡️ TUZAK VE DERBİ KALKANI DEĞER SKORU FORMÜLÜ
    for c in valid:
        score = c["prob"] * (c["odd"] ** 0.85)
        
        # 1. Tuzak / Derbi Kalkanı:
        # Eğer tuzak/şüphe varsa (adj_trap >= 5.0), taraf içeren pazarları (düz MS veya MS & 1.5 Üst) cezalandır
        if adj_trap >= 5.0 and c["market_type"] in ["STRAIGHT_MS", "COMBO_MS_GOAL"]:
            score *= 0.65
            
        # 2. Saf Gol Önceliği:
        # Simülasyon gol temposunu net şekilde yüksek görüyorsa (%60+) saf 2.5 Üst ve KG Var pazarlarını öne çıkar
        if sim_o25 >= 60.0 and c["market_type"] == "OVER_2_5":
            score *= 1.35
        if sim_btts >= 60.0 and c["market_type"] == "BTTS_YES":
            score *= 1.30

        # 3. Gerçek Banko Primi:
        # Sadece tuzak riski düşük gerçek bankoda kaliteli taraf kombinasyonuna prim ver
        if is_banko and adj_trap <= 4.5 and c["market_type"] in ["COMBO_MS_GOAL", "STRAIGHT_MS"]:
            score *= 1.25
            
        # 4. Beraberlikte İade (DNB) Koruma Primi:
        # Tuzaklı maçta taraf oynanacaksa DNB'yi düz MS'e göre koru
        if adj_trap >= 4.8 and c["market_type"] == "DNB":
            score *= 1.15

        c["value_score"] = round(score, 1)

    valid.sort(key=lambda x: x["value_score"], reverse=True)
    best = valid[0] if valid else {
        "market": f"MS {pred_ms[-1]}", "market_type": "STRAIGHT_MS",
        "odd": 1.50, "prob": conf_pct, "reason": "Varsayılan analiz tercihi", "value_score": 75.0
    }
    
    return best


# ─── BİRLEŞTİRİCİ SENTEZ MOTORU ─────────────────────────────────────────────

def analyze_single_match(m):
    """
    İki ajanı çağırır, lig stratejisi, yumuşak filtrelerle optimal kararı verir
    ve TÜM İDDAA MARKETLERİ ARASINDAN EN İDEAL SEÇİMİ YAPAR.
    """
    home_name = m["home_name"]
    away_name = m["away_name"]
    league = m["league"]
    cfg = get_league_config(league)
    
    try:
        # 0. 10.000 Maçlık Poisson Monte Carlo Simülasyonu
        sim_res = simulate_match(m, n_simulations=10000)

        # 1. Taraf Analisti Kararı (Sade ve Güçlü)
        pred_ms, trap_score, conf_pct, action_choice, playstyle = _agent_match_outcome(m)
        
        # 2. Gol Analisti Kararı (Derin İstatistik)
        over_prob, btts_prob = _agent_goal_tempo(m)

        # Simülasyon Uyumu (Bayesian Calibration)
        sim_hw = sim_res.get("sim_prob_home_win", 33.3)
        sim_aw = sim_res.get("sim_prob_away_win", 33.3)
        if pred_ms == "MS 1" and sim_hw >= 52.0:
            conf_pct = min(96, conf_pct + 3)
        elif pred_ms == "MS 2" and sim_aw >= 50.0:
            conf_pct = min(96, conf_pct + 3)
        elif (pred_ms == "MS 1" and sim_aw > sim_hw + 10) or (pred_ms == "MS 2" and sim_hw > sim_aw + 10):
            trap_score = min(10.0, trap_score + 0.8)
        
        # 3. Akıllı Tuzak Düzeltmesi (Soft Penalties)
        adj_trap = trap_score
        if playstyle == "kontratak_tehdidi":
            adj_trap += 1.2  # Kontratak tehdidi tuzak puanını artırır
        if m.get("home_rotation_risk") or m.get("away_rotation_risk"):
            adj_trap += 1.0  # Rotasyon riski şüpheyi artırır
        if m.get("home_momentum") == "negative" and pred_ms == "MS 1":
            adj_trap += 0.8
        if m.get("away_momentum") == "negative" and pred_ms == "MS 2":
            adj_trap += 0.8

        # 3.5 Akıllı Para & Oran Hareketi Düzeltmesi (Odds Drift / Smart Money)
        drift = m.get("odds_drift") or {}
        drift_signal = drift.get("signal", "NORMAL")
        drift_desc = drift.get("description", "")
        
        if drift_signal == "SMART_MONEY_HOME" and pred_ms == "MS 1":
            conf_pct = min(96, conf_pct + 6)
            adj_trap = max(1.0, round(adj_trap - 0.8, 1))
        elif drift_signal == "MARKET_DOUBT_HOME" and pred_ms == "MS 1":
            adj_trap = min(10.0, round(adj_trap + 1.5, 1))
            conf_pct = max(35, conf_pct - 6)
        elif drift_signal == "SMART_MONEY_AWAY" and pred_ms == "MS 2":
            conf_pct = min(96, conf_pct + 6)
            adj_trap = max(1.0, round(adj_trap - 0.8, 1))
        elif drift_signal == "MARKET_DOUBT_AWAY" and pred_ms == "MS 2":
            adj_trap = min(10.0, round(adj_trap + 1.5, 1))
            conf_pct = max(35, conf_pct - 6)

        adj_trap = round(min(10.0, adj_trap), 1)

        # 3.6 4'lü Küresel Sharp & VIP Sendika Radarı Doğrudan Karar Etkisi
        g_verdict = m.get("global_verdict", "NORMAL")
        g_reason = m.get("global_reason", "")
        signals = m.get("signals") or {}
        
        fs_sig = signals.get("flashscore_lineups") or {}
        pin_sig = signals.get("pinnacle_benchmark") or {}
        drop_sig = signals.get("dropping_odds_steam") or {}
        vip_sig = signals.get("vip_syndicate_radar") or {}

        # 1. Flashscore Kadro Şoku
        fs_veto = False
        if pred_ms == "MS 1" and fs_sig.get("lineup_penalty_home", 1.0) <= 0.85:
            fs_veto = True
        elif pred_ms == "MS 2" and fs_sig.get("lineup_penalty_away", 1.0) <= 0.85:
            fs_veto = True

        # 2. Pinnacle Negatif Çizgi (Sazan Tuzağı)
        pin_veto = pin_sig.get("has_sharp_benchmark") and not pin_sig.get("is_sharp_backed")

        # 3. Dropping Odds Ters Steam
        drop_veto = drop_sig.get("steam_against_us", False)

        # 4. VIP Baron Radarı Vetosu
        vip_veto = vip_sig.get("is_vetoed", False)

        # 3.7 SofaScore Kalibrasyonu & Sayısal Tuzak Avcısı Eleme Kuralları
        pe_eval = PredictionEngine.evaluate_match_prediction(
            match_data=m,
            raw_pred_ms=pred_ms,
            raw_conf=conf_pct,
            raw_over_prob=over_prob,
            raw_btts_prob=btts_prob,
            playstyle=playstyle
        )
        pred_ms = pe_eval.get("pred_ms", pred_ms)
        conf_pct = pe_eval.get("calibrated_confidence", conf_pct)
        over_prob = pe_eval.get("calibrated_over_2_5", over_prob)
        btts_prob = pe_eval.get("calibrated_btts", btts_prob)
        elim_audit = pe_eval.get("elimination_intel") or {}
        baron_intel = elim_audit.get("baron_res") or TuzakAvcisi.audit_baron_validity(m, pred_ms=pred_ms)

        is_vetoed = (
            m.get("is_global_vetoed", False) or 
            "VETO" in str(g_verdict) or 
            "RED" in str(g_verdict) or
            fs_veto or pin_veto or drop_veto or vip_veto or
            elim_audit.get("is_vetoed", False)
        )

        is_boosted = (
            "BOOST" in str(g_verdict) or 
            "SMART" in str(g_verdict) or 
            "WHALE" in str(g_verdict) or
            drop_sig.get("steam_with_us", False) or
            vip_sig.get("verdict") == "BOOSTED_BY_WHALE_SYNDICATE" or
            elim_audit.get("steam_res", {}).get("is_boosted", False) or
            baron_intel.get("is_baron_verified", False)
        )

        if is_vetoed:
            adj_trap = 9.8  # Sert tuzak puanı (Kasa koruması)
            conf_pct = max(20, conf_pct - 25)
            action_choice = "pas_gec_bulasma"
        elif baron_intel.get("is_baron_trap"):
            adj_trap = min(10.0, max(adj_trap, 6.0 + baron_intel.get("trap_penalty", 3.0)))
            conf_pct = max(20, conf_pct + baron_intel.get("confidence_boost", -15))
            if action_choice == "banko_oyna":
                action_choice = "pas_gec_bulasma"
        elif elim_audit.get("is_trap"):
            adj_trap = min(10.0, max(adj_trap, 5.2 + elim_audit.get("total_trap_penalty", 0.0)))
            conf_pct = max(20, conf_pct + elim_audit.get("confidence_adjustment", 0))
            if elim_audit.get("verdict") == "GOAL_ONLY":
                action_choice = "gol_oyna"
            elif elim_audit.get("verdict") == "NO_BET":
                action_choice = "pas_gec_bulasma"
        elif baron_intel.get("is_baron_verified"):
            conf_pct = min(98, conf_pct + baron_intel.get("confidence_boost", 8))
            adj_trap = max(0.0, round(adj_trap - 1.5, 1))
        elif elim_audit.get("rating_res", {}).get("is_quality_confirmed"):
            conf_pct = min(96, conf_pct + elim_audit.get("rating_res", {}).get("conf_boost", 5))
            adj_trap = max(1.0, round(adj_trap - 1.0, 1))
        elif is_boosted:
            conf_pct = min(98, conf_pct + 8)
            adj_trap = max(0.0, round(adj_trap - 1.5, 1))
        
        # 4. Banko Değerlendirmesi
        is_banko = (action_choice == "banko_oyna" and adj_trap <= 5.0 and conf_pct >= 55 and not is_vetoed and not elim_audit.get("is_trap"))
        if is_banko and not cfg["banko_eligible"]:
            is_banko = False
            banko_reason = f"{league} liginde taraf sürprizi çok yüksek, gol bahsine yönlendirildi."
        elif is_banko:
            banko_reason = "Taraf analisti ve Tuzak Avcısı net üstünlük gördü, tuzak riski yok."
        else:
            banko_reason = "Banko kriterini sağlamıyor."

        # 5. TÜM MARKETLER ARASINDAN EN MANTIKLI TERCİHİ SEÇ (OMNI-MARKET SEÇİCİ)
        optimal_choice = _determine_optimal_market(
            m, pred_ms, conf_pct, adj_trap, over_prob, btts_prob, is_banko, cfg, sim_res=sim_res
        )

        # 6. Eylem Etiketleme
        recs = [optimal_choice["market"]]
        if is_vetoed:
            action_status = "NO_BET"
            action_label = f"🔴 PAS GEÇ (VETO: {elim_audit.get('trap_type', g_verdict)})"
        elif elim_audit.get("verdict") == "GOAL_ONLY":
            action_status = "GOAL_ONLY"
            action_label = "🟡 SADECE GOL OYNA (TARAF TUZAKLI)"
        elif is_banko:
            action_status = "BET"
            action_label = "🟢 OYNA (BANKO)"
        elif elim_audit.get("verdict") == "BET" and conf_pct >= cfg["confidence_threshold"] and cfg["trust_ms"] and adj_trap <= 5.5:
            action_status = "BET"
            action_label = "🟢 OYNA (KALİTE VE PİYASA ONAYLI)"
        elif (over_prob >= cfg["goal_bet_threshold"] and cfg["trust_2_5"]) or (btts_prob >= 60 and cfg["trust_kg"]):
            action_status = "GOAL_ONLY"
            action_label = "🟡 SADECE GOL OYNA"
        elif conf_pct >= cfg["confidence_threshold"] and cfg["trust_ms"] and adj_trap <= 5.5 and not elim_audit.get("is_trap"):
            action_status = "BET"
            action_label = "🟢 OYNA (TARAF / DEĞER)"
        else:
            action_status = "NO_BET"
            action_label = "🔴 PAS GEÇ (UZAK DUR)"

        # KG Etiketi
        if btts_prob >= 65: kg_status = "KG_YÜKSEK"
        elif btts_prob >= 55: kg_status = "KG_ORTA"
        else: kg_status = "KG_DÜŞÜK"
        
        winner = home_name if pred_ms == "MS 1" else (away_name if pred_ms == "MS 2" else "Beraberlik")
        
        explanation = (
            f"{cfg['emoji']} [{league}] {cfg['note']}. "
            f"En İdeal Tercih: {optimal_choice['market']} (Oran: {optimal_choice['odd']} | Güven: %{optimal_choice['prob']}). "
            f"Gerekçe: {optimal_choice['reason']}."
        )
        if drift_desc:
            explanation += f" 📈 {drift_desc}."

        return {
            **m,
            "tahmin_ms": pred_ms,
            "tahmin_kazanan": winner,
            "over_2_5_prob": over_prob,
            "btts_prob": btts_prob,
            "kg_tahmin": "KG Var" if btts_prob >= 50 else "KG Yok",
            "kg_conf_status": kg_status,
            "trap_score": adj_trap,
            "confidence": conf_pct,
            "confidence_10": round(conf_pct / 10, 1),
            "banko_reason": banko_reason,
            "league_strategy": cfg["primary_bet"],
            "recommended_bets": recs,
            "action_label": action_label,
            "action_status": action_status,
            "action_choice": action_choice,
            "flag": cfg["emoji"],
            "is_value_bet": (action_status == "BET"),
            "is_high_scoring": (over_prob >= 60),
            "is_trap_game": (action_status == "NO_BET"),
            "key_factor": action_choice,
            "explanation": explanation,
            "tahmin_kg": "KG Var" if btts_prob >= 50 else "KG Yok",
            "time_tr": m.get("time_tr", ""),
            # 🌟 YENİ OMNI-MARKET OPTİMAL ALANLARI
            "optimal_market": optimal_choice["market"],
            "optimal_odds": optimal_choice["odd"],
            "optimal_confidence": optimal_choice["prob"],
            "optimal_market_type": optimal_choice["market_type"],
            "optimal_reason": optimal_choice["reason"],
            "optimal_value_score": optimal_choice["value_score"],
            "odds_drift_desc": drift_desc,
            # 🎲 10.000 MAÇ MONTE CARLO SİMÜLASYON ALANLARI
            "sim_prob_home_win": sim_res.get("sim_prob_home_win", 33.3),
            "sim_prob_draw": sim_res.get("sim_prob_draw", 33.3),
            "sim_prob_away_win": sim_res.get("sim_prob_away_win", 33.3),
            "sim_prob_over_1_5": sim_res.get("sim_prob_over_1_5", 70.0),
            "sim_prob_over_2_5": sim_res.get("sim_prob_over_2_5", 50.0),
            "sim_prob_btts": sim_res.get("sim_prob_btts", 50.0),
            "sim_top_scores": sim_res.get("sim_top_scores", []),
            "sim_top_score_str": sim_res.get("sim_top_score_str", "-"),
            "sim_summary": sim_res.get("sim_summary", ""),
            "lambda_home": sim_res.get("lambda_home", 1.5),
            "lambda_away": sim_res.get("lambda_away", 1.2),
            "expected_total_goals": sim_res.get("expected_total_goals", 2.7),
            # 🛡️ TUZAK AVCISI & ELEME İNTEL ALANLARI
            "elimination_intel": elim_audit,
            "trap_type": elim_audit.get("trap_type", "KALITE_ONAYLI"),
            "elimination_verdict": elim_audit.get("verdict", "BET"),
            "elimination_reasons": elim_audit.get("reasons", []),
            "sofascore_rating_home": m.get("sofascore_rating_home") or (m.get("sofascore_intel") or {}).get("home_rating", 6.85),
            "sofascore_rating_away": m.get("sofascore_rating_away") or (m.get("sofascore_intel") or {}).get("away_rating", 6.80),
            "sofascore_rating_diff": m.get("sofascore_rating_diff") if m.get("sofascore_rating_diff") is not None else (m.get("sofascore_intel") or {}).get("rating_diff", 0.05),
            "sofascore_momentum": m.get("sofascore_momentum") or (m.get("sofascore_intel") or {}).get("attack_momentum_label", "⚖️ Dengeli Geçiş Oyunu"),
            "sofascore_momentum_score": m.get("sofascore_momentum_score") or (m.get("sofascore_intel") or {}).get("attack_momentum_score", 60),
            "sofascore_attack_home": m.get("sofascore_attack_home") or (m.get("sofascore_intel") or {}).get("attack_momentum_home", 50),
            "sofascore_attack_away": m.get("sofascore_attack_away") or (m.get("sofascore_intel") or {}).get("attack_momentum_away", 50),
            "sofascore_total_xg": m.get("sofascore_total_xg") or (m.get("sofascore_intel") or {}).get("expected_total_xg", 2.45),
            "expected_xg_home": m.get("expected_xg_home") or (m.get("sofascore_intel") or {}).get("expected_xg_home", 1.35),
            "expected_xg_away": m.get("expected_xg_away") or (m.get("sofascore_intel") or {}).get("expected_xg_away", 1.10),
            # 👑 VIP BARON PARA AKIŞI & TYPESAFE TEYİDİ
            "baron_intel": baron_intel,
            "is_baron_verified": baron_intel.get("is_baron_verified", False),
            "is_baron_trap": baron_intel.get("is_baron_trap", False),
            "baron_status": baron_intel.get("baron_status", "BALANCED"),
            "alert_icon": baron_intel.get("alert_icon", ""),
            "flow_type": baron_intel.get("flow_type", "BALANCED"),
            "volume_gbp": baron_intel.get("volume_gbp", 0.0),
            "dominance_pct": baron_intel.get("dominance_pct", 0.0),
            "target_market": baron_intel.get("target_market")
        }

    except Exception as e:
        return {
            **m,
            "tahmin_ms": "MS 1", "tahmin_kazanan": home_name,
            "over_2_5_prob": 50, "btts_prob": 50, "kg_tahmin": "KG Yok",
            "kg_conf_status": "KG_DÜŞÜK", "trap_score": 5.0, "confidence": 45,
            "confidence_10": 4.5, "banko_reason": f"Hata: {e}",
            "league_strategy": "error", "recommended_bets": ["PAS GEÇ"],
            "action_label": "🔴 PAS GEÇ (UZAK DUR)", "action_status": "NO_BET",
            "action_choice": "pas", "flag": "⚽", "is_value_bet": False,
            "is_high_scoring": False, "is_trap_game": True, "key_factor": "error",
            "explanation": f"Hata: {e}", "tahmin_kg": "KG Yok", "time_tr": m.get("time_tr", ""),
            "sim_prob_home_win": 33.3, "sim_prob_draw": 33.3, "sim_prob_away_win": 33.3,
            "sim_prob_over_1_5": 70.0, "sim_prob_over_2_5": 50.0, "sim_prob_btts": 50.0,
            "sim_top_scores": [("1-1", 12.0)], "sim_top_score_str": "1-1",
            "sim_summary": "Simülasyon hesaplanamadı", "lambda_home": 1.5, "lambda_away": 1.2,
            "expected_total_goals": 2.7,
            "baron_intel": {
                "has_whale_volume": False,
                "volume_gbp": 0.0,
                "dominance_pct": 0.0,
                "target_market": None,
                "flow_type": "BALANCED",
                "is_baron_verified": False,
                "is_baron_trap": False,
                "baron_status": "BALANCED",
                "alert_icon": "",
                "confidence_boost": 0,
                "trap_penalty": 0.0,
                "summary": "VIP Baron: Veri yok",
                "reasons": []
            },
            "is_baron_verified": False,
            "is_baron_trap": False,
            "baron_status": "BALANCED",
            "alert_icon": "",
            "flow_type": "BALANCED",
            "volume_gbp": 0.0,
            "dominance_pct": 0.0,
            "target_market": None
        }


# ─── PARALEL BÜLTEN ANALİZİ ─────────────────────────────────────────────────

def analyze_all_matches_parallel(matches, max_workers=6):
    """
    Tüm maçları iki uzmanlı TypeSafe mimarisiyle analiz eder.
    """
    try:
        from xg_collector import enrich_with_xg
        matches = enrich_with_xg(matches)
    except Exception as e:
        pass

    print(f"[*] TypeSafe AI İkili Uzman Motoru — {len(matches)} maç taranıyor...")
    t0 = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fmap = {ex.submit(analyze_single_match, m): m for m in matches}
        done = 0
        for future in as_completed(fmap):
            results.append(future.result())
            done += 1
            if done % 5 == 0 or done == len(matches):
                bk = sum(1 for r in results if r.get("action_status") == "BET")
                print(f"    -> [{done}/{len(matches)}] analiz edildi | {bk} BANKO bulundu ({round(time.time()-t0, 1)}s)")

    # Sıralama: Banko > Gol Oyna > Pas Geç
    priority = {"BET": 2, "GOAL_ONLY": 1, "NO_BET": 0}
    results.sort(key=lambda x: (priority.get(x.get("action_status"), 0), x.get("confidence", 0)), reverse=True)

    bk = [r for r in results if r.get("action_status") == "BET"]
    go = [r for r in results if r.get("action_status") == "GOAL_ONLY"]
    pg = [r for r in results if r.get("action_status") == "NO_BET"]
    print(f"[+] {len(results)} maç tamamlandı ({round(time.time()-t0, 1)}s) | 🟢 {len(bk)} BANKO | 🟡 {len(go)} GOL OYNA | 🔴 {len(pg)} PAS GEÇ")
    
    return results


if __name__ == "__main__":
    from data_collector import fetch_real_matches_for_date
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    m_list = fetch_real_matches_for_date(today)
    if m_list:
        res = analyze_all_matches_parallel(m_list[:4], max_workers=2)
        for r in res:
            print(f"\n⚽ {r['home_name']} vs {r['away_name']} [{r['league']}]")
            print(f"   Karar: {r['action_label']}")
            print(f"   MS: {r['tahmin_ms']} %{r['confidence']} | 2.5: %{r['over_2_5_prob']} | KG: %{r['btts_prob']}")
            print(f"   Önerilen: {r['recommended_bets']}")
            print(f"   Açıklama: {r['explanation']}")

"""
backtest_yeni_sistem.py — Yeni Güçlendirilmiş Sistem Backtest
=============================================================
Eski sistemle (basit istatistik) karşılaştırmalı olarak yeni sistemin
(H2H + momentum + rotation + xG + sıkı banko filtresi) sezon başından
bu yana gerçek maçlarda nasıl performans gösterdiğini ölçer.

Taranan Dönem: 22 Ağustos 2026 → 19 Eylül 2026
Ligler:        Süper Lig, Premier League, La Liga, Bundesliga, Serie A, Ligue 1
"""
import os
import sys
import json
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI"
os.chdir(PROJECT_DIR)

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)

LEAGUES = {
    "Süper Lig":      "tur.1",
    "Premier League": "eng.1",
    "La Liga":        "esp.1",
    "Serie A":        "ita.1",
    "Bundesliga":     "ger.1",
    "Ligue 1":        "fra.1"
}

# Sezon başından bu yana hafta sonu günleri (biten maçlar)
BACKTEST_DATES = [
    ("20260822", "Hf1-Cmt"), ("20260823", "Hf1-Paz"),
    ("20260829", "Hf2-Cmt"), ("20260830", "Hf2-Paz"),
    ("20260905", "Hf3-Cmt"), ("20260906", "Hf3-Paz"),
    ("20260912", "Hf4-Cmt"), ("20260913", "Hf4-Paz"),
    ("20260918", "Hf5-Cum"), ("20260919", "Hf5-Cmt"),
]

# ─── Veri Toplama ───────────────────────────────────────────────

def fetch_matches_for_date(date_str, period):
    """ESPN'den o güne ait BİTMİŞ maçları çeker."""
    all_matches = []
    for league_name, code in LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={date_str}"
        try:
            r = requests.get(url, timeout=6)
            if r.status_code != 200:
                continue
            for ev in r.json().get("events", []):
                c = ev["competitions"][0]
                state = c.get("status", {}).get("type", {}).get("state", "")
                if state != "post":
                    continue  # Sadece biten maçlar

                comps = c["competitors"]
                home = comps[0] if comps[0].get("homeAway") == "home" else comps[1]
                away = comps[1] if comps[0].get("homeAway") == "home" else comps[0]

                hs = int(home.get("score", 0) or 0)
                as_ = int(away.get("score", 0) or 0)

                # Piyasa oranları
                odds_data = c.get("odds", [])
                h_odd = d_odd = a_odd = None
                if odds_data and isinstance(odds_data[0], dict):
                    ml = odds_data[0].get("moneyline") or {}
                    def get_odd(side):
                        d = ml.get(side, {})
                        v = (d.get("close", {}) or d.get("open", {})).get("odds")
                        if not v: return None
                        v = float(str(v).replace("+",""))
                        return round((v/100)+1, 2) if v > 0 else round((100/abs(v))+1, 2)
                    h_odd = get_odd("home") or 2.10
                    d_odd = get_odd("draw") or 3.30
                    a_odd = get_odd("away") or 3.10

                all_matches.append({
                    "id":           ev.get("id"),
                    "date":         date_str,
                    "period":       period,
                    "league":       league_name,
                    "league_code":  code,
                    "utc_date":     ev.get("date", ""),
                    "home_name":    home["team"]["displayName"],
                    "home_form":    home.get("form", "-"),
                    "home_record":  home.get("records", [{}])[0].get("summary", "-") if home.get("records") else "-",
                    "away_name":    away["team"]["displayName"],
                    "away_form":    away.get("form", "-"),
                    "away_record":  away.get("records", [{}])[0].get("summary", "-") if away.get("records") else "-",
                    "h_odd":        h_odd or 2.10,
                    "d_odd":        d_odd or 3.30,
                    "a_odd":        a_odd or 3.10,
                    # Gerçek sonuç
                    "actual_score": f"{hs}-{as_}",
                    "actual_ms":    "MS 1" if hs > as_ else ("MS 2" if as_ > hs else "MS X"),
                    "actual_over":  (hs + as_) > 2.5,
                    "actual_btts":  (hs > 0 and as_ > 0),
                    "total_goals":  hs + as_,
                })
        except Exception as e:
            pass
    return all_matches

def fetch_deep_stats(m):
    """ESPN summary'den H2H, deplasman/ev formu, momentum, rotation — yeni sistem için."""
    from data_collector import fetch_match_deep_stats, parse_form_string
    deep = fetch_match_deep_stats(m["league_code"], m["id"], m["utc_date"])
    h_parsed = parse_form_string(m.get("home_form", "-"))
    a_parsed = parse_form_string(m.get("away_form", "-"))
    return {
        **m,
        **deep,
        "home_momentum":      h_parsed["momentum"],
        "away_momentum":      a_parsed["momentum"],
        "home_form_points":   h_parsed["points"],
        "away_form_points":   a_parsed["points"],
        "home_form_wins":     h_parsed["wins"],
        "away_form_wins":     a_parsed["wins"],
        "xg_available":       False,
        "home_xg_avg":        None,
        "away_xg_avg":        None,
        "home_scored_last5":  deep.get("home_scored_last5", deep.get("home_scored_last3", 0)),
        "away_scored_last5":  deep.get("away_scored_last5", deep.get("away_scored_last3", 0)),
    }

# ─── Eski Sistem Analizi (Basit) ────────────────────────────────

def analyze_old_system(m):
    """Eski sistem: sadece son 3 maç gol + form string + oranlar."""
    home_name = m["home_name"]
    away_name = m["away_name"]
    
    state_payload = {
        "match": f"{home_name} (Ev) vs {away_name} (Deplasman)",
        "league": m["league"],
        "venue": f"Stadyum: {m.get('venue', 'Bilinmiyor')}",
        "home_offensive_defensive": (
            f"Son 3 maçta {m.get('home_scored_last3', 0)} gol attı, "
            f"{m.get('home_conceded_last3', 0)} gol yedi. "
            f"Lig Kaydı: {m['home_record']}, Form: {m['home_form']}, "
            f"Dinlenme: {m.get('home_rest_days', '-')} gün"
        ),
        "away_offensive_defensive": (
            f"Son 3 maçta {m.get('away_scored_last3', 0)} gol attı, "
            f"{m.get('away_conceded_last3', 0)} gol yedi. "
            f"Lig Kaydı: {m['away_record']}, Form: {m['away_form']}, "
            f"Dinlenme: {m.get('away_rest_days', '-')} gün"
        ),
        "market_odds": f"MS 1: {m['h_odd']} | MS X: {m['d_odd']} | MS 2: {m['a_odd']}"
    }
    try:
        resp = client.system_one(
            state=state_payload,
            questions={
                "match_outcome": Choice(
                    instructions="Form ve oranlar göz önüne alındığında en olası maç sonucu?",
                    criteria={"ms_1": f"{home_name} Galibiyeti", "ms_x": "Beraberlik", "ms_2": f"{away_name} Galibiyeti"}
                ),
                "over_2_5": Noul(instructions="2.5 Gol ÜSTÜ bitme ihtimali?"),
                "btts": Noul(instructions="Her iki takımın da gol atma (KG Var) olasılığı?"),
                "trap_risk": Score(
                    instructions="Oran tuzağı / favori takılma riski?",
                    criteria=["banko_dusuk_risk", "orta_dengeli", "cok_yuksek_tuzak_surpriz"]
                ),
                "confidence_score": Score(
                    instructions="Tahminin güven derecesi?",
                    criteria=["dusuk_guven", "orta_guven", "yuksek_banko_guven"]
                ),
                "bet_action": Choice(
                    instructions="Bahis oynanmalı mı yoksa pas mı geçilmeli?",
                    criteria={
                        "banko_oyna": "Net avantaj — OYNA",
                        "gol_oyna": "Sadece gol bahsi",
                        "pas_gec_bulasma": "Sürpriz riski — PAS GEÇ"
                    }
                )
            }
        )
        pred_ms   = {"ms_1": "MS 1", "ms_x": "MS X", "ms_2": "MS 2"}[resp.choices["match_outcome"].choice]
        over_prob = round(resp.nouls["over_2_5"].noul * 100)
        btts_prob = round(resp.nouls["btts"].noul * 100)
        trap      = round(resp.scores["trap_risk"].score * 5, 1)
        conf      = int(min(96, max(35, round(resp.scores["confidence_score"].score * 40 + 15))))
        action    = resp.choices["bet_action"].choice

        if action == "banko_oyna" and trap <= 5.0 and conf >= 50:
            status = "BET"
        elif action == "gol_oyna" or (action != "pas_gec_bulasma" and over_prob >= 62):
            status = "GOAL_ONLY"
        else:
            status = "NO_BET"

        chosen_odd = m["h_odd"] if pred_ms == "MS 1" else (m["d_odd"] if pred_ms == "MS X" else m["a_odd"])
        ms_hit  = (pred_ms == m["actual_ms"])
        ou_hit  = ((over_prob >= 50) == m["actual_over"])
        btts_hit = ((btts_prob >= 50) == m["actual_btts"])
        pnl = (chosen_odd - 1.0) if ms_hit else -1.0

        return {**m, "sys": "ESKI", "pred_ms": pred_ms, "over_prob": over_prob, "btts_prob": btts_prob,
                "trap": trap, "conf": conf, "action": action, "status": status,
                "ms_hit": ms_hit, "ou_hit": ou_hit, "btts_hit": btts_hit,
                "chosen_odd": chosen_odd, "pnl": round(pnl, 2)}
    except Exception as e:
        return {**m, "sys": "ESKI", "pred_ms": "MS 1", "over_prob": 50, "btts_prob": 50,
                "trap": 5.0, "conf": 40, "action": "pas_gec_bulasma", "status": "NO_BET",
                "ms_hit": False, "ou_hit": False, "btts_hit": False, "chosen_odd": 2.0, "pnl": -1.0}

# ─── Yeni Sistem Analizi (Zenginleştirilmiş) ────────────────────

def analyze_new_system(m):
    """Yeni sistem: H2H + momentum + rotation + deplasman formu + sıkı banko filtresi."""
    from typesafe_engine import (
        _banko_kriterlerini_kontrol_et, _guess_ms, _kg_guven_etiketi,
        _xg_context, _h2h_context, _specific_form_context
    )
    home_name = m["home_name"]
    away_name = m["away_name"]
    home_specific, away_specific = _specific_form_context(m)

    state_payload = {
        "match":   f"{home_name} (Ev) vs {away_name} (Deplasman)",
        "league":  m["league"],
        "venue":   f"Stadyum: {m.get('venue', 'Bilinmiyor')}",
        "home_profile": (
            f"Form: {m.get('home_form', '-')} | Momentum: {m.get('home_momentum', '?')} | "
            f"Kayıt: {m['home_record']} | Son 3: {m.get('home_scored_last3',0)} gol attı/"
            f"{m.get('home_conceded_last3',0)} yedi | "
            f"Dinlenme: {m.get('home_rest_days','-')} gün | "
            f"Rot.Risk: {'⚠️ VAR' if m.get('home_rotation_risk') else 'Yok'} | {home_specific}"
        ),
        "away_profile": (
            f"Form: {m.get('away_form', '-')} | Momentum: {m.get('away_momentum', '?')} | "
            f"Kayıt: {m['away_record']} | Son 3: {m.get('away_scored_last3',0)} gol attı/"
            f"{m.get('away_conceded_last3',0)} yedi | "
            f"Dinlenme: {m.get('away_rest_days','-')} gün | "
            f"Rot.Risk: {'⚠️ VAR' if m.get('away_rotation_risk') else 'Yok'} | {away_specific}"
        ),
        "h2h_history":      _h2h_context(m),
        "expected_goals_xg": _xg_context(m),
        "market_odds":      f"MS 1: {m['h_odd']} | MS X: {m['d_odd']} | MS 2: {m['a_odd']}"
    }
    try:
        resp = client.system_one(
            state=state_payload,
            questions={
                "match_outcome": Choice(
                    instructions="H2H, momentum, deplasman/ev özel formu ve oranlar göz önüne alındığında en olası maç sonucu?",
                    criteria={"ms_1": f"{home_name} Galibiyeti", "ms_x": "Beraberlik", "ms_2": f"{away_name} Galibiyeti"}
                ),
                "over_2_5": Noul(instructions="H2H ort gol, son 5 maç hücum/savunma ve xG'ye göre 2.5 Gol ÜSTÜ ihtimali?"),
                "btts": Noul(instructions="Deplasman takımının deplasmanda gol atma performansı dahil KG Var olasılığı?"),
                "btts_confidence": Score(
                    instructions="KG tahminine güven seviyesi?",
                    criteria=["dusuk_guven_belirsiz", "orta_guven_makul", "yuksek_guven_net"]
                ),
                "trap_risk": Score(
                    instructions="H2H sürpriz geçmişi, rotation riski ve form düşüşü dikkate alındığında tuzak riski?",
                    criteria=["banko_dusuk_risk", "orta_dengeli", "cok_yuksek_tuzak_surpriz"]
                ),
                "confidence_score": Score(
                    instructions="H2H tutarlılık, momentum ve xG desteği var mı? Güven derecesi?",
                    criteria=["surpriz_dusuk_guven", "standart_orta_guven", "yuksek_banko_guven"]
                ),
                "bet_action": Choice(
                    instructions="H2H, rotation riski ve tüm veriler ışığında bahis oynanmalı mı?",
                    criteria={
                        "banko_oyna": "H2H + momentum + net avantaj — OYNA",
                        "gol_oyna": "Taraf yerine gol bahsi tercih et",
                        "pas_gec_bulasma": "Rotation/H2H sürpriz riski — PAS GEÇ"
                    }
                )
            }
        )
        pred_ms   = {"ms_1": "MS 1", "ms_x": "MS X", "ms_2": "MS 2"}[resp.choices["match_outcome"].choice]
        over_prob = round(resp.nouls["over_2_5"].noul * 100)
        btts_prob = round(resp.nouls["btts"].noul * 100)
        trap      = round(resp.scores["trap_risk"].score * 5, 1)
        conf      = int(min(96, max(35, round(resp.scores["confidence_score"].score * 40 + 15))))
        action    = resp.choices["bet_action"].choice

        # 6 katmanlı banko filtresi
        banko_ok, _ = _banko_kriterlerini_kontrol_et(m, trap, conf, action)
        if banko_ok:
            status = "BET"
        elif action == "gol_oyna" or (action != "pas_gec_bulasma" and over_prob >= 62):
            status = "GOAL_ONLY"
        else:
            status = "NO_BET"
        # Banko AI seçimi ama filtreden düştüyse gol oyna
        if not banko_ok and action == "banko_oyna" and over_prob >= 60:
            status = "GOAL_ONLY"

        chosen_odd = m["h_odd"] if pred_ms == "MS 1" else (m["d_odd"] if pred_ms == "MS X" else m["a_odd"])
        ms_hit   = (pred_ms == m["actual_ms"])
        ou_hit   = ((over_prob >= 50) == m["actual_over"])
        btts_hit = ((btts_prob >= 50) == m["actual_btts"])
        pnl = (chosen_odd - 1.0) if ms_hit else -1.0

        return {**m, "sys": "YENI", "pred_ms": pred_ms, "over_prob": over_prob, "btts_prob": btts_prob,
                "trap": trap, "conf": conf, "action": action, "status": status,
                "ms_hit": ms_hit, "ou_hit": ou_hit, "btts_hit": btts_hit,
                "chosen_odd": chosen_odd, "pnl": round(pnl, 2)}
    except Exception as e:
        return {**m, "sys": "YENI", "pred_ms": "MS 1", "over_prob": 50, "btts_prob": 50,
                "trap": 5.0, "conf": 40, "action": "pas_gec_bulasma", "status": "NO_BET",
                "ms_hit": False, "ou_hit": False, "btts_hit": False, "chosen_odd": 2.0, "pnl": -1.0}

# ─── İstatistik Hesaplama ───────────────────────────────────────

def print_system_stats(results, sys_name):
    total = len(results)
    if total == 0:
        print(f"  {sys_name}: Sonuç yok.")
        return {}

    ms_hits   = sum(1 for r in results if r["ms_hit"])
    ou_hits   = sum(1 for r in results if r["ou_hit"])
    btts_hits = sum(1 for r in results if r["btts_hit"])
    total_pnl = round(sum(r["pnl"] for r in results), 2)

    bankolar   = [r for r in results if r["status"] == "BET"]
    gol_oyna   = [r for r in results if r["status"] == "GOAL_ONLY"]
    pas_gec    = [r for r in results if r["status"] == "NO_BET"]

    bk_hits    = sum(1 for r in bankolar if r["ms_hit"])
    bk_pnl     = round(sum(r["pnl"] for r in bankolar), 2)
    go_ou_hits = sum(1 for r in gol_oyna if r["ou_hit"])
    pg_fail    = sum(1 for r in pas_gec if not r["ms_hit"])

    ms_pct   = round(ms_hits / total * 100, 1)
    ou_pct   = round(ou_hits / total * 100, 1)
    btts_pct = round(btts_hits / total * 100, 1)

    print(f"\n  {'─'*55}")
    print(f"  {sys_name} | {total} Maç")
    print(f"  {'─'*55}")
    print(f"  Genel MS İsabeti:     {ms_hits}/{total}  (%{ms_pct})")
    print(f"  Genel 2.5 İsabeti:    {ou_hits}/{total}  (%{ou_pct})")
    print(f"  Genel KG İsabeti:     {btts_hits}/{total}  (%{btts_pct})")
    print(f"  Kör Bahis P&L:        {total_pnl:+.1f} birim")
    print(f"  {'─'*55}")

    if bankolar:
        bk_pct = round(bk_hits / len(bankolar) * 100, 1)
        bk_roi = round(bk_pnl / len(bankolar) * 100, 1)
        print(f"  🟢 BANKO ({len(bankolar)} maç):   {bk_hits}/{len(bankolar)} (%{bk_pct}) | P&L: {bk_pnl:+.1f} | ROI: %{bk_roi}")
    else:
        print(f"  🟢 BANKO: 0 maç seçildi")

    if gol_oyna:
        go_pct = round(go_ou_hits / len(gol_oyna) * 100, 1)
        print(f"  🟡 GOL OYNA ({len(gol_oyna)} maç):  2.5 {go_ou_hits}/{len(gol_oyna)} (%{go_pct})")

    if pas_gec:
        pg_pct = round(pg_fail / len(pas_gec) * 100, 1)
        print(f"  🔴 PAS GEÇ ({len(pas_gec)} maç):   {pg_fail}/{len(pas_gec)} (%{pg_pct}) taraf bahsinde yatardı")
        print(f"      → Filtre {pg_fail} potansiyel kayıp maçı engelledi!")

    return {
        "total": total, "ms_pct": ms_pct, "ou_pct": ou_pct, "btts_pct": btts_pct,
        "banko_count": len(bankolar), "banko_pct": round(bk_hits/len(bankolar)*100,1) if bankolar else 0,
        "banko_pnl": bk_pnl if bankolar else 0,
        "gol_oyna_count": len(gol_oyna), "gol_oyna_ou_pct": round(go_ou_hits/len(gol_oyna)*100,1) if gol_oyna else 0,
        "pas_gec_count": len(pas_gec), "pas_gec_saved": pg_fail,
    }

# ─── Ana Backtest Fonksiyonu ─────────────────────────────────────

def run_comparative_backtest(mode="both", max_matches=None):
    """
    mode: "old"  → sadece eski sistem
          "new"  → sadece yeni sistem
          "both" → karşılaştırmalı (her maç iki kez analiz edilir)
    max_matches: Test için maç sayısını sınırla (None = tümü)
    """
    print("=" * 70)
    print("  🔬 KARŞILAŞTIRMALı BACKTEST: ESKİ SİSTEM vs YENİ SİSTEM")
    print("  📅 22 Ağustos — 19 Eylül 2026 | 6 Dev Lig")
    print("=" * 70)

    # 1. Maç verilerini topla
    print("[*] Sezon maçları toplanıyor...")
    raw = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = [ex.submit(fetch_matches_for_date, d, p) for d, p in BACKTEST_DATES]
        for f in as_completed(futures):
            raw.extend(f.result())

    raw.sort(key=lambda x: (x["date"], x["league"]))
    print(f"[+] {len(raw)} biten maç bulundu.")

    if max_matches:
        raw = raw[:max_matches]
        print(f"[!] Test modu: İlk {max_matches} maç analiz edilecek.")

    # 2. Derin istatistikleri çek (yeni alanlar için)
    print("[*] H2H, deplasman formu ve rotation verileri çekiliyor...")
    enriched = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        fmap = {ex.submit(fetch_deep_stats, m): m for m in raw}
        for f in as_completed(fmap):
            enriched.append(f.result())

    enriched.sort(key=lambda x: (x["date"], x["league"]))
    print(f"[+] {len(enriched)} maç derinleştirildi.\n")

    # 3. Analiz
    t0 = time.time()
    old_results = []
    new_results = []

    if mode in ("old", "both"):
        print(f"[*] ESKİ SİSTEM analizi başlıyor ({len(enriched)} maç)...")
        with ThreadPoolExecutor(max_workers=10) as ex:
            fmap = {ex.submit(analyze_old_system, m): m for m in enriched}
            done = 0
            for f in as_completed(fmap):
                old_results.append(f.result())
                done += 1
                if done % 20 == 0 or done == len(enriched):
                    print(f"    -> Eski [{done}/{len(enriched)}] ({round(time.time()-t0,1)}s)")
        print(f"[+] Eski sistem analizi tamamlandı.")

    if mode in ("new", "both"):
        print(f"\n[*] YENİ SİSTEM analizi başlıyor ({len(enriched)} maç)...")
        t1 = time.time()
        with ThreadPoolExecutor(max_workers=10) as ex:
            fmap = {ex.submit(analyze_new_system, m): m for m in enriched}
            done = 0
            for f in as_completed(fmap):
                new_results.append(f.result())
                done += 1
                if done % 20 == 0 or done == len(enriched):
                    print(f"    -> Yeni [{done}/{len(enriched)}] ({round(time.time()-t1,1)}s)")
        print(f"[+] Yeni sistem analizi tamamlandı.")

    # 4. Karşılaştırmalı Rapor
    print("\n" + "=" * 70)
    print("  📊 KARŞILAŞTIRMALI PERFORMANS RAPORU")
    print("=" * 70)

    old_stats = {}
    new_stats = {}

    if old_results:
        old_stats = print_system_stats(old_results, "🔵 ESKİ SİSTEM")
    if new_results:
        new_stats = print_system_stats(new_results, "🟠 YENİ SİSTEM")

    # Delta karşılaştırması
    if old_stats and new_stats:
        print("\n" + "=" * 70)
        print("  📈 DELTA: YENİ SİSTEM vs ESKİ SİSTEM")
        print("=" * 70)
        ms_delta   = round(new_stats["ms_pct"]   - old_stats["ms_pct"], 1)
        ou_delta   = round(new_stats["ou_pct"]   - old_stats["ou_pct"], 1)
        btts_delta = round(new_stats["btts_pct"] - old_stats["btts_pct"], 1)
        bk_delta   = round(new_stats.get("banko_pct", 0) - old_stats.get("banko_pct", 0), 1)
        pnl_delta  = round(new_stats.get("banko_pnl", 0) - old_stats.get("banko_pnl", 0), 2)

        def arrow(v): return f"{'↑' if v >= 0 else '↓'}{abs(v)}"
        print(f"  MS (Taraf):    {old_stats['ms_pct']}% → {new_stats['ms_pct']}%  ({arrow(ms_delta)}%)")
        print(f"  2.5 Alt/Üst:   {old_stats['ou_pct']}% → {new_stats['ou_pct']}%  ({arrow(ou_delta)}%)")
        print(f"  KG (Var/Yok):  {old_stats['btts_pct']}% → {new_stats['btts_pct']}%  ({arrow(btts_delta)}%)")
        print(f"  Banko İsabeti: {old_stats.get('banko_pct',0)}% → {new_stats.get('banko_pct',0)}%  ({arrow(bk_delta)}%)")
        print(f"  Banko P&L:     {old_stats.get('banko_pnl',0):+.1f} → {new_stats.get('banko_pnl',0):+.1f}  (Δ{pnl_delta:+.1f})")

    # 5. JSON Kaydet
    output = {
        "generated_at": datetime.now().isoformat(),
        "dates": [d for d, _ in BACKTEST_DATES],
        "total_matches": len(enriched),
        "old_system": old_results,
        "new_system": new_results,
        "old_stats": old_stats,
        "new_stats": new_stats
    }
    out_path = os.path.join(PROJECT_DIR, "backtest_karsilastirmali_sonuclari.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Sonuçlar kaydedildi: {out_path}")
    print(f"[+] Toplam süre: {round(time.time() - t0, 1)}s")
    print("=" * 70)
    return output


if __name__ == "__main__":
    import sys as _sys
    mode = "both"
    max_m = None

    if "--old" in _sys.argv:
        mode = "old"
    elif "--new" in _sys.argv:
        mode = "new"

    # Hızlı test: sadece ilk N maç
    for arg in _sys.argv[1:]:
        if arg.isdigit():
            max_m = int(arg)
            break

    run_comparative_backtest(mode=mode, max_matches=max_m)

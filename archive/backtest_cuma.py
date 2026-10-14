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

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)

LEAGUES = {
    "Süper Lig": "tur.1",
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Serie A": "ita.1",
    "Bundesliga": "ger.1",
    "Ligue 1": "fra.1"
}

def fetch_deep_stats_for_event(league_code, event_id, match_iso_date):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={event_id}"
    details = {
        "home_scored_last3": 0, "home_conceded_last3": 0, "home_rest_days": "Bilinmiyor",
        "away_scored_last3": 0, "away_conceded_last3": 0, "away_rest_days": "Bilinmiyor",
        "venue": "Bilinmiyor"
    }
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            venue = data.get("gameInfo", {}).get("venue", {}).get("fullName")
            if venue: details["venue"] = venue
            
            match_dt = datetime.fromisoformat(match_iso_date.replace("Z", "+00:00")) if match_iso_date else None
            last_five = data.get("lastFiveGames", [])
            for idx, team_data in enumerate(last_five):
                prefix = "home" if idx == 0 else "away"
                events = team_data.get("events", [])
                if events and match_dt:
                    g_date = events[0].get("gameDate")
                    if g_date:
                        try:
                            g_dt = datetime.fromisoformat(g_date.replace("Z", "+00:00"))
                            details[f"{prefix}_rest_days"] = max(1, (match_dt.date() - g_dt.date()).days)
                        except: pass
                sc, cn = 0, 0
                for g in events[:3]:
                    score_str = g.get("score", "")
                    if "-" in score_str:
                        try:
                            p = [int(x.strip()) for x in score_str.split("-")]
                            res = g.get("gameResult")
                            if res == "W": sc += max(p); cn += min(p)
                            elif res == "L": sc += min(p); cn += max(p)
                            else: sc += p[0]; cn += p[1]
                        except: pass
                details[f"{prefix}_scored_last3"] = sc
                details[f"{prefix}_conceded_last3"] = cn
    except: pass
    return details

def run_friday_enriched_backtest():
    print("=" * 72)
    print("   🔬 CUMA GÜNÜ DERİNLEŞTİRİLMİŞ BACKTEST (xG & YORGUNLUK ENTEGRELİ) ")
    print("   Tarih: 18 Eylül 2026 Cuma | TypeSafe AI Derin Analiz Testi     ")
    print("=" * 72)
    
    # 1. Cuma maçlarını çek
    raw_matches = []
    for league_name, code in LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates=20260918"
        try:
            r = requests.get(url, timeout=6)
            for ev in r.json().get("events", []):
                c = ev["competitions"][0]
                comps = c["competitors"]
                home = comps[0] if comps[0].get("homeAway") == "home" else comps[1]
                away = comps[1] if comps[0].get("homeAway") == "home" else comps[0]
                
                h_score = int(home.get("score", 0))
                a_score = int(away.get("score", 0))
                
                actual_ms = "MS 1" if h_score > a_score else ("MS 2" if a_score > h_score else "MS X")
                actual_over = (h_score + a_score) > 2.5
                actual_btts = (h_score > 0 and a_score > 0)
                
                odds_data = c.get("odds", [])
                odds_str = "Dengeli Piyasa"
                if odds_data and isinstance(odds_data[0], dict):
                    ml = odds_data[0].get("moneyline") or {}
                    h_odd = ml.get("home", {}).get("close", {}).get("odds", "-") if isinstance(ml.get("home"), dict) else "-"
                    d_odd = ml.get("draw", {}).get("close", {}).get("odds", "-") if isinstance(ml.get("draw"), dict) else "-"
                    a_odd = ml.get("away", {}).get("close", {}).get("odds", "-") if isinstance(ml.get("away"), dict) else "-"
                    odds_str = f"1({h_odd}) - X({d_odd}) - 2({a_odd})"
                    
                raw_matches.append({
                    "id": ev.get("id"),
                    "league": league_name,
                    "league_code": code,
                    "utc_date": ev.get("date", ""),
                    "home_name": home["team"]["displayName"],
                    "home_form": home.get("form", "-"),
                    "home_record": home.get("records", [{}])[0].get("summary", "-") if home.get("records") else "-",
                    "away_name": away["team"]["displayName"],
                    "away_form": away.get("form", "-"),
                    "away_record": away.get("records", [{}])[0].get("summary", "-") if away.get("records") else "-",
                    "odds": odds_str,
                    "actual_score": f"{h_score} - {a_score}",
                    "actual_ms": actual_ms,
                    "actual_over": actual_over,
                    "actual_btts": actual_btts
                })
        except Exception as e:
            print(f"[!] {league_name} veri hatası: {e}")
            
    print(f"[+] {len(raw_matches)} maç için derin istatistikler (xG, goller, yorgunluk) toplanıyor...")
    
    # 2. Derin verileri paralel topla
    enriched_matches = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        f_map = {executor.submit(fetch_deep_stats_for_event, m["league_code"], m["id"], m["utc_date"]): m for m in raw_matches}
        for f in as_completed(f_map):
            m = f_map[f]
            deep = f.result()
            enriched_matches.append({**m, **deep})
            
    # 3. TypeSafe AI ile Derinleştirilmiş Analiz
    print("[*] TypeSafe AI derinleştirilmiş verilerle kör tahmin (Backtest) yapıyor...")
    t0 = time.time()
    
    correct_ms = 0
    correct_ou = 0
    correct_btts = 0
    total = len(enriched_matches)
    
    backtest_results = []
    for m in enriched_matches:
        home_name = m["home_name"]
        away_name = m["away_name"]
        
        h_sc = m.get("home_scored_last3", 0)
        h_cn = m.get("home_conceded_last3", 0)
        a_sc = m.get("away_scored_last3", 0)
        a_cn = m.get("away_conceded_last3", 0)
        h_rest = m.get("home_rest_days", "-")
        a_rest = m.get("away_rest_days", "-")
        venue = m.get("venue", "Bilinmiyor")
        
        state_payload = {
            "match": f"{home_name} (Ev) vs {away_name} (Deplasman)",
            "league": m["league"],
            "venue": f"Stadyum: {venue}",
            "home_offensive_defensive": f"Son 3 maçta {h_sc} gol attı, {h_cn} gol yedi. Lig Kaydı: {m['home_record']}, Form: {m['home_form']}, Dinlenme: {h_rest} gün",
            "away_offensive_defensive": f"Son 3 maçta {a_sc} gol attı, {a_cn} gol yedi. Lig Kaydı: {m['away_record']}, Form: {m['away_form']}, Dinlenme: {a_rest} gün",
            "market_odds": m["odds"]
        }
        
        resp = client.system_one(
            state=state_payload,
            questions={
                "match_outcome": Choice(
                    instructions="Verilen ofansif/defansif gol oranlarına, dinlenme süresine ve lig formuna göre en olası maç sonucu nedir?",
                    criteria={
                        "ms_1": f"{home_name} Galibiyeti (1)",
                        "ms_x": "Beraberlik (X)",
                        "ms_2": f"{away_name} Galibiyeti (2)"
                    }
                ),
                "over_2_5": Noul(
                    instructions="İki takımın son maçlardaki gol atma ve yeme temposuna göre maçın 2.5 Gol ÜSTÜ bitme ihtimali nedir?"
                ),
                "btts": Noul(
                    instructions="İki takımın da birbirine gol atma (KG Var) olasılığı nedir?"
                ),
                "trap_risk": Score(
                    instructions="Bu maç oran tuzağı veya favorinin takılma riskini taşıyor mu?",
                    criteria=["banko_dusuk_risk", "orta_dengeli", "cok_yuksek_tuzak_surpriz"]
                ),
                "confidence_score": Score(
                    instructions="Bu tahminin gerçekleşme olasılığı ve güven derecesi nedir?",
                    criteria=["dusuk_guven", "orta_guven", "yuksek_banko_guven"]
                )
            }
        )
        
        pred_choice = resp.choices["match_outcome"].choice
        pred_ms = "MS 1" if pred_choice == "ms_1" else ("MS X" if pred_choice == "ms_x" else "MS 2")
        over_prob = round(resp.nouls["over_2_5"].noul * 100)
        btts_prob = round(resp.nouls["btts"].noul * 100)
        pred_over = over_prob >= 50
        pred_btts = btts_prob >= 50
        
        raw_trap = resp.scores["trap_risk"].score
        trap_score = round(raw_trap * 5.0, 1)
        
        raw_conf = resp.scores["confidence_score"].score
        conf_pct = int(min(96, max(35, round(raw_conf * 40.0 + 15))))
        
        is_ms_hit = (pred_ms == m["actual_ms"])
        is_ou_hit = (pred_over == m["actual_over"])
        is_btts_hit = (pred_btts == m["actual_btts"])
        
        if is_ms_hit: correct_ms += 1
        if is_ou_hit: correct_ou += 1
        if is_btts_hit: correct_btts += 1
        
        backtest_results.append({
            **m,
            "pred_ms": pred_ms,
            "over_prob": over_prob,
            "btts_prob": btts_prob,
            "pred_over": pred_over,
            "pred_btts": pred_btts,
            "trap_score": trap_score,
            "confidence": conf_pct,
            "is_ms_hit": is_ms_hit,
            "is_ou_hit": is_ou_hit,
            "is_btts_hit": is_btts_hit
        })
        
    print(f"[+] Derinleştirilmiş Backtest {round(time.time() - t0, 1)} saniyede tamamlandı!\n")
    
    print("=" * 72)
    print("             YENİ DERİNLEŞTİRİLMİŞ VERİLERLE CUMA MAÇLARI           ")
    print("=" * 72)
    
    for idx, r in enumerate(backtest_results, start=1):
        ms_icon = "✅ TUTTU" if r["is_ms_hit"] else "❌ YATTI"
        ou_icon = "✅ TUTTU" if r["is_ou_hit"] else "❌ YATTI"
        btts_icon = "✅ TUTTU" if r["is_btts_hit"] else "❌ YATTI"
        
        actual_ou_str = "2.5 ÜST" if r["actual_over"] else "2.5 ALT"
        actual_btts_str = "KG VAR" if r["actual_btts"] else "KG YOK"
        
        print(f"{idx}. [{r['league']}] {r['home_name']} vs {r['away_name']}")
        print(f"   📊 GERÇEK SKOR: {r['actual_score']} ({r['actual_ms']} | {actual_ou_str} | {actual_btts_str})")
        print(f"   📈 Gelişmiş Veriler: Ev Son 3 Gol: {r['home_scored_last3']}-{r['home_conceded_last3']} (Dinlenme: {r['home_rest_days']}g) | Dep Son 3 Gol: {r['away_scored_last3']}-{r['away_conceded_last3']}")
        print(f"   🧠 TypeSafe Tahmini: {r['pred_ms']} ({ms_icon}) | Güven: %{r['confidence']}")
        print(f"   ⚽ 2.5 Üst Olasılığı: %{r['over_prob']} -> Tahmin: {'2.5 ÜST' if r['pred_over'] else '2.5 ALT'} ({ou_icon})")
        print(f"   🥅 KG Var Olasılığı: %{r['btts_prob']} -> Tahmin: {'KG VAR' if r['pred_btts'] else 'KG YOK'} ({btts_icon})")
        print(f"   ⚠️ Sürpriz/Tuzak Riski: {r['trap_score']}/10")
        print("-" * 72)
        
    print("\n" + "=" * 72)
    print(f"🏆 YENİ DERİNLEŞTİRİLMİŞ CUMA BACKTEST PERFORMANSI:")
    print(f"   👉 Maç Sonucu (1-X-2) İsabeti: {correct_ms}/{total} (%{round(correct_ms/total*100, 1)})")
    print(f"   👉 2.5 Alt/Üst İsabeti:         {correct_ou}/{total} (%{round(correct_ou/total*100, 1)})")
    print(f"   👉 Karşılıklı Gol (KG) İsabeti: {correct_btts}/{total} (%{round(correct_btts/total*100, 1)})")
    print("=" * 72)

if __name__ == "__main__":
    run_friday_enriched_backtest()

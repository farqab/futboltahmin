import os
import sys
import json
import time
import requests
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
    "UEFA Avrupa Ligi": "uefa.europa",
    "La Liga": "esp.1"
}

def run_thursday_backtest():
    print("=" * 70)
    print("   🏆 PERŞEMBE AVRUPA & LİG MAÇLARI CANLI BACKTEST (17 EYLÜL 2026) ")
    print("   ESPN Resmi Skorları ve TypeSafe AI Kör Tahmin Karşılaştırması  ")
    print("=" * 70)
    
    matches = []
    for league_name, code in LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates=20260917"
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
                    
                matches.append({
                    "league": league_name,
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
            
    print(f"[+] Perşembe günü oynanan {len(matches)} adet resmi maç tespit edildi.\n")
    
    correct_ms = 0
    correct_ou = 0
    correct_btts = 0
    total = len(matches)
    
    print("[*] TypeSafe AI maç öncesi verilerle kör tahmin (Backtest) yapıyor...")
    t0 = time.time()
    
    backtest_results = []
    for m in matches:
        home_name = m["home_name"]
        away_name = m["away_name"]
        
        state_payload = {
            "match": f"{home_name} vs {away_name}",
            "league": m["league"],
            "home_form": f"Form: {m['home_form']}, Kayıt: {m['home_record']}",
            "away_form": f"Form: {m['away_form']}, Kayıt: {m['away_record']}",
            "market_odds": m["odds"]
        }
        
        resp = client.system_one(
            state=state_payload,
            questions={
                "match_outcome": Choice(
                    instructions="Verilen takım güçlerine, lig/Avrupa formuna göre en olası maç sonucu nedir?",
                    criteria={
                        "ms_1": f"{home_name} Galibiyeti (1)",
                        "ms_x": "Beraberlik (X)",
                        "ms_2": f"{away_name} Galibiyeti (2)"
                    }
                ),
                "over_2_5": Noul(
                    instructions="İki takımın ofans ve defans kalitesine göre maçın 2.5 Gol ÜSTÜ bitme olasılığı nedir?"
                ),
                "btts": Noul(
                    instructions="İki takımın da birbirine gol atma (KG Var) ihtimali nedir?"
                ),
                "trap_risk": Score(
                    instructions="Bu maç oran tuzağı veya sürpriz risk barındırıyor mu?",
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
            "is_ms_hit": is_ms_hit,
            "is_ou_hit": is_ou_hit,
            "is_btts_hit": is_btts_hit
        })
        
    print(f"[+] Perşembe Backtesti {round(time.time() - t0, 1)} saniyede tamamlandı!\n")
    
    print("=" * 70)
    print("                 PERŞEMBE MAÇLARI DETAYLI ANALİZİ                   ")
    print("=" * 70)
    
    for idx, r in enumerate(backtest_results, start=1):
        ms_icon = "✅ TUTTU" if r["is_ms_hit"] else "❌ YATTI"
        ou_icon = "✅ TUTTU" if r["is_ou_hit"] else "❌ YATTI"
        btts_icon = "✅ TUTTU" if r["is_btts_hit"] else "❌ YATTI"
        
        actual_ou_str = "2.5 ÜST" if r["actual_over"] else "2.5 ALT"
        actual_btts_str = "KG VAR" if r["actual_btts"] else "KG YOK"
        
        print(f"{idx}. [{r['league']}] {r['home_name']} vs {r['away_name']}")
        print(f"   📊 GERÇEK SKOR: {r['actual_score']} ({r['actual_ms']} | {actual_ou_str} | {actual_btts_str})")
        print(f"   🧠 TypeSafe Tahmini: {r['pred_ms']} ({ms_icon})")
        print(f"   ⚽ 2.5 Üst Olasılığı: %{r['over_prob']} -> Tahmin: {'2.5 ÜST' if r['pred_over'] else '2.5 ALT'} ({ou_icon})")
        print(f"   🥅 KG Var Olasılığı: %{r['btts_prob']} -> Tahmin: {'KG VAR' if r['pred_btts'] else 'KG YOK'} ({btts_icon})")
        print(f"   ⚠️ Sürpriz/Tuzak Riski: {r['trap_score']}/10")
        print("-" * 70)
        
    print("\n" + "=" * 70)
    print(f"🏆 PERŞEMBE GÜNÜ BACKTEST PERFORMANS RAPORU:")
    print(f"   👉 Maç Sonucu (1-X-2) İsabeti: {correct_ms}/{total} (%{round(correct_ms/total*100, 1)})")
    print(f"   👉 2.5 Alt/Üst İsabeti:         {correct_ou}/{total} (%{round(correct_ou/total*100, 1)})")
    print(f"   👉 Karşılıklı Gol (KG) İsabeti: {correct_btts}/{total} (%{round(correct_btts/total*100, 1)})")
    print("=" * 70)
    
    with open("backtest_persembe_sonuclari.json", "w", encoding="utf-8") as f:
        json.dump(backtest_results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_thursday_backtest()

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

def fetch_deep_stats_for_event(event_id, match_iso_date):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/summary?event={event_id}"
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

def run_european_selective_backtest():
    print("=" * 76)
    print("   🏆 UEFA AVRUPA LİGİ SEÇİCİ FİLTRE & NO-BET (PAS GEÇ) BACKTESTİ")
    print("   Tarih: 16-17 Eylül 2026 | 18 Maçlık Kör Karşılaştırma & Eleyici Analiz")
    print("=" * 76)
    
    dates = ["20260916", "20260917"]
    raw_matches = []
    
    for dt in dates:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard?dates={dt}"
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
                
                day_name = "Çarşamba" if dt == "20260916" else "Perşembe"
                
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
                    "date": dt,
                    "day_name": day_name,
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
            print(f"[!] {dt} veri hatası: {e}")
            
    print(f"[+] Toplam {len(raw_matches)} adet resmi UEFA Avrupa Ligi maçı çekildi.")
    print(f"[*] 18 maç için derin xG ve dinlenme verileri paralel toplanıyor...")
    
    enriched_matches = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        f_map = {executor.submit(fetch_deep_stats_for_event, m["id"], m["utc_date"]): m for m in raw_matches}
        for f in as_completed(f_map):
            m = f_map[f]
            deep = f.result()
            enriched_matches.append({**m, **deep})
            
    enriched_matches.sort(key=lambda x: (x["date"], x["home_name"]))
    
    print("[*] TypeSafe AI 'Seçici Filtre (No-Bet / Oyna)' modeliyle değerlendiriyor...")
    t0 = time.time()
    
    results = []
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
            "tournament": "UEFA Avrupa Ligi",
            "venue": f"Stadyum: {venue}",
            "home_offensive_defensive": f"Son 3 maçta {h_sc} gol attı, {h_cn} gol yedi. Lig/Kupa Formu: {m['home_form']}, Dinlenme: {h_rest} gün",
            "away_offensive_defensive": f"Son 3 maçta {a_sc} gol attı, {a_cn} gol yedi. Lig/Kupa Formu: {m['away_form']}, Dinlenme: {a_rest} gün",
            "market_odds": m["odds"]
        }
        
        resp = client.system_one(
            state=state_payload,
            questions={
                "match_outcome": Choice(
                    instructions="Verilen ofansif/defansif gol oranlarına, dinlenme süresine ve Avrupa kupası dinamiklerine göre en olası maç sonucu nedir?",
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
                ),
                "bet_action": Choice(
                    instructions="Bir analist gibi düşün: Bu maç kupona ALINMALI MIDIR (OYNA), yoksa oran tuzağı/belirsizlik nedeniyle PAS MI GEÇİLMELİDİR (UZAK DUR)?",
                    criteria={
                        "banko_oyna": "Net avantaj, yüksek güvenilirlik, kupona girmeye uygun (OYNA)",
                        "gol_oyna": "Taraf bahsi yerine sadece 2.5 Üst veya KG Var gol bahsi oynanabilir",
                        "pas_gec_bulasma": "Yanıltıcı, iki ucu açık, sürpriz tehlikesi yüksek, KESİNLİKLE PAS GEÇ (UZAK DUR)"
                    }
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
        
        action_choice = resp.choices["bet_action"].choice
        
        # Akıllı Filtre Mantığı:
        if action_choice == "banko_oyna" and trap_score <= 5.0 and conf_pct >= 50:
            action_status = "BET"
            action_label = "🟢 OYNA (BANKO)"
        elif action_choice == "gol_oyna" or (action_choice != "pas_gec_bulasma" and over_prob >= 62):
            action_status = "GOAL_ONLY"
            action_label = "🟡 SADECE GOL OYNA"
        else:
            action_status = "NO_BET"
            action_label = "🔴 PAS GEÇ (UZAK DUR)"
            
        is_ms_hit = (pred_ms == m["actual_ms"])
        is_ou_hit = (pred_over == m["actual_over"])
        is_btts_hit = (pred_btts == m["actual_btts"])
        
        results.append({
            **m,
            "pred_ms": pred_ms,
            "over_prob": over_prob,
            "btts_prob": btts_prob,
            "pred_over": pred_over,
            "pred_btts": pred_btts,
            "trap_score": trap_score,
            "confidence": conf_pct,
            "action_choice": action_choice,
            "action_status": action_status,
            "action_label": action_label,
            "is_ms_hit": is_ms_hit,
            "is_ou_hit": is_ou_hit,
            "is_btts_hit": is_btts_hit
        })
        
    print(f"[+] 18 Avrupa maçının seçici analizi {round(time.time() - t0, 1)}s içinde tamamlandı!\n")
    
    # Detaylı Çıktı
    print("=" * 76)
    print("          UEFA AVRUPA LİGİ MAÇLARI SEÇİCİ FİLTRE RAPORU")
    print("=" * 76)
    
    current_day = ""
    for idx, r in enumerate(results, start=1):
        if r["day_name"] != current_day:
            current_day = r["day_name"]
            print(f"\n📅 --- {current_day.upper()} MAÇLARI ---")
            
        actual_ou_str = "2.5 ÜST" if r["actual_over"] else "2.5 ALT"
        pred_ou_str = "2.5 ÜST" if r["pred_over"] else "2.5 ALT"
        
        ms_hit_str = "✅ TUTTU" if r["is_ms_hit"] else "❌ YATTI"
        ou_hit_str = "✅ TUTTU" if r["is_ou_hit"] else "❌ YATTI"
        
        print(f"\n{idx}. {r['home_name']} vs {r['away_name']}")
        print(f"   🎯 Karar ve Filtre Durumu: {r['action_label']} (AI Tercihi: {r['action_choice']})")
        print(f"   📊 GERÇEK SKOR: {r['actual_score']} (Sonuç: {r['actual_ms']} | {actual_ou_str})")
        print(f"   🧠 Model Taraf Tahmini: {r['pred_ms']} ({ms_hit_str}) | Güven: %{r['confidence']} | Tuzak: {r['trap_score']}/10")
        print(f"   ⚽ Model 2.5 Alt/Üst:   {pred_ou_str} (%{r['over_prob']}) ({ou_hit_str})")
        
        if r["action_status"] == "BET":
            print(f"   💡 YORUM: Banko kupona alındı. Taraf tahmini {ms_hit_str}!")
        elif r["action_status"] == "GOAL_ONLY":
            print(f"   💡 YORUM: Taraf bahsi yerine gole yönlendirildi. Gol tahmini {ou_hit_str}!")
        else:
            print(f"   💡 YORUM: Sürpriz ve belirsizlik riski yüksek görüldü. PAS GEÇİLDİ (Uzak dur)!")
            
    # İstatistiksel Karşılaştırma
    total = len(results)
    all_ms_hits = sum(1 for r in results if r["is_ms_hit"])
    all_ou_hits = sum(1 for r in results if r["is_ou_hit"])
    all_btts_hits = sum(1 for r in results if r["is_btts_hit"])
    
    banko_matches = [r for r in results if r["action_status"] == "BET"]
    banko_hits = sum(1 for r in banko_matches if r["is_ms_hit"])
    
    goal_matches = [r for r in results if r["action_status"] == "GOAL_ONLY"]
    goal_ou_hits = sum(1 for r in goal_matches if r["is_ou_hit"])
    
    passed_matches = [r for r in results if r["action_status"] == "NO_BET"]
    passed_would_fail = sum(1 for r in passed_matches if not r["is_ms_hit"])
    
    print("\n" + "=" * 76)
    print("🏆 PERFORMANS KARŞILAŞTIRMASI (18 AVRUPA MAÇI): FİLTRESİZ VS SEÇİCİ")
    print("=" * 76)
    print(f"1️⃣ FİLTRESİZ / KÖR YAKLAŞIM (Tüm 18 maça zorunlu taraf oynansaydı):")
    print(f"   • Taraf İsabeti: {all_ms_hits}/{total} (%{round(all_ms_hits/total*100, 1)})")
    print(f"   • 2.5 Alt/Üst:  {all_ou_hits}/{total} (%{round(all_ou_hits/total*100, 1)})")
    print(f"   • Karşılıklı Gol: {all_btts_hits}/{total} (%{round(all_btts_hits/total*100, 1)})\n")
    
    print(f"2️⃣ SEÇİCİ FİLTRE YAKLAŞIMI (Eleyici / Sadece Değerli Kararlar):")
    if banko_matches:
        banko_pct = round(banko_hits/len(banko_matches)*100, 1)
        print(f"   🟢 OYNA (BANKO) Maçları: {banko_hits}/{len(banko_matches)} (%{banko_pct}) İSABET!")
        for b in banko_matches:
            print(f"      - {b['home_name']} vs {b['away_name']} -> Tahmin: {b['pred_ms']} | Skor: {b['actual_score']} ({'✅ TUTTU' if b['is_ms_hit'] else '❌'})")
    else:
        print("   🟢 OYNA (BANKO): Süzgeçten banko maç çıkmadı.")
        
    if goal_matches:
        goal_pct = round(goal_ou_hits/len(goal_matches)*100, 1)
        print(f"\n   🟡 SADECE GOL OYNA Maçları: {goal_ou_hits}/{len(goal_matches)} (%{goal_pct}) Gol İsabeti!")
        for g in goal_matches:
            g_ou = "2.5 ÜST" if g['pred_over'] else "2.5 ALT"
            print(f"      - {g['home_name']} vs {g['away_name']} -> Tahmin: {g_ou} | Skor: {g['actual_score']} ({'✅ TUTTU' if g['is_ou_hit'] else '❌'})")
            
    if passed_matches:
        passed_pct = round(passed_would_fail/len(passed_matches)*100, 1)
        print(f"\n   🔴 PAS GEÇİLEN (UZAK DURULAN) Maç Sayısı: {len(passed_matches)}")
        print(f"      - Pas geçilenlerin {passed_would_fail}/{len(passed_matches)} (%{passed_pct}) tanesi taraf bahsinde YATIYORDU!")
        print(f"      - Kurtarılan Tuzaklar / Zor Maçlar:")
        for p in passed_matches:
            res_note = "YATIYORDU (Kurtarıldı!)" if not p["is_ms_hit"] else "Riskli/Sürprizdi"
            print(f"        * {p['home_name']} vs {p['away_name']} (Skor: {p['actual_score']}) -> Tuzak: {p['trap_score']}/10 [{res_note}]")
            
    print("=" * 76)
    
    with open("backtest_avrupa_secici_sonuclari.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n[+] Sonuçlar 'backtest_avrupa_secici_sonuclari.json' dosyasına kaydedildi.")

if __name__ == "__main__":
    run_european_selective_backtest()

"""
backtest_v3.py — TypeSafe AI v3 Sisteminin Sezon Başı Backtesti
================================================================
Eski sistem ve yeni v3 sistemini aynı 202 tarihsel maç üzerinde
karşılaştırır. v3'ün getirdiği iyileştirmeleri ölçer:
  - 2 aşamalı banko (basit tespit + zengin doğrulama)
  - Lig bazlı strateji (Bundesliga, Serie A, Ligue 1 vb.)
  - Bağımsız 2.5 gol motoru
  - Bağımsız KG motoru

Kullanım:
    python backtest_v3.py          → Tüm sezon (202 maç)
    python backtest_v3.py 50       → İlk 50 maç (hızlı test)
    python backtest_v3.py --hf4    → Sadece Hf4-5 (form oturmuş dönem)
"""
import os, sys, json, time, requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI"
os.chdir(PROJECT_DIR)

from typesafe_sdk import TypeSafeClient, Choice, Noul, Score
from data_collector import fetch_match_deep_stats, parse_form_string
from league_strategy import get_league_config, get_dynamic_confidence_boost, get_recommended_bet_type

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

ALL_DATES = [
    ("20260822", "Hf1-Cmt"), ("20260823", "Hf1-Paz"),
    ("20260829", "Hf2-Cmt"), ("20260830", "Hf2-Paz"),
    ("20260905", "Hf3-Cmt"), ("20260906", "Hf3-Paz"),
    ("20260912", "Hf4-Cmt"), ("20260913", "Hf4-Paz"),
    ("20260918", "Hf5-Cum"), ("20260919", "Hf5-Cmt"),
]

# Sadece Hf4+ (form oturmuş dönem)
HF4_DATES = [d for d in ALL_DATES if "Hf4" in d[1] or "Hf5" in d[1]]

# ─── Veri Çekme ─────────────────────────────────────────────────

def _get_odd(ml, side):
    d = ml.get(side, {})
    if not isinstance(d, dict): return None
    v = (d.get("close") or d.get("open") or {}).get("odds")
    if not v: return None
    v = float(str(v).replace("+",""))
    return round((v/100)+1, 2) if v > 0 else round((100/abs(v))+1, 2)

def fetch_finished_matches(dates):
    raw = []
    for date_str, period in dates:
        for league, code in LEAGUES.items():
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={date_str}"
            try:
                r = requests.get(url, timeout=6)
                for ev in r.json().get("events", []):
                    c = ev["competitions"][0]
                    if c.get("status",{}).get("type",{}).get("state") != "post": continue
                    comps = c["competitors"]
                    h = comps[0] if comps[0].get("homeAway")=="home" else comps[1]
                    a = comps[1] if comps[0].get("homeAway")=="home" else comps[0]
                    hs = int(h.get("score",0) or 0); as_ = int(a.get("score",0) or 0)
                    odds_d = c.get("odds",[])
                    h_odd = d_odd = a_odd = ov_odd = un_odd = None
                    if odds_d and isinstance(odds_d[0], dict):
                        ml  = odds_d[0].get("moneyline") or {}
                        tot = odds_d[0].get("total") or {}
                        h_odd  = _get_odd(ml, "home")  or 2.10
                        d_odd  = _get_odd(ml, "draw")  or 3.30
                        a_odd  = _get_odd(ml, "away")  or 3.10
                        ov_odd = _get_odd(tot,"over")  or 1.85
                        un_odd = _get_odd(tot,"under") or 1.90
                    raw.append({
                        "id": ev.get("id"), "date": date_str, "period": period,
                        "league": league, "league_code": code,
                        "utc_date": ev.get("date",""),
                        "home_name": h["team"]["displayName"],
                        "home_form": h.get("form","-"),
                        "home_record": h.get("records",[{}])[0].get("summary","-") if h.get("records") else "-",
                        "away_name": a["team"]["displayName"],
                        "away_form": a.get("form","-"),
                        "away_record": a.get("records",[{}])[0].get("summary","-") if a.get("records") else "-",
                        "h_odd": h_odd or 2.10, "d_odd": d_odd or 3.30, "a_odd": a_odd or 3.10,
                        "over_odd": ov_odd or 1.85, "under_odd": un_odd or 1.90,
                        "actual_score": f"{hs}-{as_}",
                        "actual_ms":   "MS 1" if hs>as_ else ("MS 2" if as_>hs else "MS X"),
                        "actual_over": (hs+as_) > 2.5,
                        "actual_btts": (hs>0 and as_>0),
                        "total_goals": hs+as_,
                    })
            except: pass
    return raw

def enrich_match(m):
    """H2H, deplasman/ev formu, momentum, rotation ekle."""
    deep = fetch_match_deep_stats(m["league_code"], m["id"], m["utc_date"])
    hp = parse_form_string(m.get("home_form","-"))
    ap = parse_form_string(m.get("away_form","-"))
    return {**m, **deep,
            "home_momentum": hp["momentum"], "away_momentum": ap["momentum"],
            "home_form_points": hp["points"], "away_form_points": ap["points"],
            "home_form_wins": hp["wins"], "away_form_wins": ap["wins"],
            "xg_available": False, "home_xg_avg": None, "away_xg_avg": None,
            "home_scored_last5": deep.get("home_scored_last5", deep.get("home_scored_last3",0)),
            "away_scored_last5": deep.get("away_scored_last5", deep.get("away_scored_last3",0)),
            "odds": {"ms_1": m["h_odd"], "ms_x": m["d_odd"], "ms_2": m["a_odd"],
                     "over_2_5": m["over_odd"], "under_2_5": m["under_odd"]}}

# ─── Eski Sistem Analizi ─────────────────────────────────────────

def analyze_old(m):
    home_name = m["home_name"]; away_name = m["away_name"]
    state = {
        "match": f"{home_name} vs {away_name}", "league": m["league"],
        "home": f"Son3: {m.get('home_scored_last3',0)} attı/{m.get('home_conceded_last3',0)} yedi | Form:{m['home_form']} | Kayıt:{m['home_record']} | Dinlenme:{m.get('home_rest_days','-')}gün",
        "away": f"Son3: {m.get('away_scored_last3',0)} attı/{m.get('away_conceded_last3',0)} yedi | Form:{m['away_form']} | Kayıt:{m['away_record']} | Dinlenme:{m.get('away_rest_days','-')}gün",
        "odds": f"1:{m['h_odd']} X:{m['d_odd']} 2:{m['a_odd']} | 2.5U:{m['over_odd']}"
    }
    try:
        resp = client.system_one(state=state, questions={
            "outcome": Choice(instructions="En olası sonuç?", criteria={"ms_1":f"{home_name} Galibiyet","ms_x":"Beraberlik","ms_2":f"{away_name} Galibiyet"}),
            "over_2_5": Noul(instructions="2.5 Üst ihtimali?"),
            "btts": Noul(instructions="KG Var ihtimali?"),
            "trap": Score(instructions="Tuzak riski?", criteria=["dusuk","orta","yuksek"]),
            "conf": Score(instructions="Güven?", criteria=["dusuk","orta","yuksek"]),
            "action": Choice(instructions="Bahis oyna mı?", criteria={"banko_oyna":"OYNA","gol_oyna":"GOL","pas_gec_bulasma":"PAS"})
        })
        pred_ms   = {"ms_1":"MS 1","ms_x":"MS X","ms_2":"MS 2"}[resp.choices["outcome"].choice]
        over_prob = round(resp.nouls["over_2_5"].noul * 100)
        btts_prob = round(resp.nouls["btts"].noul * 100)
        trap      = round(resp.scores["trap"].score * 5, 1)
        conf      = int(min(96, max(35, round(resp.scores["conf"].score * 40 + 15))))
        action    = resp.choices["action"].choice
        status    = "BET" if (action=="banko_oyna" and trap<=5.0 and conf>=50) else ("GOAL_ONLY" if (action=="gol_oyna" or (action!="pas_gec_bulasma" and over_prob>=62)) else "NO_BET")
        ms_hit    = pred_ms == m["actual_ms"]
        ou_hit    = (over_prob>=50) == m["actual_over"]
        btts_hit  = (btts_prob>=50) == m["actual_btts"]
        chosen_odd = m["h_odd"] if pred_ms=="MS 1" else (m["d_odd"] if pred_ms=="MS X" else m["a_odd"])
        pnl = (chosen_odd-1.0) if ms_hit else -1.0
        return {**m,"sys":"ESKİ","pred_ms":pred_ms,"over_prob":over_prob,"btts_prob":btts_prob,
                "trap":trap,"conf":conf,"status":status,"ms_hit":ms_hit,"ou_hit":ou_hit,"btts_hit":btts_hit,
                "chosen_odd":chosen_odd,"pnl":round(pnl,2)}
    except Exception as e:
        return {**m,"sys":"ESKİ","pred_ms":"MS 1","over_prob":50,"btts_prob":50,"trap":5,"conf":40,
                "status":"NO_BET","ms_hit":False,"ou_hit":False,"btts_hit":False,"chosen_odd":2.0,"pnl":-1.0}

# ─── V3 Sistemi Analizi (typesafe_engine v3 kullanır) ───────────

def analyze_v3(m):
    """typesafe_engine.py v3'ü doğrudan çağırır."""
    from typesafe_engine import analyze_single_match
    result = analyze_single_match(m)
    # Alan isim uyumsuzluklarını düzelt (v3: action_status, backtest: status)
    pred_ms   = result.get("tahmin_ms", "MS 1")
    over_prob = result.get("over_2_5_prob", 50)
    btts_prob = result.get("btts_prob", 50)
    status    = result.get("action_status", "NO_BET")  # v3 → action_status
    ms_hit    = pred_ms == m["actual_ms"]
    ou_hit    = (over_prob >= 50) == m["actual_over"]
    btts_hit  = (btts_prob >= 50) == m["actual_btts"]
    chosen_odd = m["h_odd"] if pred_ms=="MS 1" else (m["d_odd"] if pred_ms=="MS X" else m["a_odd"])
    pnl = (chosen_odd - 1.0) if ms_hit else -1.0
    return {
        **result,
        "sys":        "V3",
        "status":     status,          # backtest için status olarak da koy
        "pred_ms":    pred_ms,
        "over_prob":  over_prob,
        "btts_prob":  btts_prob,
        "ms_hit":     ms_hit,
        "ou_hit":     ou_hit,
        "btts_hit":   btts_hit,
        "chosen_odd": chosen_odd,
        "pnl":        round(pnl, 2),
        "trap":       result.get("trap_score", 5),
        "conf":       result.get("confidence", 50),
    }

# ─── İstatistik Raporu ───────────────────────────────────────────

def print_stats(results, label):
    if not results:
        print(f"  {label}: Sonuç yok"); return {}
    total  = len(results)
    ms_h   = sum(1 for r in results if r["ms_hit"])
    ou_h   = sum(1 for r in results if r["ou_hit"])
    bt_h   = sum(1 for r in results if r["btts_hit"])
    pnl    = round(sum(r["pnl"] for r in results), 2)
    bk     = [r for r in results if r["status"]=="BET"]
    go     = [r for r in results if r["status"]=="GOAL_ONLY"]
    pg     = [r for r in results if r["status"]=="NO_BET"]
    bk_h   = sum(1 for r in bk if r["ms_hit"])
    go_ou  = sum(1 for r in go if r["ou_hit"])
    pg_f   = sum(1 for r in pg if not r["ms_hit"])

    ms_pct = round(ms_h/total*100,1); ou_pct = round(ou_h/total*100,1); bt_pct = round(bt_h/total*100,1)

    print(f"\n  {'─'*60}")
    print(f"  {label} | {total} Maç")
    print(f"  {'─'*60}")
    print(f"  MS İsabeti:       {ms_h}/{total}  (%{ms_pct})")
    print(f"  2.5 Alt/Üst:      {ou_h}/{total}  (%{ou_pct})")
    print(f"  KG Var/Yok:       {bt_h}/{total}  (%{bt_pct})")
    print(f"  Kör P&L:          {pnl:+.1f} birim")
    print(f"  {'─'*60}")
    if bk:
        bk_p = round(bk_h/len(bk)*100,1)
        bk_pnl = round(sum(r["pnl"] for r in bk),2)
        roi = round(bk_pnl/len(bk)*100,1)
        print(f"  🟢 BANKO ({len(bk)} maç):    {bk_h}/{len(bk)} (%{bk_p}) | P&L:{bk_pnl:+.1f} | ROI:%{roi}")
        for b in bk:
            icon = "✅" if b["ms_hit"] else "❌"
            val  = b.get("validation_decision","") or ""
            print(f"      {icon} [{b['period']}-{b['league'][:6]}] {b['home_name'][:14]} vs {b['away_name'][:14]} → {b['pred_ms']} | {b['actual_score']} | Güven:%{b['conf']} {val}")
    else:
        print(f"  🟢 BANKO: 0 maç seçildi")
    if go:
        print(f"  🟡 GOL OYNA ({len(go)} maç):   2.5 {go_ou}/{len(go)} (%{round(go_ou/len(go)*100,1)})")
    if pg:
        print(f"  🔴 PAS GEÇ ({len(pg)} maç):   {pg_f} taraf yatardı (%{round(pg_f/len(pg)*100,1)})")

    # Lig bazlı
    from collections import defaultdict
    lig = defaultdict(lambda: {"t":0,"ms":0,"ou":0,"bt":0})
    for r in results:
        l = r["league"]; lig[l]["t"]+=1
        if r["ms_hit"]: lig[l]["ms"]+=1
        if r["ou_hit"]: lig[l]["ou"]+=1
        if r["btts_hit"]: lig[l]["bt"]+=1
    print(f"\n  LİG DETAYI:")
    for l in sorted(lig.keys()):
        s=lig[l]; t=s["t"]
        print(f"    {l:<20} MS:%{round(s['ms']/t*100,1):5} | 2.5:%{round(s['ou']/t*100,1):5} | KG:%{round(s['bt']/t*100,1):5}")

    return {"total":total,"ms_pct":ms_pct,"ou_pct":ou_pct,"bt_pct":bt_pct,"pnl":pnl,
            "banko_count":len(bk),"banko_pct":round(bk_h/len(bk)*100,1) if bk else 0,
            "banko_pnl":round(sum(r["pnl"] for r in bk),2) if bk else 0,
            "gol_oyna_count":len(go),"pas_gec_count":len(pg),"pas_gec_saved":pg_f}

# ─── Ana Fonksiyon ───────────────────────────────────────────────

def run_v3_backtest(dates=None, max_matches=None, mode="both"):
    if dates is None: dates = ALL_DATES
    start_date = dates[0][1]; end_date = dates[-1][1]

    print("=" * 65)
    print(f"  🔬 TypeSafe AI v3 BACKTEST")
    print(f"  📅 {start_date} → {end_date} | 6 Dev Lig")
    print(f"  Mod: {mode.upper()}")
    print("=" * 65)

    # 1. Veri çek
    print("[*] Tarihsel maçlar çekiliyor...")
    raw = fetch_finished_matches(dates)
    raw.sort(key=lambda x: (x["date"], x["league"]))
    print(f"[+] {len(raw)} biten maç bulundu.")

    if max_matches:
        raw = raw[:max_matches]
        print(f"[!] Sınırlı mod: İlk {max_matches} maç analiz edilecek.")

    # 2. Zenginleştir
    print("[*] H2H, deplasman formu, momentum, rotation verileri çekiliyor...")
    enriched = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        fmap = {ex.submit(enrich_match, m): m for m in raw}
        for f in as_completed(fmap): enriched.append(f.result())
    enriched.sort(key=lambda x: (x["date"], x["league"]))
    print(f"[+] {len(enriched)} maç hazır.\n")

    t0 = time.time()
    old_results = []
    v3_results  = []

    # 3. Eski Sistem
    if mode in ("old","both"):
        print(f"[*] ESKİ SİSTEM analizi başlıyor ({len(enriched)} maç)...")
        with ThreadPoolExecutor(max_workers=10) as ex:
            fmap = {ex.submit(analyze_old, m): m for m in enriched}
            done = 0
            for f in as_completed(fmap):
                old_results.append(f.result()); done+=1
                if done%25==0 or done==len(enriched):
                    print(f"    -> Eski [{done}/{len(enriched)}] ({round(time.time()-t0,1)}s)")
        print(f"[+] Eski sistem tamamlandı.")

    # 4. V3 Sistemi
    if mode in ("v3","both"):
        print(f"\n[*] V3 SİSTEMİ analizi başlıyor ({len(enriched)} maç)...")
        t1 = time.time()
        with ThreadPoolExecutor(max_workers=6) as ex:
            fmap = {ex.submit(analyze_v3, m): m for m in enriched}
            done = 0
            for f in as_completed(fmap):
                v3_results.append(f.result()); done+=1
                bankolar = sum(1 for r in v3_results if r.get("status")=="BET")
                if done%20==0 or done==len(enriched):
                    print(f"    -> V3 [{done}/{len(enriched)}] | {bankolar} banko ({round(time.time()-t1,1)}s)")
        print(f"[+] V3 sistemi tamamlandı.")

    # 5. Rapor
    print("\n" + "="*65)
    print("  📊 KARŞILAŞTIRMALI PERFORMANS RAPORU")
    print("="*65)
    old_s = print_stats(old_results, "🔵 ESKİ SİSTEM") if old_results else {}
    v3_s  = print_stats(v3_results,  "🟠 V3 SİSTEMİ")  if v3_results  else {}

    # Delta
    if old_s and v3_s:
        print("\n" + "="*65)
        print("  📈 DELTA: V3 vs ESKİ")
        print("="*65)
        def arr(v): return f"{'↑' if v>=0 else '↓'}{abs(v)}"
        print(f"  MS:         {old_s['ms_pct']}% → {v3_s['ms_pct']}%  ({arr(round(v3_s['ms_pct']-old_s['ms_pct'],1))}%)")
        print(f"  2.5:        {old_s['ou_pct']}% → {v3_s['ou_pct']}%  ({arr(round(v3_s['ou_pct']-old_s['ou_pct'],1))}%)")
        print(f"  KG:         {old_s['bt_pct']}% → {v3_s['bt_pct']}%  ({arr(round(v3_s['bt_pct']-old_s['bt_pct'],1))}%)")
        print(f"  Kör P&L:    {old_s['pnl']:+.1f} → {v3_s['pnl']:+.1f}  (Δ{v3_s['pnl']-old_s['pnl']:+.1f})")
        print(f"  Banko:      {old_s.get('banko_count',0)} maç %{old_s.get('banko_pct',0)} → {v3_s.get('banko_count',0)} maç %{v3_s.get('banko_pct',0)}")
        print(f"  Banko P&L:  {old_s.get('banko_pnl',0):+.1f} → {v3_s.get('banko_pnl',0):+.1f}")

    # Kaydet
    out = {"generated_at": datetime.now().isoformat(), "mode": mode,
           "dates": [d for d,_ in dates], "total_matches": len(enriched),
           "old_system": old_results, "v3_system": v3_results,
           "old_stats": old_s, "v3_stats": v3_s}
    out_path = os.path.join(PROJECT_DIR, "backtest_v3_sonuclari.json")
    with open(out_path,"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Sonuçlar kaydedildi: backtest_v3_sonuclari.json")
    print(f"[+] Toplam süre: {round(time.time()-t0,1)}s")
    print("="*65)
    return out


if __name__ == "__main__":
    mode      = "both"
    max_m     = None
    dates     = ALL_DATES

    if "--v3"  in sys.argv: mode = "v3"
    if "--old" in sys.argv: mode = "old"
    if "--hf4" in sys.argv: dates = HF4_DATES; print("[*] Sadece Hf4-5 dönemi seçildi.")

    for arg in sys.argv[1:]:
        if arg.isdigit(): max_m = int(arg); break

    run_v3_backtest(dates=dates, max_matches=max_m, mode=mode)

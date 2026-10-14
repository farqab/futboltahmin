import sys, os
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match
from typesafe_engine import analyze_single_match
from smart_coupon_generator import generate_smart_coupons
from concurrent.futures import ThreadPoolExecutor

matches = fetch_finished_matches([("20260913", "13 Eyl Pazar")])
print(f"[*] 13 Eylül Pazar gününe ait {len(matches)} maç çekildi.")

with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, matches))

with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(analyze_single_match, enriched))

def eval_p(p):
    hs, as_ = map(int, p["actual_score"].split("-"))
    tot = hs + as_
    mt = p.get("optimal_market_type", "")
    mkt = p.get("optimal_market", "")
    hn, an = p["home_name"], p["away_name"]
    if mt == "COMBO_MS_GOAL":
        return ((hs > as_ and tot >= 2) if hn in mkt else (as_ > hs and tot >= 2)), False
    elif mt == "OVER_2_5": return (tot >= 3), False
    elif mt == "UNDER_2_5": return (tot <= 2), False
    elif mt == "BTTS_YES": return (hs > 0 and as_ > 0), False
    elif mt == "DNB":
        if hn in mkt: return (hs > as_), (hs == as_)
        else: return (as_ > hs), (hs == as_)
    elif mt == "STRAIGHT_MS":
        return (hs > as_ if ("MS 1" in mkt or hn in mkt) else as_ > hs), False
    return False, False

won, push = 0, 0
print("\n" + "="*75)
print("  📅 13 EYLÜL PAZAR BÜLTENİ BİTEN MAÇLAR SONUCU")
print("="*75)
for r in results:
    h, p = eval_p(r)
    if h: won += 1
    elif p: push += 1
    status = "✅ TUTTU" if h else ("🟡 İADE" if p else "❌ YATTI")
    sim_info = f" | Sim: 1.5 %{r.get('sim_prob_over_1_5')} - 2.5 %{r.get('sim_prob_over_2_5')}" if r.get('sim_prob_over_1_5') else ""
    print(f"• [{r['league']}] {r['home_name']} vs {r['away_name']} (Skor: {r['actual_score']})")
    print(f"  👑 Tercih: {r['optimal_market']} -> Oran: {r['optimal_odds']} (Güven: %{r['optimal_confidence']}) | {status}{sim_info}")

print("-" * 75)
succ = round(won / len(results) * 100, 1)
print(f"  📊 13 Eylül Pazar Özeti: {won}/{len(results)} İSABET (%{succ}) | İade: {push}")

coupons = generate_smart_coupons(results)
ak = coupons.get("altin_kasa", {})
if ak and ak.get("maclar"):
    ak_hit = all(eval_p(m["raw_match"])[0] for m in ak["maclar"])
    durum = "✅ TUTTU" if ak_hit else "❌ YATTI"
    print(f"\n  🏆 13 Eylül Günün Altın Kasası: {durum} (Toplam Oran: {ak['toplam_oran']})")
    for m in ak["maclar"]:
        h, _ = eval_p(m["raw_match"])
        ic = "✅" if h else "❌"
        print(f"     {ic} [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']})")

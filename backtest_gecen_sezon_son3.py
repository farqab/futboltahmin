import sys, os
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match
from typesafe_engine import analyze_single_match
from smart_coupon_generator import generate_smart_coupons
from concurrent.futures import ThreadPoolExecutor

WEEKS = [
    ("20250525", "38. Hafta (Sezon Finali — 25 Mayıs 2025 Pazar)"),
    ("20250518", "37. Hafta (Kritik Viraj — 18 Mayıs 2025 Pazar)"),
    ("20250510", "36. Hafta (Zirve Yarışı — 10 Mayıs 2025 Cumartesi)")
]

print("="*80)
print("  🏆 GEÇEN SEZONUN SON 3 HAFTASI BÜYÜK BACKTESTİ (MAYIS 2025)")
print("  6 Dev Lig | 10.000 Monte Carlo Simülasyonu | Nesine Kalibrasyonu | Derbi Kalkanı")
print("="*80)

raw_matches = fetch_finished_matches(WEEKS)
print(f"[*] ESPN API arşivinden toplam {len(raw_matches)} maç çekildi.")

with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, raw_matches))

print(f"[*] {len(enriched)} maç TypeSafe AI motoru ve 10k Poisson simülasyonu ile taranıyor...")
with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(analyze_single_match, enriched))

def eval_p(p):
    hs, as_ = map(int, p["actual_score"].split("-"))
    tot = hs + as_
    mt = p.get("optimal_market_type", "")
    mkt = p.get("optimal_market", "")
    hn, an = p["home_name"], p["away_name"]
    if mt == "COMBO_MS_GOAL":
        if "& 2.5 Üst" in mkt:
            return ((hs > as_ and tot >= 3) if hn in mkt else (as_ > hs and tot >= 3)), False
        elif "& 1.5 Üst" in mkt:
            return ((hs > as_ and tot >= 2) if hn in mkt else (as_ > hs and tot >= 2)), False
    elif mt == "OVER_2_5": return (tot >= 3), False
    elif mt == "UNDER_2_5": return (tot <= 2), False
    elif mt == "OVER_3_5": return (tot >= 4), False
    elif mt == "BTTS_YES": return (hs > 0 and as_ > 0), False
    elif mt == "DNB":
        if hn in mkt: return (hs > as_), (hs == as_)
        else: return (as_ > hs), (hs == as_)
    elif mt == "STRAIGHT_MS":
        return (hs > as_ if ("MS 1" in mkt or hn in mkt) else as_ > hs), False
    return False, False

from collections import defaultdict
by_week = defaultdict(list)
for r in results:
    by_week[r["date"]].append(r)

total_coupons = 0
won_coupons = 0
grand_total = 0
grand_won = 0
grand_push = 0

for dt, week_title in WEEKS:
    m_list = by_week.get(dt, [])
    if not m_list: continue
    
    print("\n" + "="*80)
    print(f"  📅 {week_title} — TOPLAM {len(m_list)} MAÇ")
    print("="*80)
    
    week_won, week_push = 0, 0
    for m in m_list:
        h, p = eval_p(m)
        if h: week_won += 1
        elif p: week_push += 1
        
    grand_total += len(m_list)
    grand_won += week_won
    grand_push += week_push
    
    succ = round(week_won / len(m_list) * 100, 1)
    print(f"  📊 Hafta Bilanço: {week_won} / {len(m_list)} İSABET (%{succ}) | 🟡 İade: {week_push}")
    
    bankolar = [m for m in m_list if m.get("action_status") == "BET"]
    if bankolar:
        print(f"  🟢 BANKOLAR ({len(bankolar)} adet):")
        for b in bankolar:
            h, _ = eval_p(b)
            st = "✅ TUTTU" if h else "❌ YATTI"
            print(f"     • [{b['league']}] {b['home_name']} vs {b['away_name']} (Skor: {b['actual_score']}) ➔ {b['optimal_market']} ({b['optimal_odds']}) | {st}")
    else:
        print("  🟢 BANKO: 0 adet (Sezon sonu sürpriz riski nedeniyle sahte banko verilmedi)")
        
    coupons = generate_smart_coupons(m_list)
    ak = coupons.get("altin_kasa", {})
    if ak and ak.get("maclar"):
        total_coupons += 1
        ak_hit = all(eval_p(m["raw_match"])[0] for m in ak["maclar"])
        if ak_hit: won_coupons += 1
        st = "✅ TUTTU" if ak_hit else "❌ YATTI"
        print(f"\n  🏆 HAFTANIN ALTIN KASA KUPONU: {st} (Toplam Oran: {ak['toplam_oran']})")
        print("  " + "-" * 60)
        for m in ak["maclar"]:
            h, _ = eval_p(m["raw_match"])
            ic = "✅" if h else "❌"
            print(f"     {ic} [{m['lig']}] {m['mac']} ➔ {m['tahmin']} (Oran: {m['oran']}) [Güven: %{m['guven']}]")

print("\n" + "="*80)
print("  🏁 GEÇEN SEZONUN SON 3 HAFTASI GENEL SONUCU")
print("="*80)
net_succ = round(grand_won / grand_total * 100, 1)
print(f"  Toplam Taranan Maç:            {grand_total}")
print(f"  ✅ Net Kazanılan Tercih:       {grand_won} / {grand_total} (%{net_succ})")
print(f"  🟡 Parası İade Olan (DNB):      {grand_push} Maç")
print(f"  🏆 Altın Kasa Kupon Başarısı:   {won_coupons} / {total_coupons} (%{round(won_coupons/max(1,total_coupons)*100, 1)})")
print("="*80)

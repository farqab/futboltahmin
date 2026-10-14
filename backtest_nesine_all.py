import sys, os
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match
from typesafe_engine import analyze_single_match
from smart_coupon_generator import generate_smart_coupons
from concurrent.futures import ThreadPoolExecutor

DATES = [
    ("20260919", "19 Eylül Cumartesi (Dün)"),
    ("20260913", "13 Eylül Pazar (Geçen Pazar)"),
    ("20260912", "12 Eylül Cumartesi (Geçen Hafta)")
]

print("="*80)
print("  🔬 TÜM GÜNLERİN NESİNE KALİBRASYONLU BÜYÜK KUPON & BANKO BACKTESTİ")
print("  Kurallar: Minimum 1.40 Oran, Dev Takım Kalibrasyonu, Derbi Kalkanı, 10k Simülasyon")
print("="*80)

raw_matches = fetch_finished_matches(DATES)
print(f"[*] 3 farklı bültenden toplam {len(raw_matches)} maç ESPN'den çekildi.")

with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, raw_matches))

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
by_date = defaultdict(list)
for r in results:
    by_date[r["date"]].append(r)

total_coupons = 0
won_coupons = 0

for dt, day_name in DATES:
    m_list = by_date.get(dt, [])
    if not m_list: continue
    
    print("\n" + "="*80)
    print(f"  📅 {day_name} — BÜLTEN: {len(m_list)} MAÇ")
    print("="*80)
    
    bankolar = [m for m in m_list if m.get("action_status") == "BET"]
    print(f"🟢 BANKO TERCİHLER: {len(bankolar)} adet")
    for b in bankolar:
        h, _ = eval_p(b)
        st = "✅ TUTTU" if h else "❌ YATTI"
        print(f"   • [{b['league']}] {b['home_name']} vs {b['away_name']} (Skor: {b['actual_score']}) ➔ {b['optimal_market']} (Oran: {b['optimal_odds']}) | {st}")
    if not bankolar:
        print("   (Bu gün tuzak ve derbi riski yüksek olduğu için hiçbir maça sahte banko denmedi!)")
        
    coupons = generate_smart_coupons(m_list)
    
    # Altın Kasa
    ak = coupons.get("altin_kasa", {})
    if ak and ak.get("maclar"):
        total_coupons += 1
        ak_hit = all(eval_p(m["raw_match"])[0] for m in ak["maclar"])
        if ak_hit: won_coupons += 1
        st = "✅ TUTTU" if ak_hit else "❌ YATTI"
        print(f"\n🏆 GÜNÜN ALTIN KASA KUPONU: {st} (Toplam Oran: {ak['toplam_oran']})")
        print("-" * 60)
        for m in ak["maclar"]:
            h, _ = eval_p(m["raw_match"])
            ic = "✅" if h else "❌"
            print(f"  {ic} [{m['lig']}] {m['mac']} ➔ {m['tahmin']} (Oran: {m['oran']}) [Güven: %{m['guven']}]")
            
    # Değer Kombinesi
    dk = coupons.get("deger_kombine", {})
    if dk and dk.get("maclar"):
        total_coupons += 1
        dk_hit = all(eval_p(m["raw_match"])[0] for m in dk["maclar"])
        if dk_hit: won_coupons += 1
        st_dk = "✅ TUTTU" if dk_hit else "❌ YATTI"
        print(f"\n🎯 GÜNÜN DEĞER KOMBİNESİ: {st_dk} (Toplam Oran: {dk['toplam_oran']})")
        print("-" * 60)
        for m in dk["maclar"]:
            h, _ = eval_p(m["raw_match"])
            ic = "✅" if h else "❌"
            print(f"  {ic} [{m['lig']}] {m['mac']} ➔ {m['tahmin']} (Oran: {m['oran']}) [Güven: %{m['guven']}]")

print("\n" + "="*80)
print("  🏁 NİHAİ GENEL KUPON BİLANÇOSU (NESİNE KALİBRASYONLU)")
print("="*80)
print(f"  Toplam Üretilen Kombine Kupon: {total_coupons}")
print(f"  ✅ Kazanan Kupon:              {won_coupons} / {total_coupons} (%{round(won_coupons/max(1,total_coupons)*100, 1)})")
print("="*80)

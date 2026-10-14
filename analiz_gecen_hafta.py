"""
analiz_gecen_hafta.py — Geçtiğimiz Haftaların (Hf3 ve Hf4) Büyük Analizi
========================================================================
5-6 Eylül (Hafta 3) ve 12-13 Eylül (Hafta 4) tarihlerindeki tüm maçları
yeni İkili Uzman (Dual-Expert) modeliyle analiz edip başarı tablosunu çıkarır.
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match
from typesafe_engine import analyze_single_match
from smart_coupon_generator import generate_smart_coupons
from concurrent.futures import ThreadPoolExecutor

DATES = [
    ("20260905", "Hf3-Cmt"),
    ("20260906", "Hf3-Paz"),
    ("20260912", "Hf4-Cmt"),
    ("20260913", "Hf4-Paz")
]

print("="*70)
print("  🔍 GEÇEN HAFTALARIN (Hf3 & Hf4) BÜYÜK ANALİZİ BAŞLATILIYOR")
print("  Tarihler: 5-6 Eylül ve 12-13 Eylül 2026 | 6 Dev Lig")
print("="*70)

raw = fetch_finished_matches(DATES)
print(f"[*] Toplam {len(raw)} adet bitmiş maç çekildi. İstatistikler derinleştiriliyor...")

with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, raw))

print(f"[*] TypeSafe AI İkili Uzman Mimarisi ile {len(enriched)} maç taranıyor...")

with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(analyze_single_match, enriched))

for r in results:
    r["ms_hit"] = (r["tahmin_ms"] == r["actual_ms"])
    r["ou_hit"] = ((r["over_2_5_prob"] >= 50) == r["actual_over"])
    r["btts_hit"] = ((r["btts_prob"] >= 50) == r["actual_btts"])

# Hafta ve Lig Bazlı Özet
from collections import defaultdict
by_period = defaultdict(list)
for r in results:
    by_period[r["period"]].append(r)

print("\n" + "="*70)
print("  📊 HAFTA BAZLI PERFORMANS TABLOSU")
print("="*70)

for p, m_list in sorted(by_period.items()):
    t = len(m_list)
    ms_c = sum(1 for m in m_list if m["ms_hit"])
    ou_c = sum(1 for m in m_list if m["ou_hit"])
    bt_c = sum(1 for m in m_list if m["btts_hit"])
    bk_list = [m for m in m_list if m["action_status"] == "BET"]
    bk_hit = sum(1 for m in bk_list if m["ms_hit"])
    
    coupons = generate_smart_coupons(m_list)
    ak = coupons.get("altin_kasa", {})
    ak_durum = "✅ TUTTU" if ak.get("tuttu_mu") else "❌ YATTI"
    ak_oran = ak.get("toplam_oran", 0)
    
    print(f"\n📌 {p} ({t} Maç):")
    print(f"   • Taraf (MS) İsabeti:  {ms_c}/{t} (%{round(ms_c/t*100, 1)})")
    print(f"   • 2.5 Alt/Üst İsabeti: {ou_c}/{t} (%{round(ou_c/t*100, 1)})")
    print(f"   • Karşılıklı Gol:     {bt_c}/{t} (%{round(bt_c/t*100, 1)})")
    if bk_list:
        print(f"   • 🟢 Banko İsabeti:    {bk_hit}/{len(bk_list)} (%{round(bk_hit/len(bk_list)*100, 1)})")
        for b in bk_list:
            durum = "✅" if b["ms_hit"] else "❌"
            print(f"      {durum} {b['home_name']} vs {b['away_name']} -> {b['tahmin_ms']} (Skor: {b['actual_score']})")
    print(f"   • 🎟️ Günün Altın Kasası: {ak_durum} (Oran: {ak_oran})")

print("\n" + "="*70)
print("  🏆 GENEL ÖZET (Hf3 & Hf4 TOPLAMI - 89 MAÇ)")
print("="*70)
total = len(results)
tot_ms = sum(1 for r in results if r["ms_hit"])
tot_ou = sum(1 for r in results if r["ou_hit"])
tot_bt = sum(1 for r in results if r["btts_hit"])
print(f"Genel MS:     {tot_ms}/{total} (%{round(tot_ms/total*100, 1)})")
print(f"Genel 2.5:    {tot_ou}/{total} (%{round(tot_ou/total*100, 1)})")
print(f"Genel KG:     {tot_bt}/{total} (%{round(tot_bt/total*100, 1)})")
print("="*70)

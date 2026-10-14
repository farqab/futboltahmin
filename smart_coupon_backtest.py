"""
test_smart_coupons.py — Tarihsel Kupon Başarı Testi
===================================================
Hf4 ve Hf5 hafta sonlarındaki maçları analiz edip gün bazında:
1. Altın Kasa (2'li)
2. Gol Yağmuru (3'lü)
kuponlarını oluşturur ve bu kuponların gerçekten TUTUP TUTMADIĞINI test eder.
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match, HF4_DATES
from typesafe_engine import analyze_single_match
from smart_coupon_generator import generate_smart_coupons
from concurrent.futures import ThreadPoolExecutor, as_completed

print("[*] Hf4 ve Hf5 dönemi maçları toplanıyor...")
raw = fetch_finished_matches(HF4_DATES)

with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, raw))

print(f"[+] Toplam {len(enriched)} maç hazırlandı. TypeSafe AI analiz ediyor...")

results = []
with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(analyze_single_match, enriched))

# Backtest vuruşlarını hesapla
for r in results:
    r["ms_hit"] = (r["tahmin_ms"] == r["actual_ms"])
    r["ou_hit"] = ((r["over_2_5_prob"] >= 50) == r["actual_over"])

# Gün bazında grupla ve kupon üret
from collections import defaultdict
by_date = defaultdict(list)
for r in results:
    by_date[r["date"]].append(r)

print("\n" + "="*70)
print("  🎟️ TYPESAFE AI AKILLI KUPONLAR — TARİHSEL TEST RAPORU")
print("="*70)

total_altin = 0
hit_altin = 0
total_gol = 0
hit_gol = 0

for dt, matches in sorted(by_date.items()):
    period = matches[0].get("period", dt)
    coupons = generate_smart_coupons(matches)
    
    ak = coupons.get("altin_kasa")
    gy = coupons.get("gol_yagmuru")
    
    print(f"\n📅 {dt} ({period}) — Bülten: {len(matches)} Maç")
    print("-" * 50)
    
    if ak and ak["maclar"]:
        total_altin += 1
        durum = "✅ TUTTU" if ak["tuttu_mu"] else "❌ YATTI"
        if ak["tuttu_mu"]: hit_altin += 1
        print(f"  {ak['baslik']} -> Oran: {ak['toplam_oran']} | {durum}")
        for m in ak["maclar"]:
            icon = "✅" if m["is_hit"] else "❌"
            print(f"    • {icon} [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']})")
            
    if gy and len(gy["maclar"]) >= 2:
        total_gol += 1
        durum = "✅ TUTTU" if gy["tuttu_mu"] else "❌ YATTI"
        if gy["tuttu_mu"]: hit_gol += 1
        print(f"  {gy['baslik']} -> Oran: {gy['toplam_oran']} | {durum}")
        for m in gy["maclar"]:
            icon = "✅" if m["is_hit"] else "❌"
            print(f"    • {icon} [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']})")

print("\n" + "="*70)
print("  🏆 KUPON MOTORU BAŞARI ÖZETİ")
print("="*70)
if total_altin > 0:
    print(f"  🥇 GÜNÜN ALTIN KASASI:   {hit_altin}/{total_altin} Kupon Başarısı (%{round(hit_altin/total_altin*100, 1)})")
if total_gol > 0:
    print(f"  ⚽ GOL YAĞMURU KOMBİNE: {hit_gol}/{total_gol} Kupon Başarısı (%{round(hit_gol/total_gol*100, 1)})")
print("="*70)

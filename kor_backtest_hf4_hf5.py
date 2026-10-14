"""
kor_backtest_hf4_hf5.py — Hafta 4 ve 5 Körleme (Blind) Backtest
================================================================
Modele skorlar ve maç sonucu ASLA verilmez.
Sadece maç öncesi verilerle TypeSafe AI tahmin üretir.
Ardından gerçek skorlarla kafa kafaya karşılaştırılır.
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match, HF4_DATES
from typesafe_engine import analyze_single_match
from concurrent.futures import ThreadPoolExecutor

print("="*75)
print("  🎯 HAFTA 4 & HAFTA 5 KÖR (BLIND) BACKTEST BAŞLATILIYOR")
print("  Tarihler: 12, 13, 18, 19 Eylül 2026 (79 Gerçek Maç)")
print("  Kural: Modele skorlar ASLA gösterilmez, tamamen maç öncesi tahmin yapar.")
print("="*75)

raw = fetch_finished_matches(HF4_DATES)
print(f"[*] Toplam {len(raw)} maç verisi ESPN'den çekildi.")

# Skorları gizleyip sadece maç öncesi verilerini hazırla
pre_match_data = []
actual_results = {}

for m in raw:
    actual_results[m["id"]] = {
        "score": m["actual_score"],
        "ms": m["actual_ms"],
        "over": m["actual_over"],
        "btts": m["actual_btts"]
    }
    # Skorları silip kör veri oluşturuyoruz
    clean_m = {k: v for k, v in m.items() if not k.startswith("actual_")}
    pre_match_data.append(clean_m)

print("[*] İstatistikler derinleştiriliyor (H2H, Dinlenme, Form, vb.)...")
with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, pre_match_data))

print(f"[*] TypeSafe AI İkili Uzman Mimarisi {len(enriched)} maçı KÖR olarak tahmin ediyor...")
with ThreadPoolExecutor(max_workers=6) as ex:
    predictions = list(ex.map(analyze_single_match, enriched))

print("\n" + "="*75)
print("  📋 KÖR TAHMİNLER VS GERÇEK SONUÇLAR KARŞILAŞTIRMASI")
print("="*75)

bankolar = []
gol_tahminleri = []
total_count = len(predictions)
ms_hits = 0
ou_hits = 0
btts_hits = 0

for p in predictions:
    mid = p["id"]
    act = actual_results[mid]
    
    is_ms_hit = (p["tahmin_ms"] == act["ms"])
    is_ou_hit = ((p["over_2_5_prob"] >= 50) == act["over"])
    is_bt_hit = ((p["btts_prob"] >= 50) == act["btts"])
    
    if is_ms_hit: ms_hits += 1
    if is_ou_hit: ou_hits += 1
    if is_bt_hit: btts_hits += 1
    
    p["is_ms_hit"] = is_ms_hit
    p["is_ou_hit"] = is_ou_hit
    p["actual_score"] = act["score"]
    p["actual_ms"] = act["ms"]
    
    if p.get("action_status") == "BET":
        bankolar.append(p)
    elif p.get("over_2_5_prob", 0) >= 60:
        gol_tahminleri.append(p)

# 1. Banko Sonuçları
print("\n🟢 TYPE-SAFE BANKO TAHMİNLERİ:")
print("-" * 65)
if bankolar:
    for b in bankolar:
        durum = "✅ TUTTU" if b["is_ms_hit"] else "❌ YATTI"
        odds = b.get("odds") or {}
        oran = odds.get("ms_1" if b["tahmin_ms"]=="MS 1" else "ms_2", "-")
        print(f"  • [{b['period']} - {b['league']}] {b['home_name']} vs {b['away_name']}")
        print(f"    Tahmin: {b['tahmin_ms']} (Oran: {oran}) | Gerçek Skor: {b['actual_score']} -> {durum}")
else:
    print("  Bu dönemde kriterleri geçen banko bulunamadı.")

# 2. Öne Çıkan En Güvenilir 2.5 Üst Gol Tahminleri
print("\n🟡 EN YÜKSEK GÜVENLİ 2.5 ÜST TAHMİNLERİ (İLK 10 MAÇ):")
print("-" * 65)
gol_tahminleri.sort(key=lambda x: x["over_2_5_prob"], reverse=True)
for g in gol_tahminleri[:10]:
    durum = "✅ TUTTU" if g["is_ou_hit"] else "❌ YATTI"
    odds = g.get("odds") or {}
    print(f"  • [{g['league']}] {g['home_name']} vs {g['away_name']}")
    print(f"    Tahmin: 2.5 Üst (%{g['over_2_5_prob']} İhtimal) | Skor: {g['actual_score']} -> {durum}")

# 3. Genel Başarı Raporu
print("\n" + "="*75)
print("  📊 GENEL KÖR TAHMİN BAŞARI TABLOSU (79 MAÇ)")
print("="*75)
print(f"  • Taraf (MS 1-X-2) İsabeti:  {ms_hits}/{total_count}  (%{round(ms_hits/total_count*100, 1)})")
print(f"  • 2.5 Alt/Üst İsabeti:       {ou_hits}/{total_count}  (%{round(ou_hits/total_count*100, 1)})")
print(f"  • Karşılıklı Gol İsabeti:    {btts_hits}/{total_count}  (%{round(btts_hits/total_count*100, 1)})")
if bankolar:
    b_hits = sum(1 for b in bankolar if b["is_ms_hit"])
    print(f"  • 🟢 Banko Başarı Oranı:     {b_hits}/{len(bankolar)}  (%{round(b_hits/len(bankolar)*100, 1)}) 🔥")
print("="*75)

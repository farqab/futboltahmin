"""
backtest_cumartesi_omni.py
Cumartesi bültenlerini (12 Eylül ve 19 Eylül 2026 Cumartesi günleri)
yeni Omni-Market + Oran Hareketi (Odds Drift / Smart Money) motoruyla test eder.
Toplamda kaçta kaç tuttuğunu, kuponların durumunu ve net başarı oranını hesaplar.
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

SATURDAYS = [
    ("20260919", "19 Eylül Cumartesi (Dün - Hf5)"),
    ("20260912", "12 Eylül Cumartesi (Geçen Hafta - Hf4)")
]

print("="*75)
print("  🔬 CUMARTESİ BÜLTENLERİ BÜYÜK BACKTESTİ (OMNI-MARKET + SMART MONEY)")
print("  Tarihler: 19 Eylül ve 12 Eylül Cumartesi Günleri | 6 Dev Lig")
print("="*75)

raw_matches = fetch_finished_matches(SATURDAYS)
print(f"[*] Toplam {len(raw_matches)} adet Cumartesi maçı ESPN'den çekildi.")

with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, raw_matches))

print(f"[*] TypeSafe AI motoru {len(enriched)} maçı derin pazar analiziyle değerlendiriyor...")
with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(analyze_single_match, enriched))

# Sonuç kontrol fonksiyonu
def evaluate_bet(p):
    score = p["actual_score"]
    try:
        hs, as_ = map(int, score.split("-"))
    except:
        hs, as_ = 0, 0
    tot = hs + as_
    m_type = p.get("optimal_market_type", "")
    market = p.get("optimal_market", "")
    h_name = p["home_name"]
    a_name = p["away_name"]
    
    is_hit = False
    is_push = False
    
    if m_type == "COMBO_MS_GOAL":
        if h_name in market:
            is_hit = (hs > as_) and (tot >= 2)
        elif a_name in market:
            is_hit = (as_ > hs) and (tot >= 2)
    elif m_type == "OVER_2_5":
        is_hit = (tot >= 3)
    elif m_type == "UNDER_2_5":
        is_hit = (tot <= 2)
    elif m_type == "BTTS_YES":
        is_hit = (hs > 0 and as_ > 0)
    elif m_type == "TEAM_GOALS":
        if h_name in market:
            is_hit = (hs >= 2)
        elif a_name in market:
            is_hit = (as_ >= 2)
    elif m_type == "DNB":
        if h_name in market:
            if hs > as_: is_hit = True
            elif hs == as_: is_push = True
        elif a_name in market:
            if as_ > hs: is_hit = True
            elif hs == as_: is_push = True
    elif m_type == "STRAIGHT_MS":
        if "MS 1" in market or h_name in market:
            is_hit = (hs > as_)
        elif "MS 2" in market or a_name in market:
            is_hit = (as_ > hs)
        elif "MS X" in market:
            is_hit = (hs == as_)
            
    return is_hit, is_push

from collections import defaultdict
by_sat = defaultdict(list)
for r in results:
    by_sat[r["date"]].append(r)

grand_total = 0
grand_won = 0
grand_push = 0

for dt, m_list in sorted(by_sat.items(), reverse=True):
    day_label = m_list[0].get("period", dt)
    print("\n" + "="*75)
    print(f"  📅 {day_label} — BÜLTEN: {len(m_list)} MAÇ")
    print("="*75)
    
    day_total = len(m_list)
    day_won = 0
    day_push = 0
    
    for p in m_list:
        hit, push = evaluate_bet(p)
        p["is_hit"] = hit
        p["is_push"] = push
        p["ms_hit"] = (p["tahmin_ms"] == p["actual_ms"])
        
        if hit: day_won += 1
        elif push: day_push += 1
        
        durum = "✅ TUTTU" if hit else ("🟡 İADE" if push else "❌ YATTI")
        drift_not = f" | {p.get('odds_drift_desc')}" if p.get('odds_drift_desc') else ""
        
        print(f"• [{p['league']}] {p['home_name']} vs {p['away_name']} (Gerçek Skor: {p['actual_score']})")
        print(f"  👑 Tercih: {p['optimal_market']} -> Oran: {p['optimal_odds']} (Güven: %{p['optimal_confidence']}) | {durum}{drift_not}")
        if p.get("sim_prob_over_1_5"):
            print(f"  🎲 10k Simülasyon: 1.5 Üst %{p.get('sim_prob_over_1_5')} | 2.5 Üst %{p.get('sim_prob_over_2_5')} | KG %{p.get('sim_prob_btts')} | En Olası: {p.get('sim_top_score_str')}")
    
    grand_total += day_total
    grand_won += day_won
    grand_push += day_push
    
    succ = round(day_won / day_total * 100, 1)
    print("-" * 75)
    print(f"  📊 {day_label} Özeti: {day_won}/{day_total} İSABET (%{succ}) | İade: {day_push}")
    
    # Kupon durumu
    coupons = generate_smart_coupons(m_list)
    ak = coupons.get("altin_kasa", {})
    if ak and ak.get("maclar"):
        ak_hit = all(evaluate_bet(m["raw_match"])[0] for m in ak["maclar"])
        durum = "✅ TUTTU" if ak_hit else "❌ YATTI"
        print(f"  🏆 Günün Altın Kasası: {durum} (Toplam Oran: {ak['toplam_oran']})")
        for m in ak["maclar"]:
            h, _ = evaluate_bet(m["raw_match"])
            ic = "✅" if h else "❌"
            print(f"     {ic} [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']})")

    dk = coupons.get("deger_kombine", {})
    if dk and dk.get("maclar"):
        dk_hit = all(evaluate_bet(m["raw_match"])[0] for m in dk["maclar"])
        durum_dk = "✅ TUTTU" if dk_hit else "❌ YATTI"
        print(f"  🎯 Günün Değer Kombinesi: {durum_dk} (Toplam Oran: {dk['toplam_oran']})")
        for m in dk["maclar"]:
            h, _ = evaluate_bet(m["raw_match"])
            ic = "✅" if h else "❌"
            print(f"     {ic} [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']})")

print("\n" + "="*75)
print("  🏆 TÜM CUMARTESİ BÜLTENLERİ GENEL SONUCU")
print("="*75)
total_valid = grand_total - grand_push
net_rate = round(grand_won / grand_total * 100, 1)
print(f"  Toplam Taranan Cumartesi Maçı: {grand_total}")
print(f"  ✅ Net Kazanılan Tercih:       {grand_won} / {grand_total} (%{net_rate})")
print(f"  🟡 Parası İade Olan (DNB):      {grand_push} Maç")
print(f"  ❌ Kaybeden:                    {grand_total - grand_won - grand_push} Maç")
print("="*75)

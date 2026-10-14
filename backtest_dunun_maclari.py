"""
backtest_dunun_maclari.py
19 Eylül 2026 (Dünün) tüm biten maçlarını yeni Omni-Market En İdeal Tercih motoruyla test eder.
Modelin seçtiği 'En İdeal Tercihlerin' ve akıllı kuponların gerçekte tutup tutmadığını kontrol eder.
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

YESTERDAY = [("20260919", "Hf5-Cmt")]

print("="*75)
print("  🔬 DÜNÜN MAÇLARI (19 EYLÜL 2026) OMNI-MARKET BACKTESTİ")
print("  Tüm pazar seçenekleri taranıp 'En İdeal Tercihler' test ediliyor...")
print("="*75)

raw = fetch_finished_matches(YESTERDAY)
print(f"[*] Toplam {len(raw)} adet dünün biten maçı ESPN'den çekildi.")

with ThreadPoolExecutor(max_workers=10) as ex:
    enriched = list(ex.map(enrich_match, raw))

print(f"[*] TypeSafe AI 24 maçın tüm bahis pazarlarını analiz ediyor...")
with ThreadPoolExecutor(max_workers=6) as ex:
    predictions = list(ex.map(analyze_single_match, enriched))

# Sonuç kontrol fonksiyonu
def evaluate_optimal_bet(p):
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

total_bets = 0
won_bets = 0
push_bets = 0

print("\n" + "="*75)
print("  📋 DÜNÜN MAÇLARI — SEÇİLEN EN İDEAL TERCİHLER VS GERÇEK SKORLAR")
print("="*75)

for p in predictions:
    hit, push = evaluate_optimal_bet(p)
    p["is_hit"] = hit
    p["is_push"] = push
    p["ms_hit"] = (p["tahmin_ms"] == p["actual_ms"])
    p["ou_hit"] = ((p["over_2_5_prob"] >= 50) == p["actual_over"])
    
    total_bets += 1
    if hit: won_bets += 1
    elif push: push_bets += 1
    
    durum = "✅ TUTTU" if hit else ("🟡 İADE" if push else "❌ YATTI")
    odds = p.get("odds") or {}
    
    print(f"• [{p['league']}] {p['home_name']} vs {p['away_name']} (Skor: {p['actual_score']})")
    print(f"  👑 En İdeal Tercih: {p['optimal_market']} (Oran: {p['optimal_odds']} | Güven: %{p['optimal_confidence']}) -> {durum}")
    print(f"  💡 Gerekçe: {p['optimal_reason']}\n")

print("="*75)
print("  🎟️ DÜNÜN AKILLI KUPONLARI NE YAPARDI?")
print("="*75)
coupons = generate_smart_coupons(predictions)

ak = coupons.get("altin_kasa", {})
if ak and ak.get("maclar"):
    ak_hit = all(evaluate_optimal_bet(m["raw_match"])[0] for m in ak["maclar"])
    durum = "✅ TUTTU" if ak_hit else "❌ YATTI"
    print(f"\n{ak['baslik']} -> Oran: {ak['toplam_oran']} | {durum}")
    for m in ak["maclar"]:
        h, _ = evaluate_optimal_bet(m["raw_match"])
        ic = "✅" if h else "❌"
        print(f"  {ic} [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']}) [Skor: {m['raw_match']['actual_score']}]")

dk = coupons.get("gol_yagmuru", {})
if dk and dk.get("maclar"):
    dk_hit = all(evaluate_optimal_bet(m["raw_match"])[0] for m in dk["maclar"])
    durum = "✅ TUTTU" if dk_hit else "❌ YATTI"
    print(f"\n{dk['baslik']} -> Oran: {dk['toplam_oran']} | {durum}")
    for m in dk["maclar"]:
        h, _ = evaluate_optimal_bet(m["raw_match"])
        ic = "✅" if h else "❌"
        print(f"  {ic} [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']}) [Skor: {m['raw_match']['actual_score']}]")

print("\n" + "="*75)
print("  🏆 DÜNÜN OMNI-MARKET BAŞARI ÖZETİ")
print("="*75)
success_rate = round(won_bets / total_bets * 100, 1)
print(f"Toplam Maç Sayısı:        {total_bets}")
print(f"Kazanılan En İdeal Tercih: {won_bets} / {total_bets} (%{success_rate})")
if push_bets > 0:
    print(f"İade Edilen Bahis (DNB):  {push_bets}")
print("="*75)

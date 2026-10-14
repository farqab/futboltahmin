import sys, os
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match
from typesafe_engine import analyze_single_match
from concurrent.futures import ThreadPoolExecutor

dates = [
    ("20260912", "12 Eylül Cumartesi"),
    ("20260913", "13 Eylül Pazar"),
    ("20260919", "19 Eylül Cumartesi (Dün)")
]

matches = fetch_finished_matches(dates)
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

bankolar = [r for r in results if r.get("action_status") == "BET"]
goller = [r for r in results if r.get("action_status") == "GOAL_ONLY"]
paslar = [r for r in results if r.get("action_status") == "NO_BET"]

print("="*75)
print(f"📊 TÜM BACKTEST TARİHLERİNDE KARAR BAZLI GENEL İSTATİSTİK")
print("="*75)

b_hit = sum(1 for b in bankolar if eval_p(b)[0])
print(f"🟢 TOPLAM BANKOLAR: {b_hit} / {len(bankolar)} TUTTU (%{round(b_hit/max(1,len(bankolar))*100, 1)})")
for b in bankolar:
    h, _ = eval_p(b)
    st = "✅ TUTTU" if h else "❌ YATTI"
    print(f"   • [{b['league']}] {b['date']} | {b['home_name']} vs {b['away_name']} (Skor: {b['actual_score']}) ➔ {b['optimal_market']} | {st}")

g_hit = sum(1 for g in goller if eval_p(g)[0])
print(f"\n🟡 TOPLAM GOL OYNA: {g_hit} / {len(goller)} TUTTU (%{round(g_hit/max(1,len(goller))*100, 1)})")

traps = 0
for p in paslar:
    hs, as_ = map(int, p["actual_score"].split("-"))
    # Pas geçilen maçta favori (tahmin_ms) kazanamadıysa tuzak patlamıştır
    actual_ms = "MS 1" if hs > as_ else ("MS 2" if as_ > hs else "MS X")
    if actual_ms != p.get("tahmin_ms"):
        traps += 1

print(f"\n🔴 TOPLAM PAS GEÇİLEN MAÇLAR: {len(paslar)} Maç")
print(f"   🛡️ Pas Kararının Başarısı: {traps} / {len(paslar)} maçta FAVORİ TAKILDI/SÜRPRİZ OLDU! (%{round(traps/max(1,len(paslar))*100, 1)} İsabetli Pas)")

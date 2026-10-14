import sys, os
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from backtest_v3 import fetch_finished_matches, enrich_match
from typesafe_engine import analyze_single_match
from concurrent.futures import ThreadPoolExecutor

matches = fetch_finished_matches([("20260919", "19 Eyl Cumartesi")])
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

bankolar = []
goller = []
paslar = []

for r in results:
    h, p = eval_p(r)
    r["is_hit"] = h
    r["is_push"] = p
    r["ms_hit"] = (r.get("tahmin_ms") == r.get("actual_ms"))
    act = r.get("action_status")
    if act == "BET":
        bankolar.append(r)
    elif act == "GOAL_ONLY":
        goller.append(r)
    else:
        paslar.append(r)

print("="*75)
print(f"🟢 1. BANKO TERCİHLER ({len(bankolar)} Maç):")
print("="*75)
b_hit = sum(1 for b in bankolar if b["is_hit"])
print(f"   Net Başarı: {b_hit} / {len(bankolar)} TUTTU (%{round(b_hit/max(1,len(bankolar))*100, 1)})")
for b in bankolar:
    st = "✅ TUTTU" if b["is_hit"] else "❌ YATTI"
    print(f"   • [{b['league']}] {b['home_name']} vs {b['away_name']} (Skor: {b['actual_score']})")
    print(f"     Tercih: {b['optimal_market']} (Oran: {b['optimal_odds']}) | {st}")

print("\n" + "="*75)
print(f"🟡 2. GOL OYNA TERCİHLERİ ({len(goller)} Maç):")
print("="*75)
g_hit = sum(1 for g in goller if g["is_hit"])
print(f"   Net Başarı: {g_hit} / {len(goller)} TUTTU (%{round(g_hit/max(1,len(goller))*100, 1)})")
for g in goller:
    st = "✅ TUTTU" if g["is_hit"] else "❌ YATTI"
    print(f"   • [{g['league']}] {g['home_name']} vs {g['away_name']} (Skor: {g['actual_score']})")
    print(f"     Tercih: {g['optimal_market']} (Oran: {g['optimal_odds']}) | {st}")

print("\n" + "="*75)
print(f"🔴 3. PAS GEÇ (UZAK DUR) DENEN MAÇLAR ({len(paslar)} Maç):")
print("="*75)
trapped = 0
for p in paslar:
    fav_failed = not p["ms_hit"]
    if fav_failed: trapped += 1
    tr_status = "🛡️ TUZAK PATLADI (Pas Geçmek Kurtardı!)" if fav_failed else "⚪ Favori Kazandı"
    print(f"   • [{p['league']}] {p['home_name']} vs {p['away_name']} (Skor: {p['actual_score']}) | Tuzak: {p.get('trap_score')}/10 ➔ {tr_status}")

rate = round(trapped/max(1,len(paslar))*100, 1)
print(f"\n   📌 Pas Kararının Doğruluğu: {trapped} / {len(paslar)} maçta FAVORİ YATTI veya SÜRPRİZ OLDU! (%{rate} İsabetli Pas!)")

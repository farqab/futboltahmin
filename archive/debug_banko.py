import sys, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

with open("backtest_karsilastirmali_sonuclari.json", encoding="utf-8") as f:
    data = json.load(f)

old = data.get("old_system", [])
new = data.get("new_system", [])

# ESKİ SİSTEM — lig bazlı banko analizi
print("=== ESKİ SİSTEM BANKOLAR ===")
old_bankolar = [m for m in old if m.get("status") == "BET"]
for b in old_bankolar:
    hit = "✅" if b.get("ms_hit") else "❌"
    print(f"  {hit} [{b['period']} - {b['league']}] {b['home_name']} vs {b['away_name']} → {b['pred_ms']} | Skor: {b['actual_score']} | Güven: %{b['conf']}")

# ESKİ SİSTEM — lig bazlı
print("\n=== ESKİ SİSTEM LİG BAZLI ===")
from collections import defaultdict
lig_old = defaultdict(lambda: {"total":0,"ms":0,"ou":0,"btts":0})
for m in old:
    l = m["league"]
    lig_old[l]["total"] += 1
    if m.get("ms_hit"): lig_old[l]["ms"] += 1
    if m.get("ou_hit"): lig_old[l]["ou"] += 1
    if m.get("btts_hit"): lig_old[l]["btts"] += 1
for l, s in sorted(lig_old.items()):
    t = s["total"]
    print(f"  {l:<20} | MS: {s['ms']}/{t} (%{round(s['ms']/t*100,1)}) | 2.5: {s['ou']}/{t} (%{round(s['ou']/t*100,1)}) | KG: {s['btts']}/{t} (%{round(s['btts']/t*100,1)})")

# YENİ SİSTEM — lig bazlı
print("\n=== YENİ SİSTEM LİG BAZLI ===")
lig_new = defaultdict(lambda: {"total":0,"ms":0,"ou":0,"btts":0})
for m in new:
    l = m["league"]
    lig_new[l]["total"] += 1
    if m.get("ms_hit"): lig_new[l]["ms"] += 1
    if m.get("ou_hit"): lig_new[l]["ou"] += 1
    if m.get("btts_hit"): lig_new[l]["btts"] += 1
for l, s in sorted(lig_new.items()):
    t = s["total"]
    print(f"  {l:<20} | MS: {s['ms']}/{t} (%{round(s['ms']/t*100,1)}) | 2.5: {s['ou']}/{t} (%{round(s['ou']/t*100,1)}) | KG: {s['btts']}/{t} (%{round(s['btts']/t*100,1)})")

# YENİ SİSTEM — AI kaç kez banko dedi?
new_banko_ai = [m for m in new if m.get("action") == "banko_oyna"]
new_gol_ai   = [m for m in new if m.get("action") == "gol_oyna"]
new_pas_ai   = [m for m in new if m.get("action") == "pas_gec_bulasma"]
print(f"\n=== YENİ SİSTEM AI SEÇİMLERİ ===")
print(f"  banko_oyna: {len(new_banko_ai)} maç")
print(f"  gol_oyna: {len(new_gol_ai)} maç")
print(f"  pas_gec_bulasma: {len(new_pas_ai)} maç")

# Hafta bazlı performans (yeni sistem)
print("\n=== YENİ SİSTEM HAFTA BAZLI MS ===")
period_new = defaultdict(lambda: {"total":0,"ms":0})
for m in new:
    p = m.get("period","?")
    period_new[p]["total"] += 1
    if m.get("ms_hit"): period_new[p]["ms"] += 1
for p, s in sorted(period_new.items()):
    t = s["total"]
    print(f"  {p}: MS {s['ms']}/{t} (%{round(s['ms']/t*100,1)})")

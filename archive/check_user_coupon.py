import sys, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

with open("tahminler_20260920.json", encoding="utf-8") as f:
    data = json.load(f)

my_picks = [
    ("Manchester City", "Man City & 1.5 Üst (1.35)"),
    ("Como", "Como & 1.5 Üst (1.46)"),
    ("Amed", "2.5 Üst (1.50)"),
    ("Leeds", "2.5 Üst (1.51)"),
    ("Juventus", "KG Var (1.68)"),
    ("Marseille", "PSG & 1.5 Üst (1.32)")
]

print("="*75)
print("  🎟️ SENİN NESİNE KUPONUNDAKİ MAÇLARIN GÜNCEL DURUM ANALİZİ")
print("="*75)

for name, user_pick in my_picks:
    matched = False
    for m in data:
        if name.lower() in m["home_name"].lower() or name.lower() in m["away_name"].lower():
            matched = True
            print(f"\n⚽ {m['home_name']} vs {m['away_name']} [{m['league']}] — Saat: {m.get('time_tr')} TSİ")
            print(f"   👉 SENİN KUPONUNDAKİ TERCİH: {user_pick}")
            print(f"   👑 SİSTEMİN ŞUANKİ SEÇİMİ:    {m.get('optimal_market')} (Oran: {m.get('optimal_odds')} | Güven: %{m.get('optimal_confidence')})")
            print(f"   🎲 10.000 Maç Simülasyonu:   1.5 Üst %{m.get('sim_prob_over_1_5')} | 2.5 Üst %{m.get('sim_prob_over_2_5')} | KG %{m.get('sim_prob_btts')} | En Olası: {m.get('sim_top_score_str')}")
            print(f"   ⚠️ Tuzak/Risk Puanı:          {m.get('trap_score')}/10")
            print(f"   📈 Akıllı Para/Oran:          {m.get('odds_drift_desc', 'Normal piyasa')}")
            break

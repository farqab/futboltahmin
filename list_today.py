import sys, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

with open("tahminler_20260920.json", encoding="utf-8") as f:
    data = json.load(f)

print("="*75)
print("  📅 20 EYLÜL 2026 (BUGÜN) — SİSTEMİN OYNADIĞI TÜM BAHİSLER")
print("="*75)

playable = [d for d in data if d.get("action_status") in ["BET", "GOAL_ONLY"]]
for p in playable:
    sim = p.get("sim_summary", "")
    top_score = p.get("sim_top_score_str", "")
    print(f"• [{p['league']}] {p.get('time_tr', '')} TSİ | {p['home_name']} vs {p['away_name']}")
    print(f"  👑 OYNANAN BAHİS: {p.get('optimal_market')} | Oran: {p.get('optimal_odds')} | Güven: %{p.get('optimal_confidence')}")
    print(f"  🎲 10k Simülasyon: 1.5 Üst %{p.get('sim_prob_over_1_5')} | 2.5 Üst %{p.get('sim_prob_over_2_5')} | KG %{p.get('sim_prob_btts')} | En Olası: {top_score}")
    print(f"  💡 Karar: {p.get('action_label')} | Gerekçe: {p.get('optimal_reason')}")
    print()

from smart_coupon_generator import generate_smart_coupons
coupons = generate_smart_coupons(data)
print("="*75)
print("  🎟️ 20 EYLÜL İÇİN OLUŞTURULAN HAZIR KOMBİNELER")
print("="*75)
for k, c in coupons.items():
    if not c.get("maclar"): continue
    print(f"\n{c['baslik']} (Toplam Oran: {c['toplam_oran']})")
    print("-" * 50)
    for m in c["maclar"]:
        print(f"  • [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']}) [Güven: %{m['guven']}]")

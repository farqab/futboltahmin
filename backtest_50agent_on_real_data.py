"""
backtest_50agent_on_real_data.py — 50-Agent Swarm tanılama raporu.
Bu script adayları listeler; tek başına isabet oranı veya ROI backtest'i değildir.
"""

import sys, os
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)
from backtest_v3 import fetch_finished_matches, enrich_match
from typesafe_engine import analyze_single_match
from agent_swarm_50 import generate_50agent_smart_portfolio, Swarm50Engine
from concurrent.futures import ThreadPoolExecutor

def main():
    print("=" * 80)
    print(" 🤖 50-AGENT SWARM GERÇEK MAÇ VERİSİ BACKTESTİ (19 EYLÜL 2026)")
    print("=" * 80)

    matches = fetch_finished_matches([("20260919", "19 Eylül Cumartesi")])
    if not matches:
        print("[!] Veri bulunamadı.")
        return

    print(f"[*] Toplam {len(matches)} adet gerçek maç çekildi. 50 Ajan analizine başlanıyor...")

    with ThreadPoolExecutor(max_workers=8) as ex:
        enriched = list(ex.map(enrich_match, matches))

    with ThreadPoolExecutor(max_workers=6) as ex:
        analyzed = list(ex.map(analyze_single_match, enriched))

    # 50-Agent Swarm ile Portföyü Hesapla
    portfolio = generate_50agent_smart_portfolio(analyzed)

    print("\n" + "=" * 80)
    print(f"📊 50-AJAN DEĞERLENDİRME ÖZETİ:")
    print(f"   Toplam Maç: {portfolio['total_matches_evaluated']}")
    print(f"   ✅ %75 Konsensüs ile Onaylananlar: {portfolio['passed_count']}")
    print(f"   🚫 Veto Edilen / Düşük Konsensüslüler: {portfolio['vetoed_count']}")
    print("=" * 80)

    print("\n🟢 ONAY ALAN EN GÜVENİLİR MAÇLAR (Konsensüs >= %75):")
    for pm in portfolio["passed_matches"][:6]:
        act = pm["match"].get("actual_score", "-")
        print(f"  • [{pm['league']}] {pm['home_name']} vs {pm['away_name']} (Skor: {act})")
        print(f"    👉 Tercih: {pm['best_market']} | Oran: {pm['best_odd']} | Konsensüs: %{pm['consensus']}")
        print(f"    💡 Gerekçe: {pm['best_reason']}")

    if portfolio.get("altin_kasa"):
        ak = portfolio["altin_kasa"]
        print("\n" + "=" * 80)
        print("🏆 50-AJAN 'ALTIN KASA' (2'Lİ BANKO KUPON):")
        print(f"Kupon: {ak['kupon_adi']}")
        print(f"Toplam Oran: {ak['toplam_oran']} | Güven: {ak['bilesik_guven']}")
        for m in ak["maclar"]:
            # Bu scriptte gerçek sonuç-market eşlemesi yapılmadığından kupon sonucu hesaplanmaz.
            print(f"  👉 {m['mac']} -> {m['tercih']} (Oran: {m['oran']}) [Konsensüs: {m['konsensus']}]")
        print("=" * 80)

if __name__ == "__main__":
    main()

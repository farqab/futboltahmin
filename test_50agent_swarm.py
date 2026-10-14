"""
test_50agent_swarm.py — 50-Agent Swarm Stres Testi ve Karşılaştırmalı Analiz
===========================================================================
Bu test, kullanıcının daha önce kupon kaybetmesine yol açan:
1) 2025 Mayıs Sezon Sonu Maçları (Lazio-Lecce vb. hedefsiz devlerin patlaması)
2) 19-20 Eylül 2026 Maçları (Como-Frosinone tuzağı, ölü Nesine oranları)
üzerinde 50 Ajanı çalıştırır ve veto mekanizmasının nasıl kuponu kurtardığını gösterir.
"""

import sys
import json
from agent_swarm_50 import Swarm50Engine, generate_50agent_smart_portfolio
from monte_carlo_simulator import simulate_match

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

def run_stress_test():
    print("=" * 80)
    print("🚀 50-AGENT SWARM & TYPESAFE JEV STRES TESTİ BAŞLATILIYOR...")
    print("=" * 80)

    # 1. TEST SETİ: SEZON SONU MAYIS 2025 TUZAK MAÇLARI (Kullanıcının Kupon Yattığı Hafta)
    may_matches = [
        {
            "league": "Serie A",
            "home_name": "Lecce",
            "away_name": "Lazio",
            "home_rank": 17, # Küme düşme potasında! Can havliyle direniyor!
            "away_rank": 7,  # Hedefi kalmamış veya rehavette!
            "round": 37,     # 37. Hafta (Sezon Sonu)
            "is_late_season": True,
            "odds": {"1": 4.10, "X": 3.40, "2": 1.78, "2.5_ust": 1.90, "kg_var": 1.82},
            "odds_drift": {"direction": "DRIFT_UP", "note": "Lazio oranı açılıştan beri şişiyor (Tuzak)"},
            "actual_result": "1-0 (Lecce Kazandı - Lazio Yattı)"
        },
        {
            "league": "Bundesliga",
            "home_name": "Eintracht Frankfurt",
            "away_name": "Augsburg",
            "home_rank": 6,
            "away_rank": 11,
            "round": 34, # Son hafta
            "is_late_season": True,
            "is_dead_rubber": True, # Hedefsiz maç
            "odds": {"1": 1.75, "X": 3.80, "2": 3.60, "2.5_ust": 1.55, "kg_var": 1.50},
            "actual_result": "1-2 (Sürpriz Bitti)"
        },
        {
            "league": "Premier League",
            "home_name": "Manchester City",
            "away_name": "Bournemouth",
            "home_rank": 1, # Şampiyonluk için mutlaka kazanmak zorunda!
            "away_rank": 12,
            "round": 37,
            "is_late_season": True,
            "odds": {"1": 1.22, "X": 5.50, "2": 9.00, "2.5_ust": 1.45, "kg_var": 1.75},
            "actual_result": "3-1 (Man City Kazandı)"
        },
        {
            "league": "La Liga",
            "home_name": "Real Madrid",
            "away_name": "Alaves",
            "home_rank": 2,
            "away_rank": 14,
            "round": 36,
            "is_late_season": True,
            "odds": {"1": 1.30, "X": 5.00, "2": 8.50, "2.5_ust": 1.50, "kg_var": 1.70},
            "actual_result": "5-0 (Real Madrid Kazandı)"
        }
    ]

    print("\n📌 SENARYO 1: SEZON SONU REHAVET & TUZAK MAÇLARI TESTİ")
    print("-" * 80)
    engine = Swarm50Engine()

    for m in may_matches:
        sim = simulate_match(m)
        votes, consensus, warnings = engine.evaluate_match_all_agents(m, sim)
        print(f"\n⚽ Maç: {m['home_name']} vs {m['away_name']} ({m['league']})")
        print(f"   📊 50 Ajan Konsensüs Skoru: %{consensus}")
        if warnings:
            print(f"   🚨 ALARMLAR VE VETOLAR ({len(warnings)} adet):")
            for w in warnings:
                print(f"      - {w}")
        else:
            print("   ✅ TÜM AJANLAR ONAYLADI (Temiz Maç)")
        print(f"   🎯 Gerçek Sonuç: {m.get('actual_result')}")

    # Portföy üret
    portfolio_may = generate_50agent_smart_portfolio(may_matches)
    print("\n" + "=" * 80)
    print("🏆 50-AGENT SWARM TARAFINDAN OLUŞTURULAN 'ALTIN KASA' (SEZON SONU):")
    if portfolio_may.get("altin_kasa"):
        ak = portfolio_may["altin_kasa"]
        print(f"Kupon: {ak['kupon_adi']}")
        print(f"Toplam Oran: {ak['toplam_oran']} | Güven: {ak['bilesik_guven']}")
        for match_info in ak["maclar"]:
            print(f"  👉 {match_info['mac']} -> {match_info['tercih']} (Oran: {match_info['oran']}) [Konsensüs: {match_info['konsensus']}]")
            print(f"     Gerekçe: {match_info['gerekce']}")
    else:
        print("⚠️ Hiçbir maç %75 konsensüsü geçemedi veya tümü veto edildi. Kupon iptal edildi (Para korundu!).")

    # 2. TEST SETİ: 19-20 EYLÜL 2026 HAFTASONU BÜLTENİ (Como-Frosinone tuzağı)
    sept_matches = [
        {
            "league": "Serie B",
            "home_name": "Como",
            "away_name": "Frosinone",
            "odds": {"1": 1.65, "X": 3.40, "2": 4.50, "2.5_ust": 1.85, "kg_var": 1.75},
            "odds_drift": {"direction": "DRIFT_UP", "note": "Como oranı yukarı yönlü drift yaptı"},
            "actual_result": "İlk Yarı 0-2 Frosinone öne geçti (Kullanıcının yattığı maç!)"
        },
        {
            "league": "Serie A",
            "home_name": "Napoli",
            "away_name": "Cagliari",
            "home_scored_last5": 11,
            "home_conceded_last5": 4,
            "away_scored_last5": 5,
            "away_conceded_last5": 8,
            "odds": {"1": 1.35, "X": 4.50, "2": 7.00, "2.5_ust": 1.65, "kg_var": 1.72},
            "actual_result": "2-1 (Kullanıcının tuttuğu KG Var maçı)"
        },
        {
            "league": "Bundesliga",
            "home_name": "Bayern Münih",
            "away_name": "Augsburg",
            "home_scored_last5": 16,
            "home_conceded_last5": 4,
            "away_scored_last5": 6,
            "away_conceded_last5": 11,
            "odds": {"1": 1.15, "X": 7.50, "2": 12.00, "2.5_ust": 1.30, "kg_var": 1.70},
            "actual_result": "4-1 (Bayern Kazandı, ama 1.15 ölü oran!)"
        },
        {
            "league": "Premier League",
            "home_name": "Arsenal",
            "away_name": "Everton",
            "home_scored_last5": 10,
            "home_conceded_last5": 2,
            "away_scored_last5": 3,
            "away_conceded_last5": 7,
            "odds": {"1": 1.45, "X": 4.20, "2": 6.50, "2.5_ust": 1.70, "kg_var": 1.85},
            "actual_result": "2-0 (Arsenal Kazandı)"
        }
    ]

    print("\n\n" + "=" * 80)
    print("📌 SENARYO 2: 19-20 EYLÜL 2026 GERÇEK BÜLTENİ & COMO TUZAĞI ANALİZİ")
    print("-" * 80)
    for m in sept_matches:
        sim = simulate_match(m)
        votes, consensus, warnings = engine.evaluate_match_all_agents(m, sim)
        print(f"\n⚽ Maç: {m['home_name']} vs {m['away_name']} ({m['league']})")
        print(f"   📊 50 Ajan Konsensüs Skoru: %{consensus}")
        if warnings:
            print(f"   🚨 ALARMLAR VE VETOLAR ({len(warnings)} adet):")
            for w in warnings:
                print(f"      - {w}")
        else:
            print("   ✅ TÜM AJANLAR ONAYLADI (Güvenilir Maç)")

    portfolio_sept = generate_50agent_smart_portfolio(sept_matches)
    print("\n" + "=" * 80)
    print("🏆 50-AGENT SWARM 'ALTIN KASA' (EYLÜL BÜLTENİ):")
    if portfolio_sept.get("altin_kasa"):
        ak = portfolio_sept["altin_kasa"]
        print(f"Kupon: {ak['kupon_adi']}")
        print(f"Toplam Oran: {ak['toplam_oran']} | Bileşik Güven: {ak['bilesik_guven']}")
        for match_info in ak["maclar"]:
            print(f"  👉 {match_info['mac']} -> {match_info['tercih']} (Oran: {match_info['oran']}) [Konsensüs: {match_info['konsensus']}]")
            print(f"     Gerekçe: {match_info['gerekce']}")
    print("=" * 80)

if __name__ == "__main__":
    run_stress_test()

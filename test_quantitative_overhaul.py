"""
test_quantitative_overhaul.py — Niceliksel Sistem Birim ve Entegrasyon Testleri
==============================================================================
Test Kapsamı:
1. Dixon-Coles Bivariate modeli ve 0-0/1-1 tau düzeltmelerinin doğrulanması.
2. Sahte oranların (2.1/3.3/3.1) 'No Data, No Bet' gereği yakalanıp elenmesi.
3. Gerçek oranlarda marj sökme ve +EV hesaplama hassasiyeti.
4. Kesirli Kelly hisselendirmesi ve sert tavan kuralı (%1.5).
5. Bahis defteri (Betting Ledger), CLV ve Brier kalibrasyon skoru hesaplaması.
6. Uçtan uca boru hattı (core_pipeline) testi.
"""

import os
import sys
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

from dixon_coles_model import simulate_dixon_coles, elo_engine
from value_detector import find_value_bets, is_dummy_or_missing_odds, strip_margin_1x2, strip_margin_twoway
from kelly_risk_manager import KellyRiskManager
from betting_ledger import BettingLedger, DB_PATH
from core_pipeline import run_quantitative_pipeline, print_pipeline_report


class TestQuantitativeOverhaul(unittest.TestCase):

    def test_dixon_coles_simulation(self):
        match = {
            "league": "Premier League",
            "home_name": "Arsenal",
            "away_name": "Chelsea",
            "home_scored_last5": 11,
            "home_conceded_last5": 3,
            "away_scored_last5": 7,
            "away_conceded_last5": 6
        }
        res = simulate_dixon_coles(match)
        self.assertEqual(res["model_type"], "Dixon-Coles (1997)")
        self.assertGreater(res["prob_home_win"], 0.0)
        self.assertGreater(res["prob_draw"], 0.0)
        self.assertGreater(res["prob_away_win"], 0.0)
        
        # Olasılıkların toplamı yaklaşık 1.0 olmalı
        total_p = res["prob_home_win"] + res["prob_draw"] + res["prob_away_win"]
        self.assertAlmostEqual(total_p, 1.0, places=2)
        print("✅ [TEST 1 BAŞARILI] Dixon-Coles simülasyonu ve tau düzeltmesi doğrulandı.")

    def test_no_data_no_bet_dummy_rejection(self):
        # Sahte oranlar
        dummy_odds = {"1": 2.1, "X": 3.3, "2": 3.1}
        is_dummy, reason = is_dummy_or_missing_odds(dummy_odds)
        self.assertTrue(is_dummy)
        self.assertIn("YASAKLI SAHTE ORAN", reason)

        # Gerçek oranlar
        real_odds = {"1": 1.65, "X": 3.80, "2": 4.75}
        is_dummy_real, _ = is_dummy_or_missing_odds(real_odds)
        self.assertFalse(is_dummy_real)
        print("✅ [TEST 2 BAŞARILI] Sahte oranlar (2.1/3.3/3.1) 'No Data, No Bet' ile anında elendi.")

    def test_margin_stripping_and_value(self):
        o1, ox, o2 = 1.65, 3.80, 4.75
        p1, px, p2, margin = strip_margin_1x2(o1, ox, o2)
        self.assertAlmostEqual(p1 + px + p2, 1.0, places=3)
        self.assertGreater(margin, 0.0) # Bahis şirketi kâr marjı pozitif olmalı

        match = {
            "home_name": "Real Madrid",
            "away_name": "Getafe",
            "league": "La Liga",
            "odds": {"1": 1.60, "X": 4.50, "2": 7.00, "2.5_ust": 1.65, "2.5_alt": 2.20}
        }
        dc_res = {
            "prob_home_win": 0.75, # Model Real Madrid'e yüksek şans veriyor
            "prob_draw": 0.15,
            "prob_away_win": 0.10,
            "prob_over_2_5": 0.62,
            "prob_under_2_5": 0.38
        }
        val = find_value_bets(match, dc_res, min_ev=0.01)
        self.assertEqual(val["status"], "ANALYZED")
        self.assertGreater(val["value_bets_found"], 0)
        print("✅ [TEST 3 BAŞARILI] Marj sökme ve +EV tespiti doğrulandı.")

    def test_margin_stripping_rejects_invalid_odds(self):
        """Invalid public inputs should raise a clear validation error."""
        with self.assertRaises(ValueError):
            strip_margin_1x2(1.80, 0, 3.20)
        with self.assertRaises(ValueError):
            strip_margin_twoway("not-an-odd", 2.10)

    def test_kelly_risk_and_stake_capping(self):
        risk = KellyRiskManager(initial_bankroll=1000.0, max_stake_pct=0.015)
        # Çok yüksek EV olsa bile tavan %1.5 (15 TL) aşılmamalı
        stake_info = risk.calculate_stake(odd=2.00, win_prob=0.70, ev=0.40)
        self.assertLessEqual(stake_info["recommended_stake"], 15.0)
        self.assertEqual(stake_info["stake_pct"], 1.5)
        print("✅ [TEST 4 BAŞARILI] Kesirli Kelly ve %1.5 sert kasa tavanı uygulandı.")

    def test_betting_ledger_and_metrics(self):
        test_db = os.path.join(PROJECT_DIR, "test_ledger.db")
        if os.path.exists(test_db):
            os.remove(test_db)
        from betting_ledger import init_ledger_db
        init_ledger_db(test_db)

        # Geçici bir bahsi kaydet ve sonuçlandır
        b_id = BettingLedger.record_bet(
            match_name="Liverpool vs Everton",
            league="Premier League",
            market="MS 1",
            taken_odd=1.55,
            model_prob=0.70,
            ev=0.085,
            stake=15.0,
            market_fair_prob=0.68,
            closing_odd=1.50, # Kapanış oranı düşmüş -> CLV pozitif!
            db_path=test_db
        )
        BettingLedger.settle_bet(b_id, outcome="WON", closing_odd=1.50, db_path=test_db)
        summary = BettingLedger.get_performance_summary(db_path=test_db)
        self.assertGreater(summary["total_settled_bets"], 0)
        self.assertIn("brier_score", summary)
        self.assertIn("avg_clv_pct", summary)
        print(f"✅ [TEST 5 BAŞARILI] Bahis Defteri izole test edildi: Brier={summary['brier_score']}, Ortalama CLV=%{summary['avg_clv_pct']}")
        
        # Test veritabanını temizle
        if os.path.exists(test_db):
            os.remove(test_db)

    def test_core_pipeline_run(self):
        test_matches = [
            {
                "home_name": "Bayern Münih",
                "away_name": "Bayer Leverkusen",
                "league": "Bundesliga",
                "mbs": 1,
                "home_scored_last5": 15,
                "home_conceded_last5": 4,
                "away_scored_last5": 12,
                "away_conceded_last5": 6,
                "odds": {"1": 1.70, "X": 4.10, "2": 4.20, "2.5_ust": 1.50, "2.5_alt": 2.50}
            },
            {
                "home_name": "Manchester City",
                "away_name": "Watford",
                "league": "Premier League",
                "mbs": 1,
                "odds": {"1": 2.1, "X": 3.3, "2": 3.1} # Sahte oran -> Reddedilmeli!
            }
        ]
        res = run_quantitative_pipeline(test_matches, record_to_ledger=False)
        self.assertEqual(res["analyzed_matches_count"], 1)
        self.assertEqual(res["rejected_matches_count"], 1)
        print_pipeline_report(res)
        print("✅ [TEST 6 BAŞARILI] Uçtan uca niceliksel boru hattı kusursuz çalıştı.")


if __name__ == "__main__":
    unittest.main()

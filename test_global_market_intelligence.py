"""
test_global_market_intelligence.py — Küresel Sharp İstihbarat Motoru Testleri
"""

import unittest
from global_market_intelligence import (
    FlashscoreNinjaClient,
    PinnacleSharpBenchmark,
    DroppingOddsAggregator,
    GlobalMarketIntelligence
)


class TestGlobalMarketIntelligence(unittest.TestCase):

    def test_pinnacle_margin_stripping(self):
        """Pinnacle keskin oranlarından marj sökme test edilir."""
        res = PinnacleSharpBenchmark.strip_pinnacle_margin(2.00, 3.40, 4.00)
        self.assertAlmostEqual(res["p_1"] + res["p_x"] + res["p_2"], 1.0, places=3)
        self.assertGreater(res["sharp_margin_pct"], 0.0)
        self.assertLess(res["sharp_margin_pct"], 6.0)

    def test_pinnacle_edge_evaluation(self):
        """Pinnacle kapanış çizgisine göre sazan tuzağı tespiti."""
        pinnacle_odds = {"1": 2.50, "X": 3.20, "2": 3.00}
        # Yerel büro 2.05 veriyorsa (Pinnacle 2.50 iken yerel oran çok düşük = -EV)
        bad_edge = PinnacleSharpBenchmark.evaluate_edge_vs_sharp("MS 1", 2.05, pinnacle_odds)
        self.assertFalse(bad_edge["is_sharp_backed"])

        # Yerel büro 2.65 veriyorsa (Pinnacle 2.50 iken yerel oran yüksek = +EV)
        good_edge = PinnacleSharpBenchmark.evaluate_edge_vs_sharp("MS 1", 2.65, pinnacle_odds)
        self.assertTrue(good_edge["is_sharp_backed"])

    def test_dropping_odds_detection(self):
        """Açılış-kapanış farkından steam move tespiti."""
        open_odds = {"1": 2.20, "X": 3.30, "2": 3.40}
        # 1'in oranı 2.20'den 1.95'e çöktü (%11.36 düşüş)
        curr_odds = {"1": 1.95, "X": 3.40, "2": 4.10}

        steam = DroppingOddsAggregator.audit_market_drops("MS 1", open_odds, curr_odds)
        self.assertTrue(steam["has_steam"])
        self.assertTrue(steam["steam_with_us"])
        self.assertFalse(steam["steam_against_us"])

    def test_opposing_steam_triggers_veto(self):
        """Biz MS 1 derken rakibe (MS 2) büyük para aktıysa VETO edilmeli."""
        open_odds = {"1": 2.10, "X": 3.20, "2": 3.50}
        # MS 2 oranı 3.50'den 2.80'e çöktü (%20 düşüş)
        curr_odds = {"1": 2.40, "X": 3.30, "2": 2.80}

        eval_res = GlobalMarketIntelligence.evaluate_bet_proposal(
            market="MS 1",
            taken_odd=2.40,
            model_prob=0.45,
            opening_odds=open_odds,
            current_odds=curr_odds
        )
        self.assertTrue(eval_res["is_vetoed"])
        self.assertEqual(eval_res["verdict"], "VETOED_BY_SHARP_DROP")
        self.assertEqual(eval_res["confidence_multiplier"], 0.0)

    def test_aligned_steam_triggers_boost(self):
        """Bizim tercihimize büyük para aktıysa BOOST almalı."""
        open_odds = {"1": 2.20, "X": 3.30, "2": 3.40}
        curr_odds = {"1": 1.95, "X": 3.40, "2": 4.10}

        eval_res = GlobalMarketIntelligence.evaluate_bet_proposal(
            market="MS 1",
            taken_odd=1.95,
            model_prob=0.55,
            opening_odds=open_odds,
            current_odds=curr_odds
        )
        self.assertFalse(eval_res["is_vetoed"])
        self.assertIn("BOOSTED", eval_res["verdict"])
        self.assertGreaterEqual(eval_res["confidence_multiplier"], 1.25)


if __name__ == "__main__":
    unittest.main()

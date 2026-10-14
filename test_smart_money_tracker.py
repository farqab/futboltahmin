"""
test_smart_money_tracker.py — Akıllı Para (Smart Money) & Steam Move Test Paketi
================================================================================
Bu test:
1. Steam Move tespit fonksiyonunun oran çöküşlerini (%4+) doğru algıladığını test eder.
2. Smart Money uyum denetiminin (ALIGNED vs VETO) sazan tuzaklarını engellediğini doğrular.
3. value_detector entegrasyonunda veto edilen maçların filtrelendiğini, onaylananların
   güven çarpanı kazandığını denetler.
"""

import unittest
from smart_money_tracker import detect_steam_moves, verify_smart_money_alignment
from value_detector import find_value_bets


class TestSmartMoneyTracker(unittest.TestCase):

    def test_steam_move_detection(self):
        """Açılıştan kapanışa oran çöküşü (Steam move) doğru algılanmalı."""
        open_odds = {"1": 2.20, "X": 3.30, "2": 3.40}
        curr_odds = {"1": 1.95, "X": 3.40, "2": 3.80}  # MS 1'e büyük para akmış (2.20 -> 1.95, %11.36 düşüş)

        res = detect_steam_moves(open_odds, curr_odds, threshold_pct=4.0)
        self.assertTrue(res["has_steam"])
        self.assertEqual(res["steam_market"], "1")
        self.assertGreater(res["steam_drop_pct"], 10.0)
        self.assertEqual(res["faded_market"], "2")  # MS 2 oran yükselmiş (piyasa kaçmış)

    def test_no_steam_move_on_stable_odds(self):
        """Oranlar stabil kaldığında steam tetiklenmemeli."""
        open_odds = {"1": 2.10, "X": 3.30, "2": 3.10}
        curr_odds = {"1": 2.08, "X": 3.32, "2": 3.12}

        res = detect_steam_moves(open_odds, curr_odds, threshold_pct=4.0)
        self.assertFalse(res["has_steam"])
        self.assertIsNone(res["steam_market"])

    def test_smart_money_alignment_boost(self):
        """Model tercihi Akıllı Para ile aynı yöndeyse onay ve güven artışı verilmeli."""
        steam_data = {
            "has_steam": True,
            "steam_market": "1",
            "steam_drop_pct": 8.5,
            "faded_market": "2"
        }

        alignment = verify_smart_money_alignment("MS 1 (Arsenal)", steam_data)
        self.assertEqual(alignment["verdict"], "ALIGNED")
        self.assertEqual(alignment["confidence_multiplier"], 1.25)
        self.assertFalse(alignment["is_vetoed"])

    def test_smart_money_alignment_veto(self):
        """Model tercihi Akıllı Paranın tersine akıyorsa sazan tuzağı olarak VETO edilmeli."""
        steam_data = {
            "has_steam": True,
            "steam_market": "2",
            "steam_drop_pct": 12.0,
            "faded_market": "1"
        }

        # Model MS 1 diyor ama büyük para MS 2'ye akmış!
        alignment = verify_smart_money_alignment("MS 1 (Chelsea)", steam_data)
        self.assertEqual(alignment["verdict"], "VETO")
        self.assertEqual(alignment["confidence_multiplier"], 0.0)
        self.assertTrue(alignment["is_vetoed"])

    def test_value_detector_veto_integration(self):
        """value_detector'da Smart Money tarafından veto edilen tercih elenmeli."""
        match_veto = {
            "home_name": "Team A",
            "away_name": "Team B",
            "odds": {
                "1": 2.50, "X": 3.20, "2": 2.60,
                "open_1": 2.10, "open_x": 3.20, "open_2": 3.20  # Deplasmana büyük para akmış (3.20 -> 2.60)
            }
        }
        # Model ev sahibini üstün görüyor
        fake_model = {"prob_home_win": 0.55, "prob_draw": 0.25, "prob_away_win": 0.20}

        res = find_value_bets(match_veto, fake_model, model_weight=0.25, min_ev=0.01)
        self.assertEqual(res["status"], "ANALYZED")
        
        # MS 1 tercihi Smart Money zıt yönde olduğu için elenmiş olmalı
        for vb in res["value_bets"]:
            self.assertNotEqual(vb["market"], "MS 1 (Team A)")


if __name__ == "__main__":
    unittest.main()

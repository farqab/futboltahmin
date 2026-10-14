"""Regression tests for reliability guards in value_detector.py."""
import unittest
from unittest.mock import patch

import value_detector


class ValueDetectorGuardTests(unittest.TestCase):
    def test_missing_odds_are_rejected(self):
        rejected, _ = value_detector.is_dummy_or_missing_odds({})
        self.assertTrue(rejected)

    def test_default_dummy_odds_are_rejected(self):
        rejected, _ = value_detector.is_dummy_or_missing_odds(
            {"1": 2.1, "X": 3.3, "2": 3.1}
        )
        self.assertTrue(rejected)

    def test_margin_removal_probabilities_sum_to_one(self):
        p1, px, p2, _ = value_detector.strip_margin_1x2(2.2, 3.4, 3.4)
        self.assertAlmostEqual(p1 + px + p2, 1.0, places=3)

    def test_missing_model_probabilities_are_rejected_not_defaulted(self):
        result = value_detector.find_value_bets(
            {"home_name": "Home", "away_name": "Away",
             "odds": {"1": 2.2, "X": 3.4, "2": 3.4}},
            {}
        )
        self.assertEqual(result["status"], "REJECTED_NO_DATA")
        self.assertEqual(result["value_bets"], [])

    def test_invalid_probability_sum_is_rejected(self):
        result = value_detector.find_value_bets(
            {"home_name": "Home", "away_name": "Away",
             "odds": {"1": 2.2, "X": 3.4, "2": 3.4}},
            {"prob_home_win": 0.8, "prob_draw": 0.8, "prob_away_win": 0.8}
        )
        self.assertEqual(result["status"], "REJECTED_INVALID_MODEL_OUTPUT")

    @patch("value_detector.detect_steam_moves", return_value={})
    @patch("value_detector.verify_smart_money_alignment",
           return_value={"verdict": "ALIGNED", "confidence_multiplier": 1.5})
    @patch("value_detector.GlobalMarketIntelligence.evaluate_bet_proposal",
           return_value={"verdict": "BOOST", "rationale": "test",
                         "signals": {}, "is_vetoed": False,
                         "confidence_multiplier": 1.5})
    def test_smart_money_boost_does_not_manufacture_ev(
        self, _global_eval, _alignment, _steam
    ):
        result = value_detector.find_value_bets(
            {"home_name": "Home", "away_name": "Away",
             "odds": {"1": 2.2, "X": 3.4, "2": 3.4}},
            {"prob_home_win": 0.80, "prob_draw": 0.10, "prob_away_win": 0.10},
            model_weight=0.25,
        )
        home = next(c for c in result["candidates"] if c["market"].startswith("MS 1"))
        p1_fair, _, _, _ = value_detector.strip_margin_1x2(2.2, 3.4, 3.4)
        expected_probability = 0.80 * 0.25 + p1_fair * 0.75
        expected_ev = round(expected_probability * 2.2 - 1.0, 4)
        self.assertEqual(home["ev"], expected_ev)
        self.assertEqual(home["smart_money_confidence_multiplier"], 1.5)


if __name__ == "__main__":
    unittest.main()

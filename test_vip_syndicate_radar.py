"""
test_vip_syndicate_radar.py — VIP Sendika ve Baron Hacmi Motoru Testleri
"""

import unittest
from vip_syndicate_radar import (
    MoneywayVolumeTracker,
    AsianHandicapTracker,
    LiveMomentumPressureTracker,
    VIPSyndicateRadar
)


class TestVIPSyndicateRadar(unittest.TestCase):

    def test_moneyway_volume_detection(self):
        """Hacim dağılımı ve whale alert tespiti."""
        vol_data = {
            "total_matched_gbp": 250000.0,
            "vol_1_gbp": 200000.0,
            "vol_x_gbp": 25000.0,
            "vol_2_gbp": 25000.0
        }
        res = MoneywayVolumeTracker.analyze_volume_distribution("Arsenal", "Chelsea", "MS 1", vol_data)
        self.assertTrue(res["is_whale_alert"])
        self.assertTrue(res["whale_with_us"])
        self.assertEqual(res["dominant_target"], "MS 1")
        self.assertAlmostEqual(res["our_market_share_pct"], 80.0, places=1)

    def test_asian_handicap_shift(self):
        """Asya çizgisi kayması tespiti."""
        # Ev sahibi -0.5'ten -1.0'e kaymışsa (Ev güçlenmiş)
        res = AsianHandicapTracker.evaluate_line_shift(open_line=-0.5, current_line=-1.0)
        self.assertTrue(res["is_significant_shift"])
        self.assertEqual(res["direction"], "HOME_STRENGTHENED")

    def test_live_pressure_momentum(self):
        """Canlı baskı ve momentum indeksi."""
        res = LiveMomentumPressureTracker.compute_pressure_index(
            home_dangerous_attacks_last15=12,
            away_dangerous_attacks_last15=2,
            home_shots_box_last15=3,
            away_shots_box_last15=0
        )
        self.assertGreater(res["home_pressure_pct"], 75)
        self.assertTrue(res["early_goal_alarm"])
        self.assertEqual(res["dominant_side"], "HOME")

    def test_opposed_whale_triggers_veto(self):
        """Baron parası zıt yöne yığılmışsa VETO tetiklenmeli."""
        vol_data = {
            "total_matched_gbp": 300000.0,
            "vol_1_gbp": 30000.0,
            "vol_x_gbp": 30000.0,
            "vol_2_gbp": 240000.0
        }
        audit = VIPSyndicateRadar.audit_vip_signals(
            home_team="Arsenal",
            away_team="Chelsea",
            market="MS 1",
            taken_odd=2.10,
            volume_data=vol_data
        )
        self.assertTrue(audit["is_vetoed"])
        self.assertEqual(audit["verdict"], "VETOED_BY_WHALE_VOLUME")
        self.assertEqual(audit["confidence_multiplier"], 0.0)

    def test_aligned_whale_triggers_boost(self):
        """Baron parası bizimle uyumluysa +%30 Güven verilmeli."""
        vol_data = {
            "total_matched_gbp": 300000.0,
            "vol_1_gbp": 240000.0,
            "vol_x_gbp": 30000.0,
            "vol_2_gbp": 30000.0
        }
        audit = VIPSyndicateRadar.audit_vip_signals(
            home_team="Arsenal",
            away_team="Chelsea",
            market="MS 1",
            taken_odd=1.90,
            volume_data=vol_data
        )
        self.assertFalse(audit["is_vetoed"])
        self.assertEqual(audit["verdict"], "BOOSTED_BY_WHALE_SYNDICATE")
        self.assertEqual(audit["confidence_multiplier"], 1.30)
        self.assertEqual(audit["flow_type"], "SHARP_WHALE")
        self.assertEqual(audit["volume_gbp"], 300000.0)
        self.assertEqual(audit["dominance_pct"], 80.0)
        self.assertEqual(audit["target_market"], "MS 1")

    def test_classify_money_flow_sharp_whale(self):
        """£50,000+ hacim ve %70+ yığılma SHARP_WHALE olarak sınıflandırılmalı."""
        from vip_syndicate_radar import classify_money_flow
        vol_data = {
            "total_matched_gbp": 85000.0,
            "share_1": 78.0,
            "share_x": 12.0,
            "share_2": 10.0
        }
        res = classify_money_flow(vol_data)
        self.assertEqual(res["flow_type"], "SHARP_WHALE")
        self.assertEqual(res["volume_gbp"], 85000.0)
        self.assertEqual(res["dominance_pct"], 78.0)
        self.assertEqual(res["target_market"], "MS 1")
        self.assertTrue(res["is_whale"])

    def test_classify_money_flow_public_trap(self):
        """Büyük hacim var fakat piyasa şüphesi (drift doubt) varsa PUBLIC_STEAM_TRAP olmalı."""
        from vip_syndicate_radar import classify_money_flow
        vol_data = {
            "total_matched_gbp": 95000.0,
            "share_1": 75.0,
            "share_x": 15.0,
            "share_2": 10.0
        }
        res = classify_money_flow(vol_data, drift={"signal": "MARKET_DOUBT_HOME"})
        self.assertEqual(res["flow_type"], "PUBLIC_STEAM_TRAP")
        self.assertEqual(res["target_market"], "MS 1")

    def test_classify_money_flow_balanced(self):
        """Düşük hacim veya dengeli dağılım BALANCED olmalı."""
        from vip_syndicate_radar import classify_money_flow
        vol_data = {
            "total_matched_gbp": 25000.0,
            "share_1": 45.0,
            "share_x": 30.0,
            "share_2": 25.0
        }
        res = classify_money_flow(vol_data)
        self.assertEqual(res["flow_type"], "BALANCED")
        self.assertFalse(res["is_whale"])

    def test_betfair_client_classify_money_flow(self):
        """BetfairMoneywayClient classify_money_flow metodu da PUBLIC_STEAM_TRAP ve SHARP_WHALE üretmelidir."""
        from betfair_moneyway_client import BetfairMoneywayClient
        vol_trap = {
            "total_matched_gbp": 80000.0,
            "share_1": 80.0,
            "share_x": 10.0,
            "share_2": 10.0
        }
        res_trap = BetfairMoneywayClient.classify_money_flow(vol_trap, drift={"signal": "MARKET_DOUBT_HOME"})
        self.assertEqual(res_trap["flow_type"], "PUBLIC_STEAM_TRAP")

        res_sharp = BetfairMoneywayClient.classify_money_flow(vol_trap)
        self.assertEqual(res_sharp["flow_type"], "SHARP_WHALE")


if __name__ == "__main__":
    unittest.main()


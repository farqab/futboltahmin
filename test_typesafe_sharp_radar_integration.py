"""
test_typesafe_sharp_radar_integration.py — 4'lü Küresel Sharp & VIP Radarı TypeSafe Entegrasyon Testleri
========================================================================================================
Doğrular:
1. Flashscore Ninja (Kadro şoku / eksikler) TypeSafe kararını VETO ettirir.
2. Pinnacle Benchmark (Sazan tuzağı / negatif marj) TypeSafe kararını VETO ettirir.
3. Dropping Odds (Steam ters yönde çöküş) TypeSafe kararını VETO ettirir.
4. VIP Baron Radarı (Whale hacmi & Asya desteği) TypeSafe güvenini artırır ve tuzak puanını düşürür.
"""

import unittest
from typesafe_engine import analyze_single_match


class TestTypeSafeSharpRadarIntegration(unittest.TestCase):

    def setUp(self):
        self.base_match = {
            "home_name": "Galatasaray",
            "away_name": "Antalyaspor",
            "league": "Trendyol Süper Lig",
            "odds": {
                "ms_1": 1.45,
                "ms_x": 4.50,
                "ms_2": 6.00,
                "over_2_5": 1.60,
                "under_2_5": 2.10
            },
            "home_form": "WWWDW",
            "away_form": "LLDLD",
            "home_record": "1. Sırada (60 Puan)",
            "away_record": "14. Sırada (22 Puan)",
            "home_scored_last3": 8,
            "home_conceded_last3": 1,
            "away_scored_last3": 1,
            "away_conceded_last3": 6,
            "home_momentum": "positive",
            "away_momentum": "negative"
        }

    def test_flashscore_lineup_shock_triggers_typesafe_veto(self):
        """Flashscore Ninja'da ev sahibinde 3+ kritik eksik / ceza <= 0.85 ise TypeSafe VETO etmelidir."""
        m = dict(self.base_match)
        m["signals"] = {
            "flashscore_lineups": {
                "is_confirmed": True,
                "lineup_penalty_home": 0.80, # Kadro şoku!
                "home_missing_count": 3
            }
        }
        res = analyze_single_match(m)
        self.assertEqual(res["action_status"], "NO_BET")
        self.assertGreaterEqual(res["trap_score"], 9.5)

    def test_pinnacle_sharp_trap_triggers_typesafe_veto(self):
        """Pinnacle Benchmark'a göre sazan tuzağı varsa TypeSafe VETO etmelidir."""
        m = dict(self.base_match)
        m["signals"] = {
            "pinnacle_benchmark": {
                "has_sharp_benchmark": True,
                "is_sharp_backed": False, # Sazan tuzağı!
                "sharp_ev_pct": -8.5
            }
        }
        res = analyze_single_match(m)
        self.assertEqual(res["action_status"], "NO_BET")
        self.assertGreaterEqual(res["trap_score"], 9.5)

    def test_dropping_odds_opposing_steam_triggers_typesafe_veto(self):
        """Dropping Odds'ta aleyhimize ters steam varsa TypeSafe VETO etmelidir."""
        m = dict(self.base_match)
        m["signals"] = {
            "dropping_odds_steam": {
                "has_steam": True,
                "steam_against_us": True, # Rakibe para aktı!
                "opp_drop_pct": 18.5
            }
        }
        res = analyze_single_match(m)
        self.assertEqual(res["action_status"], "NO_BET")
        self.assertGreaterEqual(res["trap_score"], 9.5)

    def test_vip_syndicate_whale_boosts_typesafe_decision(self):
        """VIP Baron radarında whale hacmi ve Asya desteği varsa TypeSafe güveni artmalı ve tuzak düşmelidir."""
        # Standart maç analizi
        m_base = dict(self.base_match)
        res_base = analyze_single_match(m_base)

        # VIP Baron destekli maç analizi
        m_vip = dict(self.base_match)
        m_vip["global_verdict"] = "BOOSTED_BY_WHALE_SYNDICATE"
        m_vip["global_reason"] = "£250,000 Baron Hacmi ve Asya baremi Galatasaray lehine"
        m_vip["signals"] = {
            "vip_syndicate_radar": {
                "verdict": "BOOSTED_BY_WHALE_SYNDICATE",
                "is_vetoed": False,
                "confidence_multiplier": 1.30,
                "rationale": "Büyük Para Girişi Onayı"
            }
        }
        res_vip = analyze_single_match(m_vip)
        
        self.assertGreaterEqual(res_vip["confidence"], res_base["confidence"])
        self.assertLessEqual(res_vip["trap_score"], res_base["trap_score"])
        self.assertNotEqual(res_vip["action_status"], "NO_BET")
        self.assertIn("baron_intel", res_vip)

    def test_baron_trap_warning_triggers_typesafe_penalty(self):
        """Sazan yığılması ve xG uyuşmazlığında TypeSafe baron_status='TRAP_WARNING' vermeli ve ceza uygulamalıdır."""
        m_trap = dict(self.base_match)
        m_trap["volume_data"] = {
            "total_matched_gbp": 160000.0,
            "share_1": 85.0,
            "share_x": 8.0,
            "share_2": 7.0,
            "has_volume_data": True
        }
        m_trap["expected_xg_home"] = 1.15
        m_trap["expected_xg_away"] = 1.10
        m_trap["home_xg_trend"] = "stagnant"
        m_trap["playstyle"] = "kontratak_tehdidi"
        m_trap["sofascore_attack_home"] = 46

        res = analyze_single_match(m_trap)
        self.assertTrue(res["is_baron_trap"])
        self.assertFalse(res["is_baron_verified"])
        self.assertEqual(res["baron_status"], "TRAP_WARNING")
        self.assertEqual(res["alert_icon"], "❗")
        self.assertEqual(res["flow_type"], "PUBLIC_STEAM_TRAP")
        self.assertGreaterEqual(res["trap_score"], 6.0)
        self.assertIn("baron_intel", res)

    def test_baron_verified_propagates_baron_intel(self):
        """Gerçek kurumsal whale hacmi Dixon-Coles xG ile teyit edildiğinde TypeSafe baron_status='CONFIRMED' üretmelidir."""
        m_whale = dict(self.base_match)
        m_whale["volume_data"] = {
            "total_matched_gbp": 220000.0,
            "share_1": 82.0,
            "share_x": 10.0,
            "share_2": 8.0,
            "has_volume_data": True
        }
        m_whale["expected_xg_home"] = 2.40
        m_whale["expected_xg_away"] = 0.70
        m_whale["home_xg_trend"] = "rising"
        m_whale["sofascore_attack_home"] = 72
        m_whale["sim_prob_home_win"] = 65.0

        res = analyze_single_match(m_whale)
        self.assertTrue(res["is_baron_verified"])
        self.assertFalse(res["is_baron_trap"])
        self.assertEqual(res["baron_status"], "CONFIRMED")
        self.assertEqual(res["alert_icon"], "👑")
        self.assertEqual(res["flow_type"], "SHARP_WHALE")
        self.assertEqual(res["volume_gbp"], 220000.0)
        self.assertEqual(res["dominance_pct"], 82.0)
        self.assertIn("baron_intel", res)


if __name__ == "__main__":
    unittest.main()


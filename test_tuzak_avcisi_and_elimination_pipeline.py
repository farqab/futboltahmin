"""
test_tuzak_avcisi_and_elimination_pipeline.py
=============================================
Kapsamlı Doğrulama ve Sınama Testleri:
1. xG & Attack Momentum Discrepancy Trap (Sazan Tuzağı ve VETO)
2. Dropping Odds / Sharp Steam Veto (Piyasa Çöküşü ve Oran Açılması)
3. SofaScore Kadro Kalite Farkı (Sahte Favori vs Kalite Onaylı)
4. Yorgunluk ve Dinlenme Tuzağı (Kısa Dinlenme & Rotasyon)
5. 2.5 Üst ve KG Var Niceliksel Filtreleri
6. Kupon Güvenlik Filtresi (Tuzaklı maçların kuponlara girmemesi)
7. PredictionEngine ve typesafe_engine Entegrasyonu
"""

import unittest
from tuzak_avcisi import TuzakAvcisi
from prediction_engine import PredictionEngine
from sofascore_client import SofaScoreClient
from smart_coupon_generator import generate_smart_coupons
from typesafe_engine import analyze_single_match


class TestTuzakAvcisiAndEliminations(unittest.TestCase):

    def setUp(self):
        self.clean_match = {
            "home_name": "Real Madrid",
            "away_name": "Getafe",
            "league": "La Liga",
            "odds": {
                "ms_1": 1.28,
                "ms_x": 5.50,
                "ms_2": 9.50,
                "over_2_5": 1.55,
                "under_2_5": 2.30
            },
            "home_form": "WWWWW",
            "away_form": "LDLLD",
            "home_record": "1. Sırada (65 Puan)",
            "away_record": "16. Sırada (19 Puan)",
            "home_scored_last3": 9,
            "home_conceded_last3": 1,
            "away_scored_last3": 1,
            "away_conceded_last3": 7,
            "home_momentum": "positive",
            "away_momentum": "negative",
            "home_rest_days": 6,
            "away_rest_days": 6,
            "home_rotation_risk": False,
            "away_rotation_risk": False,
            "sofascore_rating_home": 7.35,
            "sofascore_rating_away": 6.70,
            "sofascore_rating_diff": 0.65,
            "sofascore_momentum": "🔥 Yüksek Hücum Baskısı",
            "sofascore_momentum_score": 82,
            "sofascore_attack_home": 78,
            "sofascore_attack_away": 22,
            "sofascore_total_xg": 3.10,
            "expected_xg_home": 2.45,
            "expected_xg_away": 0.65,
            "home_xg_trend": "rising",
            "away_xg_trend": "stagnant"
        }

    def test_xg_momentum_trap_detection(self):
        """
        Favori takım çok düşük oranlı (1.35) ancak hücum momentumu durgun (<= 52)
        ve rakip tehlikeli kontratak tarzındaysa Sazan Tuzağı / VETO tetiklenmeli.
        """
        trap_match = dict(self.clean_match)
        trap_match["odds"] = {"ms_1": 1.35, "ms_x": 4.80, "ms_2": 7.50}
        trap_match["sofascore_momentum_score"] = 46  # Durgun
        trap_match["sofascore_attack_home"] = 48
        trap_match["expected_xg_home"] = 1.30
        trap_match["expected_xg_away"] = 1.05  # xG farkı sadece 0.25!
        trap_match["home_xg_trend"] = "stagnant"

        audit = TuzakAvcisi.audit_xg_momentum_trap(
            trap_match, pred_ms="MS 1", playstyle="kontratak_tehdidi"
        )
        self.assertTrue(audit["is_trap"], "xG ve Momentum uyuşmazlığında tuzak tespit edilmeli")
        self.assertGreater(audit["trap_penalty"], 2.0, "Tuzak cezası uygulanmalı")
        self.assertTrue(any("stagnant" in r or "durgunluk" in r or "xG" in r for r in audit["reasons"]))

    def test_dropping_odds_steam_veto(self):
        """
        Dropping Odds'ta rakip lehine sert oran çöküşü (steam_against_us) varsa VETO üretilmeli.
        """
        steam_match = dict(self.clean_match)
        steam_match["signals"] = {
            "dropping_odds_steam": {
                "steam_against_us": True,
                "opp_drop_pct": 14.5
            }
        }

        audit = TuzakAvcisi.audit_dropping_odds_steam(steam_match, pred_ms="MS 1")
        self.assertTrue(audit["is_vetoed"], "Sharp Steam aleyhimize ise VETO edilmeli")
        self.assertGreaterEqual(audit["trap_penalty"], 4.0)

    def test_rating_quality_differential_trap(self):
        """
        Oran 1.30 verilmiş ama SofaScore reyting farkı neredeyse sıfır (0.05) ise
        Sahte Favori Kalite Tuzağı bayrağı kalkmalı.
        """
        fake_fav = dict(self.clean_match)
        fake_fav["odds"] = {"ms_1": 1.30, "ms_x": 5.00, "ms_2": 8.00}
        fake_fav["sofascore_rating_home"] = 6.88
        fake_fav["sofascore_rating_away"] = 6.84
        fake_fav["sofascore_rating_diff"] = 0.04

        audit = TuzakAvcisi.audit_rating_quality_differential(fake_fav, pred_ms="MS 1")
        self.assertTrue(audit["is_trap"], "Kalite farkı olmayan düşük oranlı maçta tuzak bayrağı kalkmalı")
        self.assertTrue(any("SAHTE FAVORİ" in r for r in audit["reasons"]))

    def test_fatigue_and_rest_days_trap(self):
        """
        Favori takım 3 gün önce maç yapmış ve rotasyon riski varken rakip 7 gün dinlenmişse
        yorgunluk tuzağı devreye girmeli.
        """
        tired_match = dict(self.clean_match)
        tired_match["home_rest_days"] = 3
        tired_match["home_rotation_risk"] = True
        tired_match["away_rest_days"] = 7

        audit = TuzakAvcisi.audit_fatigue_and_rest(tired_match, pred_ms="MS 1")
        self.assertTrue(audit["is_trap"], "Yorgunluk tuzağı tespit edilmeli")
        self.assertGreater(audit["trap_penalty"], 1.0)

    def test_goal_line_and_btts_filters(self):
        """
        xG >= 2.55 ve yüksek hücum baskısında 2.5 ÜST ELİT onaylanmalı;
        düşük tempo ve xG <= 2.10 durumunda ise Düşük Tempo Tuzağı uyarısı verilmeli.
        """
        # A) Elit Üst
        high_goal_match = dict(self.clean_match)
        high_goal_match["sofascore_total_xg"] = 3.25
        high_goal_match["sofascore_momentum_score"] = 75
        high_goal_match["expected_xg_home"] = 2.05
        high_goal_match["expected_xg_away"] = 1.20
        g_audit_high = TuzakAvcisi.audit_goal_line_and_btts(high_goal_match)
        self.assertTrue(g_audit_high["is_over_elite"])
        self.assertTrue(g_audit_high["is_btts_elite"])

        # B) Düşük Tempo Tuzağı
        low_goal_match = dict(self.clean_match)
        low_goal_match["sofascore_total_xg"] = 1.95
        low_goal_match["sofascore_momentum"] = "🛡️ Taktiksel / Düşük Tempo"
        low_goal_match["sofascore_momentum_score"] = 38
        g_audit_low = TuzakAvcisi.audit_goal_line_and_btts(low_goal_match)
        self.assertTrue(g_audit_low["is_under_trap"])

    def test_coupon_safety_guard(self):
        """
        Tuzak Avcısı tarafından VETO edilmiş veya sazan tuzağına düşmüş maçlar
        kupon listesine ASLA kabul edilmemeli.
        """
        vetoed_match = dict(self.clean_match)
        vetoed_match["is_global_vetoed"] = True
        vetoed_match["global_verdict"] = "VETOED_BY_SHARP_DROP"

        is_safe, reason = TuzakAvcisi.is_coupon_safe({"raw_match": vetoed_match})
        self.assertFalse(is_safe, "VETO edilmiş maç kupona uygun olamaz")

        # Akıllı kupon üretici denetimi
        analyzed_pool = [vetoed_match]
        coupons = generate_smart_coupons(analyzed_pool)
        for c_key, c_val in coupons.items():
            for m_item in c_val.get("maclar", []):
                self.assertNotEqual(m_item["mac"], "Real Madrid vs Getafe")

    def test_prediction_engine_calibration(self):
        """
        PredictionEngine lojistik reyting kalibrasyonunu doğru hesaplamalıdır.
        """
        pred_ms, conf, adv = PredictionEngine.calibrate_win_probabilities(
            home_rating=7.40,
            away_rating=6.60,
            odds={"ms_1": 1.40, "ms_2": 6.50},
            base_conf=65
        )
        self.assertEqual(pred_ms, "MS 1")
        self.assertGreater(conf, 65)
        self.assertGreater(adv, 0.70)

    def test_typesafe_engine_integration_with_tuzak_avcisi(self):
        """
        analyze_single_match çağrıldığında Tuzak Avcısı'nın dönen sonuca
        'elimination_intel', 'trap_type' ve SofaScore verilerini eklediğini doğrula.
        """
        res = analyze_single_match(self.clean_match)
        self.assertIn("elimination_intel", res)
        self.assertIn("trap_type", res)
        self.assertIn("sofascore_rating_home", res)
        self.assertIn("sofascore_total_xg", res)
        self.assertIn(res["action_status"], ["BET", "GOAL_ONLY", "NO_BET"])
        self.assertIsNotNone(res["sofascore_rating_home"])
        self.assertIsNotNone(res["sofascore_rating_away"])

    def test_none_odds_and_missing_xg_robustness(self):
        """
        Oranlar None veya xG eksik olduğunda sistem TypeGuard ile çökmek yerine
        varsayılanlara güvenli şekilde dönmelidir.
        """
        broken_match = {
            "home_name": "Test Home",
            "away_name": "Test Away",
            "league": "Bilinmeyen Lig",
            "odds": {"ms_1": None, "ms_2": None, "over_2_5": None},
            "home_rest_days": "3 gün dinlendi",
            "away_rest_days": None
        }
        # Tuzak Avcısı çökmemeli
        audit = TuzakAvcisi.audit_match_eliminations(broken_match)
        self.assertIn("verdict", audit)
        self.assertIn("action_status", audit)

        # PredictionEngine çökmemeli
        pe_res = PredictionEngine.evaluate_match_prediction(broken_match)
        self.assertIn("pred_ms", pe_res)
        self.assertIn("calibrated_confidence", pe_res)

    def test_inverted_rating_differential_trap(self):
        """
        Ev sahibi 1.60 favori gösterilmiş ama deplasmanın kadro kalitesi
        daha yüksekse TERS KALİTE TUZAĞI tespit edilmeli.
        """
        inverted_match = dict(self.clean_match)
        inverted_match["odds"] = {"ms_1": 1.60, "ms_2": 4.50}
        inverted_match["sofascore_rating_home"] = 6.75
        inverted_match["sofascore_rating_away"] = 7.00
        inverted_match["sofascore_rating_diff"] = -0.25

        audit = TuzakAvcisi.audit_rating_quality_differential(inverted_match, pred_ms="MS 1")
        self.assertTrue(audit["is_trap"], "Ters kadro kalitesinde tuzak tespit edilmeli")
        self.assertTrue(any("TERS KALİTE" in r for r in audit["reasons"]))

    def test_sofascore_client_enrich_handles_missing_keys(self):
        """
        SofaScoreClient.enrich_match_list eski veya eksik cache verisi olan
        maçları KeyError vermeden tamamlamalıdır.
        """
        raw_list = [
            {"home_name": "Besiktas", "away_name": "Fenerbahce", "odds": {"1": 2.40, "2": 2.60}},
            {"home_name": "Liverpool", "away_name": "Chelsea", "odds": None}
        ]
        enriched = SofaScoreClient.enrich_match_list(raw_list)
        self.assertEqual(len(enriched), 2)
        for em in enriched:
            self.assertIn("sofascore_rating_home", em)
            self.assertIn("sofascore_attack_home", em)
            self.assertIn("sofascore_total_xg", em)
            self.assertIsNotNone(em["sofascore_rating_home"])

    def test_under_trap_blocked_from_smart_coupons(self):
        """
        2.5 Üst tercihi Düşük Tempo Tuzağı olan bir maçta kupona kabul edilmemelidir.
        """
        trap_cand = dict(self.clean_match)
        trap_cand["optimal_market"] = "2.5 Üst"
        trap_cand["tahmin_ms"] = "2.5 Üst"
        trap_cand["sofascore_total_xg"] = 1.90
        trap_cand["sofascore_momentum_score"] = 35
        trap_cand["elimination_intel"] = {
            "goal_res": {"is_under_trap": True, "is_over_elite": False},
            "is_trap": True,
            "is_vetoed": False
        }
        is_safe, reason = TuzakAvcisi.is_coupon_safe({"raw_match": trap_cand, "tahmin": "2.5 Üst"})
        self.assertFalse(is_safe, "Düşük tempo tuzağında 2.5 Üst kupona giremez")

    def test_agent_swarm_respects_tuzak_avcisi_is_coupon_safe(self):
        """
        50-Agent Swarm, Tuzak Avcısı tarafından kupona uygun bulunmayan maçları
        altın kasaya almamalıdır.
        """
        from agent_swarm_50 import generate_50agent_smart_portfolio
        vetoed_match = dict(self.clean_match)
        vetoed_match["elimination_intel"] = {"is_vetoed": True, "trap_type": "VETO_SHARP_STEAM"}
        vetoed_match["action_status"] = "NO_BET"
        swarm_res = generate_50agent_smart_portfolio([vetoed_match])
        self.assertIsNone(swarm_res.get("altin_kasa"))
        self.assertEqual(len(swarm_res.get("passed_matches", [])), 0)
        self.assertEqual(len(swarm_res.get("vetoed_matches", [])), 1)

    def test_audit_baron_validity_confirmed(self):
        """Büyük baron hacmi Dixon-Coles xG ve momentum ile destekleniyorsa CONFIRMED olmalı."""
        m = dict(self.clean_match)
        m["volume_data"] = {
            "total_matched_gbp": 120000.0,
            "share_1": 78.0,
            "share_x": 12.0,
            "share_2": 10.0,
            "has_volume_data": True
        }
        res = TuzakAvcisi.audit_baron_validity(m, pred_ms="MS 1")
        self.assertTrue(res["has_whale_volume"])
        self.assertTrue(res["is_baron_verified"])
        self.assertFalse(res["is_baron_trap"])
        self.assertEqual(res["baron_status"], "CONFIRMED")
        self.assertEqual(res["alert_icon"], "👑")
        self.assertEqual(res["flow_type"], "SHARP_WHALE")
        self.assertGreaterEqual(res["confidence_boost"], 8)

    def test_audit_baron_validity_trap_warning(self):
        """Para favoriye akmış fakat xG durgun ve rakip kontratak tehdidi taşıyorsa TRAP_WARNING ve ❗ olmalı."""
        m = dict(self.clean_match)
        m["volume_data"] = {
            "total_matched_gbp": 150000.0,
            "share_1": 80.0,
            "share_x": 10.0,
            "share_2": 10.0,
            "has_volume_data": True
        }
        m["expected_xg_home"] = 1.20
        m["expected_xg_away"] = 1.15
        m["home_xg_trend"] = "stagnant"
        m["playstyle"] = "kontratak_tehdidi"
        m["sofascore_attack_home"] = 45

        res = TuzakAvcisi.audit_baron_validity(m, pred_ms="MS 1")
        self.assertTrue(res["has_whale_volume"])
        self.assertTrue(res["is_baron_trap"])
        self.assertFalse(res["is_baron_verified"])
        self.assertEqual(res["baron_status"], "TRAP_WARNING")
        self.assertEqual(res["alert_icon"], "❗")
        self.assertEqual(res["flow_type"], "PUBLIC_STEAM_TRAP")
        self.assertGreaterEqual(res["trap_penalty"], 3.0)

    def test_audit_baron_validity_integrated_in_eliminations(self):
        """Baron tuzağı saptandığında audit_match_eliminations cezayı uygulamalıdır."""
        m = dict(self.clean_match)
        m["volume_data"] = {
            "total_matched_gbp": 110000.0,
            "share_1": 82.0,
            "share_x": 9.0,
            "share_2": 9.0,
            "has_volume_data": True
        }
        m["expected_xg_home"] = 1.10
        m["expected_xg_away"] = 1.15
        m["home_xg_trend"] = "stagnant"

        elim = TuzakAvcisi.audit_match_eliminations(m, pred_ms="MS 1")
        self.assertTrue(elim["is_trap"])
        self.assertIn("baron_res", elim)
        self.assertTrue(elim["baron_res"]["is_baron_trap"])
        self.assertEqual(elim["trap_type"], "SAZAN_HACMI_TUZAGI")

    def test_audit_baron_validity_root_fields(self):
        """Root seviyesindeki volume_gbp ve dominance_pct alanları da çözülmelidir."""
        m = dict(self.clean_match)
        m["volume_gbp"] = 125000.0
        m["dominance_pct"] = 80.0
        m["target_market"] = "MS 1"

        res = TuzakAvcisi.audit_baron_validity(m, pred_ms="MS 1")
        self.assertTrue(res["has_whale_volume"])
        self.assertTrue(res["is_baron_verified"])
        self.assertEqual(res["volume_gbp"], 125000.0)
        self.assertEqual(res["dominance_pct"], 80.0)
        self.assertEqual(res["target_market"], "MS 1")

    def test_audit_baron_validity_opposing_prediction_warning(self):
        """Tahminimiz MS 2 iken onaylı büyük baron parası MS 1'e akmışsa asla ONAY verilmemeli, uyarı/ceza üretilmelidir."""
        m = dict(self.clean_match)
        m["volume_data"] = {
            "total_matched_gbp": 150000.0,
            "share_1": 85.0,
            "share_x": 8.0,
            "share_2": 7.0,
            "has_volume_data": True
        }
        res = TuzakAvcisi.audit_baron_validity(m, pred_ms="MS 2")
        self.assertTrue(res["has_whale_volume"])
        self.assertFalse(res["is_baron_verified"], "Zıt yöndeki akıllı para bizim tercihimizi teyit etmemelidir")
        self.assertTrue(res["is_baron_trap"])
        self.assertEqual(res["alert_icon"], "❗")
        self.assertLess(res["confidence_boost"], 0, "Zıt yöndeki akıllı para güven cezası vermelidir")

    def test_is_coupon_safe_rejects_baron_trap(self):
        """Baron tuzağı saptanan maçlar kupon üretiminden derhal elenmelidir."""
        m = dict(self.clean_match)
        m["is_baron_trap"] = True
        safe, reason = TuzakAvcisi.is_coupon_safe(m)
        self.assertFalse(safe)
        self.assertIn("Sazan Hacmi", reason)


if __name__ == "__main__":
    unittest.main()


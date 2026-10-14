"""
test_dashboard_vip_baron.py — VIP Baron HTML Dashboard ve DOM Görsel Doğrulama Testi
=====================================================================================
Doğrular:
1. VIP Baron onaylı maçlarda altın ışıltılı kart ('vip-card-glow') ve ribbon basılması.
2. Sazan tuzağı para akışı tespit edilen maçlarda 'vip-trap-glow' ve '❗ SAZAN HACMİ / ŞÜPHELİ PARA UYARISI' rozeti basılması.
3. 4'lü Küresel Sharp kutusunda '🛡️ TypeSafe Baron Teyidi: ✅ KURUMSAL PARA ONAYLI' veya '⚠️ ŞÜPHELİ YIĞILMA' gösterilmesi.
4. Takvim/Filtre panelinde '👑 VIP Para Akışı (X Maç)' butonunun DOM'da bulunması ve 'data-vip' niteliklerinin atanması.
5. Eksik verilerde (NoneType) sıfır çökme ve güvenli geri dönüş (fallback).
"""

import os
import unittest
from html_dashboard import generate_html_report


class TestDashboardVIPBaron(unittest.TestCase):

    def setUp(self):
        self.output_file = "test_vip_bulten_output.html"
        self.mock_matches = [
            # 1. Onaylı VIP Baron Maçı
            {
                "home_name": "Arsenal",
                "away_name": "Fulham",
                "league": "Premier League",
                "time_tr": "19:00",
                "status": "Programda",
                "odds": {"ms_1": 1.35, "ms_x": 5.0, "ms_2": 8.0, "close_1": 1.35, "close_x": 5.0, "close_2": 8.0},
                "tahmin_ms": "MS 1",
                "tahmin_kazanan": "Arsenal",
                "confidence": 88,
                "over_2_5_prob": 70,
                "btts_prob": 45,
                "trap_score": 2.5,
                "action_status": "BET",
                "action_label": "🟢 OYNA (BANKO)",
                "optimal_market": "MS 1 & 1.5 Üst",
                "optimal_odds": 1.60,
                "optimal_confidence": 85,
                "is_baron_verified": True,
                "is_baron_trap": False,
                "volume_gbp": 125000.0,
                "dominance_pct": 82.0,
                "target_market": "MS 1",
                "flow_type": "SHARP_WHALE",
                "baron_intel": {
                    "has_whale_volume": True,
                    "volume_gbp": 125000.0,
                    "dominance_pct": 82.0,
                    "target_market": "MS 1",
                    "flow_type": "SHARP_WHALE",
                    "is_baron_verified": True,
                    "is_baron_trap": False,
                    "baron_status": "CONFIRMED",
                    "alert_icon": "👑"
                }
            },
            # 2. Şüpheli Sazan Tuzağı Hacmi
            {
                "home_name": "Chelsea",
                "away_name": "Crystal Palace",
                "league": "Premier League",
                "time_tr": "21:45",
                "status": "Programda",
                "odds": {"ms_1": 1.40, "ms_x": 4.5, "ms_2": 7.0, "close_1": 1.40, "close_x": 4.5, "close_2": 7.0},
                "tahmin_ms": "MS 1",
                "tahmin_kazanan": "Chelsea",
                "confidence": 42,
                "over_2_5_prob": 50,
                "btts_prob": 50,
                "trap_score": 8.5,
                "action_status": "NO_BET",
                "action_label": "🔴 PAS GEÇ (SAZAN TUZAĞI)",
                "optimal_market": "MS 1",
                "optimal_odds": 1.40,
                "optimal_confidence": 42,
                "is_baron_verified": False,
                "is_baron_trap": True,
                "volume_gbp": 95000.0,
                "dominance_pct": 79.0,
                "target_market": "MS 1",
                "flow_type": "PUBLIC_STEAM_TRAP",
                "baron_intel": {
                    "has_whale_volume": True,
                    "volume_gbp": 95000.0,
                    "dominance_pct": 79.0,
                    "target_market": "MS 1",
                    "flow_type": "PUBLIC_STEAM_TRAP",
                    "is_baron_verified": False,
                    "is_baron_trap": True,
                    "baron_status": "TRAP_WARNING",
                    "alert_icon": "❗"
                }
            },
            # 3. Normal / Dengeli Maç
            {
                "home_name": "Everton",
                "away_name": "Brentford",
                "league": "Premier League",
                "time_tr": "17:00",
                "status": "Programda",
                "odds": {"ms_1": 2.40, "ms_x": 3.2, "ms_2": 2.90, "close_1": 2.40, "close_x": 3.2, "close_2": 2.90},
                "tahmin_ms": "MS 1",
                "tahmin_kazanan": "Everton",
                "confidence": 55,
                "over_2_5_prob": 45,
                "btts_prob": 55,
                "trap_score": 4.0,
                "action_status": "BET",
                "action_label": "🟢 OYNA (DEĞER)",
                "optimal_market": "Everton (Beraberlikte İade)",
                "optimal_odds": 1.70,
                "optimal_confidence": 62,
                "is_baron_verified": False,
                "is_baron_trap": False,
                "volume_gbp": 12000.0,
                "dominance_pct": 45.0,
                "target_market": None,
                "flow_type": "BALANCED"
            }
        ]

    def tearDown(self):
        if os.path.exists(self.output_file):
            try:
                os.remove(self.output_file)
            except Exception:
                pass

    def test_html_dashboard_vip_baron_elements(self):
        """Dashboard HTML çıktısında tüm VIP Baron sınıfları, rozetleri ve filtre butonları doğrulanmalıdır."""
        out = generate_html_report(self.mock_matches, report_date="20261013", output_file=self.output_file)
        self.assertTrue(os.path.exists(out), "HTML dosyası başarıyla üretilmeli")

        with open(out, "r", encoding="utf-8") as f:
            html = f.read()

        # 1. Altın Işıltılı Kart ve Şerit
        self.assertIn("vip-card-glow", html, "Onaylı Baron maçında vip-card-glow sınıfı bulunmalı")
        self.assertIn("👑 VIP BARON RADARI:", html, "VIP Baron üst şeridi render edilmeli")
        self.assertIn("KURUMSAL PARA ONAYLI", html, "Kurumsal para onay etiketi bulunmalı")

        # 2. Sazan Tuzağı / Şüpheli Para Uyarısı ve Kırmızı Işıltı
        self.assertIn("vip-trap-glow", html, "Sazan hacminde vip-trap-glow sınıfı bulunmalı")
        self.assertIn("❗ SAZAN HACMİ / ŞÜPHELİ PARA UYARISI", html, "Pulsing ünlem rozeti bulunmalı")

        # 3. 4'lü Sharp İstihbaratı TypeSafe Teyidi
        self.assertIn("🛡️ TypeSafe Baron Teyidi: ✅ KURUMSAL PARA ONAYLI", html)
        self.assertIn("🛡️ TypeSafe Baron Teyidi: ⚠️ ŞÜPHELİ YIĞILMA", html)

        # 4. Takvim ve Filtre Paneli VIP Butonu
        self.assertIn('id="vipFilterBtn"', html, "VIP hızlı filtre butonu id'si DOM'da bulunmalı")
        self.assertIn("👑 VIP Para Akışı (2 Maç)", html, "VIP Maç sayısı (2 Maç) doğru hesaplanıp butonda gösterilmeli")
        self.assertIn('data-vip="1"', html, "Whale hacimli maçlarda data-vip='1' olmalı")
        self.assertIn('data-vip="0"', html, "Dengeli maçlarda data-vip='0' olmalı")

    def test_html_dashboard_graceful_fallbacks_on_empty_metrics(self):
        """Eksik veya NoneType metrikli maçlarda çökmeden güvenli HTML üretilmelidir."""
        empty_match = [{
            "home_name": "TestHome",
            "away_name": "TestAway",
            "league": "TestLig"
        }]
        out = generate_html_report(empty_match, report_date="20261013", output_file=self.output_file)
        self.assertTrue(os.path.exists(out))
        with open(out, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("TestHome", html)
        self.assertIn('data-vip="0"', html)

    def test_html_dashboard_unverified_high_volume_honest_badge(self):
        """Yüksek borsa hacmi olup henüz TypeSafe onayı almayan maçlarda 'YÜKSEK BORSA HACMİ' gösterilmeli."""
        unverified_match = [{
            "home_name": "Napoli",
            "away_name": "Fiorentina",
            "league": "Serie A",
            "volume_gbp": 85000.0,
            "dominance_pct": 72.0,
            "target_market": "MS 1",
            "flow_type": "SHARP_WHALE",
            "is_baron_verified": False,
            "is_baron_trap": False
        }]
        out = generate_html_report(unverified_match, report_date="20261013", output_file=self.output_file)
        self.assertTrue(os.path.exists(out))
        with open(out, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("YÜKSEK BORSA HACMİ", html, "Onaysız yüksek hacimde dürüst rozet basılmalı")
        self.assertNotIn("KURUMSAL PARA ONAYLI", html, "Onaylanmamış maçta kurumsal onay olmamalı")
        self.assertIn('data-match-id="napoli_vs_fiorentina"', html, "Benzersiz data-match-id atanmalı")


if __name__ == "__main__":
    unittest.main()

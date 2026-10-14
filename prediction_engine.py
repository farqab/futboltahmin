"""
prediction_engine.py — SofaScore & REA Tabanlı Tahmin ve Kalibrasyon Motoru
============================================================================
Bu motor, SofaScore derin analitikleri (oyuncu reytingleri, attack momentum, xG)
ve küresel piyasa çizgilerini kullanarak maç olasılıklarını, gol beklentilerini
ve güven skorlarını kalibre eder.

Tuzak Avcısı (tuzak_avcisi.py) ile entegre çalışarak sazan tuzaklarını eler.
"""

import math
from typing import Dict, Any, Tuple, Optional
from tuzak_avcisi import TuzakAvcisi


class PredictionEngine:
    """
    İstatistik ve Reyting Tabanlı Tahmin Kalibrasyon Motoru.
    """

    @classmethod
    def calibrate_win_probabilities(
        cls,
        home_rating: float,
        away_rating: float,
        odds: Dict[str, float],
        base_conf: int = 60
    ) -> Tuple[str, int, float]:
        """
        SofaScore reyting farkını ve piyasa oranlarını kullanarak
        kazanan tarafı ve kalibre edilmiş güven yüzdesini hesaplar.
        """
        rating_diff = round(home_rating - away_rating, 2)
        odds = odds or {}
        try:
            h_odd = float(odds.get("ms_1") or odds.get("1") or 2.20)
        except Exception:
            h_odd = 2.20
        try:
            a_odd = float(odds.get("ms_2") or odds.get("2") or 3.20)
        except Exception:
            a_odd = 3.20

        # Lojistik kalite avantajı: delta reyting başına %12 eğim
        rating_advantage = 1.0 / (1.0 + math.exp(-2.2 * rating_diff))

        if rating_diff >= 0.25 and h_odd <= 2.20:
            pred_ms = "MS 1"
            calibrated_conf = int(min(95, max(45, base_conf + int((rating_diff - 0.20) * 35))))
        elif rating_diff <= -0.25 and a_odd <= 2.50:
            pred_ms = "MS 2"
            calibrated_conf = int(min(95, max(45, base_conf + int((-rating_diff - 0.20) * 35))))
        elif h_odd < a_odd:
            pred_ms = "MS 1"
            calibrated_conf = int(min(90, max(40, base_conf + int(rating_diff * 20))))
        else:
            pred_ms = "MS 2"
            calibrated_conf = int(min(90, max(40, base_conf - int(rating_diff * 20))))

        return pred_ms, calibrated_conf, rating_advantage

    @classmethod
    def calibrate_goal_probabilities(
        cls,
        expected_total_xg: float,
        attack_momentum_score: int,
        base_over_prob: int = 50,
        base_btts_prob: int = 50
    ) -> Tuple[int, int]:
        """
        Toplam xG ve hücum momentum skoruna göre 2.5 Üst ve KG Var
        olasılıklarını kalibre eder.
        """
        # xG etkisi: 2.5 normuna göre kaydırma
        xg_delta = (expected_total_xg - 2.50) * 16.0

        # Momentum etkisi: 60 ortalamasına göre kaydırma
        mom_delta = (attack_momentum_score - 60) * 0.35

        calibrated_over = int(min(92, max(20, round(base_over_prob + xg_delta + mom_delta))))
        
        # KG Var kalibrasyonu
        btts_delta = (expected_total_xg - 2.40) * 10.0 + (attack_momentum_score - 60) * 0.20
        calibrated_btts = int(min(90, max(25, round(base_btts_prob + btts_delta))))

        return calibrated_over, calibrated_btts

    @classmethod
    def evaluate_match_prediction(
        cls,
        match_data: Dict[str, Any],
        raw_pred_ms: Optional[str] = None,
        raw_conf: Optional[int] = None,
        raw_over_prob: Optional[int] = None,
        raw_btts_prob: Optional[int] = None,
        playstyle: str = "temiz_ustunluk"
    ) -> Dict[str, Any]:
        """
        Maç verisini alır, SofaScore istatistiklerini uygular, Tuzak Avcısı
        kurallarını işletir ve zenginleştirilmiş tahmin sonucunu döner.
        """
        odds = match_data.get("odds") or {}
        sofascore_intel = match_data.get("sofascore_intel") or {}
        try:
            h_rating = float(match_data.get("sofascore_rating_home") or sofascore_intel.get("home_rating") or 6.85)
        except Exception:
            h_rating = 6.85
        try:
            a_rating = float(match_data.get("sofascore_rating_away") or sofascore_intel.get("away_rating") or 6.80)
        except Exception:
            a_rating = 6.80
        try:
            tot_xg = float(match_data.get("sofascore_total_xg") or sofascore_intel.get("expected_total_xg") or 2.45)
        except Exception:
            tot_xg = 2.45
        try:
            mom_score = int(match_data.get("sofascore_momentum_score") or sofascore_intel.get("attack_momentum_score") or 60)
        except Exception:
            mom_score = 60

        # 1. Taraf Tahmini & Olasılık Kalibrasyonu
        try:
            h_odd_cand = float(odds.get("ms_1") or odds.get("1") or 2.0)
            a_odd_cand = float(odds.get("ms_2") or odds.get("2") or 3.0)
        except Exception:
            h_odd_cand, a_odd_cand = 2.0, 3.0
        base_ms = raw_pred_ms or ("MS 1" if h_odd_cand < a_odd_cand else "MS 2")
        base_conf = raw_conf or 60
        pred_ms, cal_conf, rating_adv = cls.calibrate_win_probabilities(
            home_rating=h_rating,
            away_rating=a_rating,
            odds=odds,
            base_conf=base_conf
        )

        # 2. Gol Tahmini Kalibrasyonu
        base_over = raw_over_prob or 50
        base_btts = raw_btts_prob or 50
        cal_over, cal_btts = cls.calibrate_goal_probabilities(
            expected_total_xg=tot_xg,
            attack_momentum_score=mom_score,
            base_over_prob=base_over,
            base_btts_prob=base_btts
        )

        # 3. Sayısal Tuzak Avcısı & Eleme Kuralları
        elim_res = TuzakAvcisi.audit_match_eliminations(
            m=match_data,
            pred_ms=pred_ms,
            conf_pct=cal_conf,
            playstyle=playstyle
        )

        # Tuzak puanı & güven düzeltmesi
        base_trap = float(match_data.get("trap_score", 4.0))
        final_trap = round(min(10.0, max(1.0, base_trap + elim_res["total_trap_penalty"])), 1)
        final_conf = max(20, min(96, cal_conf + elim_res["confidence_adjustment"]))

        return {
            "pred_ms": pred_ms,
            "calibrated_confidence": final_conf,
            "calibrated_over_2_5": cal_over,
            "calibrated_btts": cal_btts,
            "final_trap_score": final_trap,
            "elimination_intel": elim_res,
            "action_status": elim_res["action_status"],
            "action_label": elim_res["action_label"],
            "trap_type": elim_res["trap_type"],
            "is_vetoed": elim_res["is_vetoed"],
            "is_trap": elim_res["is_trap"],
            "rating_advantage": rating_adv
        }

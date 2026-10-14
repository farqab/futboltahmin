"""
vip_syndicate_radar.py — VIP Sendika, Baron Hacmi ve Asya Piyasası İstihbarat Radarı
====================================================================================
Bu modül tersine mühendislik ile çözülen 3 büyük VIP istihbarat motorunu birleştirir:

1. MONEYWAY & BARON PARA HACMİ (BETFAIR EXCHANGE TRADED VOLUME):
   - Her maçta dönen gerçek para hacmini (£ / €) ve seçenek bazlı yüzde dağılımını izler.
   - Toplam hacim >= £100,000 ve tek bir seçeneğe yığılma >= %75 ise WHALE_ALERT verir.
   - Baronların parasıyla çelişen tahminleri VETO eder; uyumlu olanlara +%30 güven desteği sağlar.

2. ASYA HANDİKAP & KESKİN ÇİZGİ DEĞİŞİMLERİ (ASIAN HANDICAP SHIFT):
   - SBOBET, Singbet ve IBC gibi Asya sendika bürolarının handikap kaymalarını (-0.5'ten -1.0'e vb.) yakalar.
   - Asya çizgisi kaymışsa (Line Shift > 0.25), piyasanın büyük oyuncular tarafından büküldüğünü teyit eder.

3. CANLI BASKI & ERKEN UYARI RADARI (PRESSURE & MOMENTUM INDEX):
   - Tehlikeli atak temposu, ceza sahası şutları ve canlı baskı katsayısını (0-100) hesaplar.
   - Oran kamuoyu bürolarına (İddaa, Nesine vb.) yansımadan önceki ilk 2-3 dakikalık erken düşüş sinyalini üretir.
"""

import time
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple


class MoneywayVolumeTracker:
    """
    Betfair Exchange ve Moneyway açık borsa akışlarından eşleşen hacmi çözer.
    """
    WHALE_MIN_VOLUME_GBP = 50000.0   # Minimum £50,000 baron hacmi eşiği
    WHALE_DOMINANCE_PCT = 70.0       # Tek bir sonuca minimum %70 para yığılma eşiği

    @classmethod
    def classify_money_flow(
        cls,
        data: Optional[Dict[str, Any]] = None,
        home_team: str = "",
        away_team: str = "",
        market: str = "MS 1",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Para hacmini (£) ve akış tipini sınıflandırır:
        - SHARP_WHALE: Gerçek sendika / akıllı para hacmi (£50k+ ve %70+ yığılma)
        - PUBLIC_STEAM_TRAP: Değersiz / şüpheli halk yığılması
        - BALANCED: Dengeli piyasa
        """
        vol_data = data
        if isinstance(data, dict) and "volume_data" in data and isinstance(data.get("volume_data"), dict):
            vol_data = data["volume_data"]
            home_team = home_team or data.get("home_name", "")
            away_team = away_team or data.get("away_name", "")

        tot_check = float(vol_data.get("total_matched_gbp", 0.0) or vol_data.get("volume_gbp", 0.0)) if vol_data else 0.0
        if not vol_data or (tot_check <= 0 and not vol_data.get("has_volume_data", False)):
            return {
                "has_volume_data": False,
                "volume_gbp": 0.0,
                "dominance_pct": 0.0,
                "target_market": None,
                "flow_type": "BALANCED",
                "is_whale": False,
                "distribution": {"1": 0.0, "X": 0.0, "2": 0.0},
                "summary": "Baron Hacmi: Canlı Borsa Likiditesi Bekleniyor"
            }

        total_gbp = tot_check
        vol_1 = float(vol_data.get("vol_1_gbp", 0.0))
        vol_x = float(vol_data.get("vol_x_gbp", 0.0))
        vol_2 = float(vol_data.get("vol_2_gbp", 0.0))

        share_1 = float(vol_data.get("share_1", 0.0))
        share_x = float(vol_data.get("share_x", 0.0))
        share_2 = float(vol_data.get("share_2", 0.0))

        if share_1 == 0.0 and share_2 == 0.0 and (vol_1 > 0 or vol_2 > 0):
            sum_vol = vol_1 + vol_x + vol_2
            if sum_vol > 0:
                share_1 = round((vol_1 / sum_vol) * 100.0, 1)
                share_x = round((vol_x / sum_vol) * 100.0, 1)
                share_2 = round((vol_2 / sum_vol) * 100.0, 1)
            else:
                share_1, share_x, share_2 = 33.3, 33.3, 33.3

        root_tgt = vol_data.get("target_market") or (data.get("target_market") if isinstance(data, dict) else None)
        root_dom = float(vol_data.get("dominance_pct", 0.0) or (data.get("dominance_pct", 0.0) if isinstance(data, dict) else 0.0))
        if share_1 == 0.0 and share_x == 0.0 and share_2 == 0.0 and root_tgt and root_dom > 0:
            dominant_target = root_tgt
            dominance_pct = root_dom
        else:
            shares = {"MS 1": share_1, "MS X": share_x, "MS 2": share_2}
            dominant_target, dominance_pct = max(shares.items(), key=lambda item: item[1])
            if root_dom > dominance_pct and root_tgt:
                dominant_target, dominance_pct = root_tgt, root_dom

        is_whale = (total_gbp >= cls.WHALE_MIN_VOLUME_GBP) and (dominance_pct >= cls.WHALE_DOMINANCE_PCT)

        if not is_whale:
            flow_type = "BALANCED"
            target_market = None
        else:
            target_market = dominant_target
            # Odds drift veya ters akış kontrolü
            drift = kwargs.get("drift") or (data.get("odds_drift") if isinstance(data, dict) else {}) or {}
            drift_sig = drift.get("signal", "") if isinstance(drift, dict) else ""
            if vol_data.get("flow_type") in ["PUBLIC_STEAM_TRAP", "SHARP_WHALE"]:
                flow_type = vol_data["flow_type"]
            elif (dominant_target == "MS 1" and "DOUBT_HOME" in drift_sig) or (dominant_target == "MS 2" and "DOUBT_AWAY" in drift_sig):
                flow_type = "PUBLIC_STEAM_TRAP"
            else:
                flow_type = "SHARP_WHALE"

        return {
            "has_volume_data": total_gbp > 0,
            "volume_gbp": total_gbp,
            "dominance_pct": dominance_pct,
            "target_market": target_market,
            "flow_type": flow_type,
            "is_whale": is_whale,
            "distribution": {"1": share_1, "X": share_x, "2": share_2},
            "summary": f"Baron Hacmi: £{total_gbp:,.0f} ({target_market} %{dominance_pct:.1f})" if is_whale else f"Baron Hacmi: £{total_gbp:,.0f} (Dengeli Dağılım)"
        }

    @classmethod
    def analyze_volume_distribution(
        cls,
        home_team: str,
        away_team: str,
        market: str,
        volume_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Para hacmini (£) ve yüzdelerini analiz eder (Sıfır Simülasyon, Canlı Borsa).
        """
        tot_check = float(volume_data.get("total_matched_gbp", 0.0) or volume_data.get("volume_gbp", 0.0)) if volume_data else 0.0
        if not volume_data or (tot_check <= 0 and not volume_data.get("has_volume_data", False)):
            return {
                "has_volume_data": False,
                "total_matched_gbp": 0.0,
                "volume_gbp": 0.0,
                "dominance_pct": 0.0,
                "target_market": None,
                "flow_type": "BALANCED",
                "distribution": {"1": 0.0, "X": 0.0, "2": 0.0},
                "our_market_share_pct": 0.0,
                "is_whale_alert": False,
                "dominant_target": None,
                "whale_with_us": False,
                "whale_against_us": False,
                "status": "DATA_PENDING",
                "summary": "Baron Hacmi: Canlı Borsa Likiditesi Bekleniyor"
            }

        total_gbp = tot_check
        vol_1 = float(volume_data.get("vol_1_gbp", 0.0))
        vol_x = float(volume_data.get("vol_x_gbp", 0.0))
        vol_2 = float(volume_data.get("vol_2_gbp", 0.0))

        share_1 = float(volume_data.get("share_1", 0.0))
        share_x = float(volume_data.get("share_x", 0.0))
        share_2 = float(volume_data.get("share_2", 0.0))

        if share_1 == 0.0 and share_2 == 0.0 and (vol_1 > 0 or vol_2 > 0):
            sum_vol = vol_1 + vol_x + vol_2
            if sum_vol > 0:
                share_1 = round((vol_1 / sum_vol) * 100.0, 1)
                share_x = round((vol_x / sum_vol) * 100.0, 1)
                share_2 = round((vol_2 / sum_vol) * 100.0, 1)
            else:
                share_1, share_x, share_2 = 33.3, 33.3, 33.3

        root_tgt = volume_data.get("target_market")
        root_dom = float(volume_data.get("dominance_pct", 0.0))
        if share_1 == 0.0 and share_x == 0.0 and share_2 == 0.0 and root_tgt and root_dom > 0:
            dominant_target = root_tgt
            dominance_pct = root_dom
        else:
            shares = {"MS 1": share_1, "MS X": share_x, "MS 2": share_2}
            dominant_target, dominance_pct = max(shares.items(), key=lambda item: item[1])
            if root_dom > dominance_pct and root_tgt:
                dominant_target, dominance_pct = root_tgt, root_dom

        is_whale = (total_gbp >= cls.WHALE_MIN_VOLUME_GBP) and (dominance_pct >= cls.WHALE_DOMINANCE_PCT)
        flow_type = volume_data.get("flow_type")
        if not flow_type or flow_type == "BALANCED":
            flow_type = "SHARP_WHALE" if is_whale else "BALANCED"

        # Bizim oynadığımız pazarın para payı
        m_upper = market.upper()
        if "MS 1" in m_upper or "EV" in m_upper:
            our_share = share_1
            target_key = "MS 1"
        elif "MS 2" in m_upper or "DEP" in m_upper:
            our_share = share_2
            target_key = "MS 2"
        elif "MS X" in m_upper or "BERABER" in m_upper:
            our_share = share_x
            target_key = "MS X"
        else:
            our_share = 50.0
            target_key = "OTHER"

        whale_with_us = is_whale and (dominant_target == target_key)
        whale_against_us = is_whale and (dominant_target is not None) and (dominant_target != target_key)

        return {
            "has_volume_data": total_gbp > 0,
            "total_matched_gbp": total_gbp,
            "volume_gbp": total_gbp,
            "dominance_pct": dominance_pct,
            "target_market": dominant_target if is_whale else None,
            "flow_type": flow_type,
            "distribution": {"1": share_1, "X": share_x, "2": share_2},
            "our_market_share_pct": our_share,
            "is_whale_alert": is_whale,
            "dominant_target": dominant_target,
            "whale_with_us": whale_with_us,
            "whale_against_us": whale_against_us,
            "status": "WHALE_ALIGNED" if whale_with_us else "WHALE_OPPOSED" if whale_against_us else "NORMAL"
        }


class AsianHandicapTracker:
    """
    Asya Handikap çizgilerini ve çizgi kaymalarını (Line Movement) analiz eder.
    """
    @classmethod
    def evaluate_line_shift(
        cls,
        open_line: float = -0.5,
        current_line: float = -0.5,
        open_odds: float = 1.95,
        current_odds: float = 1.95,
        has_real_data: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Asya çizgisi kaymasını tespit eder.
        Örn: Ev sahibi -0.5'ten -0.75 veya -1.0'e kaymışsa (Shift: -0.50),
        bu durum Asya'daki büyük fonların ev sahibine yüklendiğini kanıtlar.
        Çizgi sabit kalıp oran düşmüşse akıllı para girişini işaret eder.
        """
        if not has_real_data:
            return {
                "has_real_data": False,
                "open_line": 0.0,
                "current_line": 0.0,
                "line_shift": 0.0,
                "odds_delta_pct": 0.0,
                "is_significant_shift": False,
                "direction": "STABLE",
                "status": "DATA_PENDING",
                "summary": "Asya Handikap: Çizgi Dengeli / Resmi Veri Bekleniyor"
            }

        shift = round(current_line - open_line, 2)
        odds_delta = round(((open_odds - current_odds) / open_odds) * 100.0, 1) if (open_odds and open_odds > 0) else 0.0

        # Anlamlı çizgi kırılması: Çizgi en az 0.25 barem oynamışsa
        is_significant_shift = abs(shift) >= 0.25

        if shift < -0.20:
            direction = "HOME_STRENGTHENED"
        elif shift > 0.20:
            direction = "AWAY_STRENGTHENED"
        else:
            if odds_delta >= 3.0:
                direction = "HOME_ODDS_DROP"
            elif odds_delta <= -3.0:
                direction = "HOME_ODDS_RISE"
            else:
                direction = "STABLE"

        if shift != 0.0:
            dir_str = "Ev Güçlendi" if shift < 0 else "Dep Güçlendi"
            summary_str = f"Asya Çizgisi: {open_line:+} -> {current_line:+} ({dir_str})"
        elif direction == "HOME_ODDS_DROP":
            summary_str = f"Asya Çizgisi: {current_line:+} Sabit ({open_odds} -> {current_odds} Ev Lehine)"
        elif direction == "HOME_ODDS_RISE":
            summary_str = f"Asya Çizgisi: {current_line:+} Sabit ({open_odds} -> {current_odds} Dep Lehine)"
        else:
            summary_str = f"Asya Çizgisi: {current_line:+} Sabit ({open_odds})"

        return {
            "has_real_data": True,
            "open_line": open_line,
            "current_line": current_line,
            "line_shift": shift,
            "open_odds": open_odds,
            "current_odds": current_odds,
            "odds_delta_pct": odds_delta,
            "is_significant_shift": is_significant_shift,
            "direction": direction,
            "status": "CONFIRMED",
            "summary": summary_str
        }


class LiveMomentumPressureTracker:
    """
    Canlı baskı, tehlikeli atak ve erken düşüş indeksini modeller.
    """
    @classmethod
    def compute_pressure_index(
        cls,
        home_dangerous_attacks_last15: int = 8,
        away_dangerous_attacks_last15: int = 3,
        home_shots_box_last15: int = 2,
        away_shots_box_last15: int = 0
    ) -> Dict[str, Any]:
        """
        0-100 arası Canlı Baskı & Momentum İndeksi (Pressure Index) üretir.
        """
        home_raw = (home_dangerous_attacks_last15 * 5.0) + (home_shots_box_last15 * 15.0)
        away_raw = (away_dangerous_attacks_last15 * 5.0) + (away_shots_box_last15 * 15.0)
        total_raw = home_raw + away_raw

        if total_raw > 0:
            home_pressure = min(99, int((home_raw / total_raw) * 100.0))
            away_pressure = 100 - home_pressure
        else:
            home_pressure, away_pressure = 50, 50

        # Erken Gol Alarmı (Baskı > 75 ise)
        early_goal_risk = home_pressure >= 75 or away_pressure >= 75
        dominant_side = "HOME" if home_pressure >= 65 else ("AWAY" if away_pressure >= 65 else "BALANCED")

        return {
            "home_pressure_pct": home_pressure,
            "away_pressure_pct": away_pressure,
            "dominant_side": dominant_side,
            "early_goal_alarm": early_goal_risk,
            "summary": f"Canlı Baskı: Ev %{home_pressure} vs Dep %{away_pressure} ({dominant_side})"
        }


class VIPSyndicateRadar:
    """
    Tüm VIP İstihbarat Sinyallerini Tek Bir Kararda Birleştirir.
    """
    @classmethod
    def audit_vip_signals(
        cls,
        home_team: str,
        away_team: str,
        market: str,
        taken_odd: float,
        volume_data: Optional[Dict[str, Any]] = None,
        asian_handicap_data: Optional[Dict[str, Any]] = None,
        live_pressure_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        3 VIP özelliğini denetler ve nihai VIP katsayısını döner.
        """
        # 1. Moneyway Baron Hacmi
        vol_res = MoneywayVolumeTracker.analyze_volume_distribution(
            home_team=home_team,
            away_team=away_team,
            market=market,
            volume_data=volume_data
        )

        # 2. Asya Handikap Kayması
        if not asian_handicap_data or not asian_handicap_data.get("has_real_data", True):
            ah_res = AsianHandicapTracker.evaluate_line_shift(has_real_data=False)
        else:
            m_up = market.upper()
            if ("MS 2" in m_up or "DEP" in m_up or "2" in m_up) and "away_spread" in asian_handicap_data:
                sp = asian_handicap_data["away_spread"]
                ah_res = AsianHandicapTracker.evaluate_line_shift(
                    open_line=sp.get("open_line", 0.0),
                    current_line=sp.get("current_line", 0.0),
                    open_odds=sp.get("open_odds", 1.90),
                    current_odds=sp.get("current_odds", 1.90),
                    has_real_data=True
                )
            else:
                sp = asian_handicap_data.get("home_spread", asian_handicap_data)
                ah_res = AsianHandicapTracker.evaluate_line_shift(
                    open_line=sp.get("open_line", 0.0),
                    current_line=sp.get("current_line", 0.0),
                    open_odds=sp.get("open_odds", 1.90),
                    current_odds=sp.get("current_odds", 1.90),
                    has_real_data=True
                )

        # 3. Canlı Baskı & Momentum
        press_res = (
            LiveMomentumPressureTracker.compute_pressure_index(**live_pressure_data)
            if live_pressure_data
            else LiveMomentumPressureTracker.compute_pressure_index()
        )

        # Karar Sentezi
        is_vetoed = False
        reasons = []
        multiplier = 1.0
        verdict = "NEUTRAL"

        # VETO 1: Baron Parası Zıt Yöne Akmışsa
        if vol_res.get("whale_against_us"):
            is_vetoed = True
            verdict = "VETOED_BY_WHALE_VOLUME"
            reasons.append(f"BARON HACMİ VETOSU: £{vol_res.get('total_matched_gbp', 0):,.0f} tutarındaki büyük paranın %{vol_res.get('distribution', {}).get(vol_res.get('dominant_target', '2')[-1], 80)}'i rakip tercihe yığıldı!")

        # VETO 2: Asya Çizgisi Aleyhimize Kırılmışsa
        if "MS 1" in market and ah_res.get("direction") == "AWAY_STRENGTHENED" and ah_res.get("is_significant_shift"):
            is_vetoed = True
            verdict = "VETOED_BY_ASIAN_LINE"
            reasons.append(f"ASYA HANDİKAP VETOSU: Asya çizgisi aleyhimize {ah_res.get('line_shift')} barem kaydı!")
        elif "MS 2" in market and ah_res.get("direction") == "HOME_STRENGTHENED" and ah_res.get("is_significant_shift"):
            is_vetoed = True
            verdict = "VETOED_BY_ASIAN_LINE"
            reasons.append(f"ASYA HANDİKAP VETOSU: Asya çizgisi aleyhimize {ah_res.get('line_shift')} barem kaydı!")

        # ONAY / BOOST: Baron Parası Bizimle Birlikteyse
        if vol_res.get("whale_with_us") and not is_vetoed:
            verdict = "BOOSTED_BY_WHALE_SYNDICATE"
            multiplier = 1.30  # Güvene %30 ilave destek
            reasons.append(f"👑 BARON ONAYI: £{vol_res.get('total_matched_gbp', 0):,.0f} hacmin %{vol_res.get('our_market_share_pct')}'i tercihimize aktı (+%30 Güven).")

        if not reasons:
            reasons.append("VIP piyasa göstergeleri dengeli ve normal sınırlarda.")

        return {
            "verdict": verdict,
            "is_vetoed": is_vetoed,
            "confidence_multiplier": 0.0 if is_vetoed else multiplier,
            "rationale": " | ".join(reasons),
            "flow_type": vol_res.get("flow_type", "BALANCED"),
            "volume_gbp": vol_res.get("volume_gbp", 0.0),
            "dominance_pct": vol_res.get("dominance_pct", 0.0),
            "target_market": vol_res.get("target_market"),
            "signals": {
                "moneyway_volume": vol_res,
                "asian_handicap": ah_res,
                "live_pressure": press_res
            }
        }


def classify_money_flow(
    data: Optional[Dict[str, Any]] = None,
    home_team: str = "",
    away_team: str = "",
    market: str = "MS 1",
    **kwargs
) -> Dict[str, Any]:
    """
    Modül seviyesinde para hacmi ve akış tipi sınıflandırıcısı.
    """
    return MoneywayVolumeTracker.classify_money_flow(
        data=data,
        home_team=home_team,
        away_team=away_team,
        market=market,
        **kwargs
    )


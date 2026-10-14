"""
tuzak_avcisi.py — Sayısal Sazan Tuzağı Avcısı ve İleri Eleme Motoru
==================================================================
Tersine Mühendislik (REA) & SofaScore / Flashscore / Pinnacle / Betfair
istihbarat katmanlarını kullanarak piyasadaki sazan tuzaklarını, ters steam
çöküşlerini ve kadro/yorgunluk zaaflarını tespit eden kantitatif eleme motoru.

Temel Eleme Mantıkları:
1. xG & Attack Momentum Discrepancy Trap (Hücum Baskısı & xG Uyuşmazlığı)
2. Dropping Odds / Sharp Steam Veto (Küresel Ters Oran Çöküşü)
3. Rating & Player Quality Differential (SofaScore Kadro Kalite Uçurumu)
4. Fatigue & Rest Days Filter (Rotasyon ve Dinlenme Zaafı)
5. Goal Line & BTTS Quantitative Filter (2.5 Üst ve KG Var Doğrulama)
"""

from typing import Dict, Any, List, Optional, Tuple


class TuzakAvcisi:
    """
    Sayısal Tuzak Avcısı ve Karar Eleme Motoru.
    """

    @classmethod
    def audit_xg_momentum_trap(
        cls,
        m: Dict[str, Any],
        pred_ms: str = "MS 1",
        playstyle: str = "temiz_ustunluk"
    ) -> Dict[str, Any]:
        """
        1. xG & Attack Momentum Discrepancy Trap:
        Favori takımın piyasa oranına karşın hücum baskısının (Attack Momentum)
        ve xG üretiminin durgun kalıp kalmadığını, rakibin kontratak tehlikesini analiz eder.
        """
        odds = m.get("odds") or {}
        try:
            h_odd = float(odds.get("ms_1") or odds.get("1") or 2.20)
        except Exception:
            h_odd = 2.20
        try:
            a_odd = float(odds.get("ms_2") or odds.get("2") or 3.20)
        except Exception:
            a_odd = 3.20

        is_home_fav = (pred_ms == "MS 1" or h_odd < a_odd)
        fav_odd = h_odd if is_home_fav else a_odd
        und_odd = a_odd if is_home_fav else h_odd

        sofascore_intel = m.get("sofascore_intel") or {}
        momentum_score = m.get("sofascore_momentum_score") or sofascore_intel.get("attack_momentum_score", 60)
        h_momentum = m.get("sofascore_attack_home") or sofascore_intel.get("attack_momentum_home", 50)
        a_momentum = m.get("sofascore_attack_away") or sofascore_intel.get("attack_momentum_away", 50)

        fav_momentum = h_momentum if is_home_fav else a_momentum
        und_momentum = a_momentum if is_home_fav else h_momentum

        try:
            exp_h_xg = float(m.get("expected_xg_home") or sofascore_intel.get("expected_xg_home") or 1.5)
        except Exception:
            exp_h_xg = 1.5
        try:
            exp_a_xg = float(m.get("expected_xg_away") or sofascore_intel.get("expected_xg_away") or 1.2)
        except Exception:
            exp_a_xg = 1.2
        fav_xg = exp_h_xg if is_home_fav else exp_a_xg
        und_xg = exp_a_xg if is_home_fav else exp_h_xg
        xg_diff = round(fav_xg - und_xg, 2)

        h_trend = m.get("home_xg_trend") or sofascore_intel.get("home_xg_trend", "normal")
        a_trend = m.get("away_xg_trend") or sofascore_intel.get("away_xg_trend", "normal")
        fav_trend = h_trend if is_home_fav else a_trend
        und_trend = a_trend if is_home_fav else h_trend

        reasons = []
        is_trap = False
        is_severe_veto = False
        trap_penalty = 0.0

        # Kural 1: Favori çok düşük oranlı (<= 1.50) ama hücum baskısı zayıf veya durgun
        if fav_odd <= 1.50:
            if fav_momentum <= 55 or momentum_score <= 52:
                is_trap = True
                trap_penalty += 2.4
                reasons.append(
                    f"Favori ({fav_odd}) hücum baskısı üretemiyor (Momentum: {fav_momentum}/100, Düşük Baskı)."
                )
            
            if fav_trend == "stagnant" or fav_xg < 1.45:
                is_trap = True
                trap_penalty += 2.0
                reasons.append(
                    f"Favori xG üretiminde durgunluk var (Beklenen xG: {fav_xg}, Trend: Durgun)."
                )

            if xg_diff < 0.40:
                is_trap = True
                trap_penalty += 1.8
                reasons.append(
                    f"Oran favori gösteriyor fakat xG farkı yetersiz (xG Farkı: {xg_diff} < 0.40)."
                )

            # Rakip kontratak tehdidi taşıyorsa tuzak kesinleşir
            if playstyle == "kontratak_tehdidi" or und_trend == "counter_attack_potent" or und_momentum >= 48:
                is_trap = True
                trap_penalty += 2.2
                reasons.append(
                    f"Rakip geçiş hücumunda ve kontratakta son derece etkili (Tehlike Skoru: {und_momentum}/100)."
                )

            # Ağır vaka kontrolü: Hem oran <= 1.40 hem 2+ tuzak sinyali varsa direkt VETO
            if fav_odd <= 1.42 and (fav_momentum <= 54 or playstyle == "kontratak_tehdidi") and xg_diff < 0.45:
                is_severe_veto = True
                reasons.append("AĞIR SAZAN TUZAĞI: Piyasa favoriyi şişirmiş fakat metrikler puan kaybına işaret ediyor!")

        elif fav_odd <= 1.75:
            # Orta derece favoriler için kontrol
            if fav_momentum <= 48 and (playstyle == "kontratak_tehdidi" or und_momentum >= 52):
                is_trap = True
                trap_penalty += 1.8
                reasons.append(f"Favori ({fav_odd}) deplasman/rakip direncine karşı hücum üstünlüğü kuramıyor.")

        return {
            "is_trap": is_trap,
            "is_severe_veto": is_severe_veto,
            "trap_penalty": round(trap_penalty, 2),
            "reasons": reasons,
            "fav_momentum": fav_momentum,
            "und_momentum": und_momentum,
            "xg_diff": xg_diff
        }

    @classmethod
    def audit_dropping_odds_steam(
        cls,
        m: Dict[str, Any],
        pred_ms: str = "MS 1"
    ) -> Dict[str, Any]:
        """
        2. Dropping Odds / Sharp Steam Veto:
        Piyasadaki oran hareketlerini, Pinnacle adil marjını ve ters yöndeki
        kurumsal (Sharp) para hareketlerini denetler.
        """
        signals = m.get("signals") or {}
        drop_sig = signals.get("dropping_odds_steam") or {}
        pin_sig = signals.get("pinnacle_benchmark") or {}
        drift = m.get("odds_drift") or {}
        drift_signal = drift.get("signal", "NORMAL")

        reasons = []
        is_vetoed = False
        is_boosted = False
        trap_penalty = 0.0

        # A) Dropping Odds Ters Steam (Sharp Money aleyhimize çöküyor)
        if drop_sig.get("steam_against_us"):
            is_vetoed = True
            trap_penalty += 4.5
            reasons.append(
                f"SHARP STEAM VETOSU: Aleyhimize %{drop_sig.get('opp_drop_pct', 0)} oran çöküşü var (Smart Money zıt yönde)."
            )
        elif drop_sig.get("steam_with_us"):
            is_boosted = True
            reasons.append(
                f"SHARP PARA ONAYI: Tercihimize %{drop_sig.get('drop_pct', 0)} kurumsal oran çöküşü teyit edildi."
            )

        # B) Piyasa Şüphesi / Oran Açılması (Odds Drift Trap)
        if pred_ms == "MS 1" and drift_signal == "MARKET_DOUBT_HOME":
            is_vetoed = True
            trap_penalty += 3.0
            reasons.append(
                f"ORAN AÇILMASI TUZAĞI: Ev sahibinin oranı açılıştan itibaren yükseldi (Piyasa güveni çekiyor)."
            )
        elif pred_ms == "MS 2" and drift_signal == "MARKET_DOUBT_AWAY":
            is_vetoed = True
            trap_penalty += 3.0
            reasons.append(
                f"ORAN AÇILMASI TUZAĞI: Deplasman oranı açılıştan itibaren yükseldi (Piyasa güveni çekiyor)."
            )

        # C) Pinnacle Keskin Çizgi Negatif Marj
        if pin_sig.get("has_sharp_benchmark") and not pin_sig.get("is_sharp_backed"):
            is_vetoed = True
            trap_penalty += 3.5
            reasons.append(
                f"PINNACLE ADİL ÇİZGİ VETOSU: Pinnacle benchmark'ına göre negatif marj (%{pin_sig.get('sharp_ev_pct', 0)} EV)."
            )

        return {
            "is_vetoed": is_vetoed,
            "is_boosted": is_boosted,
            "trap_penalty": round(trap_penalty, 2),
            "reasons": reasons
        }

    @classmethod
    def audit_rating_quality_differential(
        cls,
        m: Dict[str, Any],
        pred_ms: str = "MS 1"
    ) -> Dict[str, Any]:
        """
        3. Rating & Player Quality Differential:
        SofaScore takım/oyuncu kalite puanı farkını inceler.
        Piyasanın aşırı favori gördüğü takımın gerçek kadro kalitesi ile oranını kıyaslar.
        """
        sofascore_intel = m.get("sofascore_intel") or {}
        try:
            h_rating = float(m.get("sofascore_rating_home") or sofascore_intel.get("home_rating") or 6.85)
        except Exception:
            h_rating = 6.85
        try:
            a_rating = float(m.get("sofascore_rating_away") or sofascore_intel.get("away_rating") or 6.85)
        except Exception:
            a_rating = 6.85
        rating_diff = round(h_rating - a_rating, 2)

        odds = m.get("odds") or {}
        try:
            h_odd = float(odds.get("ms_1") or odds.get("1") or 2.20)
        except Exception:
            h_odd = 2.20
        try:
            a_odd = float(odds.get("ms_2") or odds.get("2") or 3.20)
        except Exception:
            a_odd = 3.20

        reasons = []
        is_trap = False
        is_quality_confirmed = False
        trap_penalty = 0.0
        conf_boost = 0

        if pred_ms == "MS 1":
            # Ev favorisi: h_odd <= 1.45 ama kadro farkı neredeyse yok veya negatif
            if h_odd <= 1.45 and rating_diff < 0.15:
                is_trap = True
                trap_penalty += 2.5
                reasons.append(
                    f"SAHTE FAVORİ KALİTE TUZAĞI: Oran {h_odd} fakat SofaScore kadro kalite farkı sadece {rating_diff}."
                )
            elif h_odd <= 1.75 and rating_diff < -0.05:
                is_trap = True
                trap_penalty += 2.2
                reasons.append(
                    f"TERS KALİTE TUZAĞI: Ev sahibi favori ({h_odd}) fakat deplasmanın kadro reytingi daha yüksek (Fark: {rating_diff})."
                )
            elif rating_diff >= 0.35:
                is_quality_confirmed = True
                conf_boost += 6
                reasons.append(
                    f"KADRO KALİTE TEYİDİ: SofaScore kadro reytingi belirgin şekilde üstün (Fark: +{rating_diff})."
                )
        elif pred_ms == "MS 2":
            # Deplasman favorisi: a_odd <= 1.70 ama deplasman reytingi yetersiz
            if a_odd <= 1.70 and (-rating_diff) < 0.15:
                is_trap = True
                trap_penalty += 2.5
                reasons.append(
                    f"SAHTE FAVORİ KALİTE TUZAĞI: Deplasman oranı {a_odd} fakat kadro kalite üstünlüğü yok (Fark: {-rating_diff})."
                )
            elif a_odd <= 1.90 and (-rating_diff) < -0.05:
                is_trap = True
                trap_penalty += 2.2
                reasons.append(
                    f"TERS KALİTE TUZAĞI: Deplasman favori ({a_odd}) fakat ev sahibinin kadro reytingi daha yüksek (Fark: {rating_diff})."
                )
            elif (-rating_diff) >= 0.30:
                is_quality_confirmed = True
                conf_boost += 6
                reasons.append(
                    f"KADRO KALİTE TEYİDİ: Deplasman kadro reytingi net üstünlük gösteriyor (Fark: +{-rating_diff})."
                )

        return {
            "is_trap": is_trap,
            "is_quality_confirmed": is_quality_confirmed,
            "trap_penalty": round(trap_penalty, 2),
            "conf_boost": conf_boost,
            "rating_diff": rating_diff,
            "reasons": reasons
        }

    @classmethod
    def audit_fatigue_and_rest(
        cls,
        m: Dict[str, Any],
        pred_ms: str = "MS 1"
    ) -> Dict[str, Any]:
        """
        4. Fatigue & Rest Days Filter:
        Dinlenme günleri ve rotasyon riskini kontrol eder.
        """
        h_rest = m.get("home_rest_days")
        a_rest = m.get("away_rest_days")
        h_rot = bool(m.get("home_rotation_risk"))
        a_rot = bool(m.get("away_rotation_risk"))

        reasons = []
        is_trap = False
        trap_penalty = 0.0

        import re
        def _parse_rest(val):
            if val is None:
                return 7
            if isinstance(val, (int, float)):
                return int(val)
            m_nums = re.findall(r"\d+", str(val))
            return int(m_nums[0]) if m_nums else 7

        h_rest_val = _parse_rest(h_rest)
        a_rest_val = _parse_rest(a_rest)

        if pred_ms == "MS 1" and (h_rot or h_rest_val <= 3) and a_rest_val >= 6:
            is_trap = True
            trap_penalty += 1.6
            reasons.append(
                f"YORGUNLUK / ROTASYON TUZAĞI: Ev sahibi {h_rest_val} gün önce oynadı (Rakip {a_rest_val} gün dinlendi)."
            )
        elif pred_ms == "MS 2" and (a_rot or a_rest_val <= 3) and h_rest_val >= 6:
            is_trap = True
            trap_penalty += 1.6
            reasons.append(
                f"YORGUNLUK / ROTASYON TUZAĞI: Deplasman takımı {a_rest_val} gün önce oynadı ve rotasyon riski var."
            )

        return {
            "is_trap": is_trap,
            "trap_penalty": round(trap_penalty, 2),
            "reasons": reasons
        }

    @classmethod
    def audit_goal_line_and_btts(
        cls,
        m: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        5. Goal Line & BTTS Quantitative Filter:
        Kombine xG ve Attack Momentum endekslerini kullanarak 2.5 ÜST ve KG VAR
        adaylarını sazan tuzaklarından ayırır.
        """
        sofascore_intel = m.get("sofascore_intel") or {}
        try:
            tot_xg = float(m.get("sofascore_total_xg") or sofascore_intel.get("expected_total_xg") or 2.4)
        except Exception:
            tot_xg = 2.4
        try:
            h_xg = float(m.get("expected_xg_home") or sofascore_intel.get("expected_xg_home") or 1.3)
        except Exception:
            h_xg = 1.3
        try:
            a_xg = float(m.get("expected_xg_away") or sofascore_intel.get("expected_xg_away") or 1.1)
        except Exception:
            a_xg = 1.1

        momentum_label = str(m.get("sofascore_momentum") or sofascore_intel.get("attack_momentum_label") or "⚖️ Dengeli")
        try:
            momentum_score = int(m.get("sofascore_momentum_score") or sofascore_intel.get("attack_momentum_score") or 60)
        except Exception:
            momentum_score = 60

        try:
            h_sc3 = int(m.get("home_scored_last3") or 0)
        except Exception:
            h_sc3 = 0
        try:
            a_sc3 = int(m.get("away_scored_last3") or 0)
        except Exception:
            a_sc3 = 0
        try:
            h_cn3 = int(m.get("home_conceded_last3") or 0)
        except Exception:
            h_cn3 = 0
        try:
            a_cn3 = int(m.get("away_conceded_last3") or 0)
        except Exception:
            a_cn3 = 0

        reasons = []
        is_over_elite = False
        is_under_trap = False
        is_btts_elite = False

        # 2.5 Üst Elit Onay Filtresi
        if tot_xg >= 2.55 and momentum_score >= 65 and (h_sc3 + a_sc3 >= 4):
            is_over_elite = True
            reasons.append(f"2.5 ÜST ELİT ONAY: Toplam xG {tot_xg} ve hücum momentumu {momentum_score}/100 çok yüksek.")

        # Düşük Tempo / 2.5 Üst Sazan Tuzağı Filtresi
        if tot_xg <= 2.10 or momentum_score <= 45 or "Düşük Tempo" in momentum_label:
            is_under_trap = True
            reasons.append(f"DÜŞÜK TEMPO TUZAĞI: Toplam xG {tot_xg} ve tempo düşük; 2.5 Üst tehlikeli!")

        # KG Var Elit Filtresi
        if (h_xg >= 1.25 and a_xg >= 1.05) or (h_xg >= 1.15 and a_xg >= 0.95 and (h_cn3 >= 2 or a_sc3 >= 2)):
            is_btts_elite = True
            reasons.append(f"KG VAR ELİT ONAY: İki takımın da gol beklentisi yüksek (Ev: {h_xg}, Dep: {a_xg}).")

        return {
            "is_over_elite": is_over_elite,
            "is_under_trap": is_under_trap,
            "is_btts_elite": is_btts_elite,
            "total_xg": tot_xg,
            "momentum_score": momentum_score,
            "reasons": reasons
        }

    @classmethod
    def audit_baron_validity(
        cls,
        m: Dict[str, Any],
        pred_ms: str = "MS 1",
        volume_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Büyük baronların en çok para yatırdığı seçenekleri ve borsa para akışını
        Dixon-Coles modeli, SofaScore xG ve Attack Momentum ile denetler.
        """
        # 1. Hacim Verisini Çöz
        vol_data = volume_data or m.get("volume_data") or m.get("baron_intel") or {}
        if not vol_data or not isinstance(vol_data, dict) or not (vol_data.get("total_matched_gbp") or vol_data.get("volume_gbp")):
            sig = m.get("signals") or {}
            vip_sig = sig.get("vip_syndicate_radar") or {}
            vol_data = vip_sig.get("signals", {}).get("moneyway_volume") or vol_data or {}

        tot_vol = float(
            vol_data.get("volume_gbp", 0.0) or
            vol_data.get("total_matched_gbp", 0.0) or
            m.get("volume_gbp", 0.0) or
            (m.get("baron_intel") or {}).get("volume_gbp", 0.0)
        )
        dist = vol_data.get("distribution") or {}
        s1 = float(vol_data.get("share_1", 0.0) or dist.get("1", 0.0))
        sx = float(vol_data.get("share_x", 0.0) or dist.get("X", 0.0))
        s2 = float(vol_data.get("share_2", 0.0) or dist.get("2", 0.0))

        if s1 == 0.0 and s2 == 0.0 and (vol_data.get("vol_1_gbp") or vol_data.get("vol_2_gbp")):
            v1 = float(vol_data.get("vol_1_gbp", 0.0))
            vx = float(vol_data.get("vol_x_gbp", 0.0))
            v2 = float(vol_data.get("vol_2_gbp", 0.0))
            sum_v = v1 + vx + v2
            if sum_v > 0:
                s1, sx, s2 = round(v1 / sum_v * 100, 1), round(vx / sum_v * 100, 1), round(v2 / sum_v * 100, 1)

        root_tgt = vol_data.get("target_market") or m.get("target_market") or (m.get("baron_intel") or {}).get("target_market")
        root_dom = float(vol_data.get("dominance_pct", 0.0) or m.get("dominance_pct", 0.0) or (m.get("baron_intel") or {}).get("dominance_pct", 0.0))

        if s1 == 0.0 and sx == 0.0 and s2 == 0.0 and root_tgt and root_dom > 0:
            dominant_target = root_tgt
            dominance_pct = root_dom
        else:
            shares = {"MS 1": s1, "MS X": sx, "MS 2": s2}
            dominant_target, dominance_pct = max(shares.items(), key=lambda x: x[1])
            if root_dom > dominance_pct and root_tgt:
                dominant_target, dominance_pct = root_tgt, root_dom

        # Whale Hacmi Eşiği (£50k+ ve %70+ yığılma)
        has_whale = (tot_vol >= 50000.0) and (dominance_pct >= 70.0)
        flow_type = vol_data.get("flow_type") or m.get("flow_type") or ("SHARP_WHALE" if has_whale else "BALANCED")

        if not has_whale:
            return {
                "has_whale_volume": False,
                "volume_gbp": tot_vol,
                "dominance_pct": dominance_pct,
                "target_market": None,
                "flow_type": "BALANCED",
                "is_baron_verified": False,
                "is_baron_trap": False,
                "baron_status": "BALANCED",
                "alert_icon": "",
                "confidence_boost": 0,
                "trap_penalty": 0.0,
                "summary": "VIP Baron: Para hacmi normal ve dengeli dağılmış",
                "reasons": []
            }

        # 2. SofaScore xG, Momentum ve Kadro Verileri
        s_intel = m.get("sofascore_intel") or {}
        try:
            exp_h_xg = float(m.get("expected_xg_home") or s_intel.get("expected_xg_home") or 1.35)
        except Exception:
            exp_h_xg = 1.35
        try:
            exp_a_xg = float(m.get("expected_xg_away") or s_intel.get("expected_xg_away") or 1.10)
        except Exception:
            exp_a_xg = 1.10

        h_trend = m.get("home_xg_trend") or s_intel.get("home_xg_trend", "normal")
        a_trend = m.get("away_xg_trend") or s_intel.get("away_xg_trend", "normal")
        try:
            h_mom = int(m.get("sofascore_attack_home") or s_intel.get("attack_momentum_home") or 50)
        except Exception:
            h_mom = 50
        try:
            a_mom = int(m.get("sofascore_attack_away") or s_intel.get("attack_momentum_away") or 50)
        except Exception:
            a_mom = 50

        playstyle = m.get("playstyle", "temiz_ustunluk")

        # 3. Dixon-Coles / Simülasyon Olasılıkları
        try:
            sim_hw = float(m.get("sim_prob_home_win") or 45.0)
        except Exception:
            sim_hw = 45.0
        try:
            sim_aw = float(m.get("sim_prob_away_win") or 30.0)
        except Exception:
            sim_aw = 30.0

        # Oran Drifti
        drift = m.get("odds_drift") or {}
        drift_sig = drift.get("signal", "NORMAL")

        reasons = []
        target_trap = False

        if dominant_target == "MS 1":
            is_stagnant = (h_trend == "stagnant" or exp_h_xg < 1.30)
            is_counter_threat = (playstyle == "kontratak_tehdidi" or a_trend == "counter_attack_potent" or a_mom >= 48)
            is_weak_momentum = (h_mom <= 48)
            is_model_opposed = (sim_aw > sim_hw or sim_hw < 38.0)
            is_drift_doubt = (drift_sig == "MARKET_DOUBT_HOME")

            if (is_stagnant and is_counter_threat) or is_weak_momentum or is_model_opposed or is_drift_doubt or (exp_h_xg <= exp_a_xg):
                target_trap = True

        elif dominant_target == "MS 2":
            is_stagnant = (a_trend == "stagnant" or exp_a_xg < 1.20)
            is_counter_threat = (playstyle == "kontratak_tehdidi" or h_trend == "counter_attack_potent" or h_mom >= 52)
            is_weak_momentum = (a_mom <= 48)
            is_model_opposed = (sim_hw > sim_aw or sim_aw < 35.0)
            is_drift_doubt = (drift_sig == "MARKET_DOUBT_AWAY")

            if (is_stagnant and is_counter_threat) or is_weak_momentum or is_model_opposed or is_drift_doubt or (exp_a_xg <= exp_h_xg):
                target_trap = True
        else:
            if abs(exp_h_xg - exp_a_xg) > 1.0 or sim_hw > 60.0 or sim_aw > 60.0:
                target_trap = True

        # Hedef pazar ile model tahmini (pred_ms) uyumu
        is_aligned = (dominant_target == pred_ms) or not pred_ms

        if is_aligned:
            if target_trap:
                is_baron_trap = True
                is_baron_verified = False
                flow_type = "PUBLIC_STEAM_TRAP"
                baron_status = "TRAP_WARNING"
                alert_icon = "❗"
                conf_boost = -15
                trap_pen = 3.0
                reasons.append(
                    f"❗ SAZAN HACMİ / ŞÜPHELİ PARA UYARISI: {dominant_target} tercihine £{tot_vol:,.0f} tutarında orantısız para aktı (%{dominance_pct:.1f}) fakat xG ({exp_h_xg} vs {exp_a_xg}) ve hücum baskısı yetersiz, şüpheli yığılma!"
                )
                summary = f"❗ ŞÜPHELİ YIĞILMA: £{tot_vol:,.0f} ({dominant_target} %{dominance_pct:.1f}) Metriklerle Çelişiyor"
            else:
                is_baron_trap = False
                is_baron_verified = True
                flow_type = "SHARP_WHALE"
                baron_status = "CONFIRMED"
                alert_icon = "👑"
                conf_boost = 8
                trap_pen = -1.5
                reasons.append(
                    f"👑 VIP BARON ONAYI: £{tot_vol:,.0f} tutarındaki kurumsal para akışı (%{dominance_pct:.1f} {dominant_target}) Dixon-Coles ve xG verileriyle teyit edildi."
                )
                summary = f"👑 KURUMSAL PARA ONAYLI: £{tot_vol:,.0f} ({dominant_target} %{dominance_pct:.1f}) Akıllı Para Desteği"
        else:
            # Tahminimiz baron hacminin aktığı hedefin ZIDDI
            if not target_trap:
                is_baron_trap = True
                is_baron_verified = False
                flow_type = "SHARP_WHALE"
                baron_status = "TRAP_WARNING"
                alert_icon = "❗"
                conf_boost = -20
                trap_pen = 4.0
                reasons.append(
                    f"❗ BARON VETOSU: £{tot_vol:,.0f} tutarındaki akıllı para (%{dominance_pct:.1f}) tercihimizin zıddı olan {dominant_target} yönüne aktı ve metriklerle destekleniyor!"
                )
                summary = f"❗ BARON VETOSU: £{tot_vol:,.0f} ({dominant_target} %{dominance_pct:.1f}) Tercihimizin Zıddına Akıllı Para"
            else:
                is_baron_trap = True
                is_baron_verified = False
                flow_type = "PUBLIC_STEAM_TRAP"
                baron_status = "TRAP_WARNING"
                alert_icon = "❗"
                conf_boost = 0
                trap_pen = 1.0
                reasons.append(
                    f"❗ SAZAN HACMİ UYARISI: Piyasada {dominant_target} tercihine £{tot_vol:,.0f} şüpheli para aktı (%{dominance_pct:.1f}), taraf riski yüksek!"
                )
                summary = f"❗ SAZAN HACMİ: £{tot_vol:,.0f} ({dominant_target} %{dominance_pct:.1f}) Piyasada Şüpheli Yığılma"

        return {
            "has_whale_volume": True,
            "volume_gbp": tot_vol,
            "dominance_pct": dominance_pct,
            "target_market": dominant_target,
            "flow_type": flow_type,
            "is_baron_verified": is_baron_verified,
            "is_baron_trap": is_baron_trap,
            "baron_status": baron_status,
            "alert_icon": alert_icon,
            "confidence_boost": conf_boost,
            "trap_penalty": trap_pen,
            "summary": summary,
            "reasons": reasons
        }

    @classmethod
    def audit_match_eliminations(
        cls,
        m: Dict[str, Any],
        pred_ms: str = "MS 1",
        conf_pct: int = 60,
        playstyle: str = "temiz_ustunluk"
    ) -> Dict[str, Any]:
        """
        Tüm niceliksel eleme kurallarını birleştirir ve nihai karar / veto paketini üretir.
        """
        all_reasons = []

        # 1. xG & Momentum
        xg_res = cls.audit_xg_momentum_trap(m, pred_ms=pred_ms, playstyle=playstyle)
        all_reasons.extend(xg_res["reasons"])

        # 2. Dropping Odds / Steam
        steam_res = cls.audit_dropping_odds_steam(m, pred_ms=pred_ms)
        all_reasons.extend(steam_res["reasons"])

        # 3. Rating & Quality
        rating_res = cls.audit_rating_quality_differential(m, pred_ms=pred_ms)
        all_reasons.extend(rating_res["reasons"])

        # 4. Fatigue & Rest
        fatigue_res = cls.audit_fatigue_and_rest(m, pred_ms=pred_ms)
        all_reasons.extend(fatigue_res["reasons"])

        # 5. Goal Line & BTTS
        goal_res = cls.audit_goal_line_and_btts(m)
        all_reasons.extend(goal_res["reasons"])

        # 6. Baron Para Akışı & TypeSafe Doğrulaması
        baron_res = cls.audit_baron_validity(m, pred_ms=pred_ms)
        all_reasons.extend(baron_res["reasons"])

        # Toplam tuzak puanı artışı
        total_trap_penalty = (
            xg_res["trap_penalty"] +
            steam_res["trap_penalty"] +
            rating_res["trap_penalty"] +
            fatigue_res["trap_penalty"]
        )
        if baron_res["is_baron_trap"]:
            total_trap_penalty += baron_res["trap_penalty"]

        # Güven ayarlaması
        conf_adj = rating_res["conf_boost"]
        if baron_res["is_baron_verified"]:
            conf_adj += baron_res["confidence_boost"]
        elif baron_res["is_baron_trap"]:
            conf_adj += baron_res["confidence_boost"]

        if xg_res["is_severe_veto"] or steam_res["is_vetoed"]:
            conf_adj -= 30
        elif xg_res["is_trap"]:
            conf_adj -= 18
        elif fatigue_res["is_trap"]:
            conf_adj -= 10

        # Nihai Eleme Durumu (Veto / No Bet / Goal Only / Bet)
        is_hard_veto = (
            xg_res["is_severe_veto"] or
            steam_res["is_vetoed"] or
            m.get("is_global_vetoed", False) or
            "VETO" in str(m.get("global_verdict", "")).upper()
        )

        is_trap = (
            xg_res["is_trap"] or
            rating_res["is_trap"] or
            fatigue_res["is_trap"] or
            baron_res["is_baron_trap"] or
            total_trap_penalty >= 2.0
        )

        if is_hard_veto:
            verdict = "VETO"
            action_status = "NO_BET"
            action_label = "🔴 PAS GEÇ (SHARP / TUZAK VETOSU)"
            trap_type = "VETO_SHARP_STEAM" if steam_res["is_vetoed"] else "SAZAN_TUZAGI_MOMENTUM_XG"
        elif is_trap:
            if baron_res["is_baron_trap"]:
                verdict = "NO_BET"
                action_status = "NO_BET"
                action_label = "🔴 PAS GEÇ (SAZAN HACMİ TUZAĞI)"
                trap_type = "SAZAN_HACMI_TUZAGI"
            elif goal_res["is_over_elite"] or goal_res["is_btts_elite"]:
                verdict = "GOAL_ONLY"
                action_status = "GOAL_ONLY"
                action_label = "🟡 SADECE GOL OYNA (TARAF TUZAKLI)"
                trap_type = "SAZAN_TUZAGI_KORUMASI"
            else:
                verdict = "NO_BET"
                action_status = "NO_BET"
                action_label = "🔴 PAS GEÇ (SAZAN TUZAĞI)"
                trap_type = "SAZAN_TUZAGI_UZAK_DUR"
        else:
            verdict = "BET"
            action_status = "BET"
            action_label = "🟢 OYNA (KALİTE VE PİYASA ONAYLI)"
            trap_type = "KALITE_ONAYLI"

        return {
            "verdict": verdict,
            "action_status": action_status,
            "action_label": action_label,
            "trap_type": trap_type,
            "is_vetoed": is_hard_veto,
            "is_trap": is_trap,
            "total_trap_penalty": round(total_trap_penalty, 2),
            "confidence_adjustment": conf_adj,
            "reasons": all_reasons,
            "xg_res": xg_res,
            "steam_res": steam_res,
            "rating_res": rating_res,
            "fatigue_res": fatigue_res,
            "goal_res": goal_res,
            "baron_res": baron_res
        }

    @classmethod
    def is_coupon_safe(cls, match_candidate: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Kupon üreticisi için mutlak güvenlik kontrolü:
        Sazan tuzağı, ters steam veya aşırı risk barındıran maçlar kuponlara ASLA giremez.
        """
        raw_m = match_candidate.get("raw_match", match_candidate)
        try:
            trap_score = float(raw_m.get("trap_score") or 5.0)
        except Exception:
            trap_score = 5.0
        g_verdict = str(raw_m.get("global_verdict", "")).upper()
        act_status = str(raw_m.get("action_status", "")).upper()

        if "VETO" in g_verdict or "RED" in g_verdict:
            return False, "Küresel İstihbarat Vetosu"

        if act_status in ["NO_BET", "PAS", "VETO", "REJECTED"]:
            return False, "Eylem Statüsü Pas / Veto"

        if raw_m.get("is_baron_trap"):
            return False, "Sazan Hacmi / Şüpheli Para Tuzağı"

        if trap_score > 6.2:
            return False, f"Yüksek Tuzak Riski ({trap_score}/10)"

        elim = raw_m.get("elimination_intel") or {}
        if elim.get("is_vetoed"):
            return False, f"Tuzak Avcısı Vetosu ({elim.get('trap_type', 'VETO')})"

        if elim.get("is_trap") and act_status != "GOAL_ONLY":
            return False, "Sazan Tuzağı Taraf Riski"

        # Gol tuzakları kontrolü (Düşük tempo tuzağında 2.5 Üst oynanamaz)
        goal_res = elim.get("goal_res") or {}
        target_bet = str(match_candidate.get("tahmin") or raw_m.get("optimal_market") or raw_m.get("tahmin_ms") or "")
        if "2.5 Üst" in target_bet and goal_res.get("is_under_trap"):
            return False, "Düşük Tempo / 2.5 Üst Tuzağı (Gol Beklentisi Düşük)"

        return True, "Kupona Uygun"

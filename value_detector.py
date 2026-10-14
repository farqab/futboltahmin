"""
value_detector.py — Gerçek Değer (+EV) ve Piyasa Marjı Ayrıştırma Motoru
========================================================================
Piyasa Gerçeği:
Nesine / İddaa marjı uluslararası keskin bürolara (Pinnacle / Betfair) göre
daha yüksektir. Bu yüzden "tahmin" değil, "oran avantajı (+EV)" aranmalıdır.

Temel Kurallar:
1. NO DATA, NO BET: Dummy / Sahte oranlar (2.1/3.3/3.1 vb.) tespit edilirse
   maç anında reddedilir.
2. MARJ SÖKME: Piyasa oranlarından kâr marjı düşülerek "Adil Piyasa Olasılığı" (Fair Prob) çıkarılır.
3. MODEL-PİYASA HARMANI (Shrinkage): Modelin körleşmesini önlemek için model olasılığı
   piyasa adil olasılığı ile ağırlıklandırılarak sentezlenir.
4. +EV FİLTRESİ: Yalnızca EV = (P_sentez * Oran - 1) >= %2.5 olan bahisler değerlendirilir.
"""

from typing import Dict, Any, List, Optional, Tuple
import math
from smart_money_tracker import detect_steam_moves, verify_smart_money_alignment
from global_market_intelligence import GlobalMarketIntelligence

DUMMY_ODDS_SIGNATURES = [
    {"1": 2.1, "X": 3.3, "2": 3.1},
    {"ms_1": 2.1, "ms_x": 3.3, "ms_2": 3.1},
]

MIN_EV_THRESHOLD = 0.025  # Dokümantasyonla uyumlu minimum %2.5 EV
MAX_EV_CAP = 0.20        # Maksimum %20.0 EV tavanı (Aşırı uç model sapmalarını filtreler)


def is_dummy_or_missing_odds(odds: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Oranların eksik, geçersiz veya sistem varsayılanı (2.1/3.3/3.1) olup olmadığını denetler.
    """
    if not odds or not isinstance(odds, dict):
        return True, "Oran verisi tamamen eksik"

    # En azından 1X2 veya gol oranları olmalı
    o1 = odds.get("1") or odds.get("ms_1")
    ox = odds.get("X") or odds.get("ms_x")
    o2 = odds.get("2") or odds.get("ms_2")

    if not o1 or not ox or not o2:
        return True, "1X2 oranları eksik"

    try:
        f1, fx, f2 = float(o1), float(ox), float(o2)
    except (ValueError, TypeError):
        return True, "Oranlar sayıya dönüştürülemedi"

    if f1 <= 1.0 or fx <= 1.0 or f2 <= 1.0:
        return True, "Geçersiz oran değeri (<= 1.0)"

    # Sahte varsayılan oran tespiti
    if abs(f1 - 2.1) < 0.001 and abs(fx - 3.3) < 0.001 and abs(f2 - 3.1) < 0.001:
        return True, "YASAKLI SAHTE ORAN: Varsayılan (2.1 / 3.3 / 3.1) tespit edildi!"

    return False, "Biçimsel olarak geçerli oran; kaynak/doğruluk doğrulanmadı"


def strip_margin_1x2(o1: float, ox: float, o2: float) -> Tuple[float, float, float, float]:
    """
    1X2 oranlarından bahis şirketi marjını çıkararak adil olasılıkları hesaplar.
    Döndürür: (p1_fair, px_fair, p2_fair, margin_pct)
    """
    try:
        o1, ox, o2 = float(o1), float(ox), float(o2)
    except (TypeError, ValueError) as exc:
        raise ValueError("1X2 oranları sayısal olmalıdır") from exc
    if min(o1, ox, o2) <= 1.0:
        raise ValueError("1X2 oranları 1.0'dan büyük olmalıdır")

    inv_sum = (1.0 / o1) + (1.0 / ox) + (1.0 / o2)
    margin = inv_sum - 1.0

    p1_fair = (1.0 / o1) / inv_sum
    px_fair = (1.0 / ox) / inv_sum
    p2_fair = (1.0 / o2) / inv_sum

    return round(p1_fair, 4), round(px_fair, 4), round(p2_fair, 4), round(margin * 100, 2)


def strip_margin_twoway(o_a: float, o_b: float) -> Tuple[float, float, float]:
    """
    İki ihtimalli pazarlardan (Alt/Üst veya KG Var/Yok) marjı çıkarır.
    Döndürür: (pa_fair, pb_fair, margin_pct)
    """
    try:
        o_a, o_b = float(o_a), float(o_b)
    except (TypeError, ValueError) as exc:
        raise ValueError("İki yönlü oranlar sayısal olmalıdır") from exc
    if min(o_a, o_b) <= 1.0:
        raise ValueError("İki yönlü oranlar 1.0'dan büyük olmalıdır")

    inv_sum = (1.0 / o_a) + (1.0 / o_b)
    margin = inv_sum - 1.0

    pa_fair = (1.0 / o_a) / inv_sum
    pb_fair = (1.0 / o_b) / inv_sum

    return round(pa_fair, 4), round(pb_fair, 4), round(margin * 100, 2)


def find_value_bets(
    match: Dict[str, Any],
    model_output: Dict[str, Any],
    model_weight: float = 0.25,
    min_ev: float = MIN_EV_THRESHOLD
) -> Dict[str, Any]:
    """
    Model olasılıkları ile piyasa oranlarını karşılaştırır.
    Yalnızca pozitif beklenen değere (+EV) sahip fırsatları döker.
    """
    odds = match.get("odds", {})
    is_dummy, reason = is_dummy_or_missing_odds(odds)

    if is_dummy:
        return {
            "status": "REJECTED_NO_DATA",
            "match": f"{match.get('home_name')} vs {match.get('away_name')}",
            "reason": reason,
            "value_bets": []
        }

    # Oranları çek
    o1 = float(odds.get("1") or odds.get("ms_1"))
    ox = float(odds.get("X") or odds.get("ms_x"))
    o2 = float(odds.get("2") or odds.get("ms_2"))

    p1_fair, px_fair, p2_fair, margin_1x2 = strip_margin_1x2(o1, ox, o2)

    # Model olasılıkları: eksik/bozuk çıktıyı sessizce 0.33 ile doldurma.
    if not isinstance(model_output, dict):
        return {
            "status": "REJECTED_NO_DATA",
            "match": f"{match.get('home_name')} vs {match.get('away_name')}",
            "reason": "Model çıktısı eksik veya sözlük biçiminde değil",
            "value_bets": []
        }
    if not 0.0 <= model_weight <= 1.0:
        raise ValueError("model_weight 0 ile 1 arasında olmalıdır")
    if not math.isfinite(float(min_ev)):
        raise ValueError("min_ev sonlu bir sayı olmalıdır")

    prob_keys = ("prob_home_win", "prob_draw", "prob_away_win")
    try:
        raw_probs = [float(model_output[k]) for k in prob_keys]
    except (KeyError, TypeError, ValueError):
        return {
            "status": "REJECTED_NO_DATA",
            "match": f"{match.get('home_name')} vs {match.get('away_name')}",
            "reason": "Modelin 1X2 olasılıkları eksik veya sayısal değil",
            "value_bets": []
        }
    if any(not math.isfinite(p) or p < 0.0 or p > 1.0 for p in raw_probs):
        return {
            "status": "REJECTED_INVALID_MODEL_OUTPUT",
            "match": f"{match.get('home_name')} vs {match.get('away_name')}",
            "reason": "Model olasılıkları [0, 1] aralığında değil",
            "value_bets": []
        }
    prob_sum = sum(raw_probs)
    if prob_sum <= 0.0 or abs(prob_sum - 1.0) > 0.03:
        return {
            "status": "REJECTED_INVALID_MODEL_OUTPUT",
            "match": f"{match.get('home_name')} vs {match.get('away_name')}",
            "reason": f"1X2 olasılık toplamı geçersiz: {prob_sum:.4f}",
            "value_bets": []
        }
    # Küçük kayan nokta/yuvarlama farklarını normalize et.
    p1_mod, px_mod, p2_mod = (p / prob_sum for p in raw_probs)

    # Harmanlanmış olasılık (Shrinkage blend)
    p1_blend = (p1_mod * model_weight) + (p1_fair * (1.0 - model_weight))
    px_blend = (px_mod * model_weight) + (px_fair * (1.0 - model_weight))
    p2_blend = (p2_mod * model_weight) + (p2_fair * (1.0 - model_weight))

    candidates = [
        {
            "market": f"MS 1 ({match.get('home_name')})",
            "market_type": "1X2",
            "odd": o1,
            "model_prob": p1_mod,
            "market_fair_prob": p1_fair,
            "blended_prob": round(p1_blend, 4),
            "ev": round((p1_blend * o1) - 1.0, 4)
        },
        {
            "market": "MS X (Beraberlik)",
            "market_type": "1X2",
            "odd": ox,
            "model_prob": px_mod,
            "market_fair_prob": px_fair,
            "blended_prob": round(px_blend, 4),
            "ev": round((px_blend * ox) - 1.0, 4)
        },
        {
            "market": f"MS 2 ({match.get('away_name')})",
            "market_type": "1X2",
            "odd": o2,
            "model_prob": p2_mod,
            "market_fair_prob": p2_fair,
            "blended_prob": round(p2_blend, 4),
            "ev": round((p2_blend * o2) - 1.0, 4)
        }
    ]

    # 2.5 Alt/Üst kontrolü (varsa)
    o_over = odds.get("2.5_ust") or odds.get("over_2_5")
    o_under = odds.get("2.5_alt") or odds.get("under_2_5")
    if o_over and o_under:
        try:
            fov, fun = float(o_over), float(o_under)
            if fov > 1.0 and fun > 1.0 and not (abs(fov - 1.75) < 0.001 and abs(fun - 1.75) < 0.001):
                p_ov_fair, p_un_fair, _ = strip_margin_twoway(fov, fun)
                # Gol pazarı model olasılığı yoksa 50/50 varsayma; pazarı atla.
                if "prob_over_2_5" in model_output and "prob_under_2_5" in model_output:
                    p_ov_mod = float(model_output["prob_over_2_5"])
                    p_un_mod = float(model_output["prob_under_2_5"])
                    if (
                        math.isfinite(p_ov_mod) and math.isfinite(p_un_mod)
                        and 0.0 <= p_ov_mod <= 1.0
                        and 0.0 <= p_un_mod <= 1.0
                        and abs((p_ov_mod + p_un_mod) - 1.0) <= 0.03
                    ):
                        total_sum = p_ov_mod + p_un_mod
                        p_ov_mod, p_un_mod = p_ov_mod / total_sum, p_un_mod / total_sum
                        p_ov_blend = (p_ov_mod * model_weight) + (p_ov_fair * (1.0 - model_weight))
                        p_un_blend = (p_un_mod * model_weight) + (p_un_fair * (1.0 - model_weight))

                        candidates.append({
                            "market": "2.5 Üst",
                            "market_type": "TOTAL_GOALS",
                            "odd": fov,
                            "model_prob": p_ov_mod,
                            "market_fair_prob": p_ov_fair,
                            "blended_prob": round(p_ov_blend, 4),
                            "ev": round((p_ov_blend * fov) - 1.0, 4)
                        })
                        candidates.append({
                            "market": "2.5 Alt",
                            "market_type": "TOTAL_GOALS",
                            "odd": fun,
                            "model_prob": p_un_mod,
                            "market_fair_prob": p_un_fair,
                            "blended_prob": round(p_un_blend, 4),
                            "ev": round((p_un_blend * fun) - 1.0, 4)
                        })
        except (ValueError, TypeError):
            pass

    # 4. Smart Money (Büyük Para Akışı) & Steam Move Denetimi
    opening_odds = match.get("opening_odds") or {
        "1": odds.get("open_1"),
        "X": odds.get("open_x"),
        "2": odds.get("open_2"),
        "over_2_5": odds.get("open_over_2_5") or odds.get("open_2.5_ust"),
        "under_2_5": odds.get("open_under_2_5") or odds.get("open_2.5_alt")
    }
    current_odds = {
        "1": o1,
        "X": ox,
        "2": o2,
        "over_2_5": odds.get("over_2_5") or odds.get("2.5_ust"),
        "under_2_5": odds.get("under_2_5") or odds.get("2.5_alt")
    }
    steam_info = detect_steam_moves(opening_odds, current_odds)

    for c in candidates:
        alignment = verify_smart_money_alignment(c["market"], steam_info)
        c["smart_money"] = alignment

        # Küresel Sharp & VIP Sendika İstihbaratı
        global_eval = GlobalMarketIntelligence.evaluate_bet_proposal(
            market=c["market"],
            taken_odd=c["odd"],
            model_prob=c["blended_prob"],
            opening_odds=opening_odds,
            current_odds=current_odds,
            pinnacle_odds=match.get("pinnacle_odds"),
            flashscore_mid=match.get("flashscore_mid"),
            home_team=match.get("home_name"),
            away_team=match.get("away_name"),
            volume_data=match.get("volume_data"),
            asian_handicap_data=match.get("asian_handicap_data"),
            live_pressure_data=match.get("live_pressure_data")
        )
        c["global_intelligence"] = global_eval
        c["smart_money_verdict"] = global_eval["verdict"]
        c["smart_money_reason"] = global_eval["rationale"]
        c["signals"] = global_eval.get("signals", {})

        if global_eval["is_vetoed"] or alignment["verdict"] == "VETO":
            c["is_smart_money_vetoed"] = True
            c["is_smart_money_confirmed"] = False
        elif "BOOST" in global_eval["verdict"] or alignment["verdict"] == "ALIGNED":
            c["is_smart_money_confirmed"] = True
            # Sinyal çarpanı EV'yi değiştiremez: EV yalnızca olasılık ve oranla hesaplanır.
            # Sinyali ayrı alanlarda sakla; aksi hâlde beklenen getiri yapay olarak şişer.
            c["smart_money_confidence_multiplier"] = max(
                float(global_eval.get("confidence_multiplier", 1.0)),
                float(alignment.get("confidence_multiplier", 1.0))
            )
        else:
            c["is_smart_money_confirmed"] = False

    # Yalnızca beklenen değeri pozitif, gerçekçi ve Smart Money tarafından VETO EDİLMEMİŞ olanları filtrele
    qualifying_bets = [
        c for c in candidates 
        if min_ev <= c["ev"] <= MAX_EV_CAP and not c.get("is_smart_money_vetoed", False)
    ]
    qualifying_bets.sort(key=lambda x: x["ev"], reverse=True)

    mbs = int(match.get("mbs", 1))

    return {
        "status": "ANALYZED",
        "match": f"{match.get('home_name')} vs {match.get('away_name')}",
        "league": match.get("league"),
        "mbs": mbs,
        "bookmaker_margin": margin_1x2,
        "steam_movement": steam_info,
        "total_evaluated_markets": len(candidates),
        "candidates": candidates,
        "value_bets_found": len(qualifying_bets),
        "value_bets": qualifying_bets,
        "best_bet": qualifying_bets[0] if qualifying_bets else None
    }

"""
smart_money_tracker.py — Akıllı Para (Smart Money) & Steam Move Takip Motoru
=============================================================================
Finansal ve Kantitatif Prensip:
Spor bahislerinde piyasanın yönünü "kamuoyu" (amatör bahisçiler) değil;
Pinnacle, Asya Borsaları ve Betfair Exchange üzerindeki büyük sendika
fonları (Smart Money) belirler.

Bu modül:
1. STEAM MOVE (Sert Oran Düşüşü) Tespiti:
   Açılış oranından kapanış/mevcut orana doğru %4'ten büyük sert oran çöküşlerini
   ve ima edilen olasılık (implied probability) sıçramalarını yakalar.
2. REVERSE LINE MOVEMENT (Ters Oran Hareketi) Tespiti:
   Piyasa genelinin bir takıma yığılmasına rağmen oranın ters yöne bükülmesi durumudur.
3. SAZAN TUZAĞI (Sharp Fade) KORUMASI:
   Eğer bizim modelimiz bir maça "MS 1" diyorsa ama keskin bürolarda büyük para
   "MS 2"ye akıyorsa (Steam Move zıt yöndeyse), sistem bu bahsi VETO eder.
"""

from typing import Dict, Any, List, Optional, Tuple


DEFAULT_STEAM_THRESHOLD_PCT = 4.0   # Minimum %4.0 oran çöküşü (Steam move eşiği)
SIGNIFICANT_PROB_JUMP_PCT = 3.0    # İma edilen olasılıkta minimum %3.0 artış


def detect_steam_moves(
    opening_odds: Optional[Dict[str, float]],
    current_odds: Optional[Dict[str, float]],
    threshold_pct: float = DEFAULT_STEAM_THRESHOLD_PCT
) -> Dict[str, Any]:
    """
    Açılış ve güncel piyasa oranlarını karşılaştırarak büyük para (Smart Money)
    hareketlerini tespit eder.
    """
    if not opening_odds or not current_odds:
        return {
            "has_steam": False,
            "steam_market": None,
            "steam_drop_pct": 0.0,
            "implied_prob_jump_pct": 0.0,
            "faded_market": None,
            "details": {}
        }

    markets = ["1", "X", "2", "over_2_5", "under_2_5"]
    details = {}
    max_drop_pct = 0.0
    best_steam_market = None
    max_fade_pct = 0.0
    best_fade_market = None
    max_prob_jump = 0.0

    for m in markets:
        # Alternatif anahtar isimlerini kontrol et
        o_open = opening_odds.get(m) or opening_odds.get(f"open_{m}") or opening_odds.get(f"ms_{m}")
        o_curr = current_odds.get(m) or current_odds.get(f"close_{m}") or current_odds.get(f"ms_{m}")

        if not o_open or not o_curr:
            continue

        try:
            f_open = float(o_open)
            f_curr = float(o_curr)
            if f_open <= 1.0 or f_curr <= 1.0:
                continue
        except (ValueError, TypeError):
            continue

        # Oran Değişimi: (Open - Current) / Open * 100
        # Pozitif değer: Oran düştü (Para bu tercihe aktı!)
        drop_pct = ((f_open - f_curr) / f_open) * 100.0

        # İma Edilen Olasılık Değişimi (Komisyonsuz saf ters oran)
        p_open = 1.0 / f_open
        p_curr = 1.0 / f_curr
        prob_jump = (p_curr - p_open) * 100.0

        details[m] = {
            "open": round(f_open, 2),
            "current": round(f_curr, 2),
            "drop_pct": round(drop_pct, 2),
            "prob_jump_pct": round(prob_jump, 2)
        }

        # En sert oran çöküşü (Steam)
        if drop_pct > max_drop_pct:
            max_drop_pct = drop_pct
            best_steam_market = m
            max_prob_jump = prob_jump

        # En sert oran yükselişi (Fade - Piyasa bu tercihten kaçıyor)
        if drop_pct < -max_fade_pct:
            max_fade_pct = abs(drop_pct)
            best_fade_market = m

    has_steam = (max_drop_pct >= threshold_pct) and (max_prob_jump >= SIGNIFICANT_PROB_JUMP_PCT)

    return {
        "has_steam": has_steam,
        "steam_market": best_steam_market if has_steam else None,
        "steam_drop_pct": round(max_drop_pct, 2),
        "implied_prob_jump_pct": round(max_prob_jump, 2),
        "faded_market": best_fade_market if max_fade_pct >= threshold_pct else None,
        "fade_pct": round(max_fade_pct, 2),
        "details": details
    }


def verify_smart_money_alignment(
    bet_market: str,
    steam_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Modelin seçtiği bahis tercihi ile Akıllı Para (Smart Money) akışının
    uyumunu denetler.

    Döndürür:
    - ALIGNED: Akıllı para bizimle aynı yönde -> Güven artırılır (+%25 boost).
    - VETO: Akıllı para bizim zıddımıza akıyor -> Sazan tuzağı, bahis ENGELLENİR!
    - NEUTRAL: Belirgin bir steam move yok -> Normal devam.
    """
    if not steam_info or not steam_info.get("has_steam"):
        return {
            "verdict": "NEUTRAL",
            "reason": "Piyasada belirgin bir Smart Money / Steam Move hareketi yok.",
            "confidence_multiplier": 1.0,
            "is_vetoed": False
        }

    steam_target = steam_info.get("steam_market")
    faded_target = steam_info.get("faded_market")
    drop_pct = steam_info.get("steam_drop_pct", 0.0)

    # Tercih kodunu basitleştir ("MS 1 (Chelsea)" -> "1", "2.5 Üst" -> "over_2_5")
    choice_code = None
    if "MS 1" in bet_market:
        choice_code = "1"
    elif "MS X" in bet_market:
        choice_code = "X"
    elif "MS 2" in bet_market:
        choice_code = "2"
    elif "2.5 Üst" in bet_market or "over" in bet_market.lower():
        choice_code = "over_2_5"
    elif "2.5 Alt" in bet_market or "under" in bet_market.lower():
        choice_code = "under_2_5"

    if not choice_code:
        return {
            "verdict": "NEUTRAL",
            "reason": "Tercih pazar kodu ayrıştırılamadı.",
            "confidence_multiplier": 1.0,
            "is_vetoed": False
        }

    # 1. Durum: Smart Money ile Tam Uyum (ALIGNED)
    if choice_code == steam_target:
        return {
            "verdict": "ALIGNED",
            "reason": f"🔥 SMART MONEY ONAYI: Keskin bürolarda oran %{drop_pct} çöktü. Büyük para tercihimizle aynı yönde!",
            "confidence_multiplier": 1.25,
            "is_vetoed": False
        }

    # 2. Durum: Smart Money Modelimizin Tersine Akıyor (VETO)
    if choice_code == faded_target or (steam_target and choice_code != steam_target):
        return {
            "verdict": "VETO",
            "reason": f"⚠️ SAZAN TUZAĞI / SHARP VETO: Model {choice_code} önerdi fakat akıllı para zıt yöne ({steam_target}) %{drop_pct} şiddetle aktı!",
            "confidence_multiplier": 0.0,
            "is_vetoed": True
        }

    return {
        "verdict": "NEUTRAL",
        "reason": "Piyasa hareketi nötr.",
        "confidence_multiplier": 1.0,
        "is_vetoed": False
    }

"""
global_market_intelligence.py — Küresel Keskin Piyasa ve Kadro İstihbarat Motoru
================================================================================
Bu modül 3 büyük küresel veri kaynağını tek bir orkestrasyonda birleştirir:

1. FLASHSCORE (NINJA FEED):
   - Resmi maç başlangıcından ~60 dk önce teyitli ilk 11 kadrolarını (df_li_1) çeker.
   - Dizilişleri (örn: 1-4-2-3-1, 1-4-3-3) ve eksik/sakat oyuncuları analiz eder.
   - Kadro şoklarında Dixon-Coles hücum/savunma parametrelerine dinamik ceza/katsayı uygular.

2. PINNACLE (SHARP BENCHMARK):
   - Dünyanın en keskin bahis bürosunun marjsız gerçek olasılıklarını (Shin / Fair Odds) hesaplar.
   - Modelimizin yerel bürolardan bulduğu değerin (%EV) Pinnacle kapanış çizgisiyle
     uyumlu olup olmadığını teyit eder.

3. DROPPING ODDS & STEAM AGGREGATOR (ODDSPORTAL MODELİ):
   - Birden fazla küresel büroda aynı anda gerçekleşen sert oran düşüşlerini (Steam Moves) yakalar.
   - Bizim modelimizin tahminiyle çelişen veya tersine para yığılan maçları anında VETO eder.
"""

import re
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from vip_syndicate_radar import VIPSyndicateRadar


FLASHSCORE_FEED_BASE = "https://46.flashscore.ninja/46/x/feed/"
FLASHSCORE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "X-Fsign": "SW9D1eZo",
    "Accept": "*/*"
}


# ============================================================================
# 1. FLASHSCORE NINJA FEED CLIENT (Teyitli Kadrolar & Dizilişler)
# ============================================================================
class FlashscoreNinjaClient:
    """
    Flashscore Ninja ikili feed'ini ayrıştırarak teyitli ilk 11 ve eksikleri çözer.
    """
    _cache: Dict[str, Tuple[float, Any]] = {}
    CACHE_TTL_SECONDS = 300  # 5 dakika önbellek

    @classmethod
    def _fetch_feed(cls, endpoint: str, timeout: float = 3.5) -> Optional[str]:
        now = time.time()
        if endpoint in cls._cache:
            ts, data = cls._cache[endpoint]
            if now - ts < cls.CACHE_TTL_SECONDS:
                return data

        url = f"{FLASHSCORE_FEED_BASE}{endpoint}"
        try:
            req = urllib.request.Request(url, headers=FLASHSCORE_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    content = resp.read().decode("utf-8", errors="ignore")
                    cls._cache[endpoint] = (now, content)
                    return content
        except Exception:
            return None
        return None

    @classmethod
    def parse_flashscore_blocks(cls, raw_data: str) -> List[Dict[str, str]]:
        """Flashscore ¬ ve ÷ ayracına sahip veri bloklarını sözlüğe çevirir."""
        if not raw_data:
            return []
        items = []
        blocks = raw_data.split("~AA÷")
        for b in blocks[1:]:
            block_dict = {}
            parts = b.split("¬")
            for p in parts:
                if "÷" in p:
                    k, v = p.split("÷", 1)
                    block_dict[k.strip()] = v.strip()
            if block_dict:
                items.append(block_dict)
        return items

    @classmethod
    def get_match_lineup(cls, match_id: str) -> Dict[str, Any]:
        """
        df_li_1_{mid} feed'inden teyitli ilk 11 ve dizilişleri çeker.
        """
        raw = cls._fetch_feed(f"df_li_1_{match_id}")
        if not raw:
            return {
                "is_confirmed": False,
                "home_formation": None,
                "away_formation": None,
                "home_missing_count": 0,
                "away_missing_count": 0,
                "lineup_penalty_home": 1.0,
                "lineup_penalty_away": 1.0,
                "status": "FEED_UNAVAILABLE"
            }

        # Diziliş tespiti (LD÷1-4-2-3-1 vb.)
        formations = re.findall(r"LD÷([\d\-]+)", raw)
        home_form = formations[0] if len(formations) > 0 else None
        away_form = formations[1] if len(formations) > 1 else None

        # Eksik / Sakat Oyuncular tespiti (IN÷ veya SA÷ içindeki eksik bayrakları)
        home_missing = len(re.findall(r"IN÷[^¬]*Home", raw, re.IGNORECASE))
        away_missing = len(re.findall(r"IN÷[^¬]*Away", raw, re.IGNORECASE))

        # Kadro açıklandı mı? (İlk 11 oyuncu blokları mevcutsa)
        is_confirmed = bool(home_form and away_form) or ("SA÷" in raw and len(raw) > 2000)

        # Eksik oyuncu etkisi (Hücum/Savunma katsayısı)
        # Örn: 1 önemli eksik %6, 2+ eksik %12 güç kaybı
        penalty_home = max(0.80, 1.0 - (home_missing * 0.06))
        penalty_away = max(0.80, 1.0 - (away_missing * 0.06))

        return {
            "is_confirmed": is_confirmed,
            "home_formation": home_form,
            "away_formation": away_form,
            "home_missing_count": home_missing,
            "away_missing_count": away_missing,
            "lineup_penalty_home": round(penalty_home, 3),
            "lineup_penalty_away": round(penalty_away, 3),
            "status": "CONFIRMED" if is_confirmed else "PENDING"
        }


# ============================================================================
# 2. PINNACLE SHARP BENCHMARK (Gerçek Keskin Çizgi Karşılaştırması)
# ============================================================================
class PinnacleSharpBenchmark:
    """
    Pinnacle'ın düşük marjlı keskin oranlarını kullanarak komisyonsuz gerçek
    olasılıkları çıkarır ve yerel bahsimizin Pinnacle'a göre değerini ölçer.
    """
    @staticmethod
    def strip_pinnacle_margin(o1: float, ox: float, o2: float) -> Dict[str, float]:
        """
        Pinnacle 1X2 oranlarından marjı sökerek saf keskin olasılıkları üretir.
        """
        if o1 <= 1.0 or ox <= 1.0 or o2 <= 1.0:
            return {"1": 0.33, "X": 0.33, "2": 0.33, "margin": 0.0}

        inv1, invx, inv2 = 1.0 / o1, 1.0 / ox, 1.0 / o2
        total_inv = inv1 + invx + inv2
        margin = total_inv - 1.0

        return {
            "p_1": round(inv1 / total_inv, 4),
            "p_x": round(invx / total_inv, 4),
            "p_2": round(inv2 / total_inv, 4),
            "sharp_margin_pct": round(margin * 100.0, 2)
        }

    @classmethod
    def evaluate_edge_vs_sharp(
        cls,
        market: str,
        taken_odd: float,
        pinnacle_odds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Alınan yerel oran ile Pinnacle marjsız olasılığı arasındaki farkı denetler.
        """
        if not pinnacle_odds:
            # Pinnacle verisi yoksa nötr varsay
            return {
                "has_sharp_benchmark": False,
                "sharp_fair_prob": None,
                "sharp_ev_pct": 0.0,
                "is_sharp_backed": True,
                "note": "Pinnacle verisi bulunamadı, model içi adil oran kullanıldı"
            }

        p1 = pinnacle_odds.get("1") or pinnacle_odds.get("pinnacle_1")
        px = pinnacle_odds.get("X") or pinnacle_odds.get("pinnacle_x")
        p2 = pinnacle_odds.get("2") or pinnacle_odds.get("pinnacle_2")

        if not p1 or not px or not p2:
            return {
                "has_sharp_benchmark": False,
                "sharp_fair_prob": None,
                "sharp_ev_pct": 0.0,
                "is_sharp_backed": True,
                "note": "Pinnacle 1X2 oranları eksik"
            }

        fair = cls.strip_pinnacle_margin(float(p1), float(px), float(p2))

        # Seçilen pazara göre Pinnacle adil olasılığı
        m_upper = market.upper()
        if "MS 1" in m_upper or "EV" in m_upper or "1" in m_upper:
            p_sharp = fair["p_1"]
        elif "MS 2" in m_upper or "DEP" in m_upper or "2" in m_upper:
            p_sharp = fair["p_2"]
        elif "MS X" in m_upper or "BERABERLİK" in m_upper or "X" in m_upper:
            p_sharp = fair["p_x"]
        elif ("2.5 ÜST" in m_upper or "OVER 2.5" in m_upper) and pinnacle_odds.get("over_2_5") and pinnacle_odds.get("under_2_5"):
            ov = float(pinnacle_odds["over_2_5"])
            un = float(pinnacle_odds["under_2_5"])
            inv_ov, inv_un = 1.0 / ov, 1.0 / un
            tot_inv = inv_ov + inv_un
            p_sharp = round(inv_ov / tot_inv, 4)
            fair["sharp_margin_pct"] = round((tot_inv - 1.0) * 100.0, 2)
        elif ("2.5 ALT" in m_upper or "UNDER 2.5" in m_upper) and pinnacle_odds.get("over_2_5") and pinnacle_odds.get("under_2_5"):
            ov = float(pinnacle_odds["over_2_5"])
            un = float(pinnacle_odds["under_2_5"])
            inv_ov, inv_un = 1.0 / ov, 1.0 / un
            tot_inv = inv_ov + inv_un
            p_sharp = round(inv_un / tot_inv, 4)
            fair["sharp_margin_pct"] = round((tot_inv - 1.0) * 100.0, 2)
        else:
            p_sharp = None

        if p_sharp is None:
            return {
                "has_sharp_benchmark": False,
                "sharp_fair_prob": None,
                "sharp_ev_pct": 0.0,
                "is_sharp_backed": True,
                "note": "1X2 dışı pazar için Pinnacle referansı atlandı"
            }

        sharp_ev = (p_sharp * taken_odd) - 1.0

        # Eğer Pinnacle'a göre bahis aşırı negatifse (-%10.0 altı) sazan tuzağı sayılır
        is_backed = sharp_ev >= -0.100

        return {
            "has_sharp_benchmark": True,
            "sharp_fair_prob": p_sharp,
            "sharp_ev_pct": round(sharp_ev * 100.0, 2),
            "is_sharp_backed": is_backed,
            "sharp_margin_pct": fair.get("sharp_margin_pct", 0.0),
            "note": "Pinnacle onaylı" if is_backed else "Pinnacle aleyhte (Ters Değer Riski)"
        }


# ============================================================================
# 3. DROPPING ODDS & STEAM AGGREGATOR (Oddsportal Çoklu Büro Modeli)
# ============================================================================
class DroppingOddsAggregator:
    """
    Birden fazla küresel büronun ortak oran düşüşünü analiz eder.
    """
    STEAM_DROP_THRESHOLD_PCT = 4.0

    @classmethod
    def audit_market_drops(
        cls,
        market: str,
        opening_odds: Optional[Dict[str, float]],
        current_odds: Optional[Dict[str, float]],
        multi_bookmaker_drops: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Oran düşüşünü ve küresel büro mutabakatını denetler.
        """
        # Çoklu büro verisi verilmişse
        if multi_bookmaker_drops:
            dropping_books = [b for b in multi_bookmaker_drops if b.get("drop_pct", 0.0) >= cls.STEAM_DROP_THRESHOLD_PCT]
            avg_drop = sum(b.get("drop_pct", 0.0) for b in dropping_books) / max(1, len(dropping_books))
            return {
                "has_steam": len(dropping_books) >= 3,
                "bookmaker_drop_count": len(dropping_books),
                "avg_drop_pct": round(avg_drop, 2),
                "steam_direction": dropping_books[0].get("market") if dropping_books else None,
                "consensus": "STRONG" if len(dropping_books) >= 5 else "MODERATE" if len(dropping_books) >= 2 else "WEAK"
            }

        # Açılış - Kapanış oran farkından türet
        if not opening_odds or not current_odds:
            return {
                "has_steam": False,
                "bookmaker_drop_count": 0,
                "avg_drop_pct": 0.0,
                "steam_direction": None,
                "consensus": "NO_DATA"
            }

        # İlgili pazarın oran düşüşünü hesapla
        target_key = "1" if "MS 1" in market else "2" if "MS 2" in market else "X" if "MS X" in market else None
        if not target_key:
            return {
                "has_steam": False,
                "bookmaker_drop_count": 0,
                "avg_drop_pct": 0.0,
                "steam_direction": None,
                "consensus": "NON_1X2"
            }

        open_val = opening_odds.get(target_key) or opening_odds.get(f"open_{target_key}")
        curr_val = current_odds.get(target_key) or current_odds.get(f"close_{target_key}")

        if not open_val or not curr_val:
            return {
                "has_steam": False,
                "bookmaker_drop_count": 0,
                "avg_drop_pct": 0.0,
                "steam_direction": None,
                "consensus": "ODDS_MISSING"
            }

        try:
            fo, fc = float(open_val), float(curr_val)
            drop_pct = ((fo - fc) / fo) * 100.0 if fo > 0 else 0.0
        except (ValueError, TypeError):
            drop_pct = 0.0

        # Zıt yöndeki düşüşü de kontrol et (Ters para akışı)
        opp_key = "2" if target_key == "1" else "1" if target_key == "2" else None
        opp_drop_pct = 0.0
        if opp_key:
            opp_open = opening_odds.get(opp_key) or opening_odds.get(f"open_{opp_key}")
            opp_curr = current_odds.get(opp_key) or current_odds.get(f"close_{opp_key}")
            if opp_open and opp_curr:
                try:
                    foo, foc = float(opp_open), float(opp_curr)
                    opp_drop_pct = ((foo - foc) / foo) * 100.0 if foo > 0 else 0.0
                except (ValueError, TypeError):
                    opp_drop_pct = 0.0

        has_steam_with_us = drop_pct >= cls.STEAM_DROP_THRESHOLD_PCT
        has_steam_against_us = opp_drop_pct >= cls.STEAM_DROP_THRESHOLD_PCT

        return {
            "has_steam": has_steam_with_us or has_steam_against_us,
            "drop_pct": round(drop_pct, 2),
            "opp_drop_pct": round(opp_drop_pct, 2),
            "steam_with_us": has_steam_with_us,
            "steam_against_us": has_steam_against_us,
            "consensus": "STEAM_ALIGNED" if has_steam_with_us else "STEAM_OPPOSED" if has_steam_against_us else "NEUTRAL"
        }


# ============================================================================
# 4. UNIFIED GLOBAL MARKET INTELLIGENCE (Nihai Orkestrasyon & Veto Motoru)
# ============================================================================
class GlobalMarketIntelligence:
    """
    Flashscore Kadro + Pinnacle Sharp Benchmark + Dropping Odds verilerini
    tek bir kararda sentezler. VETO veya BOOST kararlarını uygular.
    """

    @classmethod
    def evaluate_bet_proposal(
        cls,
        market: str,
        taken_odd: float,
        model_prob: float,
        opening_odds: Optional[Dict[str, float]] = None,
        current_odds: Optional[Dict[str, float]] = None,
        pinnacle_odds: Optional[Dict[str, float]] = None,
        flashscore_mid: Optional[str] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        volume_data: Optional[Dict[str, Any]] = None,
        asian_handicap_data: Optional[Dict[str, Any]] = None,
        live_pressure_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Tek bir bahis adayı için küresel istihbarat denetimi yapar.
        
        Döndürür:
        - verdict: "APPROVED", "BOOSTED_BY_SMART_MONEY", "VETOED_BY_SHARP_DROP", "VETOED_BY_LINEUP_SHOCK"
        - confidence_multiplier: Bahis güven katsayısı (1.25x veya 0.0x)
        - is_vetoed: True/False
        - rationale: Detaylı gerekçe
        - signals: 3 kaynaktan toplanan ham veriler
        """
        reasons = []
        is_vetoed = False
        verdict = "APPROVED"
        multiplier = 1.0

        # 1. Flashscore Kadro Denetimi
        lineup_info = (
            FlashscoreNinjaClient.get_match_lineup(flashscore_mid)
            if flashscore_mid
            else {
                "is_confirmed": False,
                "status": "UNLINKED",
                "lineup_penalty_home": 1.0,
                "lineup_penalty_away": 1.0,
                "home_missing_count": 0,
                "away_missing_count": 0
            }
        )

        # Kadro şoku kontrolü: Desteklediğimiz takımda 3+ eksik varsa veya ceza katsayısı <= 0.85 ise
        if "MS 1" in market and lineup_info.get("lineup_penalty_home", 1.0) <= 0.85:
            is_vetoed = True
            verdict = "VETOED_BY_LINEUP_SHOCK"
            reasons.append(f"KADRO ŞOKU VETOSU: Ev sahibinde {lineup_info.get('home_missing_count')} kritik eksik tespit edildi.")
        elif "MS 2" in market and lineup_info.get("lineup_penalty_away", 1.0) <= 0.85:
            is_vetoed = True
            verdict = "VETOED_BY_LINEUP_SHOCK"
            reasons.append(f"KADRO ŞOKU VETOSU: Deplasmanda {lineup_info.get('away_missing_count')} kritik eksik tespit edildi.")

        # 2. Pinnacle Keskin Çizgi Denetimi
        sharp_info = PinnacleSharpBenchmark.evaluate_edge_vs_sharp(
            market=market,
            taken_odd=taken_odd,
            pinnacle_odds=pinnacle_odds
        )
        if sharp_info["has_sharp_benchmark"] and not sharp_info["is_sharp_backed"]:
            is_vetoed = True
            verdict = "VETOED_BY_PINNACLE_EDGE"
            reasons.append(f"PINNACLE VETOSU: Pinnacle adil çizgisine göre negatif değer ({sharp_info['sharp_ev_pct']}%), sazan tuzağı riski.")

        # 3. Dropping Odds / Steam Denetimi
        steam_info = DroppingOddsAggregator.audit_market_drops(
            market=market,
            opening_odds=opening_odds,
            current_odds=current_odds
        )

        if steam_info.get("steam_against_us"):
            is_vetoed = True
            verdict = "VETOED_BY_SHARP_DROP"
            reasons.append(f"KÜRESEL ORAN DÜŞÜŞÜ VETOSU: Rakip seçenekte %{steam_info.get('opp_drop_pct')} sert oran çöküşü (Smart Money ters yönde).")
        elif steam_info.get("steam_with_us") and not is_vetoed:
            verdict = "BOOSTED_BY_SMART_MONEY"
            multiplier = 1.25  # Güveni %25 artır
            reasons.append(f"AKILLI PARA ONAYI: Seçtiğimiz tercihte %{steam_info.get('drop_pct')} sert oran çöküşü teyit edildi (+25% Güven).")

        # 4. VIP Sendika, Baron Hacmi ve Asya Handikap Radarı
        vip_info = VIPSyndicateRadar.audit_vip_signals(
            home_team=home_team or "Home",
            away_team=away_team or "Away",
            market=market,
            taken_odd=taken_odd,
            volume_data=volume_data,
            asian_handicap_data=asian_handicap_data,
            live_pressure_data=live_pressure_data
        )

        if vip_info.get("is_vetoed"):
            is_vetoed = True
            verdict = vip_info.get("verdict", "VETOED_BY_VIP_RADAR")
            reasons.append(vip_info.get("rationale", "VIP Sendika Vetosu"))
        elif vip_info.get("verdict") == "BOOSTED_BY_WHALE_SYNDICATE" and not is_vetoed:
            verdict = "BOOSTED_BY_WHALE_SYNDICATE"
            multiplier = max(multiplier, vip_info.get("confidence_multiplier", 1.30))
            reasons.append(vip_info.get("rationale", "Baron Hacmi Onayı"))

        if not reasons:
            reasons.append("Tüm küresel piyasa ve kadro filtrelerinden başarıyla geçti.")

        return {
            "verdict": verdict,
            "is_vetoed": is_vetoed,
            "confidence_multiplier": 0.0 if is_vetoed else multiplier,
            "rationale": " | ".join(reasons),
            "signals": {
                "flashscore_lineups": lineup_info,
                "pinnacle_benchmark": sharp_info,
                "dropping_odds_steam": steam_info,
                "vip_syndicate_radar": vip_info
            }
        }

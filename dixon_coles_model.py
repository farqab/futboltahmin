"""
dixon_coles_model.py — Dixon-Coles Bivariate Poisson & Elo Rating Engine
========================================================================
Referans: Dixon, M. J., & Coles, S. G. (1997). Modelling Association Football
Scores and Inefficiencies in the Football Betting Market. Applied Statistics, 265-280.

Klasik Poisson modelinin en büyük iki zayıflığı:
1. Düşük skorlardaki ve beraberliklerdeki bağımlılığı (0-0, 1-0, 0-1, 1-1) göz ardı etmesi.
2. Takımların zaman içindeki güç değişimini tek düze sayması.

Bu modül:
- Bivariate Dixon-Coles düzeltme fonksiyonu tau(x, y; rho) ile gerçekçi düşük skor olasılıkları üretir.
- Dinamik Elo reyting sistemiyle takımların hücum/savunma parametrelerini dengeler.
"""

import os
import json
import math
from typing import Dict, Any, Tuple, List, Optional
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_FILE = os.path.join(PROJECT_DIR, "dixon_coles_weights.json")
_TRAINED_WEIGHTS: Dict[str, Any] = None


def get_trained_weights() -> Dict[str, Any]:
    global _TRAINED_WEIGHTS
    if _TRAINED_WEIGHTS is None:
        if os.path.exists(WEIGHTS_FILE):
            try:
                with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
                    _TRAINED_WEIGHTS = json.load(f).get("leagues", {})
            except:
                _TRAINED_WEIGHTS = {}
        else:
            _TRAINED_WEIGHTS = {}
    return _TRAINED_WEIGHTS


# Ortalama lig gol normları ve saha avantajı
LEAGUE_NORMS = {
    "Premier League": {"home_avg": 1.58, "away_avg": 1.28, "rho": -0.13},
    "La Liga":        {"home_avg": 1.45, "away_avg": 1.12, "rho": -0.11},
    "Serie A":        {"home_avg": 1.48, "away_avg": 1.18, "rho": -0.14},
    "Bundesliga":      {"home_avg": 1.76, "away_avg": 1.38, "rho": -0.10},
    "Ligue 1":        {"home_avg": 1.42, "away_avg": 1.14, "rho": -0.12},
    "Süper Lig":      {"home_avg": 1.52, "away_avg": 1.22, "rho": -0.12},
    "Default":        {"home_avg": 1.50, "away_avg": 1.20, "rho": -0.13}
}


def _poisson_pmf(k: int, lam: float) -> float:
    """Poisson olasılık kütle fonksiyonu: P(X = k) = (lam^k * e^-lam) / k!"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.pow(lam, k) * math.exp(-lam)) / math.factorial(k)


def _dixon_coles_tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """
    Dixon-Coles bivariate düzeltme çarpanı tau(x, y).
    0-0, 1-0, 0-1, 1-1 skorlarının gerçek frekanslara göre hafifçe bükülmesini sağlar.
    """
    if x == 0 and y == 0:
        val = 1.0 - (lam * mu * rho)
    elif x == 0 and y == 1:
        val = 1.0 + (lam * rho)
    elif x == 1 and y == 0:
        val = 1.0 + (mu * rho)
    elif x == 1 and y == 1:
        val = 1.0 - rho
    else:
        val = 1.0
    return max(0.001, val)


class DynamicEloTracker:
    """
    Takımların göreceli güçlerini takip eden ve Dixon-Coles lambda
    hesabına zemin oluşturan dinamik Elo sistemi.
    """
    def __init__(self, base_elo: float = 1500.0, k_factor: float = 24.0):
        self.base_elo = base_elo
        self.k_factor = k_factor
        self.ratings = defaultdict(lambda: base_elo)

    def get_rating(self, team_name: str) -> float:
        return self.ratings[team_name]

    def update(self, home_team: str, away_team: str, home_goals: int, away_goals: int):
        r_home = self.ratings[home_team]
        r_away = self.ratings[away_team]

        # Saha avantajı dahil beklenti (+65 Elo puanı ev avantajı)
        dr = (r_home + 65.0) - r_away
        e_home = 1.0 / (1.0 + math.pow(10, -dr / 400.0))
        e_away = 1.0 - e_home

        # Gerçek sonuç
        if home_goals > away_goals:
            s_home, s_away = 1.0, 0.0
        elif home_goals == away_goals:
            s_home, s_away = 0.5, 0.5
        else:
            s_home, s_away = 0.0, 1.0

        # Gol farkı çarpanı (Margin of victory multiplier)
        goal_diff = abs(home_goals - away_goals)
        mov_mult = math.log(max(1, goal_diff) + 1.0) * (2.2 / ((dr * 0.001 if s_home == 1 else -dr * 0.001) + 2.2))

        self.ratings[home_team] = round(r_home + self.k_factor * mov_mult * (s_home - e_home), 2)
        self.ratings[away_team] = round(r_away + self.k_factor * mov_mult * (s_away - e_away), 2)


# Küresel Elo havuzu
elo_engine = DynamicEloTracker()


def _find_team_weights(teams_data: Dict[str, Any], team_name: str) -> Optional[Dict[str, Any]]:
    if not team_name:
        return None
    if team_name in teams_data:
        return teams_data[team_name]

    def norm_s(s: str) -> str:
        s = s.lower().replace("fc", "").replace("sk", "").replace("fk", "").replace("cf", "").strip()
        tr_map = str.maketrans("çğışöüéáíóú", "cgisoueaiou")
        return s.translate(tr_map).replace(" ", "").replace("-", "")

    target = norm_s(team_name)
    for k, val in teams_data.items():
        if norm_s(k) == target:
            return val
    for k, val in teams_data.items():
        k_norm = norm_s(k)
        if target and (target in k_norm or k_norm in target):
            return val
    return None


def estimate_lambdas(match: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Takımların form, xG, hücum/savunma direnci ve Elo farkına göre
    ev ve deplasman lambda (beklenen gol) değerlerini hesaplar.
    """
    league = match.get("league", "Default")
    norm = LEAGUE_NORMS.get(league, LEAGUE_NORMS["Default"])

    home_name = match.get("home_name", "Home")
    away_name = match.get("away_name", "Away")

    # 1. Elo farkı tabanı
    r_h = elo_engine.get_rating(home_name)
    r_a = elo_engine.get_rating(away_name)

    # Soğuk başlangıç durumunda piyasa oranlarından gerçekçi taban Elo kalibrasyonu
    if r_h == 1500.0 and r_a == 1500.0:
        odds = match.get("odds") or {}
        o1 = odds.get("1") or odds.get("ms_1")
        o2 = odds.get("2") or odds.get("ms_2")
        if o1 and o2:
            try:
                fo1, fo2 = float(o1), float(o2)
                if fo1 > 1.0 and fo2 > 1.0:
                    ratio = fo2 / fo1
                    implied_elo_diff = max(-400.0, min(400.0, 300.0 * math.log10(ratio)))
                    r_h = 1500.0 + (implied_elo_diff / 2.0)
                    r_a = 1500.0 - (implied_elo_diff / 2.0)
                    elo_engine.ratings[home_name] = round(r_h, 1)
                    elo_engine.ratings[away_name] = round(r_a, 1)
            except:
                pass

    elo_diff = (r_h + 50.0) - r_a  # 50 puan iç saha avantajı

    # Elo temelli gol çarpanı
    elo_h_factor = math.exp(elo_diff / 500.0)
    elo_a_factor = math.exp(-elo_diff / 500.0)

    # 2. Hücum ve Savunma istatistikleri
    h_sc5 = float(match.get("home_scored_last5") or 7.0) / 5.0
    h_cn5 = float(match.get("home_conceded_last5") or 5.0) / 5.0
    a_sc5 = float(match.get("away_scored_last5") or 6.0) / 5.0
    a_cn5 = float(match.get("away_conceded_last5") or 6.0) / 5.0

    # 3. xG zenginleştirmesi (varsa)
    h_xg = match.get("home_xg_avg")
    a_xg = match.get("away_xg_avg")
    if h_xg and a_xg:
        try:
            h_sc5 = h_sc5 * 0.6 + float(h_xg) * 0.4
            a_sc5 = a_sc5 * 0.6 + float(a_xg) * 0.4
        except (ValueError, TypeError):
            pass

    # 4. Eğitilmiş Dixon-Coles MLE Katsayıları Entegrasyonu
    trained_leagues = get_trained_weights()
    league_trained = trained_leagues.get(league)

    if league_trained and "teams" in league_trained:
        teams_data = league_trained["teams"]
        gamma_mle = league_trained.get("gamma_home_advantage", 1.22)
        rho_mle = league_trained.get("rho", norm["rho"])

        h_mle = _find_team_weights(teams_data, home_name)
        a_mle = _find_team_weights(teams_data, away_name)

        if h_mle and a_mle:
            alpha_h = h_mle["alpha_attack"]
            beta_h = h_mle["beta_defense"]
            alpha_a = a_mle["alpha_attack"]
            beta_a = a_mle["beta_defense"]

            # Saf Dixon-Coles MLE gol beklentileri
            lam_h_pure = alpha_h * beta_a * gamma_mle
            lam_a_pure = alpha_a * beta_h

            # Olgun MLE modelini %80 ağırlıkla, son 5 maçlık mikro formu %20 ağırlıkla sentezle
            lam_home = lam_h_pure * 0.80 + ((h_sc5 * 0.5 + a_cn5 * 0.5) * 0.20)
            lam_away = lam_a_pure * 0.80 + ((a_sc5 * 0.5 + h_cn5 * 0.5) * 0.20)

            lam_home = max(0.35, min(3.80, round(lam_home, 3)))
            lam_away = max(0.25, min(3.50, round(lam_away, 3)))
            return lam_home, lam_away, rho_mle

    # Ağırlıklı lambda sentezi (Eğitilmemiş / bilinmeyen takımlar için güvenli yedekleme)
    lam_home = (h_sc5 * 0.40 + a_cn5 * 0.35 + norm["home_avg"] * 0.25) * ((elo_h_factor * 0.3) + 0.7)
    lam_away = (a_sc5 * 0.40 + h_cn5 * 0.35 + norm["away_avg"] * 0.25) * ((elo_a_factor * 0.3) + 0.7)

    # Aşırı uçları makul sınırlara çek (0.3 - 3.8 gol aralığı)
    lam_home = max(0.35, min(3.80, round(lam_home, 3)))
    lam_away = max(0.25, min(3.50, round(lam_away, 3)))

    return lam_home, lam_away, norm["rho"]


def simulate_dixon_coles(match: Dict[str, Any], max_goals: int = 7) -> Dict[str, Any]:
    """
    Dixon-Coles bivariate modelini çalıştırır ve 1X2, Alt/Üst, KG ve skor olasılıklarını döker.
    """
    lam_h, lam_a, rho = estimate_lambdas(match)

    grid: List[List[float]] = []
    total_prob = 0.0

    for x in range(max_goals + 1):
        row = []
        p_x = _poisson_pmf(x, lam_h)
        for y in range(max_goals + 1):
            p_y = _poisson_pmf(y, lam_a)
            tau = _dixon_coles_tau(x, y, lam_h, lam_a, rho)
            cell_prob = tau * p_x * p_y
            row.append(cell_prob)
            total_prob += cell_prob
        grid.append(row)

    # Olasılıkları normalize et (toplamı 1.0 yap)
    if total_prob > 0:
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                grid[x][y] /= total_prob

    # Pazar olasılıklarını topla
    p_hw = 0.0
    p_dr = 0.0
    p_aw = 0.0
    p_o15 = 0.0
    p_o25 = 0.0
    p_o35 = 0.0
    p_btts_yes = 0.0

    score_candidates = []

    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            p = grid[x][y]
            if x > y:
                p_hw += p
            elif x == y:
                p_dr += p
            else:
                p_aw += p

            tot_g = x + y
            if tot_g > 1.5:
                p_o15 += p
            if tot_g > 2.5:
                p_o25 += p
            if tot_g > 3.5:
                p_o35 += p

            if x > 0 and y > 0:
                p_btts_yes += p

            score_candidates.append((f"{x}-{y}", p))

    score_candidates.sort(key=lambda s: s[1], reverse=True)
    top_scores = [(s[0], round(s[1] * 100, 2)) for s in score_candidates[:4]]

    return {
        "model_type": "Dixon-Coles (1997)",
        "lambda_home": lam_h,
        "lambda_away": lam_a,
        "rho": rho,
        "expected_total_goals": round(lam_h + lam_a, 2),
        "prob_home_win": round(p_hw, 4),
        "prob_draw": round(p_dr, 4),
        "prob_away_win": round(p_aw, 4),
        "prob_over_1_5": round(p_o15, 4),
        "prob_over_2_5": round(p_o25, 4),
        "prob_over_3_5": round(p_o35, 4),
        "prob_under_2_5": round(1.0 - p_o25, 4),
        "prob_btts_yes": round(p_btts_yes, 4),
        "prob_btts_no": round(1.0 - p_btts_yes, 4),
        "top_scores": top_scores,
        "most_likely_score": top_scores[0][0] if top_scores else "1-1"
    }

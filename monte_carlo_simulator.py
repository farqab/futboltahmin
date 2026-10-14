"""
monte_carlo_simulator.py — TypeSafe AI 10.000 Maç Simülasyon Motoru
==================================================================
Matematiksel Model: Poisson Dağılımı ve Monte Carlo Simülasyonu
- Takımların iç saha hücum/savunma güçleri
- Deplasman hücum/savunma güçleri
- Lig ortalama gol beklentileri
- xG (Beklenen Gol) verileri
kullanılarak her maç arka planda 10.000 kez oynatılır ve olasılıklar hesaplanır.
"""

import math
import random
from collections import Counter

# Lig bazlı ortalama ev ve deplasman gol lambdaları (Tarihsel normlar)
LEAGUE_GOAL_NORMS = {
    "Bundesliga":      {"home_avg": 1.78, "away_avg": 1.42},
    "Premier League": {"home_avg": 1.58, "away_avg": 1.32},
    "Serie A":        {"home_avg": 1.48, "away_avg": 1.22},
    "La Liga":        {"home_avg": 1.46, "away_avg": 1.14},
    "Ligue 1":        {"home_avg": 1.42, "away_avg": 1.16},
    "Süper Lig":      {"home_avg": 1.52, "away_avg": 1.25},
    "Diğer":          {"home_avg": 1.50, "away_avg": 1.20}
}

def _poisson_sample(lam):
    """Knuth algoritmasıyla Poisson rastgele değişken üretir."""
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

def calculate_lambdas(m):
    """
    TypeSafe AI Hibrit Modeli:
    Ev ve deplasman takımlarının beklenen gol (Lambda) değerlerini hesaplar.
    """
    league = m.get("league", "Diğer")
    norm = LEAGUE_GOAL_NORMS.get(league, LEAGUE_GOAL_NORMS["Diğer"])
    
    # 1. Ev sahibinin gol gücü
    h_sc5 = float(m.get("home_scored_last5") or m.get("home_scored_last3") or 7) / 5.0
    h_home_sc = float(m.get("home_home_scored_last5") or 0) / max(1, float(m.get("home_home_total") or 3))
    if h_home_sc <= 0: h_home_sc = h_sc5
    
    # 2. Deplasmanın savunma zaafiyeti
    a_cn5 = float(m.get("away_conceded_last5") or m.get("away_conceded_last3") or 6) / 5.0
    a_away_cn = float(m.get("away_away_conceded_last5") or 0) / max(1, float(m.get("away_away_total") or 3))
    if a_away_cn <= 0: a_away_cn = a_cn5

    # 3. Deplasmanın gol gücü
    a_sc5 = float(m.get("away_scored_last5") or m.get("away_scored_last3") or 6) / 5.0
    a_away_sc = float(m.get("away_away_scored_last5") or 0) / max(1, float(m.get("away_away_total") or 3))
    if a_away_sc <= 0: a_away_sc = a_sc5

    # 4. Ev sahibinin savunma direnci
    h_cn5 = float(m.get("home_conceded_last5") or m.get("home_conceded_last3") or 5) / 5.0
    h_home_cn = float(m.get("home_home_conceded_last5") or 0) / max(1, float(m.get("home_home_total") or 3))
    if h_home_cn <= 0: h_home_cn = h_cn5

    # Temel Lambda hesabı (Ağırlıklı formül)
    lam_home = (h_home_sc * 0.40 + a_away_cn * 0.35 + norm["home_avg"] * 0.25)
    lam_away = (a_away_sc * 0.40 + h_home_cn * 0.35 + norm["away_avg"] * 0.25)

    # xG varsa ağırlık ekle
    if m.get("xg_available"):
        try:
            h_xg = float(m.get("home_xg_avg") or 1.5)
            a_xg = float(m.get("away_xg_avg") or 1.2)
            lam_home = lam_home * 0.70 + h_xg * 0.30
            lam_away = lam_away * 0.70 + a_xg * 0.30
        except:
            pass

    # Sınırlandırma (aşırı uçları yumuşat)
    lam_home = max(0.4, min(3.8, round(lam_home, 2)))
    lam_away = max(0.3, min(3.2, round(lam_away, 2)))

    return lam_home, lam_away

def simulate_match(m, n_simulations=10000):
    """
    Maçı n_simulations (varsayılan 10.000) kez simüle eder.
    Tüm pazar olasılıklarını ve en olası skorları döndürür.
    """
    lam_home, lam_away = calculate_lambdas(m)
    
    home_wins = 0
    draws = 0
    away_wins = 0
    
    over_1_5 = 0
    over_2_5 = 0
    btts_yes = 0
    
    scores = []
    
    for _ in range(n_simulations):
        h_goals = _poisson_sample(lam_home)
        a_goals = _poisson_sample(lam_away)
        
        # Maç sonucu
        if h_goals > a_goals:
            home_wins += 1
        elif a_goals > h_goals:
            away_wins += 1
        else:
            draws += 1
            
        tot = h_goals + a_goals
        if tot >= 2:
            over_1_5 += 1
        if tot >= 3:
            over_2_5 += 1
            
        if h_goals > 0 and a_goals > 0:
            btts_yes += 1
            
        scores.append(f"{h_goals}-{a_goals}")
        
    # Yüzdeleri hesapla
    p_hw = round((home_wins / n_simulations) * 100, 1)
    p_dr = round((draws / n_simulations) * 100, 1)
    p_aw = round((away_wins / n_simulations) * 100, 1)
    
    p_o15 = round((over_1_5 / n_simulations) * 100, 1)
    p_o25 = round((over_2_5 / n_simulations) * 100, 1)
    p_btts = round((btts_yes / n_simulations) * 100, 1)
    
    # En sık çıkan skorlar
    c = Counter(scores)
    top3 = [(score, round((cnt / n_simulations) * 100, 1)) for score, cnt in c.most_common(3)]
    top_score_str = f"{top3[0][0]} (%{top3[0][1]})" if top3 else "1-1"

    summary_str = (
        f"10.000 Simülasyon: 1.5 Üst %{p_o15} | 2.5 Üst %{p_o25} | KG %{p_btts} | "
        f"En Olası Skor: {top_score_str}"
    )

    return {
        "lambda_home": lam_home,
        "lambda_away": lam_away,
        "expected_total_goals": round(lam_home + lam_away, 2),
        "sim_prob_home_win": p_hw,
        "sim_prob_draw": p_dr,
        "sim_prob_away_win": p_aw,
        "sim_prob_over_1_5": p_o15,
        "sim_prob_over_2_5": p_o25,
        "sim_prob_btts": p_btts,
        "sim_top_scores": top3,
        "sim_top_score_str": top_score_str,
        "sim_summary": summary_str
    }

if __name__ == "__main__":
    test_match = {
        "league": "Premier League",
        "home_name": "Manchester City",
        "away_name": "Sunderland",
        "home_scored_last5": 14,
        "home_conceded_last5": 3,
        "away_scored_last5": 4,
        "away_conceded_last5": 9
    }
    res = simulate_match(test_match)
    print("Test Simülasyonu:")
    print(res["sim_summary"])
    print(f"Lambdalar: Ev {res['lambda_home']} - Dep {res['lambda_away']}")

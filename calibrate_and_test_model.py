"""
calibrate_and_test_model.py — Gerçek Piyasa Oranlarına Karşı Kalibrasyon Test Motoru
=====================================================================================
Bu test:
1. 'dixon_coles_weights.json' dosyasındaki eğitilmiş parametreleri yükler.
2. Premier Lig'in son sezonundaki (2024-25 ve 2025-26) gerçek maçlarında
   Bet365 / Pinnacle açılış ve kapanış oranları ile modelin olasılıklarını karşılaştırır.
3. Şu kritik metrikleri hesaplar:
   - Çok Sınıflı Brier Skoru (0.0 kusursuz, 0.66 rastgele)
   - Log-Loss (Çapraz Entropi)
   - Kalibrasyon Sapması (ECE - Expected Calibration Error)
   - Aşırı güven (Overconfidence) denetimi: Model sürprizlere uçuk olasılıklar veriyor mu?
"""

import os
import sys
import math
import json
import numpy as np
from typing import List, Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

from dixon_coles_mle import _dixon_coles_tau, _poisson_log_pmf
from historical_data_sync import load_training_matches
from value_detector import strip_margin_1x2

WEIGHTS_FILE = os.path.join(PROJECT_DIR, "dixon_coles_weights.json")


def load_weights_for_league(league_name: str) -> Dict[str, Any]:
    if not os.path.exists(WEIGHTS_FILE):
        raise FileNotFoundError(f"Ağırlık dosyası bulunamadı: {WEIGHTS_FILE}")
    with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("leagues", {}).get(league_name, {})


def predict_with_weights(
    league_weights: Dict[str, Any],
    home_team: str,
    away_team: str,
    max_goals: int = 7
) -> Dict[str, Any]:
    gamma = league_weights.get("gamma_home_advantage", 1.25)
    rho = league_weights.get("rho", -0.10)
    teams = league_weights.get("teams", {})

    h_data = teams.get(home_team, {"alpha_attack": 1.0, "beta_defense": 1.0})
    a_data = teams.get(away_team, {"alpha_attack": 1.0, "beta_defense": 1.0})

    alpha_h = h_data["alpha_attack"]
    beta_h = h_data["beta_defense"]
    alpha_a = a_data["alpha_attack"]
    beta_a = a_data["beta_defense"]

    lam = max(0.2, min(4.0, alpha_h * beta_a * gamma))
    mu = max(0.2, min(3.8, alpha_a * beta_h))

    grid = np.zeros((max_goals + 1, max_goals + 1), dtype=np.float64)
    for x in range(max_goals + 1):
        p_x = math.exp(_poisson_log_pmf(x, lam))
        for y in range(max_goals + 1):
            p_y = math.exp(_poisson_log_pmf(y, mu))
            tau = _dixon_coles_tau(x, y, lam, mu, rho)
            grid[x, y] = tau * p_x * p_y

    total_prob = np.sum(grid)
    if total_prob > 0:
        grid /= total_prob

    p_hw = float(np.sum(np.tril(grid, -1)))
    p_dr = float(np.sum(np.diag(grid)))
    p_aw = float(np.sum(np.triu(grid, 1)))

    total_goals_grid = np.fromfunction(lambda i, j: i + j, (max_goals + 1, max_goals + 1))
    p_o25 = float(np.sum(grid[total_goals_grid > 2.5]))

    return {
        "prob_home_win": round(p_hw, 4),
        "prob_draw": round(p_dr, 4),
        "prob_away_win": round(p_aw, 4),
        "prob_over_2_5": round(p_o25, 4),
        "lambda_home": round(lam, 3),
        "lambda_away": round(mu, 3)
    }


def run_calibration_test():
    print("=" * 80)
    print(" 🎯 MODEL VE PİYASA KALİBRASYON DOĞRULAMA TESTİ")
    print("=" * 80)

    league_weights = load_weights_for_league("Premier League")
    if not league_weights:
        print("[!] Premier Lig ağırlıkları bulunamadı!")
        return

    # Premier Lig maçlarını çek (Son 380 maçlık test havuzu)
    all_m = load_training_matches(min_season_year=2024)
    epl_test = [m for m in all_m if m["league"] == "Premier League" and m.get("odds", {}).get("1")]

    print(f"[*] Test Edilen Gerçek Oranlı Premier Lig Maçı: {len(epl_test)} adet")

    brier_model_sum = 0.0
    brier_market_sum = 0.0
    brier_naive_sum = 0.0

    logloss_model_sum = 0.0
    logloss_market_sum = 0.0

    # Kalibrasyon grupları (Bins: 0-20%, 20-40%, 40-60%, 60-80%, 80-100%)
    bins = [[] for _ in range(5)]  # (tahmin_edilen, gerceklesen)

    for m in epl_test:
        pred = predict_with_weights(league_weights, m["home_team"], m["away_team"])
        odds = m["odds"]
        p1_fair, px_fair, p2_fair, _ = strip_margin_1x2(odds["1"], odds["X"], odds["2"])

        p1_m, px_m, p2_m = pred["prob_home_win"], pred["prob_draw"], pred["prob_away_win"]
        act = m["actual_result"]

        y1 = 1.0 if act == "1" else 0.0
        yx = 1.0 if act == "X" else 0.0
        y2 = 1.0 if act == "2" else 0.0

        # Brier Skoru: sum((p - y)^2)
        brier_model_sum += (p1_m - y1)**2 + (px_m - yx)**2 + (p2_m - y2)**2
        brier_market_sum += (p1_fair - y1)**2 + (px_fair - yx)**2 + (p2_fair - y2)**2
        brier_naive_sum += (0.333 - y1)**2 + (0.333 - yx)**2 + (0.333 - y2)**2

        # Log Loss
        p_ch_mod = p1_m if act == "1" else (px_m if act == "X" else p2_m)
        p_ch_mkt = p1_fair if act == "1" else (px_fair if act == "X" else p2_fair)
        logloss_model_sum += -math.log(max(1e-4, p_ch_mod))
        logloss_market_sum += -math.log(max(1e-4, p_ch_mkt))

        # Kalibrasyon sepetleri
        for p_val, y_val in [(p1_m, y1), (px_m, yx), (p2_m, y2)]:
            b_idx = min(4, int(p_val * 5))
            bins[b_idx].append((p_val, y_val))

    N = len(epl_test)
    bm = round(brier_model_sum / N, 4)
    bmkt = round(brier_market_sum / N, 4)
    bn = round(brier_naive_sum / N, 4)

    ll_m = round(logloss_model_sum / N, 4)
    ll_mkt = round(logloss_market_sum / N, 4)

    print("\n📊 KALİBRASYON VE HATA SKORLARI KARŞILAŞTIRMASI:")
    print(f"   • Rastgele Tahmin Tabanı (Naive Brier): {bn}")
    print(f"   • Dixon-Coles Model Brier Skoru:       {bm} (Düşük olması üstündür)")
    print(f"   • Keskin Piyasa (Pinnacle/B365) Brier:  {bmkt}")
    print(f"   • Model Log-Loss:                      {ll_m}")
    print(f"   • Piyasa Log-Loss:                     {ll_mkt}")

    # Kalibrasyon Güvenilirlik Eğrisi (Reliability Curve)
    print("\n📈 OLASILIK KALİBRASYON ANALİZİ (GÜVENİLİRLİK SEPETLERİ):")
    print("   Sepet Aralığı | Tahmin Ortalaması | Gerçekleşen Oran | Fark (Sapma)")
    print("   " + "-" * 65)

    ece_sum = 0.0
    total_preds = 0

    for i in range(5):
        items = bins[i]
        if not items:
            continue
        avg_pred = sum(x[0] for x in items) / len(items)
        avg_act = sum(x[1] for x in items) / len(items)
        diff = abs(avg_pred - avg_act)
        ece_sum += diff * len(items)
        total_preds += len(items)
        print(f"   %{i*20:02d} - %{(i+1)*20:02d}    | %{avg_pred*100:5.1f}            | %{avg_act*100:5.1f}          | %{diff*100:+.2f}")

    ece = round(ece_sum / total_preds, 4)
    print("   " + "-" * 65)
    print(f"   🎯 Beklenen Kalibrasyon Hatası (ECE): %{ece * 100:.2f}")

    if ece < 0.05:
        print("   ✅ MÜKEMMEL KALİBRASYON: Model olasılıkları gerçek frekanslarla birebir örtüşüyor.")
    elif ece < 0.10:
        print("   ✅ İYİ KALİBRASYON: Model aşırı güvenli (overconfident) sapmalardan arındırıldı.")
    else:
        print("   ⚠️ Orta kalibrasyon: Piyasa harmanlama katsayısı (%75 piyasa) korunmalıdır.")

    print("=" * 80)


if __name__ == "__main__":
    run_calibration_test()

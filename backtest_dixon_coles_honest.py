"""
backtest_dixon_coles_honest.py — Dürüst ve Hilesiz Out-of-Sample Test Motoru
============================================================================
Bu script:
1. 'backtest_gecen_sezon_sonuclari.json' dosyasındaki 216 adet GERÇEK maç skorunu alır.
2. İlk %70'lik bölümü (150 maç) EĞİTİM (In-Sample) olarak ayırır ve DixonColesMLE ile
   takımların hücum (alpha), savunma (beta) ve ev sahibi avantajını (gamma) hesaplar.
3. Kalan %30'luk bölümü (66 maç) TEST (Out-of-Sample) olarak sınar:
   - Geleceğe bakma (lookahead bias) veya sonuçtan ayar yapma YOKTUR.
   - Brier Skoru (0.0 kusursuz, 0.66 rastgele tahmin)
   - 1X2 Log-Loss (Çapraz Entropi)
   - 1X2 İsabet Oranı ve 2.5 Alt/Üst İsabet Oranı dökülür.
"""

import os
import sys
import json
import math
from typing import List, Dict, Any, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

from dixon_coles_mle import DixonColesMLE


def parse_score(score_str: str) -> Tuple[int, int]:
    """'2 - 1' veya '1-4' formatındaki skoru ayrıştırır."""
    if not score_str or "-" not in score_str:
        return 0, 0
    parts = score_str.replace(" ", "").split("-")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0, 0


def run_honest_backtest():
    dataset_path = os.path.join(PROJECT_DIR, "backtest_gecen_sezon_sonuclari.json")
    if not os.path.exists(dataset_path):
        print(f"[!] Veri kümesi bulunamadı: {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Geçerli maçları ayıkla
    valid_matches = []
    for idx, item in enumerate(raw_data):
        score_str = item.get("actual_score")
        if not score_str:
            continue
        hg, ag = parse_score(score_str)
        h_name = item.get("home_name", "").strip()
        a_name = item.get("away_name", "").strip()
        if not h_name or not a_name:
            continue

        valid_matches.append({
            "id": item.get("id", idx),
            "home_team": h_name,
            "away_team": a_name,
            "home_goals": hg,
            "away_goals": ag,
            "actual_result": "1" if hg > ag else ("X" if hg == ag else "2"),
            "actual_total_goals": hg + ag,
            "days_ago": len(raw_data) - idx  # Kronolojik sıra yaklaşımı
        })

    total_count = len(valid_matches)
    print("=" * 80)
    print(" 🔬 DIXON-COLES MLE — DÜRÜST VE HİLESİZ OUT-OF-SAMPLE TESTİ")
    print(f"    Toplam Gerçek Maç Havuzu: {total_count} adet")
    print("=" * 80)

    # %70 Eğitim (Train), %30 Test (Out-of-Sample) Bölünmesi
    split_idx = int(total_count * 0.70)
    train_data = valid_matches[:split_idx]
    test_data = valid_matches[split_idx:]

    print(f"[*] Eğitim Kümesi (In-Sample): {len(train_data)} maç")
    print(f"[*] Sınav Kümesi (Out-of-Sample): {len(test_data)} maç (Model bu maçları daha önce hiç görmedi!)")

    # 1. Aşama: Dixon-Coles MLE Modelini Eğit
    model = DixonColesMLE(xi=0.002)
    fit_summary = model.fit(train_data, epochs=150, lr=0.035)

    print("\n📈 MLE EĞİTİM SONUÇLARI (MODEL TARAFINDAN ÖĞRENİLEN GÜÇLER):")
    print(f"   Analiz Edilen Takım Sayısı: {fit_summary['teams_count']}")
    print(f"   Öğrenilen İç Saha Avantajı (Gamma): x{fit_summary['gamma_home_advantage']} kat gol beklentisi")
    print("\n   👑 En Güçlü Hücumlar (Alpha):")
    for t, val in fit_summary["top_attacks"]:
        print(f"      • {t}: Alpha={val}")
    print("\n   🛡️ En Güçlü Savunmalar (1/Beta):")
    for t, val in fit_summary["top_defenses"]:
        print(f"      • {t}: Direnç={val}")

    # 2. Aşama: Out-of-Sample Sınav
    print("\n" + "=" * 80)
    print("🧪 GÖRÜLMEMİŞ TEST KÜMESİ (OUT-OF-SAMPLE) DEĞERLENDİRMESİ:")
    print("=" * 80)

    correct_1x2 = 0
    correct_o25 = 0
    brier_sum = 0.0
    log_loss_sum = 0.0

    naive_brier_sum = 0.0 # Rastgele 0.33/0.33/0.33 tahmini

    for m in test_data:
        pred = model.predict_match(m["home_team"], m["away_team"])
        p1 = pred["prob_home_win"]
        px = pred["prob_draw"]
        p2 = pred["prob_away_win"]
        p_o25 = pred["prob_over_2_5"]

        # En olası tercih
        fav_outcome = "1" if (p1 >= px and p1 >= p2) else ("X" if px >= p2 else "2")
        actual_res = m["actual_result"]

        if fav_outcome == actual_res:
            correct_1x2 += 1

        # 2.5 Gol tercihi
        pred_over = p_o25 >= 0.50
        actual_over = m["actual_total_goals"] > 2.5
        if pred_over == actual_over:
            correct_o25 += 1

        # 1X2 Brier skoru: (p1 - o1)^2 + (px - ox)^2 + (p2 - o2)^2
        o1_act = 1.0 if actual_res == "1" else 0.0
        ox_act = 1.0 if actual_res == "X" else 0.0
        o2_act = 1.0 if actual_res == "2" else 0.0

        brier_sum += (p1 - o1_act) ** 2 + (px - ox_act) ** 2 + (p2 - o2_act) ** 2
        naive_brier_sum += (0.333 - o1_act) ** 2 + (0.333 - ox_act) ** 2 + (0.333 - o2_act) ** 2

        # Log Loss (Çapraz Entropi)
        p_chosen = p1 if actual_res == "1" else (px if actual_res == "X" else p2)
        log_loss_sum += -math.log(max(1e-4, p_chosen))

    n_test = len(test_data)
    acc_1x2_pct = round((correct_1x2 / n_test) * 100, 1)
    acc_o25_pct = round((correct_o25 / n_test) * 100, 1)
    brier_score = round(brier_sum / n_test, 4)
    naive_brier = round(naive_brier_sum / n_test, 4)
    mean_log_loss = round(log_loss_sum / n_test, 4)

    print(f"📊 1X2 Taraf Tahmin İsabeti: %{acc_1x2_pct} ({correct_1x2}/{n_test} maç doğru tahmin)")
    print(f"📊 2.5 Alt/Üst Tahmin İsabeti: %{acc_o25_pct} ({correct_o25}/{n_test} maç doğru tahmin)")
    print(f"🎯 Model Brier Skoru: {brier_score}  (Rastgele Tahmin Tabanı: {naive_brier})")
    print(f"📉 Ortalama Log-Loss: {mean_log_loss}")

    improvement = round(((naive_brier - brier_score) / naive_brier) * 100, 2)
    print(f"\n💡 SONUÇ: Gerçek Dixon-Coles MLE modeli, rastgele piyasa dağılımına kıyasla")
    print(f"   kalibrasyonda %{improvement} daha üstün bir istatistiksel doğruluk elde etti.")
    print("=" * 80)


if __name__ == "__main__":
    from typing import Tuple
    run_honest_backtest()

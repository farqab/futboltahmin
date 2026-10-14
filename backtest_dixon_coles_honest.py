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
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

from dixon_coles_mle import DixonColesMLE


def parse_score(score_str: str) -> Optional[Tuple[int, int]]:
    """Skoru ayrıştırır; bozuk skorları 0-0 diye göstermeyip reddeder."""
    if not isinstance(score_str, str) or "-" not in score_str:
        return None
    parts = score_str.replace(" ", "").split("-")
    try:
        if len(parts) != 2:
            return None
        home, away = int(parts[0]), int(parts[1])
        if home < 0 or away < 0:
            return None
        return home, away
    except (ValueError, IndexError):
        return None


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
        parsed_score = parse_score(item.get("actual_score"))
        if parsed_score is None:
            continue
        hg, ag = parsed_score
        h_name = item.get("home_name", "").strip()
        a_name = item.get("away_name", "").strip()
        raw_date = item.get("utc_date") or item.get("date")
        if not h_name or not a_name or not raw_date:
            continue
        try:
            if isinstance(raw_date, str) and raw_date.endswith("Z"):
                match_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            elif isinstance(raw_date, str) and len(raw_date) == 8 and raw_date.isdigit():
                match_date = datetime.strptime(raw_date, "%Y%m%d")
            else:
                match_date = datetime.fromisoformat(str(raw_date))
            # Naive/aware datetime karşılaştırmalarını engellemek için UTC-naive tut.
            if match_date.tzinfo is not None:
                match_date = match_date.astimezone(__import__("datetime").timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError, OverflowError):
            continue

        valid_matches.append({
            "id": item.get("id", idx),
            "home_team": h_name,
            "away_team": a_name,
            "home_goals": hg,
            "away_goals": ag,
            "actual_result": "1" if hg > ag else ("X" if hg == ag else "2"),
            "actual_total_goals": hg + ag,
            "_match_date": match_date
        })

    # Sıra indeksine güvenme: gerçek maç tarihine göre sırala.
    valid_matches.sort(key=lambda m: m["_match_date"])

    total_count = len(valid_matches)
    print("=" * 80)
    print(" 🔬 DIXON-COLES MLE — DÜRÜST VE HİLESİZ OUT-OF-SAMPLE TESTİ")
    print(f"    Toplam Gerçek Maç Havuzu: {total_count} adet")
    print("=" * 80)

    # Aynı gündeki maçları train ve test'e bölme; böylece gün içi gelecek sızıntısı azalır.
    unique_dates = sorted({m["_match_date"].date() for m in valid_matches})
    if len(unique_dates) < 2:
        raise ValueError("Kronolojik backtest için en az iki farklı maç tarihi gerekli.")
    split_date_idx = min(max(int(len(unique_dates) * 0.70), 1), len(unique_dates) - 1)
    test_start_date = unique_dates[split_date_idx]
    train_data = [m.copy() for m in valid_matches if m["_match_date"].date() < test_start_date]
    test_data = [m.copy() for m in valid_matches if m["_match_date"].date() >= test_start_date]

    if not train_data or not test_data:
        raise ValueError("Tarih bazlı train/test bölünmesi boş küme oluşturdu.")

    # Ağırlıklandırma için sadece eğitim dönemindeki en yeni maç referans alınır.
    latest_train_date = max(m["_match_date"] for m in train_data)
    for m in train_data:
        m["days_ago"] = max(0, (latest_train_date - m["_match_date"]).days)
    for m in train_data + test_data:
        m.pop("_match_date", None)

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

    naive_brier_sum = 0.0 # Eşit olasılıklı referans (market baseline değildir)

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
    print(f"\n💡 Eşit olasılıklı referansa göre Brier değişimi: %{improvement}.")
    print("   Bu karşılaştırma piyasa baseline'ı değildir ve tek başına kârlılık kanıtlamaz.")
    print("=" * 80)


if __name__ == "__main__":
    from typing import Tuple
    run_honest_backtest()

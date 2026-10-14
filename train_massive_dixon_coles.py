"""
train_massive_dixon_coles.py — 6 Büyük Lig İçin Kitlesel Dixon-Coles MLE Eğitimi
================================================================================
Bu script:
1. Premier Lig, La Liga, Serie A, Bundesliga, Ligue 1 ve Süper Lig'in
   son 4-5 sezonluk (2021-2026) 8.980+ gerçek maçını lig bazında ayrı ayrı modeller.
2. Her ligin kendine has:
   - Gol ortalaması ve hücum güçleri (alpha)
   - Savunma dirençleri (beta)
   - İç saha avantajı (gamma)
   - 0-0, 1-1 düşük skor bağımlılığı (rho)
   saf MLE ve Adam optimizasyonuyla hesaplanır.
3. Eğitilmiş olgun katsayıları 'dixon_coles_weights.json' olarak kaydeder.
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

from historical_data_sync import load_training_matches
from dixon_coles_mle import DixonColesMLE

WEIGHTS_FILE = os.path.join(PROJECT_DIR, "dixon_coles_weights.json")


def train_league_models(min_season_year: int = 2021) -> Dict[str, Any]:
    print("=" * 80)
    print(" 🚀 KİTLESEL DIXON-COLES MLE EĞİTİM MOTORU (8,980+ MAÇ)")
    print(f"    Eğitim Sezonları: {min_season_year} - 2026 | Çıktı: {WEIGHTS_FILE}")
    print("=" * 80)

    all_matches = load_training_matches(min_season_year=min_season_year)
    if not all_matches:
        print("[!] Eğitim maçı bulunamadı!")
        return {}

    # Liglere göre ayır
    matches_by_league: Dict[str, List[Dict[str, Any]]] = {}
    for m in all_matches:
        l = m["league"]
        matches_by_league.setdefault(l, []).append(m)

    trained_payload = {
        "trained_at": datetime.now().isoformat(),
        "total_matches_trained": len(all_matches),
        "leagues": {}
    }

    for league, m_list in matches_by_league.items():
        print(f"\n[*] {league} Modelleniyor ({len(m_list)} gerçek maç)...")

        # Kronolojik sıra yaklaşımı (en yeni maçlar en yüksek ağırlık)
        m_list.sort(key=lambda x: str(x.get("date", "")))
        total_m = len(m_list)
        for idx, item in enumerate(m_list):
            item["days_ago"] = (total_m - idx) * 0.8  # Yapay kronolojik zaman sönümleme

        model = DixonColesMLE(xi=0.0015)
        fit_res = model.fit(m_list, epochs=200, lr=0.035)

        # Takım ağırlıklarını sözlük olarak paketle
        team_weights = {}
        for idx, t_name in enumerate(model.teams):
            team_weights[t_name] = {
                "alpha_attack": round(float(model.alpha[idx]), 4),
                "beta_defense": round(float(model.beta[idx]), 4),
                "defense_strength": round(1.0 / max(0.1, float(model.beta[idx])), 4)
            }

        trained_payload["leagues"][league] = {
            "matches_count": total_m,
            "teams_count": fit_res["teams_count"],
            "gamma_home_advantage": fit_res["gamma_home_advantage"],
            "rho": fit_res["rho"],
            "top_attacks": fit_res["top_attacks"],
            "top_defenses": fit_res["top_defenses"],
            "teams": team_weights
        }

        print(f"   ✓ Gamma (İç Saha Avantajı): x{fit_res['gamma_home_advantage']}")
        print(f"   ✓ En Güçlü Hücumlar: {', '.join([f'{t[0]} ({t[1]})' for t in fit_res['top_attacks'][:3]])}")
        print(f"   ✓ En Güçlü Savunmalar: {', '.join([f'{t[0]} ({t[1]})' for t in fit_res['top_defenses'][:3]])}")

    # Diske kaydet
    with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump(trained_payload, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ TÜM LİGLER EĞİTİLDİ VE KAYDEDİLDİ: {WEIGHTS_FILE}")
    print("=" * 80)

    return trained_payload


if __name__ == "__main__":
    train_league_models()

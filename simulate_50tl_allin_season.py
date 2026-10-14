"""
simulate_50tl_allin_season.py — 50 TL Kasa & 50 TL Bahis Sezon Simülasyonu
==========================================================================
Kullanıcı Senaryosu:
- Başlangıç Kasası: 50 TL
- Bahis Başı Tutar: 50 TL (İlk bahiste kasanın %100'ü masada!)
- Kural:
  * İlk bahis kaybederse kasa 0 TL olur ve oyun biter (İFLAS).
  * İlk bahis kazanırsa, bakiye 50 TL üzerinde kaldığı sürece sonraki +EV maçlarına 50 TL ile devam edilir.
  * Kasa < 50 TL olduğunda bahis yapılamaz.
- Kapsam: Bu sezonun gerçek maçları ve Bet365/Pinnacle oranları.
"""

import os
import sys
import csv
import json
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

from calibrate_and_test_model import load_weights_for_league, predict_with_weights
from value_detector import find_value_bets, strip_margin_1x2
from historical_data_sync import clean_team_name


def run_50tl_simulation(season_target: str = "2024-25"):
    print("=" * 80)
    print(f" 🎲 50 TL KASA VE 50 TL BAHİS SİMÜLASYONU (SEZON: {season_target})")
    print("    Başlangıç Kasası: 50.00 TL | Sabit Bahis: 50.00 TL")
    print("    Kural: İlk bahis kaybederse anında İFLAS (0 TL). Kazanırsa devam.")
    print("=" * 80)

    # 1. Ağırlıkları yükle
    league_weights = load_weights_for_league("Premier League")

    # 2. Maçları ve skorları eşle
    scores_path = os.path.join(PROJECT_DIR, "data", "historical", "premier_league_scores.csv")
    odds_path = os.path.join(PROJECT_DIR, "data", "historical", "premier_league_with_odds.csv")

    scores_by_id = {}
    with open(scores_path, "r", encoding="utf-8") as fs:
        for r in csv.DictReader(fs):
            if r.get("match_id"):
                scores_by_id[r["match_id"]] = r

    season_matches = []
    with open(odds_path, "r", encoding="utf-8") as fo:
        for r in csv.DictReader(fo):
            if r.get("season") != season_target:
                continue
            m_id = r.get("match_id")
            sc = scores_by_id.get(m_id, {})
            fthg = sc.get("fthg", "")
            ftag = sc.get("ftag", "")
            if fthg == "" or ftag == "":
                continue

            o1 = r.get("bet365_1x2_home") or r.get("pinnacle_1x2_home")
            ox = r.get("bet365_1x2_draw") or r.get("pinnacle_1x2_draw")
            o2 = r.get("bet365_1x2_away") or r.get("pinnacle_1x2_away")
            if not o1 or not ox or not o2:
                continue

            try:
                fo1, fox, fo2 = float(o1), float(ox), float(o2)
                if fo1 <= 1.0 or fox <= 1.0 or fo2 <= 1.0:
                    continue
            except:
                continue

            season_matches.append({
                "match_id": m_id,
                "date": r.get("date"),
                "home_name": clean_team_name(r.get("home_team")),
                "away_name": clean_team_name(r.get("away_team")),
                "home_goals": int(float(fthg)),
                "away_goals": int(float(ftag)),
                "actual_result": "1" if int(float(fthg)) > int(float(ftag)) else ("X" if int(float(fthg)) == int(float(ftag)) else "2"),
                "odds": {"1": fo1, "X": fox, "2": fo2}
            })

    # Kronolojik sırala
    season_matches.sort(key=lambda x: str(x.get("date", "")))
    print(f"[*] Toplam Değerlendirilecek Maç: {len(season_matches)} adet\n")

    # 3. +EV fırsatlarını kronolojik tespit et
    bet_candidates = []
    for m in season_matches:
        pred = predict_with_weights(league_weights, m["home_name"], m["away_name"])
        eval_res = find_value_bets(m, pred, model_weight=0.25, min_ev=0.02)
        if eval_res.get("status") == "ANALYZED" and eval_res.get("best_bet"):
            bb = eval_res["best_bet"]
            bet_candidates.append({
                "date": m["date"],
                "match": f"{m['home_name']} vs {m['away_name']}",
                "choice": bb["market"],
                "odd": bb["odd"],
                "ev": bb["ev"],
                "actual_result": m["actual_result"]
            })

    print(f"[+] Modelin sezonda tespit ettiği pozitif değerli (+EV) maç sayısı: {len(bet_candidates)} adet\n")

    if not bet_candidates:
        print("[!] +EV maç bulunamadı.")
        return

    # 4. Kasa Simülasyonu
    bankroll = 50.0
    initial_bankroll = 50.0
    stake = 50.0
    bet_step = 0
    history = []

    print("-" * 80)
    print(f"{'Adım':<5} | {'Tarih':<10} | {'Maç':<30} | {'Tercih':<18} | {'Oran':<5} | {'Durum':<8} | {'Kasa (TL)'}")
    print("-" * 80)

    for b in bet_candidates:
        if bankroll < stake:
            print(f"\n🛑 KASA YETERSİZ ({bankroll:.2f} TL < 50 TL Asgari Bahis). OYUN BİTTİ.")
            break

        bet_step += 1
        choice_str = b["choice"]
        odd = b["odd"]
        act = b["actual_result"]

        # Kazanma kontrolü
        won = False
        if "MS 1" in choice_str and act == "1":
            won = True
        elif "MS X" in choice_str and act == "X":
            won = True
        elif "MS 2" in choice_str and act == "2":
            won = True

        if won:
            profit = stake * (odd - 1.0)
            bankroll += profit
            status_str = "✅ KAZANDI"
        else:
            bankroll -= stake
            status_str = "❌ YATTI"

        history.append({
            "step": bet_step,
            "match": b["match"],
            "choice": choice_str,
            "odd": odd,
            "won": won,
            "bankroll": bankroll
        })

        print(f"{bet_step:<5} | {b['date']:<10} | {b['match']:<30} | {choice_str[:17]:<18} | {odd:<5.2f} | {status_str:<8} | {bankroll:>8.2f} TL")

        if not won and bet_step == 1:
            print("\n💥 İLK BAHİS YATTI! 50 TL KASA TAMAMEN SIFIRLANDI (İFLAS).")
            break

        if bankroll <= 0:
            print(f"\n💥 KASA SIFIRLANDI ({bankroll:.2f} TL). İFLAS.")
            break

    print("-" * 80)
    print("\n📊 SİMÜLASYON RAPORU:")
    print(f"   • Başlangıç Kasası: {initial_bankroll:.2f} TL")
    print(f"   • Son Bakiye:       {bankroll:.2f} TL")
    print(f"   • Net Kâr / Zarar:  {bankroll - initial_bankroll:+.2f} TL")
    print(f"   • Yapılan Bahis:    {bet_step} adet")
    wins = sum(1 for h in history if h["won"])
    print(f"   • Kazanan / Yatan:  {wins} Kazandı / {bet_step - wins} Yattı")
    print("=" * 80)


if __name__ == "__main__":
    run_50tl_simulation("2024-25")

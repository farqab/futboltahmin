"""
backtest_pnl_simulation.py — Gerçek Out-of-Sample Kasa & PnL Simülasyonu
========================================================================
Bu script:
1. 216 gerçek maçlık veritabanından ilk 151 maçı eğitim olarak kullanır (Dixon-Coles).
2. Kalan 65 görmediği maçta (Out-of-Sample) +EV değer tespiti yapar.
3. 1/4 Fractional Kelly ve %1.5 kasa tavanı ile gerçek kasa simülasyonu koşturur.
4. Sonuçta net kazanç/kayıp (TL), ROI, İsabet Oranı ve Drawdown değerlerini çıkarır.
"""

import os
import sys
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

from dixon_coles_mle import DixonColesMLE
from value_detector import find_value_bets
from kelly_risk_manager import KellyRiskManager


def parse_score(score_str: str):
    if not score_str or "-" not in score_str:
        return 0, 0
    parts = score_str.replace(" ", "").split("-")
    try:
        return int(parts[0]), int(parts[1])
    except:
        return 0, 0


def run_pnl_backtest(initial_bankroll: float = 2000.0):
    dataset_path = os.path.join(PROJECT_DIR, "backtest_gecen_sezon_sonuclari.json")
    if not os.path.exists(dataset_path):
        print(f"[!] Veri kümesi bulunamadı: {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 1. Veri temizleme ve sıralama
    valid_matches = []
    for idx, item in enumerate(raw_data):
        score_str = item.get("actual_score")
        if not score_str:
            continue
        hg, ag = parse_score(score_str)
        h_name = item.get("home_name", "").strip()
        a_name = item.get("away_name", "").strip()
        h_odd = item.get("h_odd")
        d_odd = item.get("d_odd")
        a_odd = item.get("a_odd")

        if not h_name or not a_name or not h_odd or not d_odd or not a_odd:
            continue

        try:
            h_odd, d_odd, a_odd = float(h_odd), float(d_odd), float(a_odd)
        except:
            continue

        actual_res = "1" if hg > ag else ("X" if hg == ag else "2")
        total_goals = hg + ag

        valid_matches.append({
            "id": item.get("id", idx),
            "home_name": h_name,
            "away_name": a_name,
            "home_team": h_name,
            "away_team": a_name,
            "home_goals": hg,
            "away_goals": ag,
            "actual_result": actual_res,
            "actual_total_goals": total_goals,
            "odds": {
                "1": h_odd,
                "X": d_odd,
                "2": a_odd
            },
            "days_ago": len(raw_data) - idx
        })

    total_count = len(valid_matches)
    split_idx = int(total_count * 0.70)
    train_data = valid_matches[:split_idx]
    test_data = valid_matches[split_idx:]

    print("=" * 80)
    print(" 💰 GERÇEK OUT-OF-SAMPLE KASA VE KAZANÇ (PnL) SİMÜLASYONU")
    print(f"    Başlangıç Kasası: {initial_bankroll:,.2f} TL | Minimum Bahis: 10 TL")
    print(f"    Eğitim (In-Sample): {len(train_data)} maç | Test (Out-of-Sample): {len(test_data)} maç")
    print("=" * 80)

    # 2. Dixon-Coles MLE Modelini Eğit
    model = DixonColesMLE(xi=0.002)
    model.fit(train_data, epochs=150, lr=0.035)

    # 3. Kasa ve Risk Yöneticisi
    risk_manager = KellyRiskManager(
        initial_bankroll=initial_bankroll,
        kelly_fraction=0.25,
        max_stake_pct=0.015,
        min_stake=10.0
    )

    bet_history = []
    total_staked = 0.0
    peak_bankroll = initial_bankroll
    max_drawdown_pct = 0.0

    print("\n[+] Görmemiş 65 Test Maçında Değer (+EV) Taraması Yapılıyor...\n")

    for m in test_data:
        pred = model.predict_match(m["home_team"], m["away_team"])
        
        # +EV Arama
        eval_res = find_value_bets(match=m, model_output=pred, model_weight=0.25)
        
        if eval_res.get("status") != "ANALYZED":
            continue

        best_bet = eval_res.get("best_bet")
        if not best_bet:
            continue

        market_str = best_bet["market"]  # "MS 1 (Team)", "MS X (Beraberlik)", "MS 2 (Team)"
        odd = best_bet["odd"]
        win_prob = best_bet["blended_prob"]
        ev = best_bet["ev"]

        # Kelly payı hesapla
        stake_info = risk_manager.calculate_stake(
            odd=odd,
            win_prob=win_prob,
            ev=ev
        )

        stake = stake_info.get("recommended_stake", 0.0)
        if stake <= 0:
            continue

        # Bahis Oynandı
        total_staked += stake
        won = False
        
        if "MS 1" in market_str:
            won = (m["actual_result"] == "1")
        elif "MS X" in market_str:
            won = (m["actual_result"] == "X")
        elif "MS 2" in market_str:
            won = (m["actual_result"] == "2")
        elif "2.5 Üst" in market_str:
            won = (m["actual_total_goals"] > 2.5)
        elif "2.5 Alt" in market_str:
            won = (m["actual_total_goals"] < 2.5)

        pnl = stake * (odd - 1.0) if won else -stake

        risk_manager.record_bet_outcome(stake=stake, won=won, odd=odd)
        curr_bankroll = risk_manager.current_bankroll

        # Peak ve Drawdown takibi
        if curr_bankroll > peak_bankroll:
            peak_bankroll = curr_bankroll
        dd = (peak_bankroll - curr_bankroll) / peak_bankroll * 100
        if dd > max_drawdown_pct:
            max_drawdown_pct = dd

        status_icon = "✅ KAZANDI" if won else "❌ KAYBETTİ"
        bet_history.append({
            "match": f"{m['home_team']} vs {m['away_team']}",
            "choice": market_str,
            "odd": odd,
            "ev_pct": round(ev * 100, 2),
            "stake": stake,
            "won": won,
            "pnl": pnl,
            "bankroll": curr_bankroll
        })

        print(f"  {status_icon} | {m['home_team']} vs {m['away_team']} | {market_str} @ {odd:.2f} | "
              f"Yatırılan: {stake:.1f} TL | PnL: {pnl:+.1f} TL | Kasa: {curr_bankroll:.1f} TL")

    print("\n" + "=" * 80)
    print(" 📊 SİMÜLASYON PERFORMANS ÖZETİ")
    print("=" * 80)
    total_bets = len(bet_history)
    wins = sum(1 for b in bet_history if b["won"])
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0.0
    net_profit = risk_manager.current_bankroll - initial_bankroll
    roi_pct = (net_profit / total_staked * 100) if total_staked > 0 else 0.0

    print(f"Toplam Analiz Edilen Test Maçı: {len(test_data)}")
    print(f"Değer (+EV) Bulunup Oynanan Bahis: {total_bets} maç (Pas Geçilen: {len(test_data) - total_bets})")
    print(f"Kazanan Bahis: {wins} | Kaybeden: {total_bets - wins}")
    print(f"Kazanma Oranı (Win Rate): %{win_rate:.1f}")
    print(f"Toplam Yatırılan Tutar: {total_staked:.2f} TL")
    print(f"Net Kâr / Zarar (PnL): {net_profit:+.2f} TL")
    print(f"ROI (Yatırım Getirisi): %{roi_pct:+.2f}")
    print(f"Bitiş Kasası: {risk_manager.current_bankroll:.2f} TL (Başlangıç: {initial_bankroll:.2f} TL)")
    print(f"Maksimum Drawdown (Kasa Düşüşü): %{max_drawdown_pct:.2f}")
    print("=" * 80)


if __name__ == "__main__":
    run_pnl_backtest(initial_bankroll=2000.0)

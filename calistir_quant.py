"""
calistir_quant.py — Dixon-Coles & +EV Profesyonel Karar Çalıştırıcısı
=====================================================================
Kullanım:
    python calistir_quant.py [TARIH (Örn: 20260919)] [--ledger]

Özellikler:
1. 'No Data, No Bet' kuralı ile sahte oranları eler.
2. Dixon-Coles (1997) bivariate modeli ve Elo ile gerçek gol olasılıklarını çıkarır.
3. Nesine oranlarından marjı ayıklayıp sadece pozitif beklenen değerli (+EV) maçları seçer.
4. Kesirli Kelly (%1.5 tavan) ile her maç için optimal TL tutarını hesaplar.
5. MBS 1 olan maçlarda tekli, MBS 2 olanlarda en düşük varyanslı 2'li portföyü önerir.
6. Bahis Defteri (Betting Ledger) kâr/zarar ve CLV metriklerini raporlar.
"""

import os
import sys
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

from data_collector import fetch_real_matches_for_date
from core_pipeline import run_quantitative_pipeline, print_pipeline_report
from betting_ledger import BettingLedger


def main():
    date_arg = None  # Varsayılan: Canlı / Güncel ESPN Bülteni (Gerçek DraftKings Oranları ile)
    record_ledger = "--ledger" in sys.argv

    for arg in sys.argv[1:]:
        if arg.lower() in ["live", "today", "canli"]:
            date_arg = None
        elif arg.isdigit() and len(arg) == 8:
            date_arg = arg

    date_label = date_arg if date_arg else "Canlı / Güncel ESPN Bülteni"
    print(f"[*] ESPN API üzerinden {date_label} maçları çekiliyor...")
    matches = fetch_real_matches_for_date(date_arg)

    if not matches:
        print(f"[!] {date_arg} tarihinde maç bulunamadı.")
        return

    # Boru hattını çalıştır
    result = run_quantitative_pipeline(matches, record_to_ledger=record_ledger, bankroll=1000.0)
    print_pipeline_report(result)

    # Defter özetini bas
    perf = BettingLedger.get_performance_summary()
    print("\n" + "=" * 80)
    print("📈 GÜNCEL BAHİS DEFTERİ (BETTING LEDGER) VE METRİKLER:")
    if perf.get("status") == "NO_SETTLED_BETS":
        print(f"   ℹ️ {perf['message']}")
    else:
        print(f"   Toplam Sonuçlanan Bahis: {perf['total_settled_bets']} (Kazanılan: {perf['won']}, Kaybedilen: {perf['lost']})")
        print(f"   İsabet Oranı: %{perf['win_rate_pct']} | Toplam Yatırılan: {perf['total_staked']} TL | Net PnL: {perf['total_pnl']} TL (ROI: %{perf['roi_yield_pct']})")
        print(f"   Kapanış Oranı Değeri (CLV): %{perf['avg_clv_pct']} -> Durum: {perf['clv_status']}")
        print(f"   Model Brier Skoru: {perf['brier_score']} -> Değerlendirme: {perf['brier_evaluation']}")
    print("=" * 80)


if __name__ == "__main__":
    main()

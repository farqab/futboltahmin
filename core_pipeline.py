"""
core_pipeline.py — Profesyonel Niceliksel Bahis ve Karar Boru Hattı
===================================================================
Tüm dağınık scriptleri ve sahte varsayımları ortadan kaldıran tekil ana hat:

AKIŞ:
1. Veri Kabulü ve Doğrulama ("No Data, No Bet" kuralı).
2. Dixon-Coles Bivariate Poisson ve Dinamik Elo Simülasyonu.
3. Gerçek Piyasa Marjı Sökme ve Değer Tespiti (+EV).
4. Kesirli Kelly Kasa Paylaştırması (%1.5 Sert Tavan).
5. MBS (Minimum Bahis Sayısı) Optimizasyonu (Mümkünse Tekli, Zorunluysa 2'li).
6. Bahis Defteri Entegrasyonu (CLV ve Kalibrasyon Takibi).
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Konsol UTF-8 desteği
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

from dixon_coles_model import simulate_dixon_coles
from value_detector import find_value_bets, is_dummy_or_missing_odds
from kelly_risk_manager import KellyRiskManager, risk_engine
from betting_ledger import BettingLedger


def run_quantitative_pipeline(
    matches: List[Dict[str, Any]],
    record_to_ledger: bool = False,
    bankroll: float = 1000.0
) -> Dict[str, Any]:
    """
    Tüm maç havuzunu Dixon-Coles, +EV ve Kelly kriterlerinden geçirir.
    """
    t0 = time.time()
    risk_mgr = KellyRiskManager(initial_bankroll=bankroll)

    analyzed_matches = []
    rejected_matches = []
    all_value_bets = []

    print("=" * 80)
    print(" 🎯 NICELİKSEL FUTBOL TAHMİN AI — DIXON-COLES & +EV DEĞER BORU HATTI")
    print(f"    Başlangıç Kasası: {bankroll:,.2f} TL | Kural: No Data No Bet | Model: Dixon-Coles")
    print("=" * 80)

    for m in matches:
        home = m.get("home_name", "Home")
        away = m.get("away_name", "Away")
        match_title = f"{home} vs {away}"
        odds = m.get("odds", {})

        # 1. Aşama: Veri Güvenliği
        is_dummy, reason = is_dummy_or_missing_odds(odds)
        if is_dummy:
            rejected_matches.append({
                "match": match_title,
                "league": m.get("league"),
                "reason": reason
            })
            continue

        # 2. Aşama: Dixon-Coles Modeli
        dc_result = simulate_dixon_coles(m)

        # 3. Aşama: +EV Değer Tespiti
        val_result = find_value_bets(m, dc_result)

        if val_result.get("status") == "REJECTED_NO_DATA":
            rejected_matches.append({
                "match": match_title,
                "league": m.get("league"),
                "reason": val_result.get("reason")
            })
            continue

        m_pack = {
            "match": match_title,
            "league": m.get("league"),
            "mbs": m.get("mbs", 1),
            "dixon_coles": dc_result,
            "bookmaker_margin_pct": val_result.get("bookmaker_margin"),
            "candidates": val_result.get("candidates", []),
            "value_bets": []
        }

        # 4. Aşama: Her Değerli Bahis İçin Kelly Hesaplaması
        for vb in val_result.get("value_bets", []):
            odd = vb["odd"]
            prob = vb["blended_prob"]
            ev = vb["ev"]

            stake_info = risk_mgr.calculate_stake(odd=odd, win_prob=prob, ev=ev)

            bet_entry = {
                "match": match_title,
                "league": m.get("league"),
                "market": vb["market"],
                "market_type": vb["market_type"],
                "odd": odd,
                "model_prob_pct": round(vb["model_prob"] * 100, 1),
                "market_fair_prob_pct": round(vb["market_fair_prob"] * 100, 1),
                "blended_prob_pct": round(prob * 100, 1),
                "ev_pct": round(ev * 100, 2),
                "recommended_stake": stake_info["recommended_stake"],
                "stake_pct": stake_info["stake_pct"],
                "mbs": m.get("mbs", 1),
                "is_smart_money_confirmed": vb.get("is_smart_money_confirmed", False),
                "smart_money_verdict": vb.get("global_intelligence", {}).get("verdict") or vb.get("smart_money", {}).get("verdict", "NEUTRAL"),
                "smart_money_reason": vb.get("global_intelligence", {}).get("rationale") or vb.get("smart_money", {}).get("reason", ""),
                "signals": vb.get("signals") or vb.get("global_intelligence", {}).get("signals", {})
            }

            m_pack["value_bets"].append(bet_entry)
            all_value_bets.append(bet_entry)

            # İsteğe bağlı deftere kayıt
            if record_to_ledger and stake_info["recommended_stake"] > 0:
                BettingLedger.record_bet(
                    match_name=match_title,
                    league=m.get("league", "Other"),
                    market=vb["market"],
                    taken_odd=odd,
                    model_prob=prob,
                    ev=ev,
                    stake=stake_info["recommended_stake"],
                    market_fair_prob=vb["market_fair_prob"]
                )

        analyzed_matches.append(m_pack)

    # Değerli bahisleri EV büyüklüğüne göre sırala
    all_value_bets.sort(key=lambda x: x["ev_pct"], reverse=True)

    # 5. Aşama: MBS'ye Göre Kupon / Portföy Oluşturma
    single_bets = [b for b in all_value_bets if b["mbs"] == 1]
    mbs2_bets = [b for b in all_value_bets if b["mbs"] >= 2]

    # Eğer MBS 2 zorunluysa, en yüksek EV'li en düşük varyanslı 2 maçı eşle
    mbs2_coupons = []
    if len(mbs2_bets) >= 2:
        b1 = mbs2_bets[0]
        b2 = mbs2_bets[1]
        combo_odd = round(b1["odd"] * b2["odd"], 2)
        combo_prob = round((b1["blended_prob_pct"] / 100) * (b2["blended_prob_pct"] / 100) * 100, 1)
        mbs2_coupons.append({
            "name": "MBS-2 Zorunlu Değer Kombinesi",
            "total_odds": combo_odd,
            "joint_prob_pct": combo_prob,
            "legs": [b1, b2]
        })

    elapsed = round(time.time() - t0, 2)

    return {
        "status": "COMPLETED",
        "elapsed_seconds": elapsed,
        "total_matches_checked": len(matches),
        "analyzed_matches_count": len(analyzed_matches),
        "analyzed_matches": analyzed_matches,
        "rejected_matches_count": len(rejected_matches),
        "total_value_bets_found": len(all_value_bets),
        "all_value_bets": all_value_bets,
        "single_value_bets": single_bets,
        "mbs2_coupons": mbs2_coupons,
        "rejected_matches": rejected_matches
    }


def print_pipeline_report(res: Dict[str, Any]):
    """Konsola profesyonel niceliksel rapor basar."""
    print("\n" + "=" * 80)
    print("📊 BORU HATTI DEĞERLENDİRME ÖZETİ:")
    print(f"   İncelenen Maç: {res['total_matches_checked']} | Analiz Edilen: {res['analyzed_matches_count']} | Reddedilen: {res['rejected_matches_count']}")
    print(f"   Bulunan Pozitif Değer (+EV) Fırsatı: {res['total_value_bets_found']}")
    print("=" * 80)

    if res["rejected_matches"]:
        print(f"\n⚠️ 'NO DATA, NO BET' GEREĞİ REDDEDİLENLER ({len(res['rejected_matches'])} maç):")
        for r in res["rejected_matches"][:4]:
            print(f"   🚫 {r['match']} ({r['league']}) -> Gerekçe: {r['reason']}")
        if len(res["rejected_matches"]) > 4:
            print(f"   ... ve {len(res['rejected_matches']) - 4} maç daha.")

    print("\n👑 EN YÜKSEK POZİTİF DEĞERLİ (+EV) BAHİSLER:")
    if not res["all_value_bets"]:
        print("   [!] Bugün piyasa marjı üzerinde istatistiksel üstünlük (+EV) sağlayan maç bulunamadı.")
        print("   💡 Profesyonel İlke: Değer yoksa bahis oynanmaz, kasa korunur.")
    else:
        for idx, vb in enumerate(res["all_value_bets"][:6], 1):
            print(f"\n{idx}. [{vb['league']}] {vb['match']}")
            print(f"   🎯 Tercih: {vb['market']} | Oran: {vb['odd']} (MBS: {vb['mbs']})")
            print(f"   📈 Model Olasılığı: %{vb['model_prob_pct']} | Piyasa Adil Olasılığı: %{vb['market_fair_prob_pct']} | Sentez: %{vb['blended_prob_pct']}")
            print(f"   💎 Beklenen Değer (+EV): +%{vb['ev_pct']} | 1/4 Kelly Payı: %{vb['stake_pct']} ({vb['recommended_stake']} TL)")
            if vb.get("is_smart_money_confirmed"):
                print(f"   🔥 SMART MONEY STEAM MOVE: {vb.get('smart_money_reason')}")

    if res.get("mbs2_coupons"):
        print("\n" + "=" * 80)
        print("🎟️ MBS 2 ZORUNLULUĞUNDA OLUŞTURULAN MİNİMAL VARYANS KOMBİNESİ:")
        for c in res["mbs2_coupons"]:
            print(f"   Toplam Oran: {c['total_odds']} | Bileşik Başarı İhtimali: %{c['joint_prob_pct']}")
            for leg in c["legs"]:
                print(f"   👉 {leg['match']} -> {leg['market']} (Oran: {leg['odd']}, EV: +%{leg['ev_pct']})")

    print("=" * 80)

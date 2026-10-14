"""
kelly_risk_manager.py — Kesirli Kelly Kriteri & Risk Yönetim Motoru
====================================================================
Finansal ve Kasa Yönetimi Prensipleri:
1. KESİRLİ KELLY (1/4 Kelly): Aşırı varyansı ve kasa erimesini önlemek için
   tam Kelly yerine 1/4 (0.25) katsayısı uygulanır.
2. SERT TAVAN (%1.5): Tek bir bahse kasanın en fazla %1.5'i yatırılabilir.
3. TELAFİ / MARTINGALE YASAĞI: Kayıptan sonra bahis miktarını artırma davranışı
   matematiksel olarak intihardır; sistem asla kayıp kovalamaz.
4. DEVRE KESİCİ (Circuit Breaker): Günlük %5 veya haftalık %15 kayıp sınırına
   ulaşıldığında sistem otomatik olarak durur ve yeni bahis onaylamaz.
"""

from typing import Dict, Any, Tuple


class KellyRiskManager:
    """
    Kasa yönetimi, kesirli Kelly hisselendirmesi ve drawdown kontrolü.
    """
    def __init__(
        self,
        initial_bankroll: float = 1000.0,
        kelly_fraction: float = 0.25,
        max_stake_pct: float = 0.015,     # Maksimum %1.5 tekil bahis sınırı
        min_stake: float = 10.0,          # Minimum bahis tutarı (TL)
        max_daily_drawdown_pct: float = 0.05,
        max_weekly_drawdown_pct: float = 0.15
    ):
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.kelly_fraction = kelly_fraction
        self.max_stake_pct = max_stake_pct
        self.min_stake = min_stake
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.max_weekly_drawdown_pct = max_weekly_drawdown_pct

        # Canlı takip sayaçları
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""

    def check_circuit_breaker(self) -> Tuple[bool, str]:
        """
        Kasa düşüş sınırlarını kontrol eder.
        """
        daily_loss_limit = self.current_bankroll * self.max_daily_drawdown_pct
        weekly_loss_limit = self.current_bankroll * self.max_weekly_drawdown_pct

        if self.daily_pnl <= -daily_loss_limit:
            self.circuit_breaker_active = True
            self.circuit_breaker_reason = f"GÜNLÜK DEVRE KESİCİ: Zarar {abs(self.daily_pnl):.2f} TL limitini ({daily_loss_limit:.2f} TL) aştı!"
            return True, self.circuit_breaker_reason

        if self.weekly_pnl <= -weekly_loss_limit:
            self.circuit_breaker_active = True
            self.circuit_breaker_reason = f"HAFTALIK DEVRE KESİCİ: Zarar {abs(self.weekly_pnl):.2f} TL limitini ({weekly_loss_limit:.2f} TL) aştı!"
            return True, self.circuit_breaker_reason

        return False, "Kasa güvenli"

    def calculate_stake(self, odd: float, win_prob: float, ev: float) -> Dict[str, Any]:
        """
        Kesirli Kelly formülüyle optimal bahis tutarını belirler.
        f* = (b * p - q) / b = EV / (odd - 1)
        stake = Bankroll * f* * fraction
        """
        # Devre kesici denetimi
        tripped, reason = self.check_circuit_breaker()
        if tripped:
            return {
                "status": "CIRCUIT_BREAKER_ACTIVE",
                "recommended_stake": 0.0,
                "stake_pct": 0.0,
                "reason": reason
            }

        if ev <= 0 or odd <= 1.0 or win_prob <= 0:
            return {
                "status": "NEGATIVE_EV_NO_BET",
                "recommended_stake": 0.0,
                "stake_pct": 0.0,
                "reason": f"Beklenen değer negatif veya sıfır (EV: {ev:.3f})"
            }

        b = odd - 1.0
        p = win_prob
        q = 1.0 - p

        full_kelly = (b * p - q) / b
        if full_kelly <= 0:
            return {
                "status": "ZERO_STAKE",
                "recommended_stake": 0.0,
                "stake_pct": 0.0,
                "reason": "Tam Kelly formülü sıfır verdi"
            }

        # 1/4 Kesirli Kelly
        frac_kelly = full_kelly * self.kelly_fraction

        # Sert tavan uygula (Kasanın maks %1.5'i)
        capped_fraction = min(frac_kelly, self.max_stake_pct)
        nominal_stake = round(self.current_bankroll * capped_fraction, 2)

        # DÜZELTME: Hesaplanan tutar minimum bahis sınırının (10 TL) altındaysa
        # ASLA yukarı yuvarlanmaz! 2.9 TL yerine 10 TL basmak kasa riskini 3.5 kat aşar.
        if nominal_stake < self.min_stake:
            return {
                "status": "BELOW_MIN_STAKE_NO_BET",
                "recommended_stake": 0.0,
                "stake_pct": 0.0,
                "full_kelly_pct": round(full_kelly * 100, 2),
                "fractional_kelly_pct": round(frac_kelly * 100, 2),
                "current_bankroll": self.current_bankroll,
                "reason": f"Hesaplanan Kelly tutarı ({nominal_stake:.2f} TL) asgari kupon tutarının ({self.min_stake:.2f} TL) altında. Kasa korundu."
            }

        return {
            "status": "APPROVED",
            "recommended_stake": nominal_stake,
            "stake_pct": round(capped_fraction * 100, 2),
            "full_kelly_pct": round(full_kelly * 100, 2),
            "fractional_kelly_pct": round(frac_kelly * 100, 2),
            "current_bankroll": self.current_bankroll,
            "reason": f"1/4 Kelly optimal risk (%{capped_fraction * 100:.2f} kasa payı)"
        }

    def record_bet_outcome(self, stake: float, won: bool, odd: float):
        """
        Sonuçlanan bahsi kasaya işler. Kesinlikle kayıp kovalamaz.
        """
        if won:
            net_profit = stake * (odd - 1.0)
            self.current_bankroll += net_profit
            self.daily_pnl += net_profit
            self.weekly_pnl += net_profit
        else:
            self.current_bankroll -= stake
            self.daily_pnl -= stake
            self.weekly_pnl -= stake

        # Devre kesiciyi güncelle
        self.check_circuit_breaker()


# Varsayılan risk yöneticisi nesnesi
risk_engine = KellyRiskManager()

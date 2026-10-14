"""
betting_ledger.py — Bahis Defteri, CLV Takibi ve Brier Kalibrasyon Ölçer
========================================================================
Profesyonel Bahisçi Kuralı:
Kısa vadeli kâr/zarar yanıltıcıdır; şans faktörü yüzlerce maça yayılır.
Gerçek avantajı (Edge) anlamanın iki altın standardı vardır:
1. CLV (Closing Line Value): Kapanış oranını yenebildik mi?
   CLV = (Alınan Oran / Kapanış Oranı) - 1.0
   Pozitif CLV uzun vadeli kârın en güçlü matematiksel öncülüdür.
2. BRIER SKORU: Modelin kalibrasyon doğruluğu.
   BS = 1/N * sum((p_t - o_t)^2). 0'a ne kadar yakınsa model o kadar mükemmeldir.
"""

import sqlite3
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "betting_ledger.db")


def init_ledger_db(db_path: Optional[str] = None):
    """SQLite veritabanını ve tablosunu hazırlar."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            match_name TEXT NOT NULL,
            league TEXT,
            market TEXT NOT NULL,
            taken_odd REAL NOT NULL,
            closing_odd REAL,
            model_prob REAL NOT NULL,
            market_fair_prob REAL,
            ev REAL NOT NULL,
            stake REAL NOT NULL,
            result TEXT DEFAULT 'PENDING',
            pnl REAL DEFAULT 0.0,
            clv REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()


init_ledger_db()


class BettingLedger:
    """Bahis defteri yöneticisi ve metrik raporlayıcı."""

    @staticmethod
    def record_bet(
        match_name: str,
        league: str,
        market: str,
        taken_odd: float,
        model_prob: float,
        ev: float,
        stake: float,
        market_fair_prob: Optional[float] = None,
        closing_odd: Optional[float] = None,
        db_path: Optional[str] = None
    ) -> int:
        """Yeni bir bahsi deftere kaydeder."""
        path = db_path or DB_PATH
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        clv = 0.0
        if closing_odd and closing_odd > 0:
            clv = round((taken_odd / closing_odd) - 1.0, 4)

        cursor.execute("""
            INSERT INTO bets (timestamp, match_name, league, market, taken_odd, closing_odd, model_prob, market_fair_prob, ev, stake, result, pnl, clv)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0.0, ?)
        """, (ts, match_name, league, market, taken_odd, closing_odd, model_prob, market_fair_prob, ev, stake, clv))

        bet_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return bet_id

    @staticmethod
    def settle_bet(bet_id: int, outcome: str, closing_odd: Optional[float] = None, db_path: Optional[str] = None):
        """
        Sonuçlanan bahsi günceller.
        outcome: 'WON', 'LOST', 'VOID'
        """
        path = db_path or DB_PATH
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        cursor.execute("SELECT taken_odd, stake FROM bets WHERE id = ?", (bet_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return

        taken_odd, stake = row
        pnl = 0.0
        if outcome == "WON":
            pnl = round(stake * (taken_odd - 1.0), 2)
        elif outcome == "LOST":
            pnl = round(-stake, 2)
        elif outcome == "VOID":
            pnl = 0.0

        if closing_odd and closing_odd > 0:
            clv = round((taken_odd / closing_odd) - 1.0, 4)
            cursor.execute("""
                UPDATE bets SET result = ?, pnl = ?, closing_odd = ?, clv = ? WHERE id = ?
            """, (outcome, pnl, closing_odd, clv, bet_id))
        else:
            cursor.execute("""
                UPDATE bets SET result = ?, pnl = ? WHERE id = ?
            """, (outcome, pnl, bet_id))

        conn.commit()
        conn.close()

    @staticmethod
    def get_performance_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Tüm sonuçlanmış bahislerin kâr/zarar, ROI, CLV ve Brier skoru dökümünü çıkarır.
        """
        path = db_path or DB_PATH
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        cursor.execute("SELECT model_prob, taken_odd, closing_odd, stake, result, pnl, clv FROM bets WHERE result IN ('WON', 'LOST', 'VOID')")
        rows = cursor.fetchall()
        conn.close()

        total_settled = len(rows)
        if total_settled == 0:
            return {
                "total_bets": 0,
                "status": "NO_SETTLED_BETS",
                "message": "Henüz sonuçlanmış kayıtlı bahis bulunmuyor."
            }

        wins = sum(1 for r in rows if r[4] == "WON")
        losses = sum(1 for r in rows if r[4] == "LOST")
        voids = sum(1 for r in rows if r[4] == "VOID")

        total_stake = sum(r[3] for r in rows)
        total_pnl = sum(r[5] for r in rows)
        roi_pct = round((total_pnl / total_stake) * 100, 2) if total_stake > 0 else 0.0
        win_rate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0.0

        # Kapanış Oranı Değeri (CLV)
        clv_values = [r[6] for r in rows if r[6] != 0.0 and r[2] is not None]
        avg_clv = round(sum(clv_values) / len(clv_values) * 100, 2) if clv_values else 0.0

        # Brier Skoru (Model kalibrasyonu)
        # BS = sum((p - outcome)^2) / N
        brier_sum = 0.0
        for r in rows:
            if r[4] in ["WON", "LOST"]:
                actual_num = 1.0 if r[4] == "WON" else 0.0
                brier_sum += (r[0] - actual_num) ** 2

        valid_for_brier = wins + losses
        brier_score = round(brier_sum / valid_for_brier, 4) if valid_for_brier > 0 else 0.25

        return {
            "total_settled_bets": total_settled,
            "won": wins,
            "lost": losses,
            "void": voids,
            "win_rate_pct": win_rate,
            "total_staked": round(total_stake, 2),
            "total_pnl": round(total_pnl, 2),
            "roi_yield_pct": roi_pct,
            "avg_clv_pct": avg_clv,
            "clv_status": "BEATING_CLOSING_LINE" if avg_clv > 0 else "UNDER_CLOSING_LINE",
            "brier_score": brier_score,
            "brier_evaluation": "EXCELLENT" if brier_score < 0.18 else ("GOOD" if brier_score < 0.22 else "POOR_CALIBRATION")
        }

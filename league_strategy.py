"""
league_strategy.py — Lig Bazlı Bahis Stratejisi Konfigürasyonu
==============================================================
TypeSafe AI'nın backtest analizi sonucunda verdiği kararlar:
  - Her lig için öncelikli bahis tipi
  - Güven eşiği
  - Sezon dinamik faktör ağırlığı (%77)
  - Banko güven eşiği: %60

202 Maçlık Backtest Verisi (22 Ağ - 19 Eyl 2026):
  Bundesliga: MS=%63-67 | 2.5=%70-80 | KG=%53-57
  Serie A:    MS=%39-58 | 2.5=%60-67 | KG=%70-73
  Ligue 1:    MS=%39-44 | 2.5=%44-56 | KG=%61-64
  La Liga:    MS=%44-53 | 2.5=%62-66 | KG=%59
  Premier:    MS=%40-45 | 2.5=%45-53 | KG=%52-53
  Süper Lig:  MS=%52-58 | 2.5=%55-58 | KG=%45-48
"""

from datetime import datetime

# ─── Lig Konfigürasyonları ───────────────────────────────────────
# TypeSafe AI kararı: evet_lig_bazli_farkli_strateji
LEAGUE_CONFIG = {
    "Bundesliga": {
        "primary_bet":          "ms_and_goals",     # MS + 2.5 her ikisi de güvenilir
        "confidence_threshold": 52,                  # Daha düşük eşik — model burada çok iyi
        "trust_ms":             True,
        "trust_2_5":            True,
        "trust_kg":             False,               # KG %53 — ortalama
        "banko_eligible":       True,                # Bu ligden banko çıkabilir
        "goal_bet_threshold":   60,                  # 2.5 Üst için min olasılık
        "emoji":                "🇩🇪",
        "note":                 "En güvenilir lig — hem MS hem 2.5 yüksek"
    },
    "Serie A": {
        "primary_bet":          "kg_focus",          # KG %73 — en güçlü sinyal
        "confidence_threshold": 55,
        "trust_ms":             True,                # Yeni sistemde %57.6!
        "trust_2_5":            True,                # %66.7
        "trust_kg":             True,                # %72.7 — ALTIN
        "banko_eligible":       True,
        "goal_bet_threshold":   58,
        "emoji":                "🇮🇹",
        "note":                 "KG motoru çok güçlü — hem KG hem 2.5 oyna"
    },
    "Ligue 1": {
        "primary_bet":          "kg_only",           # Sadece KG güvenilir (%64)
        "confidence_threshold": 60,                  # Daha seçici
        "trust_ms":             False,               # %39-44 — çok zayıf
        "trust_2_5":            False,               # Yeni sistemde %44.4 — çöktü
        "trust_kg":             True,                # %61-64 — güvenilir
        "banko_eligible":       False,               # MS bankosuna girme
        "goal_bet_threshold":   62,
        "emoji":                "🇫🇷",
        "note":                 "Sadece KG Var bahsi — MS ve 2.5 güvenilmez"
    },
    "Premier League": {
        "primary_bet":          "ultra_selective",   # Her şey zayıf
        "confidence_threshold": 65,                  # En yüksek eşik
        "trust_ms":             False,               # %40-45
        "trust_2_5":            False,               # %45-52
        "trust_kg":             False,               # %52-53
        "banko_eligible":       False,               # Bu ligden banko çıkmasın
        "goal_bet_threshold":   70,                  # Çok yüksek emin olunca
        "emoji":                "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "note":                 "En belirsiz lig — sadece aşırı güvenli oranlar"
    },
    "La Liga": {
        "primary_bet":          "goals_focus",       # 2.5 %62-66 güvenilir
        "confidence_threshold": 55,
        "trust_ms":             False,               # %44-53 — zayıf
        "trust_2_5":            True,                # %62-66 — güvenilir
        "trust_kg":             False,               # %59 — ortalama
        "banko_eligible":       True,                # Yüksek kalite deplasman kazanımları
        "goal_bet_threshold":   60,
        "emoji":                "🇪🇸",
        "note":                 "Gol tahmini güçlü — MS riskli, 2.5 güvenilir"
    },
    "Süper Lig": {
        "primary_bet":          "ms_focus",          # MS %52-58 — makul
        "confidence_threshold": 55,
        "trust_ms":             True,                # %52-58
        "trust_2_5":            True,                # %55-58
        "trust_kg":             False,               # %45-48 — zayıf
        "banko_eligible":       True,
        "goal_bet_threshold":   62,
        "emoji":                "🇹🇷",
        "note":                 "MS güvenilir — KG düşük, 2.5 orta"
    }
}

# ─── Sezon Dinamik Faktörü ───────────────────────────────────────
# TypeSafe AI kararı: %77 ağırlık → sezon başında çok daha seçici ol
SEASON_DYNAMIC_WEIGHT = 0.77

def get_season_week():
    """Sezon haftasını hesaplar (Ağustos başı = Hf0)."""
    season_start = datetime(datetime.now().year, 8, 1)
    if datetime.now().month < 8:
        season_start = datetime(datetime.now().year - 1, 8, 1)
    delta = (datetime.now() - season_start).days
    return max(1, delta // 7)

def get_dynamic_confidence_boost(base_threshold, league):
    """
    Sezon haftasına göre dinamik güven eşiği artışı.
    TypeSafe AI: %77 ağırlık → sezon başı 1-3. haftada eşik belirgin yükselir.
    """
    week = get_season_week()
    
    if week <= 3:
        # Sezon başı: form henüz oturmadı, +8 puan eşik artışı
        boost = int(8 * SEASON_DYNAMIC_WEIGHT)
    elif week <= 6:
        # Sezon ortası başlangıç: +4 puan
        boost = int(4 * SEASON_DYNAMIC_WEIGHT)
    else:
        # Sezon ortası: normal
        boost = 0
    
    return base_threshold + boost

def get_league_config(league_name):
    """Lig konfigürasyonunu döndürür. Bilinmeyen lig için varsayılan."""
    return LEAGUE_CONFIG.get(league_name, {
        "primary_bet":          "ms_and_goals",
        "confidence_threshold": 58,
        "trust_ms":             True,
        "trust_2_5":            True,
        "trust_kg":             False,
        "banko_eligible":       True,
        "goal_bet_threshold":   63,
        "emoji":                "⚽",
        "note":                 "Bilinmeyen lig — standart strateji"
    })

def get_action_label_by_league(ms_pred, over_prob, btts_prob, confidence, league_name, action_from_ai):
    """
    Lig stratejisine göre eylem etiketi üretir.
    TypeSafe AI'nın ham kararını lig konfigürasyonu ile filtreler.
    """
    cfg = get_league_config(league_name)
    week = get_season_week()
    dynamic_threshold = get_dynamic_confidence_boost(cfg["confidence_threshold"], league_name)
    
    # Lig etiketi
    lig_primary = cfg["primary_bet"]
    banko_eligible = cfg["banko_eligible"]
    
    # Premier League ve Ligue 1'den MS bankosuna izin yok
    if action_from_ai == "banko_oyna" and not banko_eligible:
        if cfg["trust_kg"] and btts_prob >= 60:
            return "🟡 SADECE GOL OYNA", "GOAL_ONLY", f"{cfg['emoji']} [{league_name}] KG Var tercih et"
        elif cfg["trust_2_5"] and over_prob >= cfg["goal_bet_threshold"]:
            return "🟡 SADECE GOL OYNA", "GOAL_ONLY", f"{cfg['emoji']} [{league_name}] 2.5 Üst tercih et"
        else:
            return "🔴 PAS GEÇ (UZAK DUR)", "NO_BET", f"{cfg['emoji']} [{league_name}] {cfg['note']}"
    
    # Normal akış — eşik kontrolü
    if confidence < dynamic_threshold:
        # Güven eşiği altında — gol bahsine düşür
        if cfg["trust_2_5"] and over_prob >= cfg["goal_bet_threshold"]:
            return "🟡 SADECE GOL OYNA", "GOAL_ONLY", f"{cfg['emoji']} Güven eşiği altında — gol bahsi"
        elif cfg["trust_kg"] and btts_prob >= 62:
            return "🟡 SADECE GOL OYNA", "GOAL_ONLY", f"{cfg['emoji']} KG Var bahsi"
        else:
            return "🔴 PAS GEÇ (UZAK DUR)", "NO_BET", f"{cfg['emoji']} {cfg['note']}"
    
    return None, None, None  # Normal akışa devam et

def get_recommended_bet_type(league_name, ms_prob, over_prob, btts_prob):
    """Lig stratejisine göre önerilen bahis türünü döndürür."""
    cfg = get_league_config(league_name)
    recs = []
    
    if cfg["trust_ms"] and ms_prob >= cfg["confidence_threshold"]:
        recs.append("MS")
    if cfg["trust_2_5"] and over_prob >= cfg["goal_bet_threshold"]:
        recs.append("2.5 ÜST")
    if cfg["trust_kg"] and btts_prob >= 60:
        recs.append("KG VAR")
    
    return recs if recs else ["PAS GEÇ"]

if __name__ == "__main__":
    print("Lig Stratejisi Konfigürasyonu:")
    for lig, cfg in LEAGUE_CONFIG.items():
        print(f"\n{cfg['emoji']} {lig}:")
        print(f"   Strateji: {cfg['primary_bet']}")
        print(f"   Güven Eşiği: %{cfg['confidence_threshold']} (Dinamik: %{get_dynamic_confidence_boost(cfg['confidence_threshold'], lig)})")
        print(f"   Banko Uygun: {cfg['banko_eligible']}")
        print(f"   Not: {cfg['note']}")
    print(f"\nSezon Haftası: {get_season_week()}")
    print(f"Dinamik Faktör Ağırlığı: %{int(SEASON_DYNAMIC_WEIGHT*100)}")

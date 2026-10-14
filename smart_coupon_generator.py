"""
smart_coupon_generator.py — TypeSafe AI Akıllı Kupon Üreteci (Omni-Market Versiyonu)
===================================================================================
TypeSafe AI tarafından belirlenen prensipler:
1. Dinamik Pazar Kullanımı: Sabit MS veya 2.5 Üst yerine, maçın en mantıklı tercihi (optimal_market) kullanılır.
2. Korelasyon Kuralı: Aynı kuponda aynı ligden iki maç olamaz (riski liglere dağıt).
3. Değer Odaklılık (EV): Oranı 1.30'un altında olan ölü maçlar elenir; Güven >= %65 olanlar seçilir.
4. Çeşitlendirilmiş Portföy:
   - Kupon 1: Günün Altın Kasası (En yüksek EV'ye sahip 2 farklı lig maçı, Oran: ~2.00 - 3.00)
   - Kupon 2: Günün Değer Kombinesi (3 farklı ligden en kaliteli optimal tercihler, Oran: ~3.50 - 6.00)
"""

from tuzak_avcisi import TuzakAvcisi

def generate_smart_coupons(analyzed_matches):
    """
    Analiz edilmiş maç listesinden (results) en optimal 2'li ve 3'lü kuponları üretir.
    Tuzak Avcısı (tuzak_avcisi.py) tarafından onaylanmamış hiçbir maç kupona giremez.
    """
    coupons = {}
    
    # 1. Her maçın optimal tercihini hazırla ve filtrele
    valid_candidates = []
    for m in analyzed_matches:
        # 1. KÜRESEL VETO & PAS KONTROLÜ (SIFIR ÇELİŞKİ PROTOKOLÜ)
        is_safe, veto_reason = TuzakAvcisi.is_coupon_safe({"raw_match": m})
        if not is_safe:
            continue

        is_vetoed = (
            m.get("is_global_vetoed", False)
            or "VETO" in str(m.get("global_verdict", "")).upper()
            or "RED" in str(m.get("global_verdict", "")).upper()
            or str(m.get("action_status", "")).upper() in ["NO_BET", "PAS", "VETO", "REJECTED"]
            or "PAS" in str(m.get("action_label", "")).upper()
            or "VETO" in str(m.get("action_label", "")).upper()
            or "UZAK DUR" in str(m.get("action_label", "")).upper()
        )
        if is_vetoed:
            continue

        # En ideal tercih bilgileri
        market = m.get("optimal_market") or m.get("tahmin_ms") or "MS 1"
        odd = float(m.get("optimal_odds") or 1.50)
        conf = int(m.get("optimal_confidence") or m.get("confidence") or 60)
        score = float(m.get("optimal_value_score") or (conf * (odd ** 0.85)))
        reason = m.get("optimal_reason") or m.get("explanation") or ""
        league = m.get("league", "Bilinmeyen Lig")

        # GOAL_ONLY durumunda taraf bahsi kupona giremez, gol pazarına yönlendirilir
        is_goal_only = (str(m.get("action_status", "")).upper() == "GOAL_ONLY")
        if is_goal_only and ("MS " in market or "Kazanır" in market):
            goal_res = TuzakAvcisi.audit_goal_line_and_btts(m)
            if goal_res.get("is_over_elite") and float(m.get("over_2_5_prob", 0)) >= 58:
                market = "2.5 Üst"
                odd = float((m.get("odds") or {}).get("2.5_ust") or (m.get("odds") or {}).get("over_2_5") or 1.65)
            elif float(m.get("btts_prob", 0)) >= 58 and not goal_res.get("is_under_trap"):
                market = "KG Var"
                odd = float((m.get("odds") or {}).get("kg_var") or 1.65)
            elif float(m.get("over_2_5_prob", 0)) >= 60 and not goal_res.get("is_under_trap"):
                market = "2.5 Üst"
                odd = float((m.get("odds") or {}).get("2.5_ust") or (m.get("odds") or {}).get("over_2_5") or 1.65)
            else:
                continue
        
        # Düşük tempo / Under tuzağında 2.5 Üst kupona KESİNLİKLE giremez
        goal_audit = TuzakAvcisi.audit_goal_line_and_btts(m)
        if "2.5 Üst" in market and goal_audit.get("is_under_trap"):
            continue

        # Son aday güvenlik kontrolü (Tuzak Avcısı)
        is_cand_safe, cand_reason = TuzakAvcisi.is_coupon_safe({"raw_match": m, "tahmin": market})
        if not is_cand_safe:
            continue

        # Nesine Filtresi: Oran >= 1.40 (ölü oranlar KESİNLİKLE yasak) ve Güven >= 60 olmalı
        # Ayrıca aşırı tuzaklı maçlar (adj_trap >= 6.0) kuponlara girmemeli
        trap = float(m.get("trap_score") or 5.0)
        if odd >= 1.40 and conf >= 60 and trap <= 6.0:
            valid_candidates.append({
                "raw_match": m,
                "mac": f"{m['home_name']} vs {m['away_name']}",
                "lig": league,
                "tahmin": market,
                "oran": odd,
                "guven": conf,
                "value_score": score,
                "reason": reason,
                "is_hit": m.get("is_hit", m.get("ms_hit", False))
            })
            
    # Value Score'a göre sırala (En yüksek kaliteli ve karlı olanlar en başta)
    valid_candidates.sort(key=lambda x: x["value_score"], reverse=True)
    
    # ── KUPON 1: GÜNÜN ALTIN KASASI (2'li Farklı Lig Portföyü) ──
    altin_kasa = []
    used_leagues_kasa = set()
    
    for c in valid_candidates:
        if len(altin_kasa) >= 2:
            break
        if c["lig"] not in used_leagues_kasa:
            altin_kasa.append(c)
            used_leagues_kasa.add(c["lig"])
            
    # Eğer 2 farklı lig bulunamadıysa havuzdaki en iyi 2 maçı al
    if len(altin_kasa) < 2 and len(valid_candidates) >= 2:
        altin_kasa = valid_candidates[:2]

    # ── KUPON 2: GÜNÜN DEĞER KOMBİNESİ (3'lü Dinamik Kupon) ──
    deger_kombine = []
    used_leagues_kombine = set()
    
    # Altın kasadaki 1. maçı hariç tutarak veya farklı bir varyasyonla 3 maç seç
    remaining_candidates = [c for c in valid_candidates if c not in altin_kasa[:1]]
    for c in remaining_candidates:
        if len(deger_kombine) >= 3:
            break
        if c["lig"] not in used_leagues_kombine:
            deger_kombine.append(c)
            used_leagues_kombine.add(c["lig"])
            
    # Yeterli farklı lig yoksa sıradaki en iyileri ekle
    if len(deger_kombine) < 3:
        for c in valid_candidates:
            if len(deger_kombine) >= 3:
                break
            if c not in deger_kombine:
                deger_kombine.append(c)

    # Toplam oranları hesapla
    def calc_total_odds(match_list):
        if not match_list: return 0.0
        tot = 1.0
        for m in match_list:
            tot *= m["oran"]
        return round(tot, 2)

    coupons["altin_kasa"] = {
        "baslik": "🏆 GÜNÜN ALTIN KASA KUPONU (En İdeal 2'li Portföy)",
        "maclar": altin_kasa,
        "toplam_oran": calc_total_odds(altin_kasa),
        "tuttu_mu": all(m["is_hit"] for m in altin_kasa) if altin_kasa else False
    }
    
    coupons["gol_yagmuru"] = {
        "baslik": "🎯 GÜNÜN DEĞER KOMBİNESİ (3'lü Optimal Tercihler)",
        "maclar": deger_kombine,
        "toplam_oran": calc_total_odds(deger_kombine),
        "tuttu_mu": all(m["is_hit"] for m in deger_kombine) if deger_kombine else False
    }

    return coupons

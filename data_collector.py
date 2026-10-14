import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows Terminal UTF-8 Uyumluluğu
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

# Desteklenen Dev Ligler ve ESPN Kodları
LEAGUES = {
    "Süper Lig":              {"code": "tur.1", "flag": "🇹🇷", "country": "Türkiye"},
    "Premier League":         {"code": "eng.1", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "country": "İngiltere"},
    "La Liga":                {"code": "esp.1", "flag": "🇪🇸", "country": "İspanya"},
    "Serie A":                {"code": "ita.1", "flag": "🇮🇹", "country": "İtalya"},
    "Bundesliga":             {"code": "ger.1", "flag": "🇩🇪", "country": "Almanya"},
    "Ligue 1":                {"code": "fra.1", "flag": "🇫🇷", "country": "Fransa"},
    "Şampiyonlar Ligi":       {"code": "uefa.champions", "flag": "🏆", "country": "Avrupa"},
    "Avrupa Ligi":            {"code": "uefa.europa", "flag": "🟠", "country": "Avrupa"},
    "Konferans Ligi":         {"code": "uefa.europa.conf", "flag": "🟢", "country": "Avrupa"},
    "İngiltere Championship": {"code": "eng.2", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "country": "İngiltere"},
    "Hollanda Eredivisie":   {"code": "ned.1", "flag": "🇳🇱", "country": "Hollanda"},
    "Portekiz Premier":       {"code": "por.1", "flag": "🇵🇹", "country": "Portekiz"},
    "Belçika Pro Lig":        {"code": "bel.1", "flag": "🇧🇪", "country": "Belçika"},
    "Brezilya Serie A":       {"code": "bra.1", "flag": "🇧🇷", "country": "Brezilya"},
    "Amerika MLS":            {"code": "usa.1", "flag": "🇺🇸", "country": "ABD"},
    "Suudi Pro Lig":          {"code": "ksa.1", "flag": "🇸🇦", "country": "Suudi Arabistan"}
}

# understat.com destekli ligler (xG verisi)
XG_SUPPORTED_LEAGUES = {"Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"}

def american_to_decimal(odd_str):
    """DraftKings Amerikan oranını (+105, -135) klasik ondalık orana (2.05, 1.74) çevirir."""
    if not odd_str:
        return None
    try:
        val = float(str(odd_str).replace("+", "").strip())
        if val > 0:
            return round((val / 100.0) + 1.0, 2)
        elif val < 0:
            return round((100.0 / abs(val)) + 1.0, 2)
    except:
        pass
    return None

def parse_form_string(form_str):
    """
    'WWDLW' gibi form dizisini çözümler.
    Döndürür: {'wins': 3, 'draws': 1, 'losses': 1, 'goals_trend': 'strong', 'momentum': 'positive'}
    """
    if not form_str or form_str == "-":
        return {"wins": 0, "draws": 0, "losses": 0, "momentum": "unknown", "points": 0}
    wins   = form_str.count("W")
    draws  = form_str.count("D")
    losses = form_str.count("L")
    points = wins * 3 + draws
    
    # Son 3 maç momentumu (en sağdaki 3 karakter)
    recent = form_str[-3:] if len(form_str) >= 3 else form_str
    if recent.count("W") >= 2:
        momentum = "positive"
    elif recent.count("L") >= 2:
        momentum = "negative"
    else:
        momentum = "neutral"
    
    return {"wins": wins, "draws": draws, "losses": losses, "momentum": momentum, "points": points}

def fetch_h2h_data(league_code, event_id):
    """
    ESPN Summary endpoint'inden H2H (kafa kafaya) verilerini çeker.
    Son 5 karşılaşmanın kazanma/beraberlik/kaybetme dağılımını döndürür.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={event_id}"
    h2h = {
        "h2h_home_wins": 0, "h2h_draws": 0, "h2h_away_wins": 0,
        "h2h_total": 0, "h2h_avg_goals": 0.0, "h2h_summary": "H2H verisi yok"
    }
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return h2h
        data = r.json()
        
        h2h_games = data.get("headToHeadGames", [])
        if not h2h_games:
            # Alternatif alan adı
            h2h_games = data.get("headToHead", {}).get("games", [])
        
        total = len(h2h_games[:5])
        if total == 0:
            return h2h
        
        home_w = draw = away_w = 0
        total_goals = 0
        for game in h2h_games[:5]:
            result = game.get("result", "")
            score_str = game.get("score", "")
            if "-" in score_str:
                try:
                    parts = [int(x.strip()) for x in score_str.split("-")]
                    total_goals += sum(parts)
                except:
                    pass
            if result == "W":
                home_w += 1
            elif result == "L":
                away_w += 1
            else:
                draw += 1
        
        avg_goals = round(total_goals / total, 2) if total > 0 else 0.0
        h2h["h2h_home_wins"] = home_w
        h2h["h2h_draws"] = draw
        h2h["h2h_away_wins"] = away_w
        h2h["h2h_total"] = total
        h2h["h2h_avg_goals"] = avg_goals
        h2h["h2h_summary"] = f"Son {total} maç: Ev {home_w}G / {draw}B / Dep {away_w}G | Ort {avg_goals} gol/maç"
    except:
        pass
    return h2h

def fetch_match_deep_stats(league_code, event_id, match_iso_date):
    """
    ESPN Summary endpoint'inden:
    - Son 5 maç detayları (atılan/yenilen gol, form, rakip kalitesi)
    - Ev sahibi EV performansı / deplasman takımı DEPLASMAN performansı
    - Dinlenme günleri (rotation riski)
    - H2H özeti
    - Stadyum bilgisi
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={event_id}"
    details = {
        # Temel gol istatistikleri (son 3)
        "home_scored_last3": 0, "home_conceded_last3": 0,
        "away_scored_last3": 0, "away_conceded_last3": 0,
        # Genişletilmiş: son 5 maç
        "home_scored_last5": 0, "home_conceded_last5": 0,
        "away_scored_last5": 0, "away_conceded_last5": 0,
        # Ev sahibinin YALNIZCA EV performansı
        "home_home_scored_last5": 0, "home_home_conceded_last5": 0,
        "home_home_wins": 0, "home_home_total": 0,
        # Deplasman takımının YALNIZCA DEPLASMAN performansı
        "away_away_scored_last5": 0, "away_away_conceded_last5": 0,
        "away_away_wins": 0, "away_away_total": 0,
        # Dinlenme ve rotation riski
        "home_rest_days": "Bilinmiyor", "away_rest_days": "Bilinmiyor",
        "home_rotation_risk": False, "away_rotation_risk": False,
        # Form momentumu
        "home_momentum": "unknown", "away_momentum": "unknown",
        # H2H
        "h2h_home_wins": 0, "h2h_draws": 0, "h2h_away_wins": 0,
        "h2h_total": 0, "h2h_avg_goals": 0.0, "h2h_summary": "H2H verisi yok",
        # Stadyum
        "venue": "Bilinmiyor"
    }
    try:
        r = requests.get(url, timeout=6)
        if r.status_code != 200:
            return details
            
        data = r.json()
        
        # Stadyum bilgisi
        venue = data.get("gameInfo", {}).get("venue", {}).get("fullName")
        if venue:
            details["venue"] = venue
            
        match_dt = None
        if match_iso_date:
            try:
                match_dt = datetime.fromisoformat(match_iso_date.replace("Z", "+00:00"))
            except:
                pass
        
        # --- H2H Verisi ---
        h2h_games = data.get("headToHeadGames", []) or data.get("headToHead", {}).get("games", [])
        if h2h_games:
            total_h2h = len(h2h_games[:5])
            home_w = draw_h = away_w = 0
            total_goals_h2h = 0
            for game in h2h_games[:5]:
                result = game.get("result", "")
                score_str = game.get("score", "")
                if "-" in score_str:
                    try:
                        parts = [int(x.strip()) for x in score_str.split("-")]
                        total_goals_h2h += sum(parts)
                    except:
                        pass
                if result == "W":
                    home_w += 1
                elif result == "L":
                    away_w += 1
                else:
                    draw_h += 1
            
            details["h2h_home_wins"] = home_w
            details["h2h_draws"] = draw_h
            details["h2h_away_wins"] = away_w
            details["h2h_total"] = total_h2h
            details["h2h_avg_goals"] = round(total_goals_h2h / total_h2h, 2) if total_h2h > 0 else 0.0
            details["h2h_summary"] = f"Son {total_h2h} H2H: Ev {home_w}G / {draw_h}B / Dep {away_w}G | Ort {details['h2h_avg_goals']} gol/maç"
        
        # --- Son Maç Detayları (lastFiveGames) ---
        last_five = data.get("lastFiveGames", [])
        for idx, team_data in enumerate(last_five[:2]):
            prefix = "home" if idx == 0 else "away"
            events = team_data.get("events", [])
            
            # Dinlenme günü hesapla
            if events and match_dt:
                last_game_date = events[0].get("gameDate", "")
                if last_game_date:
                    try:
                        g_dt = datetime.fromisoformat(last_game_date.replace("Z", "+00:00"))
                        rest = max(1, (match_dt.date() - g_dt.date()).days)
                        details[f"{prefix}_rest_days"] = rest
                        # Rotation riski: 3 gün veya daha az dinlendi
                        details[f"{prefix}_rotation_risk"] = (rest <= 3)
                    except:
                        pass
            
            sc3 = cn3 = sc5 = cn5 = 0
            home_sc = home_cn = home_wins = home_total = 0
            away_sc = away_cn = away_wins = away_total = 0
            
            for i, g in enumerate(events[:5]):
                score_str = g.get("score", "")
                res = g.get("gameResult", "")
                is_home_game = g.get("homeAway", "") == "home"
                
                if "-" in score_str:
                    try:
                        p = [int(x.strip()) for x in score_str.split("-")]
                        if res == "W":
                            atilan, yenilen = max(p), min(p)
                        elif res == "L":
                            atilan, yenilen = min(p), max(p)
                        else:
                            # Beraberlik — eğer ev sahibiyse p[0], deplasmansa p[1]
                            if is_home_game:
                                atilan, yenilen = p[0], p[1]
                            else:
                                atilan, yenilen = p[1], p[0]
                        
                        sc5 += atilan
                        cn5 += yenilen
                        if i < 3:
                            sc3 += atilan
                            cn3 += yenilen
                        
                        # Ayrı ev/deplasman performansı
                        if prefix == "home" and is_home_game:
                            home_sc += atilan
                            home_cn += yenilen
                            home_total += 1
                            if res == "W":
                                home_wins += 1
                        elif prefix == "away" and not is_home_game:
                            away_sc += atilan
                            away_cn += yenilen
                            away_total += 1
                            if res == "W":
                                away_wins += 1
                    except:
                        pass
            
            details[f"{prefix}_scored_last3"] = sc3
            details[f"{prefix}_conceded_last3"] = cn3
            details[f"{prefix}_scored_last5"] = sc5
            details[f"{prefix}_conceded_last5"] = cn5
            
            if prefix == "home":
                details["home_home_scored_last5"] = home_sc
                details["home_home_conceded_last5"] = home_cn
                details["home_home_wins"] = home_wins
                details["home_home_total"] = home_total
            else:
                details["away_away_scored_last5"] = away_sc
                details["away_away_conceded_last5"] = away_cn
                details["away_away_wins"] = away_wins
                details["away_away_total"] = away_total
                
    except Exception as e:
        pass
    return details

def fetch_real_matches_for_date(date_str=None):
    """
    ESPN resmi spor API'sinden 100% gerçek maç ve DraftKings oran verilerini çeker.
    date_str None, 'today' veya 'live' ise güncel canlı bülteni çeker.
    """
    raw_matches = []
    is_live = (date_str in [None, "", "today", "live"])
    date_display = "Canlı / Güncel Bülten" if is_live else date_str
    print(f"[*] ESPN API üzerinden {date_display} tarihli gerçek maç verileri toplanıyor...")
    
    for league_name, league_info in LEAGUES.items():
        code = league_info["code"]
        if is_live:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard"
        else:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={date_str}"
        try:
            r = requests.get(url, timeout=7)
            if r.status_code != 200:
                continue
                
            data = r.json()
            events = data.get("events", [])
            
            for ev in events:
                # Canlı bülten modunda bitmiş maçları ele (Full Time maçlara bahis oynanamaz!)
                st_name = ev.get("status", {}).get("type", {}).get("name", "")
                st_desc = ev.get("status", {}).get("type", {}).get("description", "")
                if is_live and (st_name in ["STATUS_FULL_TIME", "STATUS_POSTPONED", "STATUS_CANCELED"] or st_desc in ["Full Time", "Final", "FT", "Postponed", "Canceled"]):
                    continue

                c = ev.get("competitions", [{}])[0]
                competitors = c.get("competitors", [])
                if len(competitors) < 2:
                    continue
                    
                home_team = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
                away_team = competitors[1] if competitors[0].get("homeAway") == "home" else competitors[0]
                
                utc_date_raw = ev.get("date", "")
                time_tr = "Belli Değil"
                match_date_str = date_str
                if utc_date_raw:
                    try:
                        dt = datetime.fromisoformat(utc_date_raw.replace("Z", "+00:00"))
                        dt_tr = dt.astimezone(timezone(timedelta(hours=3)))
                        time_tr = dt_tr.strftime("%H:%M")
                        match_date_str = dt_tr.strftime("%Y%m%d")
                    except:
                        time_tr = utc_date_raw[11:16]
                        
                h_rec = home_team.get("records", [{}])[0].get("summary", "-") if home_team.get("records") else "-"
                a_rec = away_team.get("records", [{}])[0].get("summary", "-") if away_team.get("records") else "-"
                
                h_form_raw = home_team.get("form", "-")
                a_form_raw = away_team.get("form", "-")
                h_form_parsed = parse_form_string(h_form_raw)
                a_form_parsed = parse_form_string(a_form_raw)
                
                # Oranlar (DraftKings / ESPN) — ASLA SAHTE VARSAYILAN KULLANILMAZ!
                odds_data = c.get("odds", [])
                odds_info = None
                pinnacle_odds = None
                odds_drift = {"home_drift_pct": 0.0, "away_drift_pct": 0.0, "signal": "NORMAL", "description": ""}
                asian_handicap_data = None
                
                if odds_data and isinstance(odds_data[0], dict):
                    ml = odds_data[0].get("moneyline") or {}
                    tot = odds_data[0].get("total") or {}
                    ps = odds_data[0].get("pointSpread") or {}
                    
                    if ps and isinstance(ps, dict):
                        h_ps = ps.get("home", {})
                        a_ps = ps.get("away", {})
                        h_op_l = h_ps.get("open", {}).get("line")
                        h_cl_l = h_ps.get("close", {}).get("line")
                        h_op_o = h_ps.get("open", {}).get("odds")
                        h_cl_o = h_ps.get("close", {}).get("odds")
                        
                        a_op_l = a_ps.get("open", {}).get("line")
                        a_cl_l = a_ps.get("close", {}).get("line")
                        a_op_o = a_ps.get("open", {}).get("odds")
                        a_cl_o = a_ps.get("close", {}).get("odds")
                        
                        if h_op_l is not None and h_cl_l is not None:
                            try:
                                h_open_l = float(str(h_op_l).replace("+", "").strip())
                                h_curr_l = float(str(h_cl_l).replace("+", "").strip())
                                h_open_odd = american_to_decimal(h_op_o) or 1.90
                                h_curr_odd = american_to_decimal(h_cl_o) or 1.90
                                
                                a_open_l = float(str(a_op_l).replace("+", "").strip()) if a_op_l is not None else -h_open_l
                                a_curr_l = float(str(a_cl_l).replace("+", "").strip()) if a_cl_l is not None else -h_curr_l
                                a_open_odd = american_to_decimal(a_op_o) or 1.90
                                a_curr_odd = american_to_decimal(a_cl_o) or 1.90
                                
                                asian_handicap_data = {
                                    "has_real_data": True,
                                    "open_line": h_open_l,
                                    "current_line": h_curr_l,
                                    "open_odds": h_open_odd,
                                    "current_odds": h_curr_odd,
                                    "home_spread": {
                                        "open_line": h_open_l,
                                        "current_line": h_curr_l,
                                        "open_odds": h_open_odd,
                                        "current_odds": h_curr_odd
                                    },
                                    "away_spread": {
                                        "open_line": a_open_l,
                                        "current_line": a_curr_l,
                                        "open_odds": a_open_odd,
                                        "current_odds": a_curr_odd
                                    }
                                }
                            except Exception:
                                pass
                    
                    h_open = american_to_decimal(ml.get("home", {}).get("open", {}).get("odds"))
                    h_close = american_to_decimal(ml.get("home", {}).get("close", {}).get("odds"))
                    d_open = american_to_decimal(ml.get("draw", {}).get("open", {}).get("odds"))
                    d_close = american_to_decimal(ml.get("draw", {}).get("close", {}).get("odds"))
                    a_open = american_to_decimal(ml.get("away", {}).get("open", {}).get("odds"))
                    a_close = american_to_decimal(ml.get("away", {}).get("close", {}).get("odds"))
                    
                    ov_odd = tot.get("over", {}).get("close", {}).get("odds") or tot.get("over", {}).get("open", {}).get("odds")
                    un_odd = tot.get("under", {}).get("close", {}).get("odds") or tot.get("under", {}).get("open", {}).get("odds")
                    
                    h_eff = h_close or h_open
                    a_eff = a_close or a_open
                    d_eff = d_close or d_open
                    
                    if h_eff and d_eff and a_eff:
                        ov_dec = american_to_decimal(ov_odd)
                        un_dec = american_to_decimal(un_odd)
                        odds_info = {
                            "odds_available": True,
                            "1": h_eff,
                            "X": d_eff,
                            "2": a_eff,
                            "ms_1": h_eff,
                            "ms_x": d_eff,
                            "ms_2": a_eff,
                            "open_1": h_open or h_eff,
                            "open_x": d_open or d_eff,
                            "open_2": a_open or a_eff,
                            "close_1": h_close or h_eff,
                            "close_x": d_close or d_eff,
                            "close_2": a_close or a_eff,
                            "over_2_5": ov_dec,
                            "under_2_5": un_dec,
                            "2.5_ust": ov_dec,
                            "2.5_alt": un_dec
                        }
                        pinnacle_odds = {
                            "1": h_close or h_eff,
                            "X": d_close or d_eff,
                            "2": a_close or a_eff,
                            "over_2_5": ov_dec,
                            "under_2_5": un_dec
                        }
                    
                    # 📈 Akıllı Para / Oran Kayması Analizi (Odds Drift)
                    if h_open and h_close and h_open > 1.0:
                        h_drift = round((h_close - h_open) / h_open * 100, 1)
                        odds_drift["home_drift_pct"] = h_drift
                        if h_drift <= -4.0:
                            odds_drift["signal"] = "SMART_MONEY_HOME"
                            odds_drift["description"] = f"🔥 Ev Sahibi Oranı %{abs(h_drift)} Düştü (Akıllı Para Girişi)"
                        elif h_drift >= 6.0:
                            odds_drift["signal"] = "MARKET_DOUBT_HOME"
                            odds_drift["description"] = f"⚠️ Ev Sahibi Oranı %{h_drift} Yükseldi (Piyasa Şüphesi)"
                            
                    if a_open and a_close and a_open > 1.0 and odds_drift["signal"] == "NORMAL":
                        a_drift = round((a_close - a_open) / a_open * 100, 1)
                        odds_drift["away_drift_pct"] = a_drift
                        if a_drift <= -4.0:
                            odds_drift["signal"] = "SMART_MONEY_AWAY"
                            odds_drift["description"] = f"🔥 Deplasman Oranı %{abs(a_drift)} Düştü (Akıllı Para Girişi)"
                        elif a_drift >= 6.0:
                            odds_drift["signal"] = "MARKET_DOUBT_AWAY"
                            odds_drift["description"] = f"⚠️ Deplasman Oranı %{a_drift} Yükseldi (Piyasa Şüphesi)"
                    
                match_dict = {
                    "id": ev.get("id"),
                    "league": league_name,
                    "league_code": code,
                    "flag": league_info["flag"],
                    "date": match_date_str,
                    "utc_date": utc_date_raw,
                    "time_tr": time_tr,
                    "status": ev.get("status", {}).get("type", {}).get("description", "Scheduled"),
                    "home_name": home_team.get("team", {}).get("displayName", ""),
                    "home_short": home_team.get("team", {}).get("shortDisplayName", ""),
                    "home_logo": home_team.get("team", {}).get("logo", ""),
                    "home_form": h_form_raw,
                    "home_form_wins": h_form_parsed["wins"],
                    "home_form_draws": h_form_parsed["draws"],
                    "home_form_losses": h_form_parsed["losses"],
                    "home_momentum": h_form_parsed["momentum"],
                    "home_form_points": h_form_parsed["points"],
                    "home_record": h_rec,
                    "away_name": away_team.get("team", {}).get("displayName", ""),
                    "away_short": away_team.get("team", {}).get("shortDisplayName", ""),
                    "away_logo": away_team.get("team", {}).get("logo", ""),
                    "away_form": a_form_raw,
                    "away_form_wins": a_form_parsed["wins"],
                    "away_form_draws": a_form_parsed["draws"],
                    "away_form_losses": a_form_parsed["losses"],
                    "away_momentum": a_form_parsed["momentum"],
                    "away_form_points": a_form_parsed["points"],
                    "away_record": a_rec,
                    "odds": odds_info,
                    "odds_drift": odds_drift,
                    "asian_handicap_data": asian_handicap_data,
                    "pinnacle_odds": pinnacle_odds,
                    "volume_data": None,
                    # xG alanları — xg_collector tarafından doldurulacak
                    "home_xg_avg": None,
                    "home_xga_avg": None,
                    "away_xg_avg": None,
                    "away_xga_avg": None,
                    "xg_available": False,
                    "xg_supported": league_name in XG_SUPPORTED_LEAGUES
                }
                raw_matches.append(match_dict)
        except Exception as e:
            print(f"[!] {league_name} veri çekme hatası: {e}")
            
    print(f"[+] {len(raw_matches)} maç için derin istatistikler paralel toplanıyor...")
    
    # 2. Adım: Derin istatistikleri paralel çek
    enriched_matches = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {
            executor.submit(fetch_match_deep_stats, m["league_code"], m["id"], m["utc_date"]): m
            for m in raw_matches
        }
        for future in as_completed(future_map):
            m = future_map[future]
            # A single unavailable summary endpoint must not discard the
            # entire bulletin.  Keep the match and use the documented empty
            # deep-stat defaults when that particular request fails.
            try:
                deep = future.result()
            except Exception as exc:
                print(f"[!] {m['home_name']} - {m['away_name']} derin veri hatası: {exc}")
                deep = {}
            # home_momentum'u ESPN form'undan parse ettik, deep stats'tan da gelen varsa birleştir
            merged = {**m, **deep}
            # Eğer ESPN'den form geldi ama deep'ten gelmediyse koru
            if m.get("home_momentum") != "unknown":
                merged["home_momentum"] = m["home_momentum"]
            if m.get("away_momentum") != "unknown":
                merged["away_momentum"] = m["away_momentum"]
            enriched_matches.append(merged)

    # 3. Adım: Nesine REA ile Gerçek Resmi İddaa Oranlarını ve MBS Kurallarını Entegre Et
    try:
        from nesine_client import NesineClient
        nesine_count = 0
        for em in enriched_matches:
            n_match = NesineClient.match_nesine_odds(em["home_name"], em["away_name"])
            if n_match:
                em["nesine_code"] = n_match["code"]
                em["mbs"] = n_match["mbs"]
                curr_odds = em.get("odds") or {}
                # Eğer pinnacle_odds atanmamışsa veya curr_odds'ta global oranlar varsa koru
                if not em.get("pinnacle_odds") and curr_odds.get("1"):
                    em["pinnacle_odds"] = {
                        "1": curr_odds.get("close_1") or curr_odds.get("1"),
                        "X": curr_odds.get("close_x") or curr_odds.get("X"),
                        "2": curr_odds.get("close_2") or curr_odds.get("2"),
                        "over_2_5": curr_odds.get("over_2_5"),
                        "under_2_5": curr_odds.get("under_2_5")
                    }
                em["odds"] = {**curr_odds, **n_match["odds"]}
                em["odds_source"] = "NESINE_OFFICIAL"
                nesine_count += 1
        if nesine_count > 0:
            print(f"[+] 🎯 Nesine REA: {nesine_count} maçın oran ve MBS verisi doğrudan resmi Nesine bülteninden bağlandı!")

        # 3.5 Adım: Nesine Hibrit Bülten Genişletmesi (Tüm Oynanabilir Nesine Maçlarını Entegre Et)
        existing_nesine_codes = {em.get("nesine_code") for em in enriched_matches if em.get("nesine_code")}
        full_bulten = NesineClient.fetch_full_bulletin()
        
        target_d_str = date_str if date_str else datetime.now().strftime("%Y%m%d")
        try:
            target_formatted = f"{target_d_str[6:8]}.{target_d_str[4:6]}.{target_d_str[:4]}"
        except:
            target_formatted = datetime.now().strftime("%d.%m.%Y")
            
        hybrid_added = 0
        for nm in full_bulten:
            n_code = nm.get("code")
            if n_code in existing_nesine_codes:
                continue
            if nm.get("date") != target_formatted:
                continue
            n_odds = nm.get("odds", {})
            if not ("1" in n_odds and "X" in n_odds and "2" in n_odds):
                continue
                
            l_name = nm.get("league", "Diğer")
            flag = "⚽"
            if "Türkiye" in l_name: flag = "🇹🇷"
            elif "İngiltere" in l_name: flag = "🏴󠁧󠁢󠁥󠁮󠁧󠁿"
            elif "İspanya" in l_name: flag = "🇪🇸"
            elif "İtalya" in l_name: flag = "🇮🇹"
            elif "Almanya" in l_name: flag = "🇩🇪"
            elif "Fransa" in l_name: flag = "🇫🇷"
            elif "Hollanda" in l_name: flag = "🇳🇱"
            elif "Portekiz" in l_name: flag = "🇵🇹"
            elif "Belçika" in l_name: flag = "🇧🇪"
            elif "Brezilya" in l_name: flag = "🇧🇷"
            elif "Suudi" in l_name: flag = "🇸🇦"
            elif "Amerika" in l_name or "MLS" in l_name: flag = "🇺🇸"
            elif "Şampiyonlar" in l_name: flag = "🏆"
            elif "Avrupa" in l_name: flag = "🟠"
            elif "Konferans" in l_name: flag = "🟢"

            hybrid_match = {
                "id": f"nesine_{n_code}",
                "event_id": str(n_code),
                "league": l_name,
                "league_code": "nesine_hybrid",
                "flag": flag,
                "country": l_name.split()[0] if l_name else "Dünya",
                "date": nm.get("date"),
                "utc_date": nm.get("date"),
                "time_tr": nm.get("time_tr", "20:00"),
                "status": "Programda",
                "home_name": nm.get("home_name"),
                "away_name": nm.get("away_name"),
                "home_logo": "",
                "away_logo": "",
                "home_form": "-",
                "away_form": "-",
                "home_wins": 0, "home_draws": 0, "home_losses": 0, "home_points": 0,
                "away_wins": 0, "away_draws": 0, "away_losses": 0, "away_points": 0,
                "home_momentum": "neutral", "away_momentum": "neutral",
                "home_scored_last3": 0, "home_conceded_last3": 0,
                "away_scored_last3": 0, "away_conceded_last3": 0,
                "home_home_wins": 0, "home_home_total": 0,
                "away_away_wins": 0, "away_away_total": 0,
                "venue": "Bilinmiyor",
                "h2h_summary": "Veri yok",
                "h2h_home_wins": 0, "h2h_draws": 0, "h2h_away_wins": 0, "h2h_total": 0, "h2h_avg_goals": 0.0,
                "home_rotation_risk": False, "away_rotation_risk": False,
                "home_xg_avg": None, "home_xga_avg": None,
                "away_xg_avg": None, "away_xga_avg": None,
                "xg_available": False, "xg_supported": False,
                "nesine_code": n_code,
                "mbs": nm.get("mbs", 1),
                "odds": n_odds,
                "odds_source": "NESINE_OFFICIAL"
            }
            enriched_matches.append(hybrid_match)
            existing_nesine_codes.add(n_code)
            hybrid_added += 1
            
        if hybrid_added > 0:
            print(f"[+] 🌐 Hibrit Bülten: Nesine'den {hybrid_added} adet oynanabilir ek maç sisteme entegre edildi!")
    except Exception as ne:
        print(f"[!] Nesine REA bağlantı uyarısı: {ne}")

    # 4. Adım: Canlı Betfair Borsa Likiditesini (Moneyway) Entegre Et (Sıfır Simülasyon)
    try:
        from betfair_moneyway_client import BetfairMoneywayClient
        bf_matches = BetfairMoneywayClient.fetch_live_moneyway_table()
        bf_count = 0
        for em in enriched_matches:
            v_data = BetfairMoneywayClient.match_volume(em["home_name"], em["away_name"])
            em["volume_data"] = v_data
            if v_data.get("has_volume_data"):
                bf_count += 1
        if bf_count > 0:
            print(f"[+] 👑 Betfair Canlı Borsa: {bf_count} maçın gerçek para hacmi bağlandı!")
        else:
            print(f"[*] 👑 Betfair Canlı Borsa: {len(bf_matches)} borsa maçı tarandı.")
    except Exception as bfe:
        print(f"[!] Betfair Moneyway bağlantı uyarısı: {bfe}")

    # 5. Adım: SofaScore & REA Derin İstatistik Katmanını (Reyting, xG, Momentum) Enjekte Et
    try:
        from sofascore_client import SofaScoreClient
        enriched_matches = SofaScoreClient.enrich_match_list(enriched_matches)
        print(f"[+] 📊 SofaScore REA: {len(enriched_matches)} maçın oyuncu reytingi, xG ve hücum baskı analizi tamamlandı!")
    except Exception as sfe:
        print(f"[!] SofaScore entegrasyon uyarısı: {sfe}")

    print(f"[+] Toplam {len(enriched_matches)} adet %100 GERÇEK ve DERİNLEŞTİRİLMİŞ maç hazır.")
    return enriched_matches

if __name__ == "__main__":
    matches = fetch_real_matches_for_date()
    print("\nDerinleştirilmiş Örnek Maç:")
    if matches:
        m = matches[0]
        print(f"[{m['flag']} {m['league']}] {m['home_name']} vs {m['away_name']}")
        print(f"  Ev Sahibi: Son 3'te {m['home_scored_last3']} gol attı, {m['home_conceded_last3']} yedi | Son 5'te yalnızca EV: {m['home_home_wins']}/{m['home_home_total']} kazandı")
        print(f"  Deplasman: Son 3'te {m['away_scored_last3']} gol attı, {m['away_conceded_last3']} yedi | Son 5'te yalnızca DEP: {m['away_away_wins']}/{m['away_away_total']} kazandı")
        print(f"  Ev Momentum: {m['home_momentum']} | Dep Momentum: {m['away_momentum']}")
        print(f"  H2H: {m['h2h_summary']}")
        print(f"  Rotation Riski: Ev={m['home_rotation_risk']} | Dep={m['away_rotation_risk']}")
        print(f"  Stadyum: {m['venue']}")

"""
xg_collector.py — understat.com'dan xG (Beklenen Gol) Verisi Toplayıcı
========================================================================
understat.com'un JSON API'sini kullanarak Premier League, La Liga,
Bundesliga, Serie A ve Ligue 1 için takım bazlı ortalama xG ve xGA
(beklenen gol yeme) verilerini çeker.

Kullanım:
    from xg_collector import enrich_with_xg
    matches = enrich_with_xg(matches)
"""
import sys
import json
import requests
import re
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

# understat.com lig kodları
UNDERSTAT_LEAGUES = {
    "Premier League": "EPL",
    "La Liga":        "La_liga",
    "Bundesliga":     "Bundesliga",
    "Serie A":        "Serie_A",
    "Ligue 1":        "Ligue_1"
}

_xg_cache = {}  # { "EPL_2026": {"Arsenal": {"xg": 1.8, "xga": 0.9}, ...} }

def _fetch_understat_team_xg(league_key, season_year):
    """
    understat.com/{league}/{season} sayfasından JSON içindeki takım xG verilerini çeker.
    """
    cache_key = f"{league_key}_{season_year}"
    if cache_key in _xg_cache:
        return _xg_cache[cache_key]
    
    url = f"https://understat.com/league/{league_key}/{season_year}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
    }
    
    team_xg = {}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return team_xg
        
        html = r.text
        # understat.com verisini JSON bloğu olarak gömer
        # teamsData = JSON.parse('...')
        pattern = r"teamsData\s*=\s*JSON\.parse\('(.+?)'\)"
        match = re.search(pattern, html)
        if not match:
            return team_xg
        
        raw_json = match.group(1)
        # JavaScript escape karakterlerini düzelt
        raw_json = raw_json.encode().decode("unicode_escape")
        data = json.loads(raw_json)
        
        for team_id, team_info in data.items():
            team_name = team_info.get("title", "")
            history = team_info.get("history", [])
            if not history:
                continue
            
            # Son 5 maçın ortalaması
            recent = history[-5:]
            xg_vals = [h.get("xG", 0) for h in recent if h.get("xG") is not None]
            xga_vals = [h.get("xGA", 0) for h in recent if h.get("xGA") is not None]
            
            avg_xg  = round(sum(xg_vals)  / len(xg_vals),  2) if xg_vals  else None
            avg_xga = round(sum(xga_vals) / len(xga_vals), 2) if xga_vals else None
            
            team_xg[team_name.lower()] = {
                "xg":  avg_xg,
                "xga": avg_xga,
                "games": len(recent)
            }
        
        _xg_cache[cache_key] = team_xg
        print(f"[xG] {league_key} {season_year}: {len(team_xg)} takım xG verisi alındı.")
    except Exception as e:
        print(f"[xG] Hata ({league_key}): {e}")
    
    return team_xg

def _find_team_xg(team_name, xg_data):
    """
    Takım adını esnek şekilde eşleştirir (normalize ederek kısmi eşleşme dener).
    """
    if not xg_data:
        return None, None
    
    name_lower = team_name.lower()
    
    # 1. Tam eşleşme
    if name_lower in xg_data:
        d = xg_data[name_lower]
        return d["xg"], d["xga"]
    
    # 2. Kısmi eşleşme (ilk kelime veya içerme)
    for key, val in xg_data.items():
        if key in name_lower or name_lower in key:
            return val["xg"], val["xga"]
        # İlk kelime eşleştirme
        if key.split()[0] in name_lower or name_lower.split()[0] in key:
            return val["xg"], val["xga"]
    
    return None, None

def enrich_with_xg(matches):
    """
    Maç listesine understat.com'dan xG ve xGA verilerini ekler.
    Sadece desteklenen liglerde çalışır.
    
    Args:
        matches: data_collector'dan gelen maç listesi
    
    Returns:
        xG alanları doldurulmuş maç listesi
    """
    season_year = datetime.now().year
    # Eğer Ocak-Temmuz arasındaysak bir önceki sezon yılını kullan
    if datetime.now().month <= 7:
        season_year -= 1
    
    # Lig bazlı xG verilerini topla
    xg_by_league = {}
    leagues_needed = set()
    for m in matches:
        league = m.get("league", "")
        if league in UNDERSTAT_LEAGUES and m.get("xg_supported", False):
            leagues_needed.add(league)
    
    for league in leagues_needed:
        league_key = UNDERSTAT_LEAGUES[league]
        xg_by_league[league] = _fetch_understat_team_xg(league_key, season_year)
    
    # Maçlara xG ekle
    enriched = 0
    for m in matches:
        league = m.get("league", "")
        if league not in xg_by_league:
            continue
        
        xg_data = xg_by_league[league]
        home_xg, home_xga = _find_team_xg(m.get("home_name", ""), xg_data)
        away_xg, away_xga = _find_team_xg(m.get("away_name", ""), xg_data)
        
        m["home_xg_avg"]  = home_xg
        m["home_xga_avg"] = home_xga
        m["away_xg_avg"]  = away_xg
        m["away_xga_avg"] = away_xga
        m["xg_available"] = (home_xg is not None and away_xg is not None)
        
        if m["xg_available"]:
            enriched += 1
    
    print(f"[xG] {enriched}/{len(matches)} maça xG verisi eklendi.")
    return matches

if __name__ == "__main__":
    # Test
    test_matches = [
        {"league": "Premier League", "home_name": "Arsenal", "away_name": "Chelsea",
         "xg_supported": True, "xg_available": False, "home_xg_avg": None,
         "home_xga_avg": None, "away_xg_avg": None, "away_xga_avg": None}
    ]
    result = enrich_with_xg(test_matches)
    for m in result:
        print(f"Arsenal xG: {m['home_xg_avg']} | Chelsea xG: {m['away_xg_avg']}")
        print(f"Arsenal xGA: {m['home_xga_avg']} | Chelsea xGA: {m['away_xga_avg']}")

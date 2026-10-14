"""
historical_data_sync.py — Çoklu Lig Gerçek Maç ve Oran Veri İndiricisi
========================================================================
Bu modül:
1. Premier Lig (9.000+ oranlı maç, 12.700+ skor)
2. La Liga (27.000+ maç)
3. Serie A (28.000+ maç)
4. Bundesliga (38.000+ maç)
5. Ligue 1 (france.csv)
6. Süper Lig (turkey.csv)
resmi açık kaynak repolarından indirir, temizler ve yerel önbelleğe kaydeder.
"""

import os
import sys
import csv
import io
import json
import requests
from typing import List, Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data", "historical")
os.makedirs(DATA_DIR, exist_ok=True)

# İsim eşleştirme sözlüğü (ESPN ile uyumlu standart isimler)
NAME_ALIASES = {
    "Man City": "Manchester City",
    "Man United": "Manchester United",
    "Spurs": "Tottenham Hotspur",
    "Tottenham": "Tottenham Hotspur",
    "Wolves": "Wolverhampton Wanderers",
    "Wolverhampton": "Wolverhampton Wanderers",
    "West Brom": "West Bromwich Albion",
    "Nott'm Forest": "Nottingham Forest",
    "Sheff Utd": "Sheffield United",
    "Sheff Wed": "Sheffield Wednesday",
    "Brighton": "Brighton & Hove Albion",
    "Bournemouth": "AFC Bournemouth",
    "Leeds": "Leeds United",
    "Leicester": "Leicester City",
    "Newcastle": "Newcastle United",
    "West Ham": "West Ham United",
    "Norwich": "Norwich City",
    "Ipswich": "Ipswich Town",
    "Luton": "Luton Town",
    "Southampton": "Southampton",
    "Atletico Madrid": "Atlético Madrid",
    "Athletic Bilbao": "Athletic Club",
    "Betis": "Real Betis",
    "Sociedad": "Real Sociedad",
    "Celta": "Celta Vigo",
    "Inter": "Internazionale",
    "Milan": "AC Milan",
    "Roma": "AS Roma",
    "Dortmund": "Borussia Dortmund",
    "Leverkusen": "Bayer Leverkusen",
    "M'gladbach": "Borussia Mönchengladbach",
    "Frankfurt": "Eintracht Frankfurt",
    "Bayern": "FC Bayern München",
    "PSG": "Paris Saint-Germain",
    "Marseille": "Olympique de Marseille",
    "Lyon": "Olympique Lyonnais",
    "Fenerbahce": "Fenerbahçe",
    "Galatasaray": "Galatasaray",
    "Besiktas": "Beşiktaş",
    "Trabzonspor": "Trabzonspor"
}


def clean_team_name(name: str) -> str:
    if not name:
        return ""
    n = name.strip()
    return NAME_ALIASES.get(n, n)


def sync_all_historical_datasets():
    print("=" * 80)
    print(" 📥 GERÇEK TARİHSEL MAÇ VE PİYASA ORANLARI SENKRONİZASYONU")
    print(f"    Hedef Klasör: {DATA_DIR}")
    print("=" * 80)

    # 1. Premier Lig (Detaylı Açılış & Kapanış Oranları ile)
    epl_url = "https://raw.githubusercontent.com/AnishKhetani/premier-league-data/main/data/processed/results_with_odds.csv"
    epl_path = os.path.join(DATA_DIR, "premier_league_with_odds.csv")
    
    if not os.path.exists(epl_path):
        print("[*] Premier Lig açılış/kapanış oranlı veri kümesi indiriliyor...")
        r = requests.get(epl_url, timeout=30)
        if r.status_code == 200:
            with open(epl_path, "w", encoding="utf-8") as f:
                f.write(r.text)
            print(f"[+] Premier Lig kaydedildi: {os.path.getsize(epl_path) / 1024:.1f} KB")
        else:
            print(f"[!] Premier Lig indirilemedi (HTTP {r.status_code})")
    else:
        print("[✓] Premier Lig veri kümesi yerelde mevcut.")

    # 2. Avrupa Ligleri (Skor & Sonuç Havuzu)
    league_files = {
        "spain.csv": "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/spain.csv",
        "italy.csv": "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/italy.csv",
        "germany.csv": "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/germany.csv",
        "france.csv": "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/france.csv",
        "turkey.csv": "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/turkey.csv"
    }

    for fname, url in league_files.items():
        l_path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(l_path):
            print(f"[*] {fname} indiriliyor...")
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    with open(l_path, "w", encoding="utf-8") as f:
                        f.write(r.text)
                    print(f"[+] {fname} kaydedildi: {os.path.getsize(l_path) / 1024:.1f} KB")
                else:
                    print(f"[!] {fname} indirilemedi (HTTP {r.status_code})")
            except Exception as e:
                print(f"[!] {fname} hata: {e}")
        else:
            print(f"[✓] {fname} yerelde mevcut.")

    print("\n[+] Tüm veri kümeleri başarıyla yerelleştirildi.")


def load_training_matches(min_season_year: int = 2021) -> List[Dict[str, Any]]:
    """
    Tüm liglerden son yıllara ait (örn 2021-2026) maçları birleştirip temizler.
    Dixon-Coles eğitimi için standart formatta liste döner.
    """
    matches = []

    # 1. Premier Lig (Skorlar + Oranlar)
    epl_odds_path = os.path.join(DATA_DIR, "premier_league_with_odds.csv")
    epl_scores_path = os.path.join(DATA_DIR, "premier_league_scores.csv")
    if os.path.exists(epl_odds_path) and os.path.exists(epl_scores_path):
        scores_by_id = {}
        with open(epl_scores_path, "r", encoding="utf-8") as fs:
            for row in csv.DictReader(fs):
                m_id = row.get("match_id")
                if m_id:
                    scores_by_id[m_id] = row

        with open(epl_odds_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                m_id = row.get("match_id")
                sc = scores_by_id.get(m_id, {})
                season = row.get("season", "")
                try:
                    start_yr = int(season.split("-")[0])
                    if start_yr < 100:  # 93-94 formatı
                        start_yr = 1900 + start_yr if start_yr > 50 else 2000 + start_yr
                except:
                    continue
                if start_yr < min_season_year:
                    continue

                home = clean_team_name(row.get("home_team"))
                away = clean_team_name(row.get("away_team"))
                fthg = sc.get("fthg", "")
                ftag = sc.get("ftag", "")
                if not home or not away or fthg == "" or ftag == "":
                    continue

                try:
                    hg = int(float(fthg))
                    ag = int(float(ftag))
                except:
                    continue

                # Oranlar (Bet365 / Pinnacle)
                o1 = row.get("bet365_1x2_home") or row.get("pinnacle_1x2_home") or row.get("market_avg_1x2_home")
                ox = row.get("bet365_1x2_draw") or row.get("pinnacle_1x2_draw") or row.get("market_avg_1x2_draw")
                o2 = row.get("bet365_1x2_away") or row.get("pinnacle_1x2_away") or row.get("market_avg_1x2_away")
                
                odds_dict = {}
                try:
                    if o1 and ox and o2 and float(o1) > 1.0:
                        odds_dict = {"1": float(o1), "X": float(ox), "2": float(o2)}
                except:
                    pass

                matches.append({
                    "league": "Premier League",
                    "date": row.get("date"),
                    "season": season,
                    "home_team": home,
                    "away_team": away,
                    "home_goals": hg,
                    "away_goals": ag,
                    "actual_result": "1" if hg > ag else ("X" if hg == ag else "2"),
                    "odds": odds_dict
                })


    # 2. Diğer Avrupa Ligleri
    league_map = {
        "spain.csv": "La Liga",
        "italy.csv": "Serie A",
        "germany.csv": "Bundesliga",
        "france.csv": "Ligue 1",
        "turkey.csv": "Süper Lig"
    }

    for fname, league_name in league_map.items():
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                season = row.get("Season")
                try:
                    s_yr = int(season)
                except:
                    continue
                if s_yr < min_season_year:
                    continue

                # Yalnızca 1. lig maçları (tier == '1')
                tier = row.get("tier", "1")
                if tier != "1":
                    continue

                home = clean_team_name(row.get("home"))
                away = clean_team_name(row.get("visitor"))
                hgoal = row.get("hgoal")
                vgoal = row.get("vgoal")
                if not home or not away or hgoal in ["NA", ""] or vgoal in ["NA", ""]:
                    continue

                try:
                    hg = int(hgoal)
                    ag = int(vgoal)
                except:
                    continue

                matches.append({
                    "league": league_name,
                    "date": row.get("Date"),
                    "season": str(season),
                    "home_team": home,
                    "away_team": away,
                    "home_goals": hg,
                    "away_goals": ag,
                    "actual_result": "1" if hg > ag else ("X" if hg == ag else "2"),
                    "odds": {}
                })

    return matches


if __name__ == "__main__":
    sync_all_historical_datasets()
    all_m = load_training_matches(min_season_year=2021)
    print(f"\n[+] 2021-2026 Arası Toplam Hazırlanan Kaliteli Maç: {len(all_m):,} adet")
    by_l = {}
    for m in all_m:
        by_l[m["league"]] = by_l.get(m["league"], 0) + 1
    for l, cnt in by_l.items():
        print(f"   • {l}: {cnt:,} maç")

"""
nesine_client.py — Nesine Canlı Bülten & Gerçek Oran Tersine Mühendislik İstemcisi
==================================================================================
Tersine Mühendislik Bulguları:
- Endpoint: https://cdnbulten.nesine.com/api/bulten/getprebultenfull
- Spor Grubu: data['sg']['EA'] (Event Array, TYPE==1 Futbol)
- Pazar Tipleri (MTID):
    * MTID 1:  Maç Sonucu 1X2 (N=1: 1, N=2: X, N=3: 2)
    * MTID 12: 2.5 Alt / Üst (SOV=2.5, N=1: Alt, N=2: Üst)
    * MTID 38: Karşılıklı Gol (N=1: Var, N=2: Yok)
    * MBS: Minimum Bahis Sayısı (1 veya 2)
"""

import time
import json
import gzip
import urllib.request
import urllib.error
import unicodedata
import re
from typing import Dict, Any, List, Optional, Tuple


NESINE_BULTEN_URL = "https://cdnbulten.nesine.com/api/bulten/getprebultenfull"
NESINE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nesine.com/iddaa",
    "Origin": "https://www.nesine.com",
    "Accept-Encoding": "gzip, deflate"
}


class NesineClient:
    """
    Nesine'nin CDN bülten API'sini okuyarak %100 gerçek resmi İddaa oranlarını çeker.
    """
    _cache_data: Optional[Dict[str, Any]] = None
    _cache_time: float = 0.0
    CACHE_TTL_SECONDS = 300  # 5 dakika önbellek

    @classmethod
    def fetch_full_bulletin(cls, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Nesine'deki tüm pre-match futbol maçlarını ve oranlarını çeker.
        """
        now = time.time()
        if not force_refresh and cls._cache_data and (now - cls._cache_time < cls.CACHE_TTL_SECONDS):
            return cls._cache_data

        try:
            req = urllib.request.Request(NESINE_BULTEN_URL, headers=NESINE_HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    content = gzip.decompress(content)
                raw_json = json.loads(content.decode("utf-8", errors="ignore"))
                
                events = raw_json.get("sg", {}).get("EA", [])
                leagues_map = {lg.get("LID"): lg.get("N") for lg in raw_json.get("sg", {}).get("LA", [])}

                parsed_matches = []
                for ev in events:
                    if ev.get("TYPE") != 1:  # Sadece Futbol
                        continue

                    home = ev.get("HN", "").strip()
                    away = ev.get("AN", "").strip()
                    code = ev.get("C")
                    date_str = ev.get("D", "")
                    time_str = ev.get("T", "")
                    league = leagues_map.get(ev.get("LC"), "Diğer")

                    odds_dict = {}
                    mbs_val = 1

                    for m in ev.get("MA", []):
                        mtid = m.get("MTID")
                        mbs_candidate = m.get("MBS", 1)
                        if mbs_candidate and mbs_candidate > mbs_val:
                            mbs_val = mbs_candidate

                        oca = m.get("OCA", [])
                        
                        # 1X2 Oranları (MTID == 1)
                        if mtid == 1:
                            for o in oca:
                                n_val = o.get("N")
                                odd_val = float(o.get("O", 0.0))
                                if n_val == 1: odds_dict["1"] = odd_val; odds_dict["ms_1"] = odd_val
                                elif n_val == 2: odds_dict["X"] = odd_val; odds_dict["ms_x"] = odd_val
                                elif n_val == 3: odds_dict["2"] = odd_val; odds_dict["ms_2"] = odd_val

                        # 2.5 Alt / Üst (MTID == 12)
                        elif mtid == 12 and m.get("SOV") == 2.5:
                            for o in oca:
                                n_val = o.get("N")
                                odd_val = float(o.get("O", 0.0))
                                if n_val == 1: odds_dict["2.5_alt"] = odd_val; odds_dict["under_2_5"] = odd_val
                                elif n_val == 2: odds_dict["2.5_ust"] = odd_val; odds_dict["over_2_5"] = odd_val

                        # Karşılıklı Gol Var / Yok (MTID == 38)
                        elif mtid == 38:
                            for o in oca:
                                n_val = o.get("N")
                                odd_val = float(o.get("O", 0.0))
                                if n_val == 1: odds_dict["kg_var"] = odd_val
                                elif n_val == 2: odds_dict["kg_yok"] = odd_val

                    # Eğer en azından 1X2 oranları varsa listeye ekle
                    if "1" in odds_dict and "X" in odds_dict and "2" in odds_dict:
                        parsed_matches.append({
                            "id": f"nesine_{code}",
                            "code": code,
                            "home_name": home,
                            "away_name": away,
                            "date": date_str,
                            "time_tr": time_str,
                            "league": league,
                            "mbs": mbs_val,
                            "odds": odds_dict,
                            "source": "NESINE_REA"
                        })

                cls._cache_data = parsed_matches
                cls._cache_time = now
                return parsed_matches

        except Exception as e:
            # Hata durumunda boş liste dön
            return []

    @classmethod
    def match_nesine_odds(cls, home_team: str, away_team: str) -> Optional[Dict[str, Any]]:
        """
        Başka bir kaynaktan gelen takım isimlerini Nesine bülteniyle eşleştirir.
        """
        bulten = cls.fetch_full_bulletin()
        if not bulten:
            return None

        def get_tokens(s: str) -> set:
            if not s:
                return set()
            s_clean = s.lower().strip()
            tr_map = {'ü': 'u', 'ö': 'o', 'ı': 'i', 'ş': 's', 'ç': 'c', 'ğ': 'g'}
            for k, v in tr_map.items():
                s_clean = s_clean.replace(k, v)
            s_clean = ''.join(c for c in unicodedata.normalize('NFD', s_clean) if unicodedata.category(c) != 'Mn')
            # Bilinen kısaltma ve lakapları eşitle
            s_clean = re.sub(r'\batl\b', 'atletico', s_clean)
            s_clean = re.sub(r'\bman\b', 'manchester', s_clean)
            s_clean = re.sub(r'\bmunich\b', 'munih', s_clean)
            s_clean = re.sub(r'\bmunchen\b', 'munih', s_clean)
            s_clean = re.sub(r'\binter\b', 'internazionale', s_clean)
            s_clean = re.sub(r'\b(united|utd)\b', 'utd', s_clean)
            s_clean = re.sub(r'\b(city|town|fc|cf|as|sk|fk|spor|sc|hove|albion)\b', '', s_clean)
            tokens = set(re.findall(r'[a-z0-9]{3,}', s_clean))
            return tokens

        ht = get_tokens(home_team)
        at = get_tokens(away_team)

        for m in bulten:
            # Gençler/U19/U21 maçlarını A takım yerine eşleştirmeyi önle
            m_home_lower = m["home_name"].lower()
            if ("u19" in m_home_lower or "u21" in m_home_lower) and ("u19" not in home_team.lower()):
                continue

            mht = get_tokens(m["home_name"])
            mat = get_tokens(m["away_name"])

            # Hem ev sahibi hem deplasman token kümelerinde ortak anlamlı kelime var mı?
            if (ht & mht) and (at & mat):
                return m

        return None

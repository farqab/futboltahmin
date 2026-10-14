"""
betfair_moneyway_client.py — Canlı Betfair Borsa Likiditesi & Moneyway Kazıyıcı (REA)
====================================================================================
Betfair Exchange borsasındaki canlı eşleşen para hacmini (£/€) ve 1X2 pazar
yüzdelerini hiçbir yapay simülasyon olmadan doğrudan canlı çeker.
DNS kısıtlamalarını aşmak için Cloudflare DoH (DNS-over-HTTPS) kullanır.
"""

import re
import socket
import time
import unicodedata
from typing import Dict, Any, List, Optional
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class BetfairMoneywayClient:
    """
    Arbworld / Betfair Moneyway canlı borsa likiditesi kazıyıcı istemcisi.
    """
    MONEYWAY_URL = "https://www.arbworld.net/moneyway/football/1x2"
    CACHE_TTL_SECONDS = 90  # 1.5 dakika önbellek (aynı bültende tekrar tekrar çekmez)

    _cached_data: Optional[List[Dict[str, Any]]] = None
    _last_fetch_time: float = 0.0
    _dns_cache: Dict[str, str] = {}
    _doh_installed: bool = False

    @classmethod
    def _install_doh_resolver(cls):
        """DNS engellerini aşmak için Cloudflare DoH (1.1.1.1) entegrasyonu kurar."""
        if cls._doh_installed:
            return

        orig_getaddrinfo = socket.getaddrinfo

        def doh_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            if host not in cls._dns_cache and any(k in host for k in ["arbworld", "betfair"]):
                try:
                    r = requests.get(
                        f"https://cloudflare-dns.com/dns-query?name={host}&type=A",
                        headers={"accept": "application/dns-json"},
                        timeout=3
                    ).json()
                    ips = [ans["data"] for ans in r.get("Answer", []) if ans.get("type") == 1]
                    if ips:
                        cls._dns_cache[host] = ips[0]
                except Exception:
                    pass

            if host in cls._dns_cache:
                return orig_getaddrinfo(cls._dns_cache[host], port, family, type, proto, flags)
            return orig_getaddrinfo(host, port, family, type, proto, flags)

        socket.getaddrinfo = doh_getaddrinfo
        cls._doh_installed = True

    @staticmethod
    def _clean_team_name(name: str) -> str:
        """Karşılaştırma için takım isimlerini temizler ve normalize eder."""
        if not name:
            return ""
        name = unicodedata.normalize("NFKD", name)
        name = "".join(c for c in name if not unicodedata.combining(c))
        name = name.lower()
        replacements = {
            "ü": "u", "ö": "o", "ı": "i", "ş": "s", "ç": "c", "ğ": "g",
            "united": "utd", "city": "cty", "football club": "", "fc": "",
            "sk": "", "fk": "", "u19": "", "u21": "", "(w)": "", "women": "",
            "-": " ", "_": " ", ".": ""
        }
        for k, v in replacements.items():
            name = name.replace(k, v)
        return " ".join(name.split())

    @staticmethod
    def _parse_num(val_str: str) -> float:
        """'€4,017' veya '100.0%' gibi metinleri saf float sayıya çevirir."""
        if not val_str:
            return 0.0
        cleaned = re.sub(r"[^\d.]", "", val_str.replace(",", ""))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @classmethod
    def fetch_live_moneyway_table(cls, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Canlı Betfair Moneyway tablosunu indirir ve maçları ayrıştırır.
        """
        now = time.time()
        if not force_refresh and cls._cached_data is not None and (now - cls._last_fetch_time < cls.CACHE_TTL_SECONDS):
            return cls._cached_data

        cls._install_doh_resolver()
        parsed_matches = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        try:
            resp = requests.get(cls.MONEYWAY_URL, headers=headers, timeout=8)
            if resp.status_code == 200:
                if BeautifulSoup is not None:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    rows = soup.find_all("tr")

                    for row in rows:
                        tds = row.find_all("td")
                        if len(tds) < 5:
                            continue

                        td_event = tds[0]
                        home = td_event.get("data-home") or ""
                        away = td_event.get("data-away") or ""
                        league = td_event.get("data-league") or ""
                        date_str = td_event.get("data-date") or ""

                        if not home or not away:
                            # Fallback span text parsing
                            ev_home = td_event.find("span", class_="ev-home")
                            ev_away = td_event.find("span", class_="ev-away")
                            if ev_home and ev_away:
                                home = ev_home.get_text(strip=True)
                                away = ev_away.get_text(strip=True)

                        if not home or not away:
                            continue

                        # 1X2 Oranlar, Yüzdeler ve Hacimler
                        def parse_col(td):
                            odd_el = td.find("div", class_="mw-odds")
                            pct_el = td.find("span", class_="mw-pct")
                            vol_el = td.find("span", class_="mw-vol")
                            odd = cls._parse_num(odd_el.get_text(strip=True)) if odd_el else 0.0
                            pct = cls._parse_num(pct_el.get_text(strip=True)) if pct_el else 0.0
                            vol = cls._parse_num(vol_el.get_text(strip=True)) if vol_el else 0.0
                            return odd, pct, vol

                        o1, p1, v1 = parse_col(tds[1])
                        ox, px, vx = parse_col(tds[2])
                        o2, p2, v2 = parse_col(tds[3])

                        tot_el = tds[4].find("div", class_="vl-vol")
                        tot_vol = cls._parse_num(tot_el.get_text(strip=True)) if tot_el else (v1 + vx + v2)

                        # Betfair Market Link / ID
                        market_id = None
                        link_el = tds[4].find("a", href=re.compile(r"market/1\.\d+"))
                        if link_el:
                            m_match = re.search(r"1\.\d+", link_el["href"])
                            if m_match:
                                market_id = m_match.group(0)

                        parsed_matches.append({
                            "home_team": home,
                            "away_team": away,
                            "home_clean": cls._clean_team_name(home),
                            "away_clean": cls._clean_team_name(away),
                            "league": league,
                            "date": date_str,
                            "odd_1": o1, "pct_1": p1, "vol_1": v1,
                            "odd_x": ox, "pct_x": px, "vol_x": vx,
                            "odd_2": o2, "pct_2": p2, "vol_2": v2,
                            "total_volume": tot_vol,
                            "betfair_market_id": market_id
                        })
                else:
                    # Sıfır bağımlılık: Regex HTML Ayrıştırıcı
                    tr_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', resp.text, re.DOTALL | re.IGNORECASE)
                    for r_html in tr_matches:
                        tds = re.findall(r'<td[^>]*>(.*?)</td>', r_html, re.DOTALL | re.IGNORECASE)
                        if len(tds) < 5:
                            continue
                        td_ev = tds[0]
                        h_m = re.search(r'data-home=["\']([^"\']+)["\']', td_ev)
                        a_m = re.search(r'data-away=["\']([^"\']+)["\']', td_ev)
                        home = h_m.group(1) if h_m else ""
                        away = a_m.group(1) if a_m else ""
                        if not home or not away:
                            ev_h = re.search(r'class=["\'][^"\']*ev-home[^"\']*["\'][^>]*>([^<]+)<', td_ev)
                            ev_a = re.search(r'class=["\'][^"\']*ev-away[^"\']*["\'][^>]*>([^<]+)<', td_ev)
                            if ev_h and ev_a:
                                home = ev_h.group(1).strip()
                                away = ev_a.group(1).strip()
                        if not home or not away:
                            continue
                        l_m = re.search(r'data-league=["\']([^"\']+)["\']', td_ev)
                        d_m = re.search(r'data-date=["\']([^"\']+)["\']', td_ev)
                        league = l_m.group(1) if l_m else ""
                        date_str = d_m.group(1) if d_m else ""

                        def parse_col_re(td_str):
                            o_m = re.search(r'class=["\'][^"\']*mw-odds[^"\']*["\'][^>]*>([^<]+)<', td_str)
                            p_m = re.search(r'class=["\'][^"\']*mw-pct[^"\']*["\'][^>]*>([^<]+)<', td_str)
                            v_m = re.search(r'class=["\'][^"\']*mw-vol[^"\']*["\'][^>]*>([^<]+)<', td_str)
                            odd = cls._parse_num(o_m.group(1)) if o_m else 0.0
                            pct = cls._parse_num(p_m.group(1)) if p_m else 0.0
                            vol = cls._parse_num(v_m.group(1)) if v_m else 0.0
                            return odd, pct, vol

                        o1, p1, v1 = parse_col_re(tds[1])
                        ox, px, vx = parse_col_re(tds[2])
                        o2, p2, v2 = parse_col_re(tds[3])

                        tot_m = re.search(r'class=["\'][^"\']*vl-vol[^"\']*["\'][^>]*>([^<]+)<', tds[4])
                        tot_vol = cls._parse_num(tot_m.group(1)) if tot_m else (v1 + vx + v2)

                        market_id = None
                        m_link = re.search(r'href=["\'][^"\']*market/(1\.\d+)[^"\']*["\']', tds[4])
                        if m_link:
                            market_id = m_link.group(1)

                        parsed_matches.append({
                            "home_team": home,
                            "away_team": away,
                            "home_clean": cls._clean_team_name(home),
                            "away_clean": cls._clean_team_name(away),
                            "league": league,
                            "date": date_str,
                            "odd_1": o1, "pct_1": p1, "vol_1": v1,
                            "odd_x": ox, "pct_x": px, "vol_x": vx,
                            "odd_2": o2, "pct_2": p2, "vol_2": v2,
                            "total_volume": tot_vol,
                            "betfair_market_id": market_id
                        })

                cls._cached_data = parsed_matches
                cls._last_fetch_time = now
        except Exception as e:
            # Hata durumunda boş liste döner, ASLA SAHTE VERİ ÜRETMEZ
            pass

        return cls._cached_data or []

    @classmethod
    def classify_money_flow(cls, volume_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Betfair işlem hacmini SHARP_WHALE, PUBLIC_STEAM_TRAP, BALANCED olarak sınıflandırır."""
        if not volume_data:
            return {
                "has_volume_data": False,
                "volume_gbp": 0.0,
                "dominance_pct": 0.0,
                "target_market": None,
                "flow_type": "BALANCED"
            }
        tot = float(volume_data.get("total_matched_gbp", 0.0) or volume_data.get("volume_gbp", 0.0))
        s1 = float(volume_data.get("share_1", 0.0))
        sx = float(volume_data.get("share_x", 0.0))
        s2 = float(volume_data.get("share_2", 0.0))
        max_s = max(s1, sx, s2)
        tgt = "MS 1" if s1 == max_s else ("MS 2" if s2 == max_s else "MS X")
        is_w = (tot >= 50000.0) and (max_s >= 70.0)

        drift = kwargs.get("drift") or volume_data.get("odds_drift") or {}
        drift_sig = drift.get("signal", "") if isinstance(drift, dict) else ""
        if is_w and ((tgt == "MS 1" and "DOUBT_HOME" in drift_sig) or (tgt == "MS 2" and "DOUBT_AWAY" in drift_sig) or volume_data.get("is_steam_trap")):
            f_type = "PUBLIC_STEAM_TRAP"
        elif is_w:
            f_type = "SHARP_WHALE"
        else:
            f_type = "BALANCED"

        return {
            "has_volume_data": tot > 0,
            "volume_gbp": tot,
            "dominance_pct": max_s,
            "target_market": tgt if is_w else None,
            "flow_type": f_type
        }

    @classmethod
    def match_volume(cls, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Verilen maç için Betfair canlı para hacmini arar ve eşleştirir.
        Bulamazsa dürüstçe has_volume_data=False döner (SIFIR HALÜSİNASYON).
        """
        table = cls.fetch_live_moneyway_table()
        if not table or not home_team or not away_team:
            return {
                "has_volume_data": False,
                "total_matched_gbp": 0.0,
                "volume_gbp": 0.0,
                "dominance_pct": 0.0,
                "target_market": None,
                "flow_type": "BALANCED",
                "status": "DATA_PENDING",
                "source": "NONE"
            }

        h_clean = cls._clean_team_name(home_team)
        a_clean = cls._clean_team_name(away_team)

        for item in table:
            ih_clean = item["home_clean"]
            ia_clean = item["away_clean"]

            # 1. Tam eşleşme
            exact_match = (h_clean == ih_clean and a_clean == ia_clean)

            # 2. İçeriksel / Alt kelime eşleşmesi
            sub_match = (
                (h_clean in ih_clean or ih_clean in h_clean) and
                (a_clean in ia_clean or ia_clean in a_clean)
            )

            # 3. İlk kelime eşleşmesi (örn: Newcastle <-> Newcastle United)
            h_first = h_clean.split()[0] if h_clean else ""
            a_first = a_clean.split()[0] if a_clean else ""
            first_match = (
                len(h_first) >= 4 and len(a_first) >= 4 and
                h_first in ih_clean and a_first in ia_clean
            )

            if exact_match or sub_match or first_match:
                tot = item["total_volume"]
                s1, sx, s2 = item["pct_1"], item["pct_x"], item["pct_2"]
                max_s = max(s1, sx, s2)
                dominant_tgt = "MS 1" if s1 == max_s else ("MS 2" if s2 == max_s else "MS X")
                is_whale = (tot >= 50000.0) and (max_s >= 70.0)
                flow_type = "SHARP_WHALE" if is_whale else "BALANCED"

                return {
                    "has_volume_data": tot > 0,
                    "total_matched_gbp": tot,
                    "volume_gbp": tot,
                    "vol_1_gbp": item["vol_1"],
                    "vol_x_gbp": item["vol_x"],
                    "vol_2_gbp": item["vol_2"],
                    "share_1": s1,
                    "share_x": sx,
                    "share_2": s2,
                    "dominance_pct": max_s,
                    "target_market": dominant_tgt if is_whale else None,
                    "flow_type": flow_type,
                    "betfair_market_id": item.get("betfair_market_id"),
                    "source": "BETFAIR_LIVE_EXCHANGE",
                    "status": "CONFIRMED"
                }

        return {
            "has_volume_data": False,
            "total_matched_gbp": 0.0,
            "volume_gbp": 0.0,
            "dominance_pct": 0.0,
            "target_market": None,
            "flow_type": "BALANCED",
            "status": "DATA_PENDING",
            "source": "NONE"
        }


def classify_money_flow(volume_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    return BetfairMoneywayClient.classify_money_flow(volume_data, **kwargs)


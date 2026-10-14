import os
import sys
import json
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

leagues = {
    'tur.1': 'Süper Lig',
    'eng.1': 'Premier League',
    'esp.1': 'La Liga',
    'ger.1': 'Bundesliga',
    'ita.1': 'Serie A',
    'fra.1': 'Ligue 1'
}

pred_data = {d['id']: d for d in json.load(open('tahminler_20260919.json', encoding='utf-8'))}

finished = []
live = []
upcoming = []

for code, lg_name in leagues.items():
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates=20260919"
    try:
        r = requests.get(url, timeout=6).json()
        for ev in r.get('events', []):
            c = ev['competitions'][0]
            st = c.get('status', {}).get('type', {})
            state = st.get('state', '')
            status_desc = st.get('description', '')
            clock = c.get('status', {}).get('displayClock', '')
            
            comps = c['competitors']
            h = comps[0] if comps[0].get('homeAway') == 'home' else comps[1]
            a = comps[1] if comps[0].get('homeAway') == 'home' else comps[0]
            
            hs = int(h.get('score', 0)) if h.get('score') is not None else 0
            as_ = int(a.get('score', 0)) if a.get('score') is not None else 0
            
            act_res = 'MS 1' if hs > as_ else ('MS 2' if as_ > hs else 'MS X')
            act_ou = '2.5 ÜST' if (hs + as_) > 2.5 else '2.5 ALT'
            act_btts = 'KG VAR' if (hs > 0 and as_ > 0) else 'KG YOK'
            
            p = pred_data.get(ev.get('id'), {})
            pred_ms = p.get('tahmin_ms', '-')
            pred_ou = '2.5 ÜST' if p.get('over_2_5_prob', 50) >= 50 else '2.5 ALT'
            pred_btts = 'KG VAR' if p.get('btts_prob', 50) >= 50 else 'KG YOK'
            
            item = {
                'league': lg_name,
                'home': h['team']['displayName'],
                'away': a['team']['displayName'],
                'score': f"{hs} - {as_}",
                'act_res': act_res,
                'pred_ms': pred_ms,
                'ms_hit': (act_res == pred_ms),
                'act_ou': act_ou,
                'pred_ou': pred_ou,
                'ou_prob': p.get('over_2_5_prob', 0),
                'ou_hit': (act_ou == pred_ou),
                'act_btts': act_btts,
                'pred_btts': pred_btts,
                'btts_prob': p.get('btts_prob', 0),
                'btts_hit': (act_btts == pred_btts),
                'action_label': p.get('action_label', '-'),
                'action_status': p.get('action_status', '-'),
                'status_desc': status_desc,
                'clock': clock
            }
            
            if state == 'post':
                finished.append(item)
            elif state == 'in':
                live.append(item)
            else:
                upcoming.append(item)
    except Exception as e:
        print(f"Hata: {e}")

print("=== 19:00 İTİBARIYLA BİTEN MAÇLAR RAPORU ===")
print(f"Biten Maç Sayısı: {len(finished)}")
print(f"Canlı Devam Eden: {len(live)}")
print(f"Başlamayan: {len(upcoming)}\n")

print("JSON_START")
print(json.dumps({
    'finished': finished,
    'live': live,
    'upcoming': upcoming
}, ensure_ascii=False, indent=2))
print("JSON_END")

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

pred_file = 'tahminler_20260919.json'
pred_data = {d['id']: d for d in json.load(open(pred_file, encoding='utf-8'))}

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

print("==========================================================================================")
print("                           BİTEN MAÇLAR VE TAHMİN SONUÇLARI                              ")
print("==========================================================================================")
for m in finished:
    ms_icon = "✅" if m['ms_hit'] else "❌"
    ou_icon = "✅" if m['ou_hit'] else "❌"
    btts_icon = "✅" if m['btts_hit'] else "❌"
    print(f"[{m['league'][:7]}] {m['home']} {m['score']} {m['away']}")
    print(f"   Taraf: Beklenen {m['pred_ms']} -> Gerçek {m['act_res']} {ms_icon} | Alt/Üst: Beklenen {m['pred_ou']} ({m['ou_prob']}%) -> Gerçek {m['act_ou']} {ou_icon} | KG: Beklenen {m['pred_btts']} ({m['btts_prob']}%) -> Gerçek {m['act_btts']} {btts_icon}")
    print(f"   Kategori: {m['action_label']}\n")

print("==========================================================================================")
print("                                 GENEL İSTATİSTİKLER                                     ")
print("==========================================================================================")
total_f = len(finished)
ms_hits = sum(1 for m in finished if m['ms_hit'])
ou_hits = sum(1 for m in finished if m['ou_hit'])
btts_hits = sum(1 for m in finished if m['btts_hit'])

print(f"Toplam Biten Maç: {total_f}")
print(f"MS (Taraf) Başarısı:       {ms_hits} / {total_f} (%{ms_hits/total_f*100:.1f})")
print(f"2.5 Alt / Üst Başarısı:   {ou_hits} / {total_f} (%{ou_hits/total_f*100:.1f})")
print(f"KG Var / Yok Başarısı:     {btts_hits} / {total_f} (%{btts_hits/total_f*100:.1f})")

# Kategori bazlı istatistikler
by_action = {}
for m in finished:
    cat = m['action_label']
    if cat not in by_action:
        by_action[cat] = {'count': 0, 'ms': 0, 'ou': 0, 'btts': 0, 'ou_ust_hit': 0, 'btts_var_hit': 0}
    by_action[cat]['count'] += 1
    if m['ms_hit']: by_action[cat]['ms'] += 1
    if m['ou_hit']: by_action[cat]['ou'] += 1
    if m['btts_hit']: by_action[cat]['btts'] += 1

print("\n--- KATEGORİ DETAYLARI ---")
for cat, s in by_action.items():
    c = s['count']
    print(f"📌 {cat} (Toplam {c} maç):")
    print(f"   - Taraf: {s['ms']}/{c} (%{s['ms']/c*100:.1f})")
    print(f"   - 2.5 A/Ü: {s['ou']}/{c} (%{s['ou']/c*100:.1f})")
    print(f"   - KG: {s['btts']}/{c} (%{s['btts']/c*100:.1f})")

print("\n==========================================================================================")
print("                                  CANLI MAÇLAR                                           ")
print("==========================================================================================")
for m in live:
    print(f"[{m['league']}] {m['home']} {m['score']} {m['away']} ({m['status_desc']} {m['clock']}) | Kategori: {m['action_label']} | Taraf: {m['pred_ms']}, 2.5: {m['pred_ou']}, KG: {m['pred_btts']}")

print("\n==========================================================================================")
print("                                 BEKLEYEN MAÇLAR                                          ")
print("==========================================================================================")
for m in upcoming:
    print(f"[{m['league']}] {m['home']} vs {m['away']} | Kategori: {m['action_label']} | Taraf: {m['pred_ms']}, 2.5: {m['pred_ou']}, KG: {m['pred_btts']}")

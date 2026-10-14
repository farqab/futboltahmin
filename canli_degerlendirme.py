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
            comps = c['competitors']
            h = comps[0] if comps[0].get('homeAway') == 'home' else comps[1]
            a = comps[1] if comps[0].get('homeAway') == 'home' else comps[0]
            hs = int(h.get('score', 0)) if h.get('score') is not None else 0
            as_ = int(a.get('score', 0)) if a.get('score') is not None else 0
            
            act_res = 'MS 1' if hs > as_ else ('MS 2' if as_ > hs else 'MS X')
            act_ou = (hs + as_) > 2.5
            
            p = pred_data.get(ev.get('id'), {})
            pred_ms = p.get('tahmin_ms', '-')
            pred_ou = p.get('over_2_5_prob', 50) >= 50
            
            item = {
                'league': lg_name,
                'h': h['team']['displayName'],
                'a': a['team']['displayName'],
                's': f"{hs} - {as_}",
                'act': act_res,
                'pred': pred_ms,
                'act_ou': act_ou,
                'pred_ou': pred_ou,
                'lbl': p.get('action_label', '-'),
                'status_act': p.get('action_status', '-'),
                'clk': c.get('status', {}).get('displayClock', ''),
                'desc': st.get('description', '')
            }
            if state == 'post':
                finished.append(item)
            elif state == 'in':
                live.append(item)
            else:
                upcoming.append(item)
    except Exception as e:
        print(f"Hata ({lg_name}): {e}")

print("=" * 75)
print(f"  📊 18:20 İTİBARIYLA GÜNÜN TÜM MAÇLARININ DETAYLI DEĞERLENDİRMESİ")
print("=" * 75)
print(f"Toplam Maç: 27 | Biten: {len(finished)} | Canlı Devam Eden: {len(live)} | Başlamayan: {len(upcoming)}\n")

print("--- 🏁 1. TAMAMLANAN MAÇLAR VE MODELİN İSABETİ ---")
f_ms_hit = 0
f_ou_hit = 0
for m in finished:
    m_hit = (m['act'] == m['pred'])
    o_hit = (m['act_ou'] == m['pred_ou'])
    if m_hit: f_ms_hit += 1
    if o_hit: f_ou_hit += 1
    hit_str = "✅ TUTTU" if m_hit else "❌ YATTI"
    ou_str = "GOL TUTTU" if o_hit else "GOL YATTI"
    print(f"• [{m['league']}] {m['h']} {m['s']} {m['a']} | Sonuç: {m['act']} | Model: {m['pred']} ({hit_str}) | {ou_str} | {m['lbl']}")

if finished:
    print(f"\n👉 Biten Maç Karnesi: Taraf İsabeti: {f_ms_hit}/{len(finished)} (%{round(f_ms_hit/len(finished)*100, 1)}) | 2.5 Alt/Üst: {f_ou_hit}/{len(finished)} (%{round(f_ou_hit/len(finished)*100, 1)})\n")

print("--- ⚡ 2. ŞU AN CANLI OYNANAN MAÇLAR (ANLIK SKORLAR) ---")
for m in live:
    m_hit = (m['act'] == m['pred'])
    hit_str = "✅ ÖNDE/TUTUYOR" if m_hit else "❌ GERİDE/YATIYOR"
    print(f"• [{m['league']}] {m['h']} {m['s']} {m['a']} ({m['desc']} {m['clk']}) | Anlık: {m['act']} | Model: {m['pred']} ({hit_str}) | {m['lbl']}")

print("\n--- ⏳ 3. HENÜZ BAŞLAMAYAN MAÇLAR (AKŞAM BÜLTENİ) ---")
for m in upcoming:
    print(f"• [{m['league']}] {m['h']} vs {m['a']} | Model: {m['pred']} | Kategori: {m['lbl']}")

print("=" * 75)

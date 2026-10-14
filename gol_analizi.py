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

goal_matches = []
for code, lg_name in leagues.items():
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates=20260919"
    try:
        r = requests.get(url, timeout=6).json()
        for ev in r.get('events', []):
            p = pred_data.get(ev.get('id'), {})
            if 'GOL' in p.get('action_label', ''):
                c = ev['competitions'][0]
                st = c.get('status', {}).get('type', {})
                state = st.get('state', '')
                comps = c['competitors']
                h = comps[0] if comps[0].get('homeAway') == 'home' else comps[1]
                a = comps[1] if comps[0].get('homeAway') == 'home' else comps[0]
                hs = int(h.get('score', 0)) if h.get('score') is not None else 0
                as_ = int(a.get('score', 0)) if a.get('score') is not None else 0
                total_goals = hs + as_
                actual_ou = '2.5 ÜST' if total_goals > 2.5 else '2.5 ALT'
                actual_btts = 'KG VAR' if (hs > 0 and as_ > 0) else 'KG YOK'
                
                pred_ou = '2.5 ÜST' if p.get('over_2_5_prob', 50) >= 50 else '2.5 ALT'
                pred_btts = 'KG VAR' if p.get('btts_prob', 50) >= 50 else 'KG YOK'
                
                goal_matches.append({
                    'league': lg_name,
                    'h': h['team']['displayName'],
                    'a': a['team']['displayName'],
                    'score': f"{hs} - {as_}",
                    'total_goals': total_goals,
                    'state': state,
                    'desc': st.get('description', ''),
                    'clock': c.get('status', {}).get('displayClock', ''),
                    'actual_ou': actual_ou,
                    'pred_ou': pred_ou,
                    'ou_prob': p.get('over_2_5_prob', 0),
                    'actual_btts': actual_btts,
                    'pred_btts': pred_btts,
                    'btts_prob': p.get('btts_prob', 0),
                    'is_ou_hit': (actual_ou == pred_ou),
                    'is_btts_hit': (actual_btts == pred_btts)
                })
    except Exception as e:
        print(f"Hata: {e}")

print("=" * 75)
print("     🟡 'SADECE GOL OYNA' KATEGORİSİNDEKİ MAÇLARIN KARNESİ")
print("=" * 75)

finished_or_late = [m for m in goal_matches if m['state'] in ['post', 'in']]
ou_hits = sum(1 for m in finished_or_late if m['is_ou_hit'])
btts_hits = sum(1 for m in finished_or_late if m['is_btts_hit'])

print(f"Toplam 'Sadece Gol Oyna' Maç Sayısı: {len(goal_matches)}")
print(f"Şu Ana Kadar Oynanan/Biten: {len(finished_or_late)} | Henüz Başlamayan (Akşam): {len(goal_matches) - len(finished_or_late)}\n")

for i, m in enumerate(goal_matches, 1):
    if m['state'] == 'post':
        badge = "[🏁 BİTTİ]"
    elif m['state'] == 'in':
        badge = f"[⚡ CANLI {m['clock']}]"
    else:
        badge = "[⏳ BAŞLAMADI]"
        
    ou_hit_icon = "✅ TUTTU" if m['is_ou_hit'] else "❌ YATTI"
    btts_hit_icon = "✅ TUTTU" if m['is_btts_hit'] else "❌ YATTI"
    
    print(f"{i}. [{m['league']}] {m['h']} {m['score']} {m['a']} {badge}")
    print(f"   👉 2.5 Alt/Üst: Tahmin: {m['pred_ou']} (%{m['ou_prob']}) -> Gerçek: {m['actual_ou']} ({ou_hit_icon})")
    print(f"   👉 Karşılıklı Gol: Tahmin: {m['pred_btts']} (%{m['btts_prob']}) -> Gerçek: {m['actual_btts']} ({btts_hit_icon})")
    print("-" * 70)

print("\n" + "=" * 75)
print(f"🏆 OYNANAN / DEVAM EDEN MAÇLARDA GOL KARNESİ:")
print(f"   • 2.5 Alt / Üst İsabeti: {ou_hits}/{len(finished_or_late)} (%{round(ou_hits/len(finished_or_late)*100, 1)})")
print(f"   • Karşılıklı Gol (KG) İsabeti: {btts_hits}/{len(finished_or_late)} (%{round(btts_hits/len(finished_or_late)*100, 1)})")
print("=" * 75)

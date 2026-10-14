import os
import sys
import json
import time
import webbrowser
from datetime import datetime

# Windows Terminal UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI"
os.chdir(PROJECT_DIR)

from data_collector import fetch_real_matches_for_date
from typesafe_engine import analyze_all_matches_parallel
from core_pipeline import run_quantitative_pipeline, print_pipeline_report
from global_market_intelligence import GlobalMarketIntelligence
from html_dashboard import generate_html_report

def run_daily_prediction(target_date=None):
    date_label = target_date if target_date else "Canlı / Güncel Bülten"
    print("=" * 75)
    print(f"   ⚽ FUTBOL TAHMİN AI | 3'LÜ KÜRESEL SHARP İSTİHBARAT BÜLTENİ   ")
    print(f"   Tarih: {date_label}  |  Flashscore + Pinnacle + Dropping Odds   ")
    print("=" * 75)
    
    t0 = time.time()
    
    # 1. 100% Gerçek Verileri Çek (H2H, xG, deplasman formu, rotation riski dahil)
    matches = fetch_real_matches_for_date(target_date)
    if not matches:
        print("[!] Belirtilen tarihte canlı/oynanmamış maç bulunamadı.")
        if os.path.exists("gunluk_bulten.html"):
            print("📊 En güncel bülten paneli tarayıcınızda açılıyor...")
            try:
                webbrowser.open(f"file:///{os.path.abspath('gunluk_bulten.html').replace(os.sep, '/')}")
            except:
                pass
        return
        
    print(f"[+] Toplam {len(matches)} adet doğrulanmış maç bültene alındı.\n")
    
    # 2. Dixon-Coles Bivariate Poisson & 4'lü Küresel Sharp İstihbarat Boru Hattı
    print("=" * 75)
    print(" 🌐 4'LÜ KÜRESEL SHARP & VIP SENDİKA RADARI DEVREYE ALINIYOR:")
    print("    ⚡ 1. Flashscore Ninja: Resmi İlk 11, Dizilişler & Eksik Analizi")
    print("    🎯 2. Pinnacle Benchmark: Saf Gerçek Çizgi & Sazan Tuzağı Korunması")
    print("    🌊 3. Dropping Odds: Çoklu Yabancı Büro Oran Çöküşü & Veto Motoru")
    print("    👑 4. VIP Baron Radarı: Betfair Matched Volume, Moneyway & Asya Çizgisi")
    print("=" * 75)
    quant_res = run_quantitative_pipeline(matches, record_to_ledger=False, bankroll=1000.0)
    print_pipeline_report(quant_res)
    
    # 2.5 4'LÜ KÜRESEL SHARP & VIP RADAR VERİLERİNİ TYPESAFE ÖNCESİ MAÇLARA ENJEKTE ET
    for m in matches:
        m_title = f"{m.get('home_name')} vs {m.get('away_name')}"
        q_m = next((qm for qm in quant_res.get("analyzed_matches", []) if qm.get("match") == m_title), None)
        if q_m:
            m["quant_data"] = q_m
            m["value_bets"] = q_m.get("value_bets", [])
            if q_m.get("value_bets"):
                top_bet = q_m["value_bets"][0]
                m["global_verdict"] = top_bet.get("smart_money_verdict", "APPROVED")
                m["global_reason"] = top_bet.get("smart_money_reason", "Piyasa onaylı")
                m["is_global_vetoed"] = False
                m["ev_pct"] = top_bet.get("ev_pct", 0.0)
                m["recommended_stake"] = top_bet.get("recommended_stake", 0.0)
                m["signals"] = top_bet.get("signals", {})
            else:
                top_cand = next((c for c in q_m.get("candidates", []) if "MS 1" in c.get("market", "")), None)
                if not top_cand and q_m.get("candidates"):
                    top_cand = q_m["candidates"][0]
                
                if top_cand and top_cand.get("global_intelligence"):
                    gi = top_cand["global_intelligence"]
                    m["global_verdict"] = gi.get("verdict", "DEĞER YOK / PAS")
                    m["global_reason"] = gi.get("rationale", "Piyasa marjı üzerinde istatistiksel üstünlük bulunamadı")
                    m["is_global_vetoed"] = gi.get("is_vetoed", False)
                    m["signals"] = gi.get("signals", {})
                else:
                    m["global_verdict"] = "DEĞER YOK / PAS"
                    m["global_reason"] = "Piyasa marjı üzerinde istatistiksel üstünlük bulunamadı"
                    m["is_global_vetoed"] = False
                    m["signals"] = {}
        else:
            rej = next((rm for rm in quant_res.get("rejected_matches", []) if rm.get("match") == m_title), None)
            if rej:
                m["global_verdict"] = "REDDEDİLDİ"
                m["global_reason"] = rej.get("reason", "No Data, No Bet")
                m["is_global_vetoed"] = True
                m["signals"] = {}

    # 3. TypeSafe AI ile Zenginleştirilmiş Paralel Analiz (4'lü Küresel Radar Doğrudan Etkiler)
    results = analyze_all_matches_parallel(matches, max_workers=8)

    # 5. JSON Önbelleğe Kaydet
    file_date_tag = target_date if target_date else datetime.now().strftime("%Y%m%d")
    json_path = os.path.join(PROJECT_DIR, f"tahminler_{file_date_tag}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[+] Ham analiz verisi kaydedildi: {json_path}")
    
    # 6. Modern HTML Dashboard Üret
    html_filename   = f"gunluk_bulten_{file_date_tag}.html"
    html_path       = os.path.join(PROJECT_DIR, html_filename)
    main_html_path  = os.path.join(PROJECT_DIR, "gunluk_bulten.html")
    
    generate_html_report(results, report_date=file_date_tag, output_file=html_path)
    generate_html_report(results, report_date=file_date_tag, output_file=main_html_path)
    
    # 5. Konsol Özeti
    bankolar   = [r for r in results if r.get("action_status") == "BET"]
    gol_oyna   = [r for r in results if r.get("action_status") == "GOAL_ONLY"]
    pas_gec    = [r for r in results if r.get("action_status") == "NO_BET"]
    xg_sayisi  = sum(1 for r in results if r.get("xg_available", False))
    rotation_r = sum(1 for r in results if r.get("home_rotation_risk") or r.get("away_rotation_risk"))
    
    print("\n" + "=" * 65)
    print("            ⭐ GÜNÜN ÖNE ÇIKAN EN KRİTİK MAÇLARI            ")
    print("=" * 65)
    
    for idx, r in enumerate(results[:8], start=1):
        odds = r.get("odds") or {}
        kg_bilgi = f"{r.get('kg_tahmin', 'KG ?')} ({r.get('btts_conf', '-')} güven)"
        xg_bilgi = ""
        if r.get("xg_available"):
            xg_bilgi = f" | xG: Ev {r.get('home_xg_avg')} vs Dep {r.get('away_xg_avg')}"
        
        o1 = odds.get('open_1', odds.get('ms_1', '-'))
        ox = odds.get('open_x', odds.get('ms_x', '-'))
        o2 = odds.get('open_2', odds.get('ms_2', '-'))
        c1 = odds.get('close_1', odds.get('ms_1', '-'))
        cx = odds.get('close_x', odds.get('ms_x', '-'))
        c2 = odds.get('close_2', odds.get('ms_2', '-'))
        drift_str = f" | {r.get('odds_drift_desc')}" if r.get('odds_drift_desc') else ""

        print(f"{idx}. [{r['flag']} {r['league']}] {r['time_tr']} TSİ | {r['home_name']} vs {r['away_name']}")
        print(f"   👑 EN İDEAL TERCİH: {r.get('optimal_market')} -> Oran: {r.get('optimal_odds')} | Güven: %{r.get('optimal_confidence')}")
        print(f"   👉 Taraf Analizi: {r['tahmin_ms']} ({r['tahmin_kazanan']}) | Güven: %{r['confidence']} | 2.5 Üst: %{r['over_2_5_prob']} | {kg_bilgi}{xg_bilgi}")
        print(f"   📈 Oran Hareketi: Açılış [{o1} - {ox} - {o2}] ➔ Güncel [{c1} - {cx} - {c2}]{drift_str}")
        if r.get("sim_prob_over_1_5") is not None:
            print(f"   🎲 10k Simülasyon: 1.5 Üst %{r.get('sim_prob_over_1_5')} | 2.5 Üst %{r.get('sim_prob_over_2_5')} | KG %{r.get('sim_prob_btts')} | En Olası Skor: {r.get('sim_top_score_str')} (Gol Beklentisi: {r.get('expected_total_goals')})")
        print(f"   ⚠️ Tuzak/Risk: {r['trap_score']}/10 | Oranlar: 1({odds.get('ms_1')}) - X({odds.get('ms_x')}) - 2({odds.get('ms_2')})")
        print(f"   📊 Karar: {r['action_label']}")
        if r.get("global_verdict"):
            print(f"   🌐 KÜRESEL SHARP RADARI: {r['global_verdict']} -> {r.get('global_reason', '')}")
            if r.get("ev_pct"):
                print(f"   💎 NİCELİKSEL DEĞER: +%{r['ev_pct']} EV | 1/4 Kelly Önerisi: {r.get('recommended_stake')} TL")
            if "WHALE" in str(r.get("global_verdict")) or "BARON" in str(r.get("global_reason")):
                print(f"   👑 VIP BARON RADARI: Büyük Para Girişi / Sendika Onaylı!")
        if r.get("sofascore_rating_home"):
            diff = r.get('sofascore_rating_diff', 0.0)
            diff_str = f"+{diff}" if diff > 0 else f"{diff}"
            print(f"   👑 SofaScore: Ev {r.get('sofascore_rating_home')} vs Dep {r.get('sofascore_rating_away')} ({diff_str}) | {r.get('sofascore_momentum')} ({r.get('sofascore_momentum_score')}/100)")
        if r.get("trap_type") and r.get("trap_type") != "KALITE_ONAYLI":
            print(f"   🛡️ TUZAK AVCISI: {r.get('trap_type')} (Eleme: {r.get('action_status')})")
        if r.get("h2h_total", 0) > 0:
            print(f"   🔄 H2H: {r.get('h2h_summary', '-')}")
        print(f"   💡 Gerekçe: {r.get('optimal_reason', r['explanation'])}\n")
    
    # 6. Özet İstatistik & Akıllı Kuponlar
    veto_sayisi = sum(1 for r in results if r.get('elimination_intel', {}).get('is_vetoed'))
    sazan_sayisi = sum(1 for r in results if 'SAZAN' in str(r.get('trap_type', '')))
    print("=" * 65)
    print(f"  📌 ÖZET: {len(bankolar)} BANKO | {len(gol_oyna)} GOL OYNA | {len(pas_gec)} PAS GEÇ")
    print(f"  🛡️ TUZAK AVCISI: {veto_sayisi} Maç VETO Edildi | {sazan_sayisi} Sazan Tuzağı Savuşturuldu")
    print(f"  📈 xG Verisi: {xg_sayisi}/{len(results)} maç | Rotation Riski: {rotation_r} maç")
    if bankolar:
        print(f"  🟢 BANKOLAR:")
        for b in bankolar:
            print(f"     • {b['home_name']} vs {b['away_name']} → {b['tahmin_ms']} (Güven: %{b['confidence']})")
    
    # Akıllı Kuponlar ve 50-Agent Swarm Bölümü
    try:
        from agent_swarm_50 import generate_50agent_smart_portfolio
        swarm_res = generate_50agent_smart_portfolio(results)
        print("\n" + "=" * 65)
        print("     🤖 50-AGENT SWARM & TYPESAFE JEV 'ALTIN KASA' (2'Lİ BANKO)     ")
        print("=" * 65)
        if swarm_res.get("altin_kasa"):
            ak = swarm_res["altin_kasa"]
            print(f"📌 {ak['kupon_adi']} | Toplam Oran: {ak['toplam_oran']} | Güven: {ak['bilesik_guven']}")
            print("-" * 65)
            for m in ak["maclar"]:
                print(f"  👉 [{m['lig']}] {m['mac']} -> {m['tercih']} (Oran: {m['oran']}) [Konsensüs: {m['konsensus']}]")
                print(f"     Gerekçe: {m['gerekce']}")
        else:
            print("⚠️ 50-Ajan Swarm: Yüksek riskli/vetolu maçlar sebebiyle bugün 2'li kasa kuponu onaylanmadı (Kasa korundu!).")
            
        if swarm_res.get("tekli_degerler"):
            print("\n  🎯 TEKLİ DEĞER BAHİSLERİ (Tek Maçtan Yatma Riskini Yok Eden Portföy):")
            for sv in swarm_res["tekli_degerler"]:
                print(f"     • [{sv['lig']}] {sv['mac']} -> {sv['tercih']} (Oran: {sv['oran']}) [Konsensüs: {sv['konsensus']}]")
    except Exception as e:
        print(f"[!] 50-Agent Swarm çalıştırılamadı: {e}")

    try:
        from smart_coupon_generator import generate_smart_coupons
        coupons = generate_smart_coupons(results)
        print("\n" + "=" * 65)
        print("         🎟️ TYPESAFE AI GÜNÜN DİĞER KOMBİNE KUPONLARI         ")
        print("=" * 65)
        for k, c in coupons.items():
            if not c.get("maclar"): continue
            print(f"\n{c['baslik']} | Toplam Oran: {c['toplam_oran']}")
            print("-" * 55)
            for m in c["maclar"]:
                print(f"  • [{m['lig']}] {m['mac']} -> {m['tahmin']} (Oran: {m['oran']}) [Güven: %{m['guven']}]")
    except Exception as e:
        print(f"[!] Diğer kuponlar üretilemedi: {e}")
        
    print("=" * 65)
        
    print(f"\n[OK] Tüm bülten taraması {round(time.time() - t0, 1)} saniyede tamamlandı!")
    print(f"📊 İnteraktif Dashboard: {main_html_path}")
    
    # Tarayıcıda aç
    try:
        webbrowser.open(f"file:///{main_html_path.replace(os.sep, '/')}")
    except:
        pass

if __name__ == "__main__":
    date_arg = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        date_arg = sys.argv[1]
    run_daily_prediction(date_arg)
    
    # Gün sonu modunda çalışıyorsa (--feedback argümanı verilmişse)
    # ya da önceki günün feedback'ini üret
    if "--feedback" in sys.argv:
        from feedback_logger import run_feedback_logger
        prev_date = sys.argv[sys.argv.index("--feedback") + 1] if sys.argv.index("--feedback") + 1 < len(sys.argv) else date_arg
        run_feedback_logger(prev_date)

"""
feedback_logger.py — Günlük Geri Bildirim & Öğrenme Döngüsü
=============================================================
Gün sonunda otomatik olarak tahminleri gerçek sonuçlarla karşılaştırır,
feedback_log.json dosyasına yazar ve kategori/lig bazlı başarı istatistiklerini
hesaplar. Bu veriler zamanla modelin hangi senaryolarda yanıldığını gösterir.

Kullanım:
    python feedback_logger.py 20260919
    
veya program içinden:
    from feedback_logger import run_feedback_logger
    run_feedback_logger("20260919")
"""
import os
import sys
import json
import requests
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

PROJECT_DIR = r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI"
FEEDBACK_LOG_PATH = os.path.join(PROJECT_DIR, "feedback_log.json")

LEAGUES = {
    "Süper Lig":     "tur.1",
    "Premier League":"eng.1",
    "La Liga":       "esp.1",
    "Serie A":       "ita.1",
    "Bundesliga":    "ger.1",
    "Ligue 1":       "fra.1"
}

def _load_feedback_log():
    if os.path.exists(FEEDBACK_LOG_PATH):
        try:
            with open(FEEDBACK_LOG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"days": [], "cumulative": {}}

def _save_feedback_log(log):
    with open(FEEDBACK_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def _fetch_final_scores(date_str):
    """ESPN'den o günün bitmiş maç sonuçlarını çeker."""
    results = {}
    for league, code in LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={date_str}"
        try:
            r = requests.get(url, timeout=6).json()
            for ev in r.get("events", []):
                c = ev["competitions"][0]
                st = c.get("status", {}).get("type", {})
                if st.get("state") != "post":
                    continue
                comps = c["competitors"]
                h = comps[0] if comps[0].get("homeAway") == "home" else comps[1]
                a = comps[1] if comps[0].get("homeAway") == "home" else comps[0]
                hs = int(h.get("score", 0) or 0)
                as_ = int(a.get("score", 0) or 0)
                act_ms  = "MS 1" if hs > as_ else ("MS 2" if as_ > hs else "MS X")
                act_ou  = "2.5 ÜST" if (hs + as_) > 2.5 else "2.5 ALT"
                act_btts = "KG VAR" if (hs > 0 and as_ > 0) else "KG YOK"
                results[ev.get("id")] = {
                    "score": f"{hs}-{as_}",
                    "act_ms": act_ms,
                    "act_ou": act_ou,
                    "act_btts": act_btts,
                    "total_goals": hs + as_
                }
        except Exception as e:
            print(f"[!] {league} skor çekme hatası: {e}")
    return results

def run_feedback_logger(date_str=None):
    """
    Belirtilen tarihin tahminlerini gerçek sonuçlarla karşılaştırır
    ve feedback_log.json'a yazar.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    pred_path = os.path.join(PROJECT_DIR, f"tahminler_{date_str}.json")
    if not os.path.exists(pred_path):
        print(f"[!] {pred_path} bulunamadı. Önce gunluk_tahmin.py çalıştırın.")
        return
    
    with open(pred_path, encoding="utf-8") as f:
        predictions = json.load(f)
    
    print(f"[*] {date_str} için gerçek sonuçlar ESPN'den çekiliyor...")
    actual_scores = _fetch_final_scores(date_str)
    
    if not actual_scores:
        print("[!] Gerçek skor verisi alınamadı. Maçlar henüz bitmemiş olabilir.")
        return
    
    # --- Karşılaştırma ---
    day_results = []
    cat_stats = {}  # Kategori bazlı istatistikler
    lig_stats = {}  # Lig bazlı istatistikler
    
    total_ms  = total_ou  = total_btts  = 0
    hit_ms    = hit_ou    = hit_btts    = 0
    
    for pred in predictions:
        match_id = str(pred.get("id", ""))
        if match_id not in actual_scores:
            continue  # Henüz bitmemiş maç
        
        actual = actual_scores[match_id]
        pred_ms   = pred.get("tahmin_ms", "MS 1")
        pred_ou   = "2.5 ÜST" if pred.get("over_2_5_prob", 50) >= 50 else "2.5 ALT"
        pred_btts = "KG VAR"  if pred.get("btts_prob", 50) >= 50 else "KG YOK"
        action    = pred.get("action_status", "NO_BET")
        category  = pred.get("action_label", "-")
        league    = pred.get("league", "-")
        
        ms_hit   = (pred_ms   == actual["act_ms"])
        ou_hit   = (pred_ou   == actual["act_ou"])
        btts_hit = (pred_btts == actual["act_btts"])
        
        total_ms   += 1; hit_ms   += int(ms_hit)
        total_ou   += 1; hit_ou   += int(ou_hit)
        total_btts += 1; hit_btts += int(btts_hit)
        
        # Kategori istatistiği
        if category not in cat_stats:
            cat_stats[category] = {"total": 0, "ms": 0, "ou": 0, "btts": 0}
        cat_stats[category]["total"] += 1
        cat_stats[category]["ms"]    += int(ms_hit)
        cat_stats[category]["ou"]    += int(ou_hit)
        cat_stats[category]["btts"]  += int(btts_hit)
        
        # Lig istatistiği
        if league not in lig_stats:
            lig_stats[league] = {"total": 0, "ms": 0, "ou": 0, "btts": 0}
        lig_stats[league]["total"] += 1
        lig_stats[league]["ms"]    += int(ms_hit)
        lig_stats[league]["ou"]    += int(ou_hit)
        lig_stats[league]["btts"]  += int(btts_hit)
        
        day_results.append({
            "id": match_id,
            "home": pred.get("home_name", ""),
            "away": pred.get("away_name", ""),
            "league": league,
            "score": actual["score"],
            "total_goals": actual["total_goals"],
            "pred_ms":   pred_ms,   "act_ms":   actual["act_ms"],   "ms_hit":   ms_hit,
            "pred_ou":   pred_ou,   "act_ou":   actual["act_ou"],   "ou_hit":   ou_hit,
            "pred_btts": pred_btts, "act_btts": actual["act_btts"], "btts_hit": btts_hit,
            "over_2_5_prob": pred.get("over_2_5_prob"),
            "btts_prob": pred.get("btts_prob"),
            "confidence": pred.get("confidence"),
            "trap_score": pred.get("trap_score"),
            "action": action,
            "category": category,
            # Yeni zengin alanlar
            "home_momentum": pred.get("home_momentum", "unknown"),
            "away_momentum": pred.get("away_momentum", "unknown"),
            "home_rotation_risk": pred.get("home_rotation_risk", False),
            "away_rotation_risk": pred.get("away_rotation_risk", False),
            "h2h_summary": pred.get("h2h_summary", ""),
            "home_xg_avg": pred.get("home_xg_avg"),
            "away_xg_avg": pred.get("away_xg_avg"),
        })
    
    if not day_results:
        print("[!] Karşılaştırılacak biten maç bulunamadı.")
        return
    
    ms_rate   = round(hit_ms   / total_ms   * 100, 1) if total_ms   else 0
    ou_rate   = round(hit_ou   / total_ou   * 100, 1) if total_ou   else 0
    btts_rate = round(hit_btts / total_btts * 100, 1) if total_btts else 0
    
    day_entry = {
        "date": date_str,
        "created_at": datetime.now().isoformat(),
        "total_matches": len(day_results),
        "summary": {
            "ms_hits":   hit_ms,   "ms_total":   total_ms,   "ms_rate_%":   ms_rate,
            "ou_hits":   hit_ou,   "ou_total":   total_ou,   "ou_rate_%":   ou_rate,
            "btts_hits": hit_btts, "btts_total": total_btts, "btts_rate_%": btts_rate
        },
        "category_stats": cat_stats,
        "league_stats": lig_stats,
        "matches": day_results
    }
    
    # --- Kümülatif Güncelleme ---
    log = _load_feedback_log()
    
    # Aynı gün varsa güncelle
    log["days"] = [d for d in log["days"] if d["date"] != date_str]
    log["days"].append(day_entry)
    log["days"].sort(key=lambda x: x["date"])
    
    # Kümülatif istatistikler
    cum = {"ms_hits": 0, "ms_total": 0, "ou_hits": 0, "ou_total": 0,
           "btts_hits": 0, "btts_total": 0, "days_counted": 0, "category": {}, "league": {}}
    for d in log["days"]:
        s = d["summary"]
        cum["ms_hits"]    += s["ms_hits"];    cum["ms_total"]    += s["ms_total"]
        cum["ou_hits"]    += s["ou_hits"];    cum["ou_total"]    += s["ou_total"]
        cum["btts_hits"]  += s["btts_hits"];  cum["btts_total"]  += s["btts_total"]
        cum["days_counted"] += 1
        for cat, cs in d.get("category_stats", {}).items():
            if cat not in cum["category"]:
                cum["category"][cat] = {"total": 0, "ms": 0, "ou": 0, "btts": 0}
            for k in ["total", "ms", "ou", "btts"]:
                cum["category"][cat][k] += cs[k]
        for lig, ls in d.get("league_stats", {}).items():
            if lig not in cum["league"]:
                cum["league"][lig] = {"total": 0, "ms": 0, "ou": 0, "btts": 0}
            for k in ["total", "ms", "ou", "btts"]:
                cum["league"][lig][k] += ls[k]
    
    cum["ms_rate_%"]   = round(cum["ms_hits"]   / cum["ms_total"]   * 100, 1) if cum["ms_total"]   else 0
    cum["ou_rate_%"]   = round(cum["ou_hits"]   / cum["ou_total"]   * 100, 1) if cum["ou_total"]   else 0
    cum["btts_rate_%"] = round(cum["btts_hits"] / cum["btts_total"] * 100, 1) if cum["btts_total"] else 0
    log["cumulative"] = cum
    
    _save_feedback_log(log)
    
    # --- Konsol Raporu ---
    print(f"\n{'='*65}")
    print(f"  📊 {date_str} GÜNÜ GERİ BİLDİRİM RAPORU  ({len(day_results)} maç)")
    print(f"{'='*65}")
    print(f"  MS (Taraf):       {hit_ms}/{total_ms} — %{ms_rate}")
    print(f"  2.5 Alt/Üst:      {hit_ou}/{total_ou} — %{ou_rate}")
    print(f"  KG (Var/Yok):     {hit_btts}/{total_btts} — %{btts_rate}")
    print(f"\n  KATEGORİ DETAYLARI:")
    for cat, s in cat_stats.items():
        t = s["total"]
        print(f"  {cat[:35]:<35} | MS: {s['ms']}/{t} | 2.5: {s['ou']}/{t} | KG: {s['btts']}/{t}")
    print(f"\n  LİG DETAYLARI:")
    for lig, s in lig_stats.items():
        t = s["total"]
        print(f"  {lig:<20} | MS: {s['ms']}/{t} | 2.5: {s['ou']}/{t} | KG: {s['btts']}/{t}")
    print(f"\n  KÜMÜLATİF ({cum['days_counted']} gün): MS %{cum['ms_rate_%']} | 2.5 %{cum['ou_rate_%']} | KG %{cum['btts_rate_%']}")
    print(f"{'='*65}")
    print(f"[+] Feedback log kaydedildi: {FEEDBACK_LOG_PATH}")
    
    return day_entry

if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
    run_feedback_logger(date_arg)

"""
typesafe_strateji_danisma.py
TypeSafe AI'ya backtest sonuçlarını gösterip en iyi mimariyi sorar.
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)

# Backtest bulgularını yükle
backtest_data = json.load(open("backtest_karsilastirmali_sonuclari.json", encoding="utf-8"))
old = backtest_data["old_system"]
new = backtest_data["new_system"]

# Lig istatistiklerini hesapla
from collections import defaultdict
def lig_stats(matches):
    s = defaultdict(lambda: {"t":0,"ms":0,"ou":0,"btts":0})
    for m in matches:
        l = m["league"]
        s[l]["t"] += 1
        if m.get("ms_hit"): s[l]["ms"] += 1
        if m.get("ou_hit"): s[l]["ou"] += 1
        if m.get("btts_hit"): s[l]["btts"] += 1
    return {l: {k: v for k,v in d.items()} for l,d in s.items()}

old_stats = lig_stats(old)
new_stats = lig_stats(new)

lig_ozet = ""
for lig in sorted(old_stats.keys()):
    o = old_stats[lig]; n = new_stats.get(lig, o)
    t = o["t"]
    lig_ozet += (
        f"\n{lig}: "
        f"ESKİ MS=%{round(o['ms']/t*100,1)} 2.5=%{round(o['ou']/t*100,1)} KG=%{round(o['btts']/t*100,1)} | "
        f"YENİ MS=%{round(n['ms']/t*100,1)} 2.5=%{round(n['ou']/t*100,1)} KG=%{round(n['btts']/t*100,1)}"
    )

hafta_ozet = ""
from collections import defaultdict
period_ms = defaultdict(lambda: {"t":0,"ms":0})
for m in new:
    p = m.get("period","?")
    period_ms[p]["t"] += 1
    if m.get("ms_hit"): period_ms[p]["ms"] += 1
for p in sorted(period_ms.keys()):
    s = period_ms[p]
    hafta_ozet += f"\n{p}: MS {s['ms']}/{s['t']} (%{round(s['ms']/s['t']*100,1)})"

state = {
    "görev": (
        "Sen bir futbol bahis sistemi mimarisisin. 202 maçlık gerçek backtest verisi aşağıda. "
        "Bu veriye dayanarak optimal sistemi tasarlamanı istiyorum."
    ),
    "genel_sonuclar": (
        f"202 maç, 6 lig, Ağustos-Eylül 2026. "
        f"ESKİ SİSTEM: MS=%49 2.5=%60.9 KG=%57.9 P&L=+23.9 | Banko: 9/10 (%90) ROI=%99. "
        f"YENİ SİSTEM (H2H+momentum+rotation): MS=%50 2.5=%56.9 KG=%57.9 P&L=+45.7 | Banko: 0/202 seçildi. "
        f"Yeni sistem ham P&L'de +21.8 birim daha iyi ama banko seçemiyor çünkü zengin veri AI'ı paranoyak yapıyor."
    ),
    "lig_bazli_istatistikler": lig_ozet,
    "hafta_bazli_ms_yeni": hafta_ozet,
    "kritik_bulgular": (
        "1. Bundesliga: Yeni sistemde MS %63.3→%66.7 iyileşti, 2.5 %80→%70 geriledi. "
        "2. Serie A: Yeni sistemde MS %39→%57.6 (+18 puan!), KG %72.7 çok güçlü. "
        "3. Ligue 1: 2.5 yeni sistemde %55.6→%44.4 kötüleşti, KG hep güçlü (%63.9). "
        "4. Premier League: Her iki sistemde de en zayıf lig. "
        "5. Sezon ilerledikçe doğruluk artıyor: Hf4-Paz %64.7, Hf5-Cmt %63.0. "
        "6. Eski banko mekanizması: ALTIN - 10 seçti 9 tuttu (%90). "
        "7. Yeni banko mekanizması: 202 maçtan 0 seçti - zengin prompt AI'ı 'pas geç' demeye zorluyor."
    )
}

print("TypeSafe AI'ya backtest verisi gonderiliyor ve strateji soruluyor...\n")

resp = client.system_one(
    state=state,
    questions={
        "banko_mimari": Choice(
            instructions=(
                "Banko seçim mekanizması için en doğru mimari hangisi? "
                "Eski sistem %90 banko isabeti yapıyor, yeni sistem 0 seçiyor. "
                "202 maçlık backtest verisini dikkate al."
            ),
            criteria={
                "eski_prompt_yeni_veri_dogrulama": (
                    "Önce eski basit prompt ile banko aday seç, "
                    "sonra yeni zengin veri ile doğrula (H2H/momentum/xG validasyon katmanı)"
                ),
                "iki_asama_typesafe": (
                    "TypeSafe AI'ya iki ayrı çağrı: "
                    "1. Basit soru - banko adayı bul, "
                    "2. Zengin veri ile sadece 'onayla/reddet' sor"
                ),
                "sadece_eski_kalsın": (
                    "Eski banko mekanizması zaten %90 çalışıyor, "
                    "yeni veriyi sadece açıklama/taktik not için kullan, karar için değil"
                )
            }
        ),
        "lig_stratejisi": Choice(
            instructions=(
                "Lig bazlı farklı bahis stratejisi kullanılmalı mı? "
                "Bundesliga'da 2.5 %80, Ligue 1'de KG %64, Serie A'da KG %72.7 çıkıyor."
            ),
            criteria={
                "evet_lig_bazli_farkli_strateji": (
                    "Her lig için ayrı bahis tipi önceliği: "
                    "Bundesliga=2.5+MS, Serie A=KG odak, Ligue 1=sadece KG, PL=çok seçici"
                ),
                "hayir_tek_model_yeterli": (
                    "Tek model tüm liglere uygun, "
                    "sadece güven eşiğini lig bazlı ayarla"
                ),
                "karma_hibrit": (
                    "Ana model aynı kalsın ama çıktıya lig bazlı "
                    "'tavsiye etilen bahis tipi' etiketi ekle"
                )
            }
        ),
        "iki_beson_motor": Choice(
            instructions=(
                "2.5 Alt/Üst için MS motorundan bağımsız ayrı bir TypeSafe motoru kurulmalı mı? "
                "Şu an 2.5 tahmini MS'in yan ürünü. "
                "H2H ortalama gol + son 5 maç hücum/savunma + xG odaklı ayrı bir Noul sorusu çok daha isabetli olabilir."
            ),
            criteria={
                "evet_bagimsiz_2_5_motoru": (
                    "Ayrı bir TypeSafe çağrısıyla sadece gol sayısına odaklanan "
                    "bağımsız 2.5 motoru kur — H2H gol ort, xG toplamı, ev/dep gol oranları"
                ),
                "hayir_mevcut_yeterli": (
                    "Mevcut Noul sorusu yeterince güçlü, "
                    "sadece prompt'a daha fazla gol verisi ekle"
                )
            }
        ),
        "sezon_dinamik_esik": Noul(
            instructions=(
                "Sezon başında (ilk 3 hafta) güven eşiği daha yüksek tutulmalı mı? "
                "Hf1-2'de MS %44-58 iken Hf4-5'te %63-72 çıkıyor. "
                "0.0 = sezon boyunca sabit eşik, 1.0 = sezon başında çok daha yüksek eşik"
            )
        ),
        "optimal_banko_guven_esigi": Score(
            instructions=(
                "Eski sistem confidence >= 50 ile bankolar seçti ve %90 isabetli oldu. "
                "Yeni zengin verilerle birlikte optimal banko güven eşiği ne olmalı? "
                "0=çok düşük (50%), 1=mevcut (60%), 2=yüksek (70%+)"
            ),
            criteria=["dusuk_50_yuzde", "orta_60_yuzde", "yuksek_70_yuzde"]
        )
    }
)

print("=" * 65)
print("  TypeSafe AI STRATEJI KARARLARI")
print("=" * 65)
print(f"\n1. Banko Mimarisi:    {resp.choices['banko_mimari'].choice}")
print(f"2. Lig Stratejisi:    {resp.choices['lig_stratejisi'].choice}")
print(f"3. Bagimsiz 2.5 Motor: {resp.choices['iki_beson_motor'].choice}")
print(f"4. Sezon Dinamik Esik: {round(resp.nouls['sezon_dinamik_esik'].noul * 100)}% agirlik")
raw_conf = resp.scores['optimal_banko_guven_esigi'].score
conf_map = {0: "50%", 1: "60%", 2: "70%+"}
conf_label = "50%" if raw_conf < 0.67 else ("60%" if raw_conf < 1.33 else "70%+")
print(f"5. Optimal Banko Guven Esigi: {conf_label} (raw={round(raw_conf,2)})")
print("=" * 65)

# Sonuçları kaydet
strateji = {
    "banko_mimari": resp.choices["banko_mimari"].choice,
    "lig_stratejisi": resp.choices["lig_stratejisi"].choice,
    "bagimsiz_2_5": resp.choices["iki_beson_motor"].choice,
    "sezon_dinamik_agirlik": round(resp.nouls["sezon_dinamik_esik"].noul, 3),
    "banko_guven_esigi_raw": round(raw_conf, 3),
    "banko_guven_esigi": conf_label
}
with open("typesafe_strateji_karari.json", "w", encoding="utf-8") as f:
    json.dump(strateji, f, ensure_ascii=False, indent=2)
print(f"\n[+] Strateji karari kaydedildi: typesafe_strateji_karari.json")

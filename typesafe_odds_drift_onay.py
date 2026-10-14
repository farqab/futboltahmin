"""
typesafe_odds_drift_onay.py
TypeSafe AI'ya Odds Drift (Smart Money / Oran Hareketi) radarının sisteme eklenip eklenmeyeceğini sorar.
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from typesafe_sdk import TypeSafeClient, Choice, Score

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)

context = {
    "oneri": (
        "Sisteme 'Oran Hareketi ve Akıllı Para Radarı (Odds Drift / Smart Money Tracker)' eklemek istiyoruz. "
        "ESPN API'mizde hem 'açılış oranları' (open odds) hem de 'güncel oranlar' (close/current odds) mevcut. "
        "Eğer bir takımın oranı açılıştan bu yana belirgin düşmüşse (örneğin 1.80 -> 1.50): "
        "Bu durum piyasaya büyük para girdiği, antrenmanda sakatlık/kadro avantajı oluştuğu anlamına gelir. "
        "Tersine, favorinin oranı yükselmişse (1.45 -> 1.70): 'Tuzak / Kadro Alarmı' verilir."
    )
}

print("[*] TypeSafe AI'ya Odds Drift özelliğinin entegrasyonu danışılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "ozellik_entegrasyon_karari": Choice(
            instructions="Oran Hareketi (Odds Drift / Smart Money) özelliğini hemen sisteme entegre edelim mi?",
            criteria={
                "evet_hemen_entegre_et": (
                    "KESİNLİKLE EVET: Canlı kadro bekleme ihtiyacını bertaraf eder, piyasanın gizli bilgisini modele katar, "
                    "yanıltıcı favorileri anında yakalar. Hemen uygulanmalıdır."
                ),
                "hayir_gerek_yok": "HAYIR: Mevcut istatistiksel model tek başına yeterlidir."
            }
        ),
        "uygulama_mimarisi": Choice(
            instructions="Bu özellik sisteme nasıl dahil edilmeli?",
            criteria={
                "tuzak_ve_guven_carpanina_bagla": (
                    "Oran düşüşü (%5+ düşüş) varsa Güven Puanını +5 artır ve '🔥 Akıllı Para Girişi' rozeti tak. "
                    "Oran yükselişi (%5+ yükseliş) varsa Tuzak Skorunu +1.5 artır ve '⚠️ Piyasa Şüphesi / Oran Yükseldi' alarmı ver."
                ),
                "sadece_bilgi_notu_yaz": "Sadece taktik nota bilgi olarak ekle, matematiksel puanlara dokunma."
            }
        ),
        "etki_gucu": Score(
            instructions="Bu özelliğin sistemin keskinliğini artırma derecesi?",
            criteria=["orta_katki", "cok_guclu_katki", "devrimsel_ustunluk"]
        )
    }
)

print("="*65)
print("  🎯 TYPESAFE AI ORAN HAREKETİ RADARI KARARI")
print("="*65)
print(f"1. Karar:         {resp.choices['ozellik_entegrasyon_karari'].choice}")
print(f"2. Uygulama Şekli:{resp.choices['uygulama_mimarisi'].choice}")
skor = round(resp.scores['etki_gucu'].score * 5.0, 1)
print(f"3. Etki Gücü:     {skor} / 10")
print("="*65)

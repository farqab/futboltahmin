"""
typesafe_telafi_karari.py
TypeSafe AI'ya 50 TL'lik Telafi (Hedge) Kuponu'nun risk analizini yaptırır.
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)

context = {
    "kullanici_amaci": (
        "Kullanıcı ilk 50 TL'sini 6 maçlık yüksek oranlı (~10.00) ana kupona yatırdı. "
        "Kalan son 50 TL'sini ise ilk kupon yatarsa ana parayı (100 TL) kurtaracak ve kâra geçirecek "
        "bir 'TELAFİ (HEDGE) SİGORTA KUPONU' olarak değerlendirmek istiyor. "
        "Hedef oran: 2.20 - 2.70 bandı."
    ),
    "onerilen_telafi_kuponu": (
        "1. Maç: AC Milan vs Lecce -> MS 1 & 1.5 ÜST (Oran: ~1.50) [Model Güveni %87, Tuzak 1.9/10] "
        "2. Maç: Juventus vs Atalanta -> Karşılıklı Gol VAR (Oran: ~1.68) [Model Güveni %65, Serie A KG başarısı %72.7] "
        "Toplam Oran: ~2.52 -> 50 TL yatırılırsa 126 TL döner (100 TL ana kasa kurtulur + 26 TL net kâr)."
    )
}

print("[*] TypeSafe AI'ya Telafi Kuponu Risk ve Portföy Denetimi soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "telafi_kuponu_onayi": Choice(
            instructions=(
                "Bir profesyonel portföy yöneticisi ve algoritmik analiz motoru olarak: "
                "Bu önerilen 2'li kombinasyon (Milan 1 & 1.5 Üst + Juve/Atalanta KG Var) "
                "50 TL'lik telafi / kasa koruma görevi için optimal midir?"
            ),
            criteria={
                "tam_onay_optimal_portfoy": (
                    "TAM ONAY: 1 Taraf Bankosu (Milan) + 1 Gol Temposu (Juve/Atalanta KG) tam korelasyon kuralına uygundur, "
                    "2.52 oran kasayı kurtarmak için mükemmel bir risk/ödül dengesidir."
                ),
                "daha_guvenli_alternatif_gerekli": (
                    "RİSKLİ: İki maç da Serie A'dan olduğu için lig korelasyon riski taşır, maçlardan biri farklı lige kaydırılmalıdır."
                ),
                "tek_maca_inilmeli": (
                    "AŞIRI TEMKİNLİ: 2 maç yerine tek bir 1.80-2.00 oranlı maça 50 TL basılmalıdır."
                )
            }
        ),
        "lig_korelasyon_riski": Choice(
            instructions="İki maçın da Serie A'da olması bir risk teşkil ediyor mu?",
            criteria={
                "risk_yok_farkli_pazarlar": "Risk yok çünkü biri net taraf/kalite farkı (Milan), diğeri iki ofansif devin karşılıklı golüdür (Juve/Atalanta).",
                "farkli_lig_daha_iyi": "Farklı ligden bir maç seçilirse (örneğin Fransa veya İspanya) portföy riski daha iyi dağılır."
            }
        ),
        "telafi_kuponu_guven_skoru": Score(
            instructions="Bu telafi kuponunun kasayı kurtarma ve başarı olasılığı derecesi?",
            criteria=["orta_guven", "yuksek_kasa_koruma", "kusursuz_banko"]
        )
    }
)

print("="*65)
print("  🛡️ TYPESAFE AI TELAFİ KUPONU DENETİM RAPORU")
print("="*65)
print(f"1. Portföy Kararı:    {resp.choices['telafi_kuponu_onayi'].choice}")
print(f"2. Lig Korelasyonu:   {resp.choices['lig_korelasyon_riski'].choice}")
skor = round(resp.scores['telafi_kuponu_guven_skoru'].score * 5.0, 1)
print(f"3. Kasa Koruma Gücü:  {skor} / 10")
print("="*65)

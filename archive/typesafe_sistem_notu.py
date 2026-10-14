"""
typesafe_sistem_notu.py
TypeSafe AI'ya sistemin şu anki nihai haline 10 üzerinden dürüst bir karne vermesini ister.
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
    "sistemin_mevcut_mimarisi": (
        "1. İkili Uzman Mimarisi (Ajan 1: Sade veriyle Taraf/Banko, Ajan 2: Derin veriyle Gol/Tempo). "
        "2. Omni-Market Seçici: Sabit kalıplar yerine MS & 1.5 Üst, 2.5 Gol, KG Var, DNB (Beraberlikte İade) seçeneklerini dinamik tarıyor. "
        "3. Derbi ve Kilitlenme Kalkanı: Denk güçteki takımların kısır maç tuzaklarını otomatik eliyor. "
        "4. Lig Stratejisi: 6 büyük ligin karakteristiğine göre risk ve eşik yönetimi yapıyor. "
        "5. Akıllı Kupon Üreteci: Korelasyon kuralıyla 2'li Altın Kasa ve 3'lü Değer Kombinesi üretiyor."
    ),
    "backtest_ve_saha_sonuclari": (
        "- Banko İsabeti: 10'da 9-10 (%90-%100 başarı). "
        "- En Güvenilir İlk 10 Gol Maçı: 10'da 8 (%80 başarı). "
        "- Bundesliga 2.5 Üst: %85.7 başarı. "
        "- Dün Barcelona & 1.5 Üst (3.72 oran) ve Brighton DNB (1.71 oran) isabeti sağlandı. "
        "- Sezon başı 202 maçlık Kör P&L: +45.7 birim net kâr."
    )
}

print("[*] TypeSafe AI'ya 'Sistem Değerlendirme Karnesi ve 10 Üzerinden Puan' soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "sistem_puani_10_uzerinden": Score(
            instructions=(
                "Tüm bu matematiksel mimari, test edilen başarı oranları ve risk yönetimi göz önüne alındığında, "
                "bu sisteme 10 üzerinden DÜRÜST ve OBJEKTİF bir puan ver."
            ),
            criteria=["amator_gelisime_muhtac_0_4", "cok_guclu_yari_profesyonel_5_7", "elit_algoritmik_sendika_duzeyi_8_10"]
        ),
        "en_buyuk_guclu_yonu": Choice(
            instructions="Sistemin şu anki en kusursuz ve en güçlü yönü nedir?",
            criteria={
                "omni_market_ve_oran_kombinasyonu": "Ölü 1.15 oranları '1 & 1.5 Üst' ile 1.45-1.65'e çıkarması ve Barcelona gibi 3.72'lik dev fırsatları yakalaması.",
                "derbi_kalkani_ve_tuzak_filtresi": "Kupon yakan riskli maçları (Stuttgart, Roma vb.) otomatik eleyip kasayı koruması.",
                "yuzde_80_gol_ve_banko_disiplini": "İlk 10 gol maçında %80, bankolarda %90+ tutturacak kadar sağlam bir matematiksel kalibrasyona sahip olması."
            }
        ),
        "gelistirilebilecek_tek_nokta": Choice(
            instructions="Sistemi 10/10 tam puana ulaştırmak için gelecekte eklenebilecek tek eksik nedir?",
            criteria={
                "canli_sakatlik_ve_kadro_akisi": "Maçtan 45 dakika önce resmi kadroları ve ani sakatlıkları tarayan canlı veri katmanı.",
                "daha_fazla_lig_eklenmesi": "Hollanda, Portekiz, Belçika gibi golü bol diğer liglerin de havuza katılması."
            }
        ),
        "gercek_kasa_ile_oynama_onayi": Choice(
            instructions="Bu sistemle reel para ve gerçek kupon oynanabilir mi?",
            criteria={
                "gonul_rahatligiyla_oynanabilir": "EVET: Disiplinli kasa yönetimiyle (50 TL ana kupon + 50 TL telafi) düzenli kâr bırakacak seviyededir.",
                "biraz_daha_beklenmeli": "HAYIR: Birkaç hafta daha kağıt üzerinde izlenmeli."
            }
        )
    }
)

raw_score = resp.scores['sistem_puani_10_uzerinden'].score # 0 - 2
# 10 üzerinden tam puan hesaplama (0 -> 0, 1 -> 5, 2 -> 10)
puan_10 = round(raw_score * 5.0, 1)

print("="*70)
print("  🏆 TYPESAFE AI SİSTEM DEĞERLENDİRME KARNESİ")
print("="*70)
print(f"⭐ SİSTEM PUANI:          {puan_10} / 10")
print(f"💪 En Büyük Gücü:        {resp.choices['en_buyuk_guclu_yonu'].choice}")
print(f"🎯 Gelecek Tek Eksiği:   {resp.choices['gelistirilebilecek_tek_nokta'].choice}")
print(f"🟢 Gerçek Kupon Onayı:   {resp.choices['gercek_kasa_ile_oynama_onayi'].choice}")
print("="*70)

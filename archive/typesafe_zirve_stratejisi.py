"""
typesafe_zirve_stratejisi.py
TypeSafe AI'ya sistemin geleceğini, geliştirmeye devam edip etmeyeceğimizi ve
8.5 - 9.0 bandına çıkmak için sıradaki hamleyi sorar.
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
    "mevcut_durum": (
        "Sistemimiz muazzam bir evrim geçirdi: "
        "- İkili Uzman Mimarisi kuruldu. "
        "- Omni-Market En İdeal Tercih seçicisi eklendi. "
        "- Oran Hareketi ve Akıllı Para Radarı (Açılış vs Kapanış Oranları) canlı çalışıyor. "
        "- 56 Cumartesi maçında %69.6 kayıpsızlık ve 6.35 kazanan kupon kanıtlandı. "
        "- Sistem puanı 7.2 / 10 seviyesine yükseldi."
    ),
    "stratejik_soru": (
        "Geliştirici ve kullanıcı soruyor: 'Sistemi geliştirmeye devam edelim mi, en iyi hale getirmek için sıradaki adım nedir?' "
        "Sistemi 8.5 - 9.0 (milyar dolarlık profesyonel sendika düzeyi) bandına taşımak için hangi son dokunuş yapılmalı?"
    )
}

print("[*] TypeSafe AI ile 'Zirveye Yolculuk ve Gelecek Geliştirme Stratejisi' görüşmesi yapılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "gelistirmeye_devam_edilmeli_mi": Choice(
            instructions="Şu aşamada geliştirmeye devam mı edilmeli, yoksa sistem sahaya sürülüp izlenmeli mi?",
            criteria={
                "devam_et_son_zirve_hamlesi": (
                    "GELİŞTİRMEYE DEVAM ET: Sistem 7.2 seviyesine geldi ancak 1 kritik matematiksel katman daha eklenirse "
                    "8.5+ sendika düzeyine ulaşabilir. Son dokunuş yapılmalıdır."
                ),
                "mevcut_haliyle_canli_kullan": (
                    "YETERLİ: Şu anki 7.2'lik mimari reel kazanç için fazlasıyla olgun ve hazırdır. "
                    "Artık kod değiştirmek yerine birkaç hafta kuponların tadı çıkarılmalıdır."
                )
            }
        ),
        "zirve_icin_siradaki_en_iyi_ozellik": Choice(
            instructions="Eğer geliştirmeye devam edilecekse, 8.5+ puan için sıradaki EN DEV ENTEGRASYON nedir?",
            criteria={
                "monte_carlo_poisson_simulasyon_motoru": (
                    "Monte Carlo / Poisson 10.000 Maç Simülasyon Motoru: Maçın gol beklentilerini (xG) "
                    "ve geçmiş verilerini arkada 10.000 kez oynatıp skor ve gol ihtimallerini net yüzdelere dökmek."
                ),
                "otonom_gunluk_kasa_ve_kelly_yonetimi": (
                    "Akıllı Kasa ve Bütçe Yöneticisi (Kelly Criterion): Kullanıcının 100 TL'sini her maça "
                    "matematiksel getiri oranına göre 'Şu maça 30 TL, şu maça 70 TL bas' şeklinde dinamik paylaştıran sermaye robotu."
                ),
                "daha_fazla_lig_havuzu": (
                    "Lig Havuzunu Genişletme: Hollanda Eredivisie ve Portekiz gibi gol cenneti ligleri sisteme dahil etmek."
                )
            }
        ),
        "nihai_potansiyel_puani": Score(
            instructions="Bu son adım da tamamlanırsa sistemin ulaşacağı nihai profesyonellik seviyesi?",
            criteria=["yari_profesyonel_7", "ust_duzey_sendika_8_9", "rakipsiz_kusursuz_10"]
        )
    }
)

raw_score = resp.scores['nihai_potansiyel_puani'].score
potansiyel_puan = round(raw_score * 5.0, 1)

print("="*70)
print("  🚀 TYPESAFE AI ZİRVEYE YOLCULUK STRATEJİSİ")
print("="*70)
print(f"1. Geliştirmeye Devam Edelim mi?: {resp.choices['gelistirmeye_devam_edilmeli_mi'].choice}")
print(f"2. Sıradaki En Büyük Hamle:       {resp.choices['zirve_icin_siradaki_en_iyi_ozellik'].choice}")
print(f"3. Ulaşılacak Nihai Puan:         {potansiyel_puan} / 10")
print("="*70)

"""
typesafe_puan_yukseltme_danisma.py
Kullanıcının haklı tespiti: "Maçtan 45 dk önce kadro beklemek pratik değil, kuponlar sabahtan yapılıyor."
TypeSafe AI'ya kadro beklemeden 4.3 skorunu 7-8 bandına çıkaracak pratik ve matematiksel yenilikleri sorar.
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
    "kullanici_itirazi": (
        "Kullanıcı çok pratik ve hayatın içinden bir itirazda bulundu: "
        "'Maçtan 45 dakika önce kadro beklemek mümkün görünmüyor. Çünkü maçlar farklı saatlerde (14:30, 16:00, 19:00, 21:45) "
        "oynanıyor ve kullanıcı sabahtan tek seferde kuponunu yapıp günlük hayatına devam etmek istiyor.' "
        "Soru: Canlı 45 dk kadro beklemesine GEREK KALMADAN, maç öncesi verilerle 4.3 olan sistem puanını "
        "7 - 8 seviyesine çıkaracak en etkili ve pratik matematiksel özellikler nelerdir?"
    )
}

print("[*] TypeSafe AI'ya 'Kadro beklemeden skoru 7-8'e çıkaracak pratik özellikler' soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "en_etkili_pratik_ozellik": Choice(
            instructions=(
                "Canlı kadro beklemeden maç öncesi verilerle sistem doğruluğunu sıçratacak en güçlü özellik hangisidir?"
            ),
            criteria={
                "piyasa_oran_kaymasi_ve_akilli_para": (
                    "Piyasa Oran Hareketi (Odds Drift / Smart Money): Açılış oranı ile sabahki oran arasındaki fark. "
                    "Piyasadaki milyon dolarlar zaten sakatlıkları ve kadro dedikodularını önceden fiyatlar! "
                    "Oranı aniden düşen takımı yakalamak kadro bekleme ihtiyacını %80 oranında ortadan kaldırır."
                ),
                "monte_carlo_ve_poisson_simulasyonu": (
                    "Monte Carlo ve Poisson Gol Simülasyonu: Takımların iç/dış saha xG ve gol beklentilerini "
                    "maç öncesinde 10.000 kez simüle ederek 1.5 Üst, 2.5 Üst ve skor ihtimallerini net olasılık dağılımına dökmek."
                ),
                "avrupa_kupasi_ve_fikstur_yorgunlugu": (
                    "Fikstür ve Takvim Yorgunluk Modeli: Takımın 3 gün önce Şampiyonlar Ligi maçı oynayıp oynamadığı "
                    "veya 3 gün sonra kritik bir maçı olup olmadığı günler öncesinden bellidir. Bunu derin hesaba katmak."
                ),
                "elo_ve_rakip_kalite_endeksi": (
                    "Dinamik ELO Puanı: Takımların son 5 maçtaki puanı yerine, o puanları hangi kalitedeki rakiplere karşı "
                    "aldığını hesaplayan matematiksel lig güç endeksi."
                )
            }
        ),
        "oran_hareketinin_kadro_ikamesi_gucu": Noul(
            instructions=(
                "Piyasa oran hareketlerinin (örneğin 1.80'den 1.55'e düşüş) sakatlık ve kadro eksiklerini "
                "kullanıcı beklemeden önceden yansıtma ve telafi etme gücü nedir? (0.0=Hiç yansıtmaz, 1.0=Tamamen yansıtır)"
            )
        ),
        "bu_ozelliklerle_yeni_sistem_puani": Score(
            instructions=(
                "Bu pratik özellikler (Oran hareketi + Poisson simülasyonu + Fikstür takvimi) sisteme eklenirse, "
                "maç öncesi kupon yapan bir kullanıcı için sistemin yeni puanı ne seviyeye çıkar?"
            ),
            criteria=["hala_orta_5_6", "guclu_profesyonel_7_8", "zirve_kusursuz_9_10"]
        )
    }
)

raw_new_score = resp.scores['bu_ozelliklerle_yeni_sistem_puani'].score
new_puan = round(raw_new_score * 5.0, 1)

print("="*70)
print("  🚀 TYPESAFE AI'DAN 4.3 SKORUNU YÜKSELTME YOL HARİTASI")
print("="*70)
print(f"1. En Güçlü Pratik Özellik:   {resp.choices['en_etkili_pratik_ozellik'].choice}")
drift_guc = round(resp.nouls['oran_hareketinin_kadro_ikamesi_gucu'].noul * 100)
print(f"2. Oran Hareketinin Kadro İkame Gücü: %{drift_guc}")
print(f"3. Beklenen Yeni Sistem Puanı: {new_puan} / 10")
print("="*70)

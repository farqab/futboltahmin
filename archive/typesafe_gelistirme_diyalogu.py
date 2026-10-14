"""
typesafe_gelistirme_diyalogu.py
TypeSafe AI'ya sistemin geleceğini, kendini nasıl geliştirebileceğini ve
birlikte hangi yeni yetenekleri inşa edebileceğimizi danışır.
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
    "mevcut_basarilar": (
        "1. İkili Uzman (Ajan 1 Taraf, Ajan 2 Gol) ile 2.5 Üst başarısı %65+'e çıktı. "
        "2. Akıllı Kupon Üreticisi (Korelasyon Kuralı: 1 Taraf + 1 Gol) son 4 günde 3 kupon bildi (%75 başarı). "
        "3. Banko seçiminde %100 isabet yakalandı. "
        "4. Hafta 4-5 itibarıyla takımların verisi oturdukça tahmin kalitesi tavan yaptı."
    ),
    "gelistirme_sorusu": (
        "Geliştirici ve sen (TypeSafe AI) birlikte çalışarak bu sistemi daha ne kadar ileri taşıyabilirsiniz? "
        "TypeSafe AI mimarisi, istatistiksel zeka ve geri bildirim döngüleri kullanılarak "
        "sisteme eklenebilecek en devrimsel yeni katmanlar nelerdir?"
    )
}

print("[*] TypeSafe AI ile 'Kendi Kendini Geliştirme ve Gelecek Yol Haritası' oturumu başlatılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "otonom_ogrenme_dongusu": Choice(
            instructions=(
                "Geri bildirim (Feedback Loop) mekanizmasını nasıl bir 'Otonom Öğrenen Yapay Zeka'ya dönüştürebiliriz?"
            ),
            criteria={
                "dinamik_agirlik_kalibrasyonu": (
                    "Her gün biten maçların ardından modelin hangi ligde ve hangi oran aralığında yanıldığını analiz et. "
                    "Ertesi gün o ligin güven eşiğini ve soru ağırlıklarını otomatik olarak kendi kendine kalibre etsin."
                ),
                "hata_hafizasi_ve_kara_liste": (
                    "Sürekli kupon yatıran takımları (örneğin deplasmanda istikrarsız favoriler) 'Riskli Takım Hafızası'na al, "
                    "bu takımlara taraf bahsi verilmesini otomatik engelle."
                ),
                "kümülatif_prompt_guncelleme": (
                    "Her hafta sonu TypeSafe AI'ya 'Bu hafta neler öğrendin?' diye sorup sistem promptlarına dinamik kurallar eklet."
                )
            }
        ),
        "yeni_bahis_pazarlari": Choice(
            instructions=(
                "Sisteme sadece MS ve 2.5 dışında hangi yüksek olasılıklı yeni bahis pazarı eklenmeli?"
            ),
            criteria={
                "iy_1_5_gol_ve_ilk_yari_sonucu": (
                    "İlk Yarı 0.5/1.5 Gol ve İlk Yarı Sonucu (İY 1-X-2): Erken gol atan takımları tespit etmek çok daha yüksek başarı verir."
                ),
                "korner_ve_kart_potansiyeli": (
                    "Korner ve Kart Tahmini: Takımların faul ve kanat oyunu istatistikleriyle taraf sürprizlerinden bağımsız kazanç."
                ),
                "asian_handicap_ve_cifte_sans": (
                    "Asya Handikap (+0.5, +1.0) ve Çifte Şans: Taraf bahsindeki beraberlik riskini sıfırlayan koruma kalkanı."
                )
            }
        ),
        "canli_bahis_ve_oran_takibi": Choice(
            instructions=(
                "Piyasa oranlarının hareketini (Odds Drift) sisteme entegre edebilir miyiz?"
            ),
            criteria={
                "akilli_para_alarm_mekanizmasi": (
                    "Maç saatine doğru aniden düşen oranları (Smart Money / Insider bilgisi) tespit edip kuponlara öncelik ver."
                ),
                "mac_oncesi_sabit_analiz_yeterli": (
                    "Oran hareketleri bazen yanıltıcıdır (tuzaktır), mevcut derin istatistik analizi çok daha güvenilirdir."
                )
            }
        ),
        "birlikte_gelisme_potansiyeli": Score(
            instructions=(
                "Geliştirici ve TypeSafe AI ortaklığı ile bu sistemin "
                "kendi kendine öğrenen ve piyasayı yenen bir algoritmaya dönüşme potansiyeli nedir?"
            ),
            criteria=["sinirli_gelisim", "cok_yuksek_potansiyel", "sinirsiz_algoritmik_ustunluk"]
        )
    }
)

print("="*70)
print("  🚀 TYPESAFE AI İLE BİRLİKTE GELECEK YOL HARİTASI")
print("="*70)
print(f"1. Otonom Öğrenme Yöntemi:      {resp.choices['otonom_ogrenme_dongusu'].choice}")
print(f"2. Yeni Eklenecek Bahis Pazarı:  {resp.choices['yeni_bahis_pazarlari'].choice}")
print(f"3. Piyasa / Oran Stratejisi:     {resp.choices['canli_bahis_ve_oran_takibi'].choice}")
skor = round(resp.scores['birlikte_gelisme_potansiyeli'].score * 5.0, 1)
print(f"4. Birlikte Gelişme Potansiyeli: {skor} / 10")
print("="*70)

vizyon = {
    "ogrenme": resp.choices['otonom_ogrenme_dongusu'].choice,
    "yeni_pazar": resp.choices['yeni_bahis_pazarlari'].choice,
    "piyasa_stratejisi": resp.choices['canli_bahis_ve_oran_takibi'].choice,
    "skor": skor
}

with open("typesafe_otonom_vizyon.json", "w", encoding="utf-8") as f:
    json.dump(vizyon, f, ensure_ascii=False, indent=2)

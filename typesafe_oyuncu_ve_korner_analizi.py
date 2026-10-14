"""
typesafe_oyuncu_ve_korner_analizi.py
Kullanıcının sorusu: "Oyuncu şutları (ör: 1.5 şut çeker), Korner alt/üst, Kart sayısı gibi 
yeni nesil mikro bahisler neden sistemde yok? Bunları eklemeli miyiz, TypeSafe AI ne diyor?"
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
    "kullanici_sorusu": (
        "İddaa ve bahis sitelerinde son dönemde çok popüler olan 'Mikro Pazarlar' var: "
        "Oyuncu İstatistikleri (X oyuncusu 1.5 isabetli şut çeker, oyuncu gol atar), "
        "Korner Alt/Üst (9.5 Korner Üst), Kart Sayısı (4.5 Kart Üst) vb. "
        "Kullanıcı soruyor: 'Bunlar sistemimizde neden ekli değil? TypeSafe AI bunları eklememizi ister mi?'"
    )
}

print("[*] TypeSafe AI'ya Oyuncu Şutları, Korner ve Kart Bahisleri danışılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "mikro_pazarlarin_guvenilirligi": Choice(
            instructions=(
                "Oyuncu şutu, korner ve kart pazarları yapay zeka ile tahmin edilebilir mi? "
                "Matematiksel tutarlılığı ve şans faktörü nedir?"
            ),
            criteria={
                "asiri_yuksek_sans_ve_tuzak": (
                    "YÜKSEK ŞANS VE TUZAK: Oyuncunun 60. dakikada oyundan çıkması, erken sakatlanması, "
                    "hakemin kart standardı veya rüzgar gibi etkenler bu pazarları aşırı manipülatif ve tesadüfi kılar. "
                    "Büyük bahis sendikaları bunlara 'Eğlence Bahsi' (Prop Bet) der, kasayı büyütmek için profesyonelce güvenmez."
                ),
                "belirli_oyuncularda_avantajli": (
                    "SEÇİCİ AVANTAJ: Sadece Haaland, Kane veya Salah gibi maçı 90 dakika oynayan süper yıldızların "
                    "isabetli şutlarında model kurulabilir, ancak genel korner/kart pazarları hala çok gürültülüdür."
                )
            }
        ),
        "teknik_ve_veri_engeli": Choice(
            instructions="Bu pazarların şu an sistemde olmamasının arkasındaki teknik ve veri sebebi nedir?",
            criteria={
                "veri_ve_kadro_bagimliligi": (
                    "KADRO VE CANLI VERİ ZORUNLULUĞU: Bir oyuncunun şutuna oynamak için maçtan 45 dakika önce "
                    "kesin 11'de başlayıp başlamadığının bilinmesi şarttır. Yedek başlarsa veya erken çıkarsa para çöpe gider. "
                    "Ayrıca ESPN genel skorboard API'sinde oyuncu bazlı canlı iddaa oranları sunulmaz."
                ),
                "sistem_sinirlamasi": "Sistem sadece takım bazlı düşünmeye programlanmıştır."
            }
        ),
        "sisteme_eklenme_tavsiyesi": Choice(
            instructions="Geliştirici ve kullanıcıya nihai stratejik tavsiyen nedir?",
            criteria={
                "ana_kasa_takim_bazli_kalsin": (
                    "ÖNCELİK KORUNMALI: Ana kasa kuponları takım bazlı (MS & 1.5 Üst, 2.5 Gol, KG Var, DNB) devam etmeli. "
                    "Çünkü 11 kişinin emeği 1 kişinin sakatlığından veya oyundan çıkmasından çok daha istikrarlıdır. "
                    "Oyuncu şutları ileride sadece eğlence/fantezi kuponu olarak eklenebilir."
                ),
                "hemen_tum_korner_ve_oyuncu_eklensin": "Takım pazarlarını bırakıp tamamen korner ve oyuncu şutlarına geçilmeli."
            }
        ),
        "mikro_pazar_profesyonellik_puani": Score(
            instructions="Oyuncu şutları ve kornerlerin sürdürülebilir karlı bahis modeli olma derecesi?",
            criteria=["kumar_ve_sans_duzeyi", "orta_duzey_hobi", "profesyonel_yatirim_duzeyi"]
        )
    }
)

print("="*70)
print("  🧠 TYPESAFE AI'NIN 'OYUNCU ŞUTU VE KORNERLER' RAPORU")
print("="*70)
print(f"1. Matematiksel Doğası:     {resp.choices['mikro_pazarlarin_guvenilirligi'].choice}")
print(f"2. Teknik & Veri Nedeni:    {resp.choices['teknik_ve_veri_engeli'].choice}")
print(f"3. Nihai Strateji Tavsiyesi: {resp.choices['sisteme_eklenme_tavsiyesi'].choice}")
skor = round(resp.scores['mikro_pazar_profesyonellik_puani'].score * 5.0, 1)
print(f"4. Profesyonel Yatırım Gücü: {skor} / 10")
print("="*70)

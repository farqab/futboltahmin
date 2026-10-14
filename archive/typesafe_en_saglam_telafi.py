"""
typesafe_en_saglam_telafi.py
TypeSafe AI'dan Milan'ın yanına en stressiz, derbi riski taşımayan telafi maçını seçmesini ister.
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
    "durum": (
        "AC Milan vs Lecce (MS 1 veya 1 & 1.5 Üst) cepte ve çok sağlam (%87 güven). "
        "Kullanıcının son 50 TL'sini korumak için Juventus-Atalanta gibi kilitlenme riski olan derbi yerine, "
        "bültenden yanına konabilecek EN RİSKSİZ ikinci maçı arıyoruz."
    ),
    "aday_maclar": (
        "1. Frosinone vs Como -> Como Çifte Şans (X2) veya Como DNB (Beraberlikte İade): Como çok formda, Frosinone yenemez. Oran ~1.35 - 1.45. "
        "2. Manchester City vs Sunderland -> 2.5 ÜST veya City 1.5 Üst Gol: City evinde gol şov yapar. Oran ~1.30 - 1.40. "
        "3. Leeds United vs Crystal Palace -> 1.5 ÜST (Garanti Baraj): İki takımın temposu 2.5 üst yerine daha risksiz 1.5 Üst ile alınır. Oran ~1.30. "
        "4. Como Kazanır (MS 2): Como'nun doğrudan galibiyeti. Oran ~1.50."
    )
}

print("[*] TypeSafe AI'ya Milan'ın yanına en güvenli telafi partneri soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "en_saglam_partner": Choice(
            instructions="Milan'ın yanına son 50 TL'yi riske atmayacak en sağlam maç tercihi hangisi?",
            criteria={
                "como_x2_veya_dnb": "Frosinone vs Como -> Como Yenilmez (X2) veya Beraberlikte İade Como (DNB). Sıfır risk.",
                "city_evinde_gol": "Man City vs Sunderland -> 2.5 Üst veya City 1.5 Üst Gol. City gol garantisi.",
                "como_direkt_galibiyet": "Frosinone vs Como -> Como Kazanır (MS 2). Oranı daha dolgun (1.50).",
                "leeds_guvenli_gol": "Leeds vs Crystal Palace -> 1.5 ÜST (Baraj düşürülmüş süper garanti)."
            }
        ),
        "yeni_kupon_guvenilirligi": Score(
            instructions="Bu yeni eşleşmenin kasayı kesin koruma derecesi?",
            criteria=["orta_guven", "cok_yuksek_guven", "demir_kasa_seviyesi"]
        )
    }
)

print("="*65)
print("  🎯 TYPESAFE AI EN SAĞLAM TELAFİ PARTNERİ")
print("="*65)
print(f"Önerilen Tercih:  {resp.choices['en_saglam_partner'].choice}")
skor = round(resp.scores['yeni_kupon_guvenilirligi'].score * 5.0, 1)
print(f"Güven Skoru:      {skor} / 10")
print("="*65)

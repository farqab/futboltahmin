"""
typesafe_nesine_2oran.py
Nesine oranlarıyla net 2.00+ verecek en sağlam farklı lig ikilisini bulur.
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
    "problem": (
        "Kullanıcı Nesine'den oynuyor. Nesine'de marjlar düşük olduğu için Milan düz 1 ve FB düz 1 çarpımı 2.00 etmiyor (~1.75 kalıyor). "
        "Kullanıcının 50 TL'si için Net 2.00 - 2.25 oran verecek, farklı liglerden en güvenilir 2 maçlık telafi kombinasyonu gerekiyor."
    ),
    "secenekler": (
        "Seçenek 1: AC Milan (1 & 1.5 Üst - Nesine Oranı ~1.45) + Fenerbahçe (1 & 2.5 Üst veya İY 1.5 Üst - Nesine Oranı ~1.45). Toplam: 2.10. "
        "Seçenek 2: AC Milan (MS 1 - 1.25) + Como Kazanır (MS 2 - Nesine Oranı 1.65). Toplam: 2.06. "
        "Seçenek 3: AC Milan (1 & 1.5 Üst - 1.45) + Man City vs Sunderland (2.5 Üst - Nesine Oranı 1.45). Toplam: 2.10."
    )
}

print("[*] TypeSafe AI'ya Nesine'de net 2.00+ verecek en sağlam kombinasyon soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "en_iyi_nesine_ikilisi": Choice(
            instructions="Nesine oranlarıyla net 2.00+ verecek en sağlam telafi kombinasyonu hangisi?",
            criteria={
                "milan_ve_city_gol": "AC Milan (1 & 1.5 Üst) + Manchester City vs Sunderland (2.5 Üst) -> Toplam Oran ~2.10 (İtalya + İngiltere).",
                "milan_ve_como": "AC Milan (MS 1) + Como Kazanır (MS 2) -> Toplam Oran ~2.06 (İtalya Bankoları).",
                "milan_ve_fenerbahce_gol": "AC Milan (1 & 1.5 Üst) + Fenerbahçe (1 & 1.5 Üst) -> Toplam Oran ~2.05 (İtalya + Türkiye)."
            }
        )
    }
)

print("="*65)
print("  🎯 TYPESAFE AI NESİNE 2.00+ KUPON SEÇİMİ")
print("="*65)
print(f"Seçilen Kupon: {resp.choices['en_iyi_nesine_ikilisi'].choice}")
print("="*65)

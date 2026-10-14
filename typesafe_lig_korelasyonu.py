"""
typesafe_lig_korelasyonu.py
Garanti kuponda iki maçın da aynı ligden (Serie A: Milan + Como) olmasının
riskini TypeSafe AI'ya sorar.
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
    "soru": (
        "Kullanıcı son 50 TL'siyle 2 maçlık garanti/telafi kuponu yapacak. "
        "Adaylar: AC Milan vs Lecce (MS 1) ve Frosinone vs Como (Como X2 veya DNB). "
        "Her iki maç da İtalya Serie A'da. "
        "Aynı ligden 2 maç oynamak (İtalya ligi kilitlenmesi vb.) portföy riski yaratır mı, "
        "yoksa biri Serie A, diğeri başka ligden (örneğin Süper Lig'den Fenerbahçe 1 & 1.5 Üst) mi olmalı?"
    )
}

print("[*] TypeSafe AI'ya Lig Dağıtımı / Korelasyonu soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "lig_dagitimi": Choice(
            instructions="Garanti kuponda aynı lig (İtalya) mi yoksa farklı ligler mi seçilmeli?",
            criteria={
                "farkli_lig_daha_guvenli": (
                    "FARKLI LİG SEÇ (Örn: Milan + Fenerbahçe): İki maçın aynı ligde olması o ligdeki genel sürpriz dalgasından etkilenme riski taşır. "
                    "Ligleri dağıtmak (1 İtalya + 1 Türkiye) riski böler ve garantiyi artırır."
                ),
                "ayni_lig_sorun_degil": (
                    "AYNI LİG OLABİLİR (Milan + Como): İki maçın da dinamikleri tamamen bağımsızdır, aynı lig olması önemli değildir."
                )
            }
        ),
        "ideal_ikili": Choice(
            instructions="Hangisi daha 'çelik gibi garanti' bir ikilidir?",
            criteria={
                "milan_ve_fenerbahce": "AC Milan (MS 1) + Fenerbahçe (1 & 1.5 Üst) -> Farklı ligler, iki dev ev sahibi bankosu.",
                "milan_ve_como": "AC Milan (MS 1) + Como (X2 veya DNB) -> İkisi de İtalya."
            }
        )
    }
)

print("="*65)
print("  🛡️ TYPESAFE AI LİG KORELASYONU KARARI")
print("="*65)
print(f"Lig Dağılımı:   {resp.choices['lig_dagitimi'].choice}")
print(f"İdeal İkili:    {resp.choices['ideal_ikili'].choice}")
print("="*65)

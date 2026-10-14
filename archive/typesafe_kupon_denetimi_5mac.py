"""
typesafe_kupon_denetimi_5mac.py
Kullanıcının 5 maçlık 7.50 oranlı kuponunu TypeSafe AI'ya denetletir.
Ekstra maç eklenmeli mi, yoksa böyle mi kalmalı?
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
    "mevcut_kupon": (
        "1. Man City vs Sunderland -> 1 & 1.5 Üst (1.35) [Çok Sağlam] "
        "2. Frosinone vs Como -> 2 & 1.5 Üst (1.46) [Model Güveni %78] "
        "3. Amed vs Beşiktaş -> 2.5 Üst (1.50) [Model KG %75, 2.5 Üst %65] "
        "4. Leeds vs Crystal Palace -> 2.5 Üst (1.51) [Model Güveni %61] "
        "5. Juventus vs Atalanta -> Karşılıklı Gol Var (1.68) [Model Serie A KG Güveni %65 - Başarı %72.7] "
        "Toplam Oran: 7.50 (50 TL -> 375 TL)"
    ),
    "soru": (
        "Bir risk ve olasılık optimizasyon motoru olarak: "
        "Bu kupona 6. bir maç (örneğin AC Milan vs Lecce 1 & 1.5 Üst veya başka bir garanti maç) "
        "eklenerek oran 11.00+ bandına mı çekilmeli, yoksa 5 maçta bırakıp riski sınırlamak mı daha mantıklı?"
    )
}

print("[*] TypeSafe AI'ya 5 maçlık kuponun son dokunuşu soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "kupon_karari": Choice(
            instructions="Bu 5 maçlık kupona ne yapılmalı?",
            criteria={
                "milan_ekle_11_oran_yap": (
                    "AC Milan vs Lecce (1 & 1.5 Üst - Oran ~1.50) EKLE: Modelin %87 güven verdiği günün en sağlam bankosu. "
                    "Kuponu hiç bozmaz, riski neredeyse artırmadan oranı 7.50'den 11.25'e çıkarır (50 TL -> 562 TL)."
                ),
                "boyle_birak_dokunma": (
                    "BÖYLE BIRAK (5 Maç Kalsın): 7.50 oran 50 TL için zaten çok tatmin edici, 6. maç fazladan risk yaratır."
                ),
                "fenerbahce_ekle": (
                    "Fenerbahçe vs Eyüpspor (1 & 1.5 Üst - Oran ~1.38) EKLE: Kadıköy bankosuyla oranı 10.35'e çıkar."
                )
            }
        ),
        "mevcut_5_macin_saglamligi": Score(
            instructions="Kullanıcının hazırladığı bu 5 maçlık kuponun matematiksel sağlamlık derecesi?",
            criteria=["orta_risk", "cok_saglam_kombinasyon", "kusursuz_elit_kupon"]
        )
    }
)

print("="*65)
print("  🎯 TYPESAFE AI KUPON KARARI")
print("="*65)
print(f"Nihai Tavsiye:    {resp.choices['kupon_karari'].choice}")
skor = round(resp.scores['mevcut_5_macin_saglamligi'].score * 5.0, 1)
print(f"Kupon Kalitesi:   {skor} / 10")
print("="*65)

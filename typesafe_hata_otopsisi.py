"""
typesafe_hata_otopsisi.py
Yatan 2 maçın (Stuttgart 0-1 Dortmund, Strasbourg 1-1 Monaco) analizi ve son ince ayar.
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
    "basari_ve_hata_durumu": (
        "Model 10 en güvenilir 2.5 Üst maçından 8'ini bildi (%80 isabet). "
        "Fakat şu 2 maç 2.5 Alt bitti ve kuponları riske attı: "
        "1. VfB Stuttgart vs Borussia Dortmund (Tahmin: 2.5 Üst %65 | Sonuç: 0-1 ALT) "
        "2. Strasbourg vs AS Monaco (Tahmin: 2.5 Üst %61 | Sonuç: 1-1 ALT) "
        "Bu iki maçın ortak özelliği: İki denk ve taktiksel olarak birbirini kilitleyen güçlü takımın karşılaşması olması (Derbi / Üst Sıra Mücadelesi)."
    ),
    "soru": (
        "Yarınki gerçek kuponları yapmadan önce, bu tarz kilitlenen maçları (taktiksel derbi kilitlenmesi) "
        "2.5 Üst kuponlarından elemek için son koruma kalkanı ne olmalıdır?"
    )
}

print("[*] TypeSafe AI ile 'Son Hata Otopsisi ve Koruma Kalkanı' toplantısı yapılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "gol_kilitlenme_filtresi": Choice(
            instructions=(
                "Stuttgart-Dortmund ve Strasbourg-Monaco gibi tempolu ama birbirini kilitleyen maçları 2.5 Üst kuponuna almamak için hangi kural eklenmeli?"
            ),
            criteria={
                "ust_sira_ve_derbi_katsayisi": (
                    "İki takım da ligin üst sıralarındaysa (ilk 6) veya denk güçteyse, takımların temkinli oynama riski nedeniyle 2.5 Üst eşiğini %60'tan %68'e çıkar."
                ),
                "savunma_verimliligi_onceligi": (
                    "Eğer iki takımdan birinin son 3 maçta yediği gol sayısı 1 veya 0 ise (katı savunma), hücum tempoları yüksek olsa bile maçı 'Riskli Gol Bahsi' olarak işaretle."
                ),
                "dnb_veya_kg_donusumu": (
                    "Bu tür denk güç maçlarında 2.5 Üst yerine doğrudan KG Var veya Beraberlikte İade (DNB) tercih et."
                )
            }
        ),
        "yarin_icin_kupon_guvencesi": Score(
            instructions="Bu son ayarla birlikte yarınki kuponların kazanma olasılığı ve sağlamlık derecesi nedir?",
            criteria=["orta_guven", "cok_yuksek_guven", "zirve_banko_seviyesi"]
        )
    }
)

print("="*65)
print("  🛡️ TYPESAFE AI SON KORUMA KALKANI KARARI")
print("="*65)
print(f"Alınacak Önlem:   {resp.choices['gol_kilitlenme_filtresi'].choice}")
skor = round(resp.scores['yarin_icin_kupon_guvencesi'].score * 5.0, 1)
print(f"Yarınki Güvence:  {skor} / 10")
print("="*65)

karar = {
    "onlem": resp.choices['gol_kilitlenme_filtresi'].choice,
    "guvence": skor
}

with open("typesafe_son_onlem.json", "w", encoding="utf-8") as f:
    json.dump(karar, f, ensure_ascii=False, indent=2)

"""
typesafe_oran_alternatifi.py
Çifte şansın oran düşüklüğü itirazı ve yüksek oranlı alternatif pazar tespiti.
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
    "kullanici_geri_bildirimi": (
        "Kullanıcı çok haklı bir itirazda bulundu: 'Çifte Şans pazarında oranlar 1.15 - 1.25 seviyesine düşüyor, "
        "bu reel bir bahisçiyi tatmin etmez ve kasayı büyütmez.' "
        "Bizim hedefimiz: Oranı 1.60 - 2.20 bandında tutarak hem değerli (value) hem de yüksek olasılıklı bir pazar bulmak."
    )
}

print("[*] TypeSafe AI'ya Çifte Şans itirazı iletiliyor ve 1.60 - 2.20 bandı için alternatif soruluyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "degerli_alternatif_pazar": Choice(
            instructions=(
                "Çifte şans yerine, oranı 1.60 - 2.20 bandında olan ve beraberlik/taraf riskini süzen en iyi pazar hangisidir?"
            ),
            criteria={
                "takim_1_5_ust_gol": (
                    "Ev Sahibi / Deplasman 1.5 Üst Gol: Favori takım maçı kazanamasa bile (örneğin 2-2 bitse) 2 gol attığı an bahis kazanır. Oran: 1.65 - 2.10."
                ),
                "dnb_beraberlikte_iade": (
                    "Beraberlikte İade (Draw No Bet / Asian 0): Takım kazanırsa tam kazanç, beraberlikte para iade edilir. Oran: 1.50 - 1.95."
                ),
                "iy_0_5_veya_1_5_ust": (
                    "İlk Yarı Gol Bahisleri (İY 0.5 veya İY 1.5 Üst): 90 dakikanın yorgunluk/kırmızı kart sürprizlerinden kaçıp ilk yarı temposuna oynamak. Oran: 1.60 - 2.30."
                )
            }
        ),
        "uygulanabilirlik_derecesi": Score(
            instructions="Seçilen alternatifin kupon karlılığını ve isabetini optimize etme gücü nedir?",
            criteria=["dusuk", "orta", "cok_yuksek_deger"]
        )
    }
)

print("="*65)
print("  🎯 TYPESAFE AI'NIN ALTERNATİF PAZAR YANITI")
print("="*65)
print(f"Önerilen Pazar: {resp.choices['degerli_alternatif_pazar'].choice}")
skor = round(resp.scores['uygulanabilirlik_derecesi'].score * 5.0, 1)
print(f"Değer Gücü:     {skor} / 10")
print("="*65)

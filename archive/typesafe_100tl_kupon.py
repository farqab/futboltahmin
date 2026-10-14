"""
typesafe_100tl_kupon.py
Kullanıcının 100 TL kasası için:
- Beşiktaş maçı YASAK (tuttuğu takım / duygusal risk)
- 1.35 altı ölü oranlar YASAK (FB, City)
- İki kuponda aynı maç kullanımı YASAK
- Hedef: 1.80 - 3.00 bandında en sağlam portföy
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)

# 20 Eylül analiz edilmiş maçlarını yükle
with open("tahminler_20260920.json", encoding="utf-8") as f:
    matches = json.load(f)

# Filtreler:
# 1. Beşiktaş maçı elenecek
# 2. Oranı 1.35 altı olanlar elenecek
aday_maclar = []
for m in matches:
    h = m.get("home_name", "")
    a = m.get("away_name", "")
    if "besiktas" in h.lower() or "besiktas" in a.lower():
        continue
    odds = m.get("odds") or {}
    h_odd = float(odds.get("ms_1") or 2.0)
    a_odd = float(odds.get("ms_2") or 2.0)
    
    # Çok düşük oranları ele (FB, City vb.)
    if m.get("action_status") == "BET":
        pred_odd = h_odd if m.get("tahmin_ms") == "MS 1" else a_odd
        if pred_odd < 1.35:
            continue
            
    aday_maclar.append({
        "mac": f"{h} vs {a}",
        "lig": m.get("league"),
        "tahmin_ms": m.get("tahmin_ms"),
        "guven": m.get("confidence"),
        "tuzak": m.get("trap_score"),
        "over_prob": m.get("over_2_5_prob"),
        "btts_prob": m.get("btts_prob"),
        "h_odd": h_odd,
        "a_odd": a_odd,
        "over_odd": float(odds.get("over_2_5") or 1.80),
        "status": m.get("action_status")
    })

state = {
    "kasa_durumu": "Kullanıcının tam 100 TL sermayesi var. Sıfır hata ile en mantıklı şekilde oynanmalı.",
    "kisitlamalar": "Beşiktaş maçı kesinlikle yok. 1.35 altı ölü oranlar yok.",
    "havuzdaki_en_guclu_maclar": [
        "Como Galibiyeti (Frosinone vs Como): Oran ~1.50, Como formda, Model Güveni %78, Tuzak 4.3",
        "Leeds vs Crystal Palace 2.5 Üst: Oran ~1.70, Model 2.5 Üst Güveni %61",
        "Marseille vs PSG KG Var: Oran ~1.60, Derbi ateşi, Model KG Güveni %69",
        "Juventus vs Atalanta KG Var: Oran ~1.70, İki ofansif dev, Model KG Güveni %65",
        "Nice vs Lille 2.5 Alt veya KG Var: Oran ~1.75, Model KG Güveni %67"
    ]
}

print("[*] TypeSafe AI ile 100 TL'lik En Güvenli Kupon Stratejisi belirleniyor...\n")

resp = client.system_one(
    state=state,
    questions={
        "en_ideal_kupon_secimi": Choice(
            instructions=(
                "Kullanıcının tam 100 TL'si var. Bu 100 TL'yi riske atmadan, 2.00 - 3.00 arası tatmin edici bir oranla "
                "en yüksek olasılıkla kasayı katlayacak 2 maçlık kombinasyon hangisidir?"
            ),
            criteria={
                "kombinasyon_a": (
                    "Kombinasyon A (Como Kazanır + Leeds/Palace 2.5 Üst): "
                    "1 Taraf Güvencesi (Como 1.50) + 1 Premier Lig Tempolu Golü (Leeds 2.5 Üst 1.70). Toplam Oran: ~2.55."
                ),
                "kombinasyon_b": (
                    "Kombinasyon B (Como Kazanır + Marseille/PSG KG Var): "
                    "1 Taraf Güvencesi (Como 1.50) + 1 Fransız Derbisi Karşılıklı Gol (PSG KG Var 1.60). Toplam Oran: ~2.40."
                ),
                "kombinasyon_c": (
                    "Kombinasyon C (İki Büyük Maç KG Var: Marseille/PSG KG + Juventus/Atalanta KG): "
                    "Taraflara hiç bulaşmadan iki ligin dev maçında karşılıklı goller. Toplam Oran: ~2.72."
                )
            }
        ),
        "kasa_yonetimi_tavsiyesi": Choice(
            instructions="100 TL nasıl yatırılmalı?",
            criteria={
                "tek_kursun_100_tl": "En güvendiğimiz tek bir 2'li kupona 100 TL basıp parayı 2.5 katına çıkarmak.",
                "ikiye_bol_50_50": "50 TL Ana Kasaya (Kombinasyon B), 50 TL Gol Kuponuna (Kombinasyon C) paylaştırmak."
            }
        ),
        "secilen_kuponun_guveni": Score(
            instructions="Seçilen kuponun gerçekleşme ve 100 TL'yi koruyup büyütme gücü?",
            criteria=["orta_risk", "guclu_kasa", "kusursuz_deger"]
        )
    }
)

print("="*65)
print("  🎯 TYPESAFE AI 100 TL STRATEJİSİ")
print("="*65)
print(f"Önerilen Kupon:  {resp.choices['en_ideal_kupon_secimi'].choice}")
print(f"Para Dağıtımı:   {resp.choices['kasa_yonetimi_tavsiyesi'].choice}")
skor = round(resp.scores['secilen_kuponun_guveni'].score * 5.0, 1)
print(f"Kupon Güveni:    {skor} / 10")
print("="*65)

"""
typesafe_derin_sohbet.py
TypeSafe AI ile ileri düzey inovasyon ve kupon optimizasyon oturumu.
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
    "mevcut_durum": (
        "İkili Uzman Mimarisi (Dual-Expert: Ajan 1 Taraf, Ajan 2 Gol) ile büyük bir atılım yaptık: "
        "- 2.5 Alt/Üst isabeti %46.8'den %65.8'e yükseldi (Bundesliga'da %85.7, Premier Lig'de %66.7). "
        "- Banko seçiminde %100 başarı sağlandı. "
        "- Taraf isabeti %52 civarında stabilize oldu."
    ),
    "soru_amaci": (
        "Şimdi sistemi bir sonraki seviyeye (Next-Gen AI Betting Model) taşımak istiyoruz. "
        "Matematiksel kesinliği artırmak, kupon getirisini (ROI) maksimize etmek ve "
        "tahminlerdeki varyansı minimuma indirmek için hangi çığır açıcı mekanizmaları eklemeliyiz?"
    )
}

print("[*] TypeSafe AI ile 'Yeni Nesil İnovasyon' istişaresi başlatılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "kupon_kombinasyon_zekasi": Choice(
            instructions=(
                "Şu an tekil maç tahminleri yapıyoruz. Gerçek dünyada kullanıcılar 2'li veya 3'lü kombineler oynuyor. "
                "En karlı ve güvenli kupon kombinasyon motoru (Smart Combinator) nasıl çalışmalı?"
            ),
            criteria={
                "korelasyon_bazli_kombine": (
                    "Korelasyonlu bahisleri birleştir: Örneğin Bundesliga'dan banko 2.5 Üst + La Liga'dan banko MS 1. "
                    "Aynı ligden risk birikimi yapma, riski liglere dağıt."
                ),
                "kelly_kriteri_kasa_yonetimi": (
                    "Kelly Kriteri (Kelly Criterion) & Değer Bahsi (Value Bet): Sadece olasılığı yüksek olanı değil, "
                    "piyasa oranının gerçek ihtimalden yüksek olduğu matematiksel arbitraj maçlarını kupona al."
                ),
                "dinamik_2li_sistem": (
                    "Her gün sadece EN GÜVENİLİR 1 Taraf Bankosu + 1 Gol Bankosu seçerek 'Günün Çifte Kasası'nı üret."
                )
            }
        ),
        "taraf_bahsi_derinlesmesi": Choice(
            instructions=(
                "MS (Taraf) isabetini %52'den %60+ bandına çekmek için ne tür bir taktiksel veri katmanı eklenmeli?"
            ),
            criteria={
                "cifte_sans_ve_dnb_donusumu": (
                    "Riskli maçlarda saf MS 1 yerine Çifte Şans (1X) veya Beraberlikte İade (DNB) olasılığı hesaplat. "
                    "Bu sayede beraberlik sürprizleri kuponu yatırmaz."
                ),
                "pres_ve_oyun_tarzi_uyusmazligi": (
                    "Takımların taktik uyumu: Topa sahip olma takımı vs Kontratak takımı eşleşmelerini analiz et."
                ),
                "oran_hareketleri_ve_akilli_para": (
                    "Piyasa açılış vs kapanış oranlarındaki düşüş/yükseliş trendlerini (Smart Money) modele besle."
                )
            }
        ),
        "canli_risk_kalibrasyonu": Noul(
            instructions=(
                "Modelin tahminlerine bir 'Kalibrasyon Katsayısı' eklenirse "
                "(örneğin AI %70 diyorsa bu tarihsel olarak gerçekten %70 mi tutuyor yoksa aşırı mı güveniyor), "
                "bunun tahmin doğruluğunu zirveye taşıma etki gücü nedir? (0.0=Önemsiz, 1.0=Devrimsel)"
            )
        ),
        "nihai_inovasyon_vizyonu": Score(
            instructions=(
                "Bu özellikler eklenirse sistemin piyasadaki profesyonel algoritmik bahis sendikaları "
                "(Tony Bloom / Matthew Benham tarzı) seviyesine yaklaşma derecesi nedir?"
            ),
            criteria=["iyi_amator_arac", "profesyonel_analiz_seviyesi", "algoritmik_sendika_duzeyi"]
        )
    }
)

print("="*70)
print("  🧠 TYPESAFE AI İLERİ DÜZEY GELİŞTİRME VİZYONU")
print("="*70)
print(f"1. Kupon Kombinasyon Zekası:   {resp.choices['kupon_kombinasyon_zekasi'].choice}")
print(f"2. Taraf İsabeti Yükseltme:     {resp.choices['taraf_bahsi_derinlesmesi'].choice}")
print(f"3. Olasılık Kalibrasyon Gücü:   %{round(resp.nouls['canli_risk_kalibrasyonu'].noul * 100)}")
skor = round(resp.scores['nihai_inovasyon_vizyonu'].score * 5.0, 1)
print(f"4. Algoritmik Güç Skoru:        {skor} / 10")
print("="*70)

plan = {
    "kombinasyon_stratejisi": resp.choices['kupon_kombinasyon_zekasi'].choice,
    "taraf_derinlesmesi": resp.choices['taraf_bahsi_derinlesmesi'].choice,
    "kalibrasyon_etkisi": round(resp.nouls['canli_risk_kalibrasyonu'].noul, 2),
    "vizyon_skoru": skor
}

with open("typesafe_ileri_vizyon.json", "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

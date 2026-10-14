"""
typesafe_mimari_danisma.py
TypeSafe AI ile derin istişare ve optimal mimari belirleme.
"""
import sys, os, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

os.chdir(r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI")
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

API_KEY = os.environ.get("TYPESAFE_API_KEY", "apikey_2602055d44d82ff4d00800ce1a9c1b0d59a_9dc9fa7b2e8e83e0c23bde23f22ac099206b463d7d0ef440d34a4754655b918b")
client = TypeSafeClient(api_key=API_KEY)

# Backtest gerçekleri
context = {
    "problem_tanimi": (
        "Futbol tahmin motorunu geliştirirken ilginç bir bulguya rastladık: "
        "1. ESKİ BASİT SİSTEM: Sadece Lig Sıralaması, Son 3 Maç Skoru ve İddaa Oranlarını alıyordu. "
        "Sonuç: MS (Taraf) isabeti %54.4, Banko isabeti 10'da 9 (%90 - ROI %99). Fakat 2.5 Alt/Üst isabeti %49-53 civarında zayıftı. "
        "2. AŞIRI DETAYLI YENİ SİSTEM: H2H, xG, Dinlenme günü, Rotation riski, Deplasman/Ev özel golleri, Momentum eklendi. "
        "Sonuç: 2.5 Alt/Üst isabeti %64.6'ya fırladı (Serie A'da %90.9, Bundesliga'da %85.7 oldu!). "
        "ANCAK MS (Taraf) isabeti %43'e düştü ve sistem 0 BANKO seçti. Çünkü aşırı detay ve çelişkili sinyaller (over-prompting/gürültü) "
        "AI'yı korkuttu ve taraf tahmininde belirsizlik yarattı."
    ),
    "hedef": (
        "Hem eski sistemin %90 tutan BANKO / MS gücünü geri kazanmak, "
        "hem de yeni sistemin 2.5 Alt/Üst'teki %65-%90'lık muazzam gol analiz gücünü korumak."
    )
}

print("[*] TypeSafe AI ile ortak mimari planlaması yapılıyor...")

resp = client.system_one(
    state=context,
    questions={
        "ayrik_soru_mimarisi": Choice(
            instructions=(
                "MS (Taraf) ve Gol (2.5 & KG) tahminlerinin state/prompt girdileri nasıl ayrıştırılmalı?"
            ),
            criteria={
                "hibrit_tek_cagri_moduler_state": (
                    "Tek bir çağrıda ama net ayrılmış bölümler: Taraf sorusu için sadece Temel Güç/Oranlar vurgulanmalı, "
                    "Gol soruları için tempo/gol istatistikleri vurgulanmalı."
                ),
                "iki_ozellesmis_ajan": (
                    "İki ayrı uzmanlaşmış model/fonksiyon: 1. Model sadece Taraf & Banko Analisti (Sade veriyle %90 banko üretir), "
                    "2. Model sadece Gol & Tempo Analisti (Derin istatistikle %70-90 gol üretir)."
                )
            }
        ),
        "banko_filtresi_revizyonu": Choice(
            instructions=(
                "Yeni sistemin 0 banko çıkarmasının sebebi aşırı katı 6 katmanlı filtreydi (en ufak rotasyon veya H2H eksiğinde eliyordu). "
                "Eski sistem trap <= 5.0 ve conf >= 50 ile 10'da 9 bilmişti. Banko filtresi nasıl olmalı?"
            ),
            criteria={
                "eski_esik_yeni_denetim": (
                    "Eski eşiklere dön (Conf >= 55, Trap <= 5.0). Yeni verileri (rotasyon, xG) mutlak engelleyici kural değil, "
                    "sadece puan kırıcı/tuzak puanını artırıcı faktör olarak kullan."
                ),
                "sadece_ai_karari": (
                    "Filtreleri kaldır, kararı tamamen TypeSafe AI'nın 'banko_oyna' seçimine bırak."
                )
            }
        ),
        "lig_ozellestirme_kullanimi": Choice(
            instructions=(
                "Backtest'te Serie A ve Bundesliga'da gol tahmini %85-90 tutarken, Premier Lig sürprizlerle dolu çıktı. "
                "Lig stratejisi motora nasıl entegre edilmeli?"
            ),
            criteria={
                "aktif_kupon_yonlendirici": (
                    "Ligin güçlü yönüne göre kupon tipi öner: Bundesliga/Serie A ise öncelik 2.5 Üst/KG; "
                    "Süper Lig/La Liga ise MS/Taraf; Premier Lig ise yüksek tuzak uyarısı ver."
                ),
                "pasif_bilgi": (
                    "Sadece not olarak yaz, kararlara ve filtrelere müdahale etme."
                )
            }
        ),
        "ideal_tahmin_guvenilirligi": Score(
            instructions="Bu hibrit yaklaşımla tahminlerin genel kalitesinin zirveye çıkma derecesi nedir?",
            criteria=["orta_duzey", "yuksek_basari", "zirve_performans"]
        )
    }
)

print("\n" + "="*65)
print("  🤝 TYPESAFE AI MİMARİ KARARLARI")
print("="*65)
print(f"1. Prompt Mimarisi:      {resp.choices['ayrik_soru_mimarisi'].choice}")
print(f"2. Banko Filtre Mantığı: {resp.choices['banko_filtresi_revizyonu'].choice}")
print(f"3. Lig Entegrasyonu:     {resp.choices['lig_ozellestirme_kullanimi'].choice}")
print(f"4. Güven/Başarı Skoru:   {round(resp.scores['ideal_tahmin_guvenilirligi'].score * 5.0, 1)} / 10")
print("="*65)

karar = {
    "ayrik_soru_mimarisi": resp.choices['ayrik_soru_mimarisi'].choice,
    "banko_filtresi_revizyonu": resp.choices['banko_filtresi_revizyonu'].choice,
    "lig_ozellestirme_kullanimi": resp.choices['lig_ozellestirme_kullanimi'].choice,
    "skor": round(resp.scores['ideal_tahmin_guvenilirligi'].score * 5.0, 1)
}

with open("typesafe_ortak_plan.json", "w", encoding="utf-8") as f:
    json.dump(karar, f, ensure_ascii=False, indent=2)

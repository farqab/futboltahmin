"""
typesafe_omni_market_danisma.py
Kullanıcının vizyoner fikri: "Bütün İddaa marketleri (MS & 1.5 Üst, 2.5 Alt/Üst, İY Gol, 
ÇŞ, KG vb.) taranıp içlerinden 'En Yüksek Güven + En Tatmin Edici Oran' dengesine sahip 
EN İDEAL tek tercihi TypeSafe AI otomatik seçebilir mi?"
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
    "kullanici_fikri": (
        "Kullanıcı çok vizyoner bir sistem yükseltmesi önerdi: "
        "'Biz şu ana kadar sadece MS ve 2.5 Alt/Üst üzerinde odaklandık. "
        "Oysa İddaa'da bir maç için onlarca market var: MS & 1.5 Üst, İY 0.5 Üst, Çifte Şans, "
        "Takım Golü (Ev 1.5 Üst), 2.5 Üst, KG Var, Handikap vb. "
        "TypeSafe AI maçın bütün parametrelerini ve piyasadaki tüm oranları önüne koysak, "
        "her maç için sabit bir markete zorlamak yerine, o maç özelinde 'EN YÜKSEK GÜVENİLİRLİK + EN GÜZEL ORAN' "
        "(En Yüksek Beklenen Değer - Expected Value) dengesine sahip tek bir en akıllı tercihi otomatik seçebilir mi?'"
    ),
    "mevcut_altyapi": (
        "Mevcut sistemde maçın verileri (H2H, iç/dış saha tempoları, oranlar, rotasyon) var. "
        "Eğer her maç için olası 6-8 ana İddaa marketinin olasılığını ve oranını hesaplatırsak, "
        "TypeSafe AI en karlı ve en güvenli marketi doğrudan 'Günün İncisi / En Mantıklı Bahis' olarak seçebilir."
    )
}

print("[*] TypeSafe AI'ya 'Bütüncül Market Seçici (Omni-Market Optimal Picker)' fikri danışılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "omni_market_uygulanabilirlik": Choice(
            instructions=(
                "TypeSafe AI olarak bir maça tek bir sabit pazar (sadece MS veya sadece 2.5) dayatmak yerine, "
                "o maça ait tüm olası pazarlar arasından en karlı/güvenli seçimi dinamik olarak yapabilir misin?"
            ),
            criteria={
                "dinamik_en_iyi_tercih_secici": (
                    "KESİNLİKLE EVET: Her maçın karakteri farklıdır. Kimi maçın en garanti tercihi 'MS & 1.5 Üst' iken, "
                    "kimi maçta 'Ev 1.5 Üst Gol' veya 'KG Var' açık ara en mantıklı ve en risksiz tercihtir. "
                    "Bunu dinamik seçmek sistemin getirisini ve tutma oranını katlar."
                ),
                "mevcut_sabit_yapi_daha_guvenli": (
                    "HAYIR: Çok fazla pazar eklemek modelin odaklanmasını zorlaştırabilir, sadece MS ve 2.5 üzerinde kalınmalı."
                )
            }
        ),
        "en_karlı_ve_tahmin_edilebilir_pazarlar": Choice(
            instructions=(
                "İddaa bültenindeki onlarca pazar içinden makine öğrenimi ve yapay zeka ile "
                "tahmin tutarlılığı en yüksek olan 'Altın 5 Market' hangileridir?"
            ),
            criteria={
                "kombinasyonlu_ve_korumali_marketler": (
                    "1. MS & 1.5 Üst (Favori kazanır + gol garanti) "
                    "2. Takım 1.5 Üst Gol (Ev/Dep en az 2 atar - sonuçtan bağımsız) "
                    "3. 2.5 Alt / Üst (Tempo analizi) "
                    "4. Karşılıklı Gol Var/Yok (Hücum/Savunma dengesi) "
                    "5. Beraberlikte İade (DNB - Beraberlikte para iadesi)"
                ),
                "ozel_ve_nadir_marketler": (
                    "Korner sayısı, kart sayısı, ilk golü kim atar, kaleci kurtarış sayısı gibi mikro pazarlar."
                )
            }
        ),
        "matematiksel_deger_formulu": Choice(
            instructions=(
                "En mantıklı tercihi seçerken TypeSafe AI hangi matematiksel algoritmayı kullanmalı?"
            ),
            criteria={
                "expected_value_ve_guven_skoru": (
                    "Beklenen Değer (EV = Güven_Olasılığı x Oran) ve Tuzak Puanı Filtresi: "
                    "Örn: %85 güvenli 1.45 oranlı tercih, %55 güvenli 2.00 oranlı tercihten matematiksel olarak çok daha üstündür. "
                    "Güven barajı >= %70 olanlar arasında en yüksek orana sahip tercih 'Optimal Seçim' ilan edilir."
                ),
                "sadece_en_yuksek_guven": (
                    "Orana bakılmaksızın sadece gerçekleşme olasılığı en yüksek (%90+) olan pazar seçilsin (oran 1.20 olsa bile)."
                )
            }
        ),
        "sistem_donusum_etkisi": Score(
            instructions=(
                "Bu dinamik market seçici özellik eklenirse, kullanıcının kupon başarı yüzdesi ve "
                "kasa katlama performansındaki sıçrama derecesi ne olur?"
            ),
            criteria=["onemsiz_fark", "ciddi_iyilesme", "devrimsel_kasa_katlama"]
        )
    }
)

print("="*70)
print("  🧠 TYPESAFE AI'NIN 'TÜM İDDAA MARKETLERİ' DANIŞMA RAPORU")
print("="*70)
print(f"1. Yapılabilir mi / Mantıklı mı?: {resp.choices['omni_market_uygulanabilirlik'].choice}")
print(f"2. En İdeal Market Havuzu:       {resp.choices['en_karlı_ve_tahmin_edilebilir_pazarlar'].choice}")
print(f"3. Matematiksel Seçim Motoru:    {resp.choices['matematiksel_deger_formulu'].choice}")
skor = round(resp.scores['sistem_donusum_etkisi'].score * 5.0, 1)
print(f"4. Sistem Dönüşüm Skoru:         {skor} / 10")
print("="*70)

sonuc = {
    "uygulanabilirlik": resp.choices['omni_market_uygulanabilirlik'].choice,
    "ideal_pazarlar": resp.choices['en_karlı_ve_tahmin_edilebilir_pazarlar'].choice,
    "formül": resp.choices['matematiksel_deger_formulu'].choice,
    "etki_skoru": skor
}

with open("typesafe_omni_market_karar.json", "w", encoding="utf-8") as f:
    json.dump(sonuc, f, ensure_ascii=False, indent=2)

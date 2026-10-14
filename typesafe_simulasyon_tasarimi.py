"""
typesafe_simulasyon_tasarimi.py
TypeSafe AI ile Monte Carlo & Poisson 10.000 Maç Simülasyon Motorunun
matematiksel mimarisini ve entegrasyon parametrelerini belirler.
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
    "amac": (
        "Sisteme Monte Carlo ve Poisson 10.000 Maç Simülasyon Motoru kuruyoruz. "
        "Her maç için takımların iç/dış saha gol ortalamaları, savunma direnci ve xG verilerinden "
        "iki takımın beklenen gol lambdaları (Lambda_Ev ve Lambda_Dep) hesaplanacak. "
        "Ardından maç 10.000 kez oynatılıp simüle edilecek."
    )
}

print("[*] TypeSafe AI ile Simülasyon Motoru Matematiksel Tasarımı yapılıyor...\n")

resp = client.system_one(
    state=context,
    questions={
        "lambda_hesaplama_mantigi": Choice(
            instructions="Beklenen gol (Poisson Lambda) parametresi nasıl hesaplanmalı?",
            criteria={
                "hibrit_ev_deplasman_ve_xg": (
                    "HİBRİT FORMÜL: Ev sahibinin evdeki gol gücü + Deplasmanın dış saha zaafiyeti + "
                    "Ligin genel gol ortalaması + xG (varsa). Bu 4 faktörün ağırlıklı ortalamasıyla "
                    "en hassas Lambda_Ev ve Lambda_Dep değerleri üretilir."
                ),
                "sadece_genel_gol_ortalamasi": "Sadece son 5 maçın düz gol ortalaması alınsın."
            }
        ),
        "simulasyon_sayisi": Choice(
            instructions="Performans ve kesinlik açısından kaç simülasyon iterasyonu idealdir?",
            criteria={
                "on_bin_simulasyon": "10.000 İterasyon: Hızlı NumPy vektörizasyonu ile milisaniyeler sürer ve %99.9 istatistiksel güven aralığı verir.",
                "bin_simulasyon": "1.000 İterasyon: Yeterlidir ancak küçük varyans sapmaları olabilir."
            }
        ),
        "yapay_zeka_entegrasyonu": Choice(
            instructions="Simülasyon sonuçları yapay zekaya (TypeSafe AI) nasıl beslenmeli?",
            criteria={
                "dogrudan_state_ve_karar_filtresi": (
                    "Yapay Zeka State'ine '10.000 Simülasyon Çıktısı' olarak doğrudan girsin. "
                    "Ayrıca yapay zekanın 1.5 Üst veya 2.5 Üst tahmini simülasyonla çelişirse, "
                    "simülasyon yapay zekayı denetleyip daha güvenli pazara (ör: 2.5 yerine 1.5 Üst) yönlendirsin."
                ),
                "sadece_ekranda_goster": "Sadece kullanıcıya bilgi olarak gösterilsin, karar mekanizmasına karışmasın."
            }
        )
    }
)

print("="*65)
print("  🎲 TYPESAFE AI SİMÜLASYON TASARIM RAPORU")
print("="*65)
print(f"1. Lambda Modeli:   {resp.choices['lambda_hesaplama_mantigi'].choice}")
print(f"2. Simülasyon Hacmi:{resp.choices['simulasyon_sayisi'].choice}")
print(f"3. AI Entegrasyonu: {resp.choices['yapay_zeka_entegrasyonu'].choice}")
print("="*65)

bat_lines = [
    "@echo off",
    "title FutbolTahminAI",
    'cd /d "%~dp0"',
    "echo ===================================================================",
    "echo   FUTBOL TAHMIN AI - 100%% GERCEK VERI VE TYPESAFE ANALIZ",
    "echo ===================================================================",
    "echo.",
    "echo [*] ESPN API'den bugunun mac verileri aliniyor ve analiz basliyor...",
    "echo.",
    r'"..\TurkceSesliAsistan\.venv\Scripts\python.exe" gunluk_tahmin.py %*',
    "echo.",
    "echo ===================================================================",
    "echo   Analiz tamamlandi! Rapor tarayicinizda acildi.",
    "echo ===================================================================",
    "pause"
]

target = r"C:\Users\farqa\OneDrive\Masaüstü\FutbolTahminAI\baslat.bat"
content = "\r\n".join(bat_lines) + "\r\n"

with open(target, "wb") as f:
    f.write(content.encode("ascii"))

print("baslat.bat 100% pure ASCII ve CRLF ile guncellendi!")

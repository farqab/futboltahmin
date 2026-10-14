@echo off
title FutbolTahminAI - Kuresel Sharp Istihbarat & Dixon-Coles Boru Hatti
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================================
echo   FUTBOL TAHMIN AI - KURESEL SHARP ISTIHBARAT & DIXON-COLES
echo   1. FLASHSCORE NINJA: Teyitli Ilk 11 ve Dizilis Analizi
echo   2. PINNACLE SHARP: Marjsiz Gercek Cizgi ve Sazan Tuzagi Korumasi
echo   3. DROPPING ODDS: Coklu Yabanci Buro Oran Cokusu (Steam Moves)
echo   4. VIP BARON RADARI: Betfair Matched Volume, Moneyway & Asya Cizgisi
echo ===================================================================
echo.
echo [*] Canli maclar cekiliyor, 3'lu kuresel filtre ve +EV analizi calistiriliyor...
echo.
"..\TurkceSesliAsistan\.venv\Scripts\python.exe" gunluk_tahmin.py %*
echo.
echo ===================================================================
echo   Analiz tamamlandi! Rapor tarayicinizda acildi.
echo ===================================================================
pause

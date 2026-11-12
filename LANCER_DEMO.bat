@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
echo === Mon Kiosque / Moki : demarrage de la demo ===
taskkill /F /IM uvicorn.exe >nul 2>&1
if exist moki_demo.db del moki_demo.db
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R /C:"IPv4"') do set IP=%%a
echo Adresse du reseau : %IP%
echo (verifie que MOKI_URL_PUBLIQUE dans le fichier .env correspond : http://ADRESSE:8000)
start "" http://localhost:8000/qr
.venv\Scripts\uvicorn.exe app.api.main:creer_app --factory --host 0.0.0.0 --port 8000

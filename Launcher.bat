@echo off
setlocal

REM Cek apakah pythonw tersedia
where pythonw >nul 2>nul
if errorlevel 1 (
    echo Pythonw tidak ditemukan di PATH.
    echo Silakan instal Python 3.12+ dan pastikan sudah ditambahkan ke PATH.
    pause
    exit /b 1
)

REM Install dependencies dari requirements.txt
if exist "%~dp0requirements.txt" (
    pythonw -m pip install --upgrade pip
    pythonw -m pip install -r "%~dp0requirements.txt"
)

REM Jalankan aplikasi utama tanpa membuka cmd window
start "" pythonw "%~dp0main.py"
exit /b 0
endlocal

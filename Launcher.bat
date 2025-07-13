@echo off
setlocal

REM Cek apakah python tersedia
where python >nul 2>nul
if errorlevel 1 (
    echo Python tidak ditemukan di PATH.
    echo Silakan instal Python 3.12+ dan pastikan sudah ditambahkan ke PATH.
    pause
    exit /b 1
)

REM Install dependencies dari requirements.txt
if exist "%~dp0requirements.txt" (
    python -m pip install --upgrade pip
    python -m pip install -r "%~dp0requirements.txt"
)

REM Jalankan aplikasi utama
python "%~dp0main.py"
if errorlevel 1 (
    echo Terjadi kesalahan saat menjalankan aplikasi.
    pause
    exit /b 1
)

endlocal

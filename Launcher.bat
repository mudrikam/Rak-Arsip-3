::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdDWDJHuR/U40FClVR0mjLnizFvhP1Pr+/NaVo0YUX+0xNobY1dQ=
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSDk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpCI=
::egkzugNsPRvcWATEpCI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+IeA==
::cxY6rQJ7JhzQF1fEqQJgZksaHErTXA==
::ZQ05rAF9IBncCkqN+0xwdVsEAlTMbyXqZg==
::ZQ05rAF9IAHYFVzEqQICKRAUbRaRNXv6VdU=
::eg0/rx1wNQPfEVWB+kM9LVsJDDaDNyubFKYV+Kiojw==
::fBEirQZwNQPfEVWB+kM9LVsJDDaDNyubFKYV+Kiojw==
::cRolqwZ3JBvQF1fEqQICKRAUbRaRNXv6VdU=
::dhA7uBVwLU+EWH2B50M5JhJVLA==
::YQ03rBFzNR3SWATE0EcjKRJaRQXi
::dhAmsQZ3MwfNWATE0EcjKRJaRQXi
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdDWDJHuR/U40FClVR0mjLnizFvhP1Nr65KqmsF4URKJsNorD39Q=
::YB416Ek+ZG8=
::
::
::978f952a14a936cc963da21a135fa983
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

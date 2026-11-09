@echo off
setlocal
cd /d "%~dp0.."

echo ================================================
echo Shobi - Fragrantica brand logo archive (LOCAL)
echo ================================================
echo.
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo ERRORE: questa cartella non e' una copia Git del repository.
  echo Clona prima https://github.com/MarvvRed/Shobi_Inspiration
  pause
  exit /b 1
)

for /f %%B in ('git branch --show-current') do set CURRENT_BRANCH=%%B
if not "%CURRENT_BRANCH%"=="main" (
  echo ERRORE: sei sul branch "%CURRENT_BRANCH%". Passa a main prima di continuare.
  pause
  exit /b 1
)

where py >nul 2>&1
if errorlevel 1 (
  echo ERRORE: Python non trovato. Installa Python 3.11 o 3.12 e abilita "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv-brand-logos\Scripts\python.exe" (
  py -3 -m venv .venv-brand-logos
  if errorlevel 1 goto :error
)

".venv-brand-logos\Scripts\python.exe" -m pip install --upgrade requests beautifulsoup4 pillow
if errorlevel 1 goto :error

set MAX_PAGES=1
set BRAND_LIMIT=30
echo.
set /p MAX_PAGES=Numero pagine directory (invio = 1): 
if "%MAX_PAGES%"=="" set MAX_PAGES=1
set /p BRAND_LIMIT=Numero marchi (invio = 30): 
if "%BRAND_LIMIT%"=="" set BRAND_LIMIT=30

echo.
echo Avvio raccolta locale: pagine=%MAX_PAGES%, marchi=%BRAND_LIMIT%
".venv-brand-logos\Scripts\python.exe" tools\build_fragrantica_brand_logos.py --max-pages %MAX_PAGES% --limit %BRAND_LIMIT% --delay 4
if errorlevel 1 goto :error

git add database/brands/brands_logos.json database/assets/brand-logos
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Add Fragrantica brand logo archive pilot"
  if errorlevel 1 goto :error
  git push origin main
  if errorlevel 1 goto :error
  echo.
  echo ARCHIVIO PUBBLICATO SU GITHUB.
) else (
  echo Nessuna modifica da pubblicare.
)
echo.
echo Operazione completata. Puoi chiudere questa finestra.
pause
exit /b 0

:error
echo.
echo Operazione interrotta. Leggi l'errore qui sopra e conserva i file generati.
pause
exit /b 1

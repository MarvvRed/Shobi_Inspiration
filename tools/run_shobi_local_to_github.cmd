@echo off
setlocal
cd /d "%~dp0\.."

echo === Shobi local resolver - PC to GitHub ===
where python >nul 2>nul || (echo ERROR: Python not found in PATH & exit /b 1)
where git >nul 2>nul || (echo ERROR: Git not found in PATH & exit /b 1)

git pull --rebase || exit /b 1

python tools\shobi_identity_resolver.py run --resolver-cmd "python tools\shobi_fragrantica_direct_resolver.py" --limit 5 --timeout 90 --retries 2 --retry-delay 4
if errorlevel 1 exit /b 1

python tools\shobi_identity_resolver.py stats

git add data\shobi-fragrantica-mapping.csv data\identity-resolver-state.json data\identity-resolver-errors.csv 2>nul
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Checkpoint Shobi identities from local PC" || exit /b 1
  git push || exit /b 1
) else (
  echo No new resolver progress to push.
)

echo === Done ===
endlocal

@echo off
setlocal
cd /d "%~dp0.."
python tools\shobi_identity_resolver.py run --resolver-cmd "python tools\shobi_online_resolver.py" %*
endlocal

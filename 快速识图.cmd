@echo off
setlocal
cd /d "%~dp0"
if not exist "wjdr_fast_vision.py" (
  echo [ERROR] wjdr_fast_vision.py is missing from this package.
  exit /b 2
)
python wjdr_fast_vision.py %*
exit /b %errorlevel%

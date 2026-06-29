@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  set "PYTHON=python"
)

if not exist ".venv\Scripts\python.exe" (
  %PYTHON% -m venv .venv
  if errorlevel 1 goto error
)

call ".venv\Scripts\activate.bat"
python -m pip install -e ".[dev]"
if errorlevel 1 goto error

python -m keysmith.app
if errorlevel 1 goto error

goto end

:error
echo.
echo Keysmith could not start. Make sure Python 3.9 or newer is installed and available on PATH.
pause
exit /b 1

:end
endlocal

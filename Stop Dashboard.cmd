@echo off
setlocal
set "DESK_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%DESK_PYTHON%" (
  echo Bundled Python was not found. See README.md.
  pause
  exit /b 1
)
"%DESK_PYTHON%" -X utf8 -B "%~dp0launcher.py" stop
if errorlevel 1 pause
endlocal

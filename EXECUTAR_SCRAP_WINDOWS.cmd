@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%PS_EXE%" (
  echo [erro] powershell.exe nao encontrado em "%PS_EXE%"
  exit /b 1
)

"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%EXECUTAR_SCRAP_WINDOWS.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo [erro] fluxo finalizado com falha ^(exit_code=%EXIT_CODE%^)
)

exit /b %EXIT_CODE%

@echo off
setlocal EnableExtensions
title Stop Property Investment Consultant

rem Stops whatever is listening on the app's ports, and closes the launcher windows.
rem Set PORTS yourself to stop only those ports, for example:  set PORTS=8000 && stop.bat

set "KILLWINDOWS="
if defined PORTS goto have_ports
set "PORTS=8000 5173 8501"
set "KILLWINDOWS=1"
:have_ports

echo Stopping the Property Investment Consultant servers...
set "FOUND="
for %%P in (%PORTS%) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
    echo   port %%P: stopping process %%I
    taskkill /PID %%I /T /F >nul 2>nul
    set "FOUND=1"
  )
)

if defined KILLWINDOWS (
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | Where-Object { $_.CommandLine -like '*npm run dev*' -or $_.CommandLine -like '*backend\venv\Scripts\python.exe*app.py*' -or $_.CommandLine -like '*streamlit run app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul
)

if not defined FOUND echo   nothing was running on ports %PORTS%
echo Done.
endlocal
exit /b 0

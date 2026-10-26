@echo off
setlocal EnableExtensions
title Property Investment Consultant launcher

rem Usage:  start.bat [all] [dev] [nobrowser] [dryrun]
rem   all        also start the Streamlit app on http://localhost:8501
rem   dev        backend auto-reloads when .py files change (slower, and it can crash on a locked file)
rem   nobrowser  do not open the browser
rem   dryrun     show what would run and start nothing

set "ROOT=%~dp0"
set "BACKEND_PY=%ROOT%backend\venv\Scripts\python.exe"
set "STREAMLIT_PY=%ROOT%streamlit_app\.venv\Scripts\python.exe"
set "ALL="
set "DEV="
set "NOBROWSER="
set "DRY="
for %%A in (%*) do (
  if /i "%%A"=="all" set "ALL=1"
  if /i "%%A"=="dev" set "DEV=1"
  if /i "%%A"=="nobrowser" set "NOBROWSER=1"
  if /i "%%A"=="dryrun" set "DRY=1"
)

if not exist "%BACKEND_PY%" (
  echo [!] The backend environment was not found at:
  echo     %BACKEND_PY%
  echo     Create it once with these commands:
  echo       cd backend
  echo       python -m venv venv
  echo       venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
if not exist "%ROOT%frontend\node_modules" (
  echo [!] The frontend packages are missing. Run this once:
  echo       cd frontend
  echo       npm install
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo [!] Node.js was not found on PATH. Install it from nodejs.org and try again.
  pause
  exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not defined DEV set "DEBUG=False"

echo.
call :listening 8000
if not errorlevel 1 goto backend_running
echo [backend ] starting on port 8000
if defined DRY goto backend_done
start "Property backend" /D "%ROOT%backend" cmd /k ""%BACKEND_PY%" app.py"
goto backend_done
:backend_running
echo [backend ] already running on port 8000
:backend_done

call :listening 5173
if not errorlevel 1 goto frontend_running
echo [frontend] starting on port 5173
if defined DRY goto frontend_done
start "Property frontend" /D "%ROOT%frontend" cmd /k "npm run dev"
goto frontend_done
:frontend_running
echo [frontend] already running on port 5173
:frontend_done

if not defined ALL goto streamlit_done
if not exist "%STREAMLIT_PY%" (
  echo [streamlit] skipped: environment not found at %STREAMLIT_PY%
  goto streamlit_done
)
call :listening 8501
if not errorlevel 1 goto streamlit_running
echo [streamlit] starting on port 8501
if defined DRY goto streamlit_done
start "Property streamlit" /D "%ROOT%streamlit_app" cmd /k ""%STREAMLIT_PY%" -m streamlit run app.py --server.headless true --browser.gatherUsageStats false"
goto streamlit_done
:streamlit_running
echo [streamlit] already running on port 8501
:streamlit_done

if defined DRY (
  echo.
  echo Dry run only: nothing was started.
  goto finish
)

echo.
echo Waiting for the backend. The first start loads the documents and takes 1 to 2 minutes...
set /a tries=0
:wait
curl.exe -s -m 3 http://localhost:8000/health 2>nul | findstr /c:"healthy" >nul
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% geq 75 goto timed_out
ping -n 5 127.0.0.1 >nul
goto wait

:ready
echo.
echo Ready.
echo   Chat app:  http://localhost:5173
echo   API docs:  http://localhost:8000/docs
if defined ALL echo   Streamlit: http://localhost:8501
if not defined NOBROWSER start "" "http://localhost:5173"
goto finish

:timed_out
echo.
echo [!] The backend did not answer after about 5 minutes.
echo     Look at the "Property backend" window for the error message.
pause

:finish
echo.
echo To stop everything, run stop.bat
endlocal
exit /b 0

:listening
netstat -ano | findstr /r /c:":%1 .*LISTENING" >nul
exit /b

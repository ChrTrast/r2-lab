@echo off
rem Starts R2 Lab on Windows without installing it.
rem Needs Python from python.org ("Add python.exe to PATH" ticked).
rem Installs pygame-ce by itself: the maintained pygame fork with wheels for Python 3.10-3.15.
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py
if not defined PY (
    python --version >nul 2>nul
    if not errorlevel 1 set PY=python
)
if not defined PY goto nopython
%PY% -c "import pygame" >nul 2>nul
if not errorlevel 1 goto run
echo Installing pygame-ce...
%PY% -m pip install --user pygame-ce
if not errorlevel 1 goto run
echo.
echo Retrying from the official index (pypi.org)...
%PY% -m pip install --user --index-url https://pypi.org/simple pygame-ce
if not errorlevel 1 goto run
echo.
echo pygame-ce installation failed.
echo Check the internet connection and the Python version:
%PY% --version
pause
exit /b 1

:nopython
echo.
echo Python is not installed on this PC.
echo.
echo   Install Python from the page that opens now
echo   (tick "Add python.exe to PATH"), then run this file again.
echo.
start "" https://www.python.org/downloads/windows/
pause
exit /b 1

:run
set PYW=pythonw
where pyw >nul 2>nul && set PYW=pyw
start "" %PYW% main.py

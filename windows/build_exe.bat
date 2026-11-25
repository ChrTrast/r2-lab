@echo off
rem R2 Lab - builds dist\R2-Lab-Setup-<version>.exe, the installer for Windows 10/11.
rem The installed program needs no Python: PyInstaller puts Python and pygame-ce inside R2Lab.exe.
rem Same steps as Sebran's build_exe.bat. Run it on a 64-bit Windows PC that has Python.
rem Needs Inno Setup once:  winget install JRSoftware.InnoSetup
cd /d "%~dp0\.."
set PY=
where py >nul 2>nul && set PY=py
if not defined PY (
    python --version >nul 2>nul
    if not errorlevel 1 set PY=python
)
if not defined PY (
    echo Python is not installed on this PC. Install it from python.org
    echo and tick "Add python.exe to PATH", then run this file again.
    start "" https://www.python.org/downloads/windows/
    pause
    exit /b 1
)
set IDX=
%PY% -m pip install --user --upgrade pyinstaller
if errorlevel 1 set IDX=--index-url https://pypi.org/simple
if defined IDX %PY% -m pip install --user --upgrade %IDX% pyinstaller
if errorlevel 1 ( echo pip failed. & pause & exit /b 1 )
%PY% -c "import pygame" >nul 2>nul
if errorlevel 1 %PY% -m pip install --user %IDX% pygame-ce
if errorlevel 1 ( echo pygame-ce installation failed. & pause & exit /b 1 )
for /f "delims=" %%V in ('%PY% -c "import core; print(core.__version__)"') do set VER=%%V
echo Version %VER%

echo.
echo === 1/2  Building build\windows\R2Lab\R2Lab.exe ===
%PY% -m PyInstaller --noconfirm --clean --windowed --name R2Lab --exclude-module numpy ^
  --icon "%CD%\assets\r2-lab.ico" --paths "%CD%" ^
  --collect-submodules core --collect-submodules games ^
  --distpath "%CD%\build\windows" --workpath "%CD%\build\pyinstaller" --specpath "%CD%\build" ^
  main.py
if errorlevel 1 ( echo Build failed. & pause & exit /b 1 )
copy /y README.md build\windows\R2Lab\ >nul

echo.
echo === 2/2  Building the installer (Inno Setup) ===
set ISCC=
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe") do if exist %%P set ISCC=%%P
if not defined ISCC (
    where iscc >nul 2>nul
    if not errorlevel 1 set ISCC=iscc
)
if not defined ISCC goto noinno
echo Using %ISCC%
%ISCC% /DAppVer=%VER% windows\r2_lab.iss
if errorlevel 1 ( echo Installer build failed. & pause & exit /b 1 )
if not exist dist\R2-Lab-Setup-%VER%.exe goto missing
echo.
echo Done. Installer for the other PCs:
echo   %CD%\dist\R2-Lab-Setup-%VER%.exe
if not "%1"=="--no-pause" pause
exit /b 0

:missing
echo.
echo Inno Setup reported success, but dist\R2-Lab-Setup-%VER%.exe is missing.
echo Your antivirus may have removed it: Windows Security ^> Protection history.
pause
exit /b 1

:noinno
echo Inno Setup was not found, so only the program folder was built:
echo   %CD%\build\windows\R2Lab\R2Lab.exe  (copy the whole folder)
echo To also get the installer, run once:  winget install JRSoftware.InnoSetup
echo and then run this file again.
pause
exit /b 1

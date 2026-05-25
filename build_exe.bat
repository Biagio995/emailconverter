@echo off
cd /d "%~dp0"
echo Build app + installer (richiede Inno Setup 6 per il pacchetto finale)
python build_exe.py
if errorlevel 1 pause & exit /b 1
pause

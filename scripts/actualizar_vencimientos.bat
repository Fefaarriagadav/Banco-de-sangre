@echo off
setlocal

cd /d "%~dp0.."
if errorlevel 1 exit /b 1

python -m servicios.vencimientos
exit /b %errorlevel%
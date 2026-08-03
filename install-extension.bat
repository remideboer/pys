@echo off
setlocal
cd /d "%~dp0"
python -m transpiler install extension %*
if errorlevel 1 exit /b %ERRORLEVEL%

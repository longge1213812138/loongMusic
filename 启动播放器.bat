@echo off
title Music Player Server
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  python server.py
  goto :end
)

if exist "C:\Users\91533\.workbuddy\binaries\python\versions\3.13.12\python.exe" (
  "C:\Users\91533\.workbuddy\binaries\python\versions\3.13.12\python.exe" server.py
  goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 server.py
  goto :end
)

echo Python 3 not found. Please install Python first.
pause

:end

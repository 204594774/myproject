@echo off
setlocal
set PORT=5001
echo Finding process running on port %PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Killing process PID: %%a
    taskkill /F /PID %%a
)
echo App on port %PORT% has been stopped.
pause

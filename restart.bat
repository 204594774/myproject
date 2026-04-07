@echo off
chcp 65001 >nul
setlocal
set PORT=5001
echo 正在关闭后端...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Killing process PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
echo 等待3秒...
timeout /t 3 /nobreak >nul
echo 正在启动后端...
start "" cmd /k "cd /d D:\桌面\new12 && python -u run.py"
echo 后端已启动！

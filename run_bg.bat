@echo off
cd /d %~dp0
echo Starting Flask App in Background...
start /B python -u run.py > app_bg.log 2>&1
echo App started in background. Check app_bg.log for logs.
pause

@echo off
cd /d %~dp0
echo Starting Flask App Unbuffered... > app.log
python -u run.py >> app.log 2>&1

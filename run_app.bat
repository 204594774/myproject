@echo off
echo Starting Flask App Unbuffered... > app.log
python -u app.py >> app.log 2>&1

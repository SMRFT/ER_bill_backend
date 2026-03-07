@echo off
echo Starting ER Billing Services...

echo Starting Django Server...
start "Django Server" cmd /k "python manage.py runserver 0.0.0.0:8000"

echo Starting Automation Worker...
start "Automation Worker" cmd /k "python manage.py automate_results"

echo Services started. You can close this window.
pause

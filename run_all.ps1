Write-Host "------------------------------------" -ForegroundColor Cyan
Write-Host "   Starting ER Billing Services     " -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Cyan

# Start Django Server in a new window using venv
Write-Host "Starting Django Server on port 8000..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000"

# Start Automation Worker in a new window using venv
Write-Host "Starting Automation Worker..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\venv\Scripts\python.exe manage.py automate_results"

Write-Host "Done! Services are running in separate windows." -ForegroundColor Green
Write-Host "You can close this main window."
pause

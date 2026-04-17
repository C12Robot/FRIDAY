@echo off
start "FRIDAY Backend" cmd /k "cd C:\Users\meena\Documents\ARIA && venv\Scripts\activate.bat && uvicorn api:app --reload --port 8000"

timeout /t 8

start "FRIDAY App" cmd /k "cd C:\Users\meena\Documents\friday-dashboard && .\node_modules\.bin\electron.cmd electron.js"
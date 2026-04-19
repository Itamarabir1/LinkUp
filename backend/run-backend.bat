@echo off
REM For development only. In production use Docker.
chcp 65001 >nul
echo ========================================
echo   LinkUp - הרצת בקאנד (פורט 8000)
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] בודק אם משהו רץ על פורט 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo     מוצא תהליך על 8000 - PID: %%a - עוצר...
    taskkill /F /PID %%a 2>nul
    timeout /t 2 /nobreak >nul
)
echo [2/2] מפעיל את הבקאנד...
echo.
echo אם אתה רואה למטה "[LinkUp] Backend נטען" - הבקאנד הנכון רץ.
echo כשתנסה הרשמה באתר, כאן אמורות להופיע שורות [LinkUp] >>> בקשה
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause

@echo off
echo Starting Project Bonk Discord Bot...
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure your bot token.
    echo.
    pause
    exit /b 1
)

REM Start the bot
echo Starting bot...
python main.py

pause

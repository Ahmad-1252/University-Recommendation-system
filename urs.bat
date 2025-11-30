@echo off
REM University Recommendation System CLI Launcher
REM This script activates the virtual environment and runs the CLI

echo Activating virtual environment...
call "%~dp0.venv\Scripts\activate.bat"

echo Starting University Recommendation System CLI...
python -m src.cli.commands %*

echo.
echo CLI session ended.
pause
@echo off
python "%~dp0gui.py"
if errorlevel 1 (
    echo.
    echo Python not found or error occurred.
    echo Make sure Python is installed and on your PATH.
    pause
)

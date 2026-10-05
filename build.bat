@echo off
REM Builds dist\TypingHelper.exe (single file, no console window)
python -m typinghelper.icons icon.ico || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon icon.ico --name TypingHelper main.py

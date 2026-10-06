# Typing Helper

Types text into the focused window like a person: random per-key delay, pauses between lines, and typos on nearby keys that it then fixes with Backspace.

## Run
    pip install -r requirements.txt
    python main.py

Or build a single exe with `build.bat`, which creates `dist\TypingHelper.exe`.

## Use
1. Paste the text and click **Start**.
2. During the countdown (3 s by default), click into the target window.
3. Press **F8** to pause or resume, and **F9** to stop. You can also stop from the tray menu.

Tray icon: green = idle, red = typing. Closing the window hides it to the tray; use the tray menu to Quit.

Settings are saved in the registry under `HKEY_CURRENT_USER\Software\TypingHelper`.

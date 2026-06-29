# CapsLockShow

CapsLockShow is a small Windows 11 style flyout app for keyboard lock keys.
It only displays `Caps Lock`, `Num Lock`, and `Scroll Lock` state changes.

## Features

- Win11/Fluent-style tray app and settings window.
- Lock key flyout for Caps Lock, Num Lock, and Scroll Lock.
- Shows the current Caps Lock state once after startup so the user knows the app is running.
- Uses `Icon.png` for the executable, application window, taskbar, and system tray icon.
- Global low-level keyboard hook implemented with Win32 `WH_KEYBOARD_LL`.
- Reads the final key state after `WM_KEYUP`.
- Hides the flyout only when `SHQueryUserNotificationState` reports DirectX exclusive fullscreen.
- Shows on the monitor that currently contains the mouse cursor.
- Settings are stored in `%APPDATA%\CapsLockShow\config.json`.
- Optional current-user startup entry in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\app.py
```

If `python` is not in `PATH`, pass an explicit interpreter path.

## Build

```powershell
.\build.ps1
```

The single-file executable is written to `dist\CapsLockShow.exe`.

## License

This project is licensed under GPLv3. It uses `PySide6-Fluent-Widgets`, which is
GPLv3 for non-commercial open-source use and requires a commercial license for
commercial use.

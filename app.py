from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import main as core


APP_USER_MODEL_ID = "CapsLockShow.CapsLockShow"
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 680


def resource_path(name: str) -> Path:
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_dir / name


def application_icon() -> QIcon:
    icon_path = resource_path("Icon.png")
    icon = QIcon(str(icon_path))
    if icon.isNull():
        raise RuntimeError(f"无法加载应用图标：{icon_path}")
    return icon


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{Path(__file__).resolve()}"'


# main.py 的开机启动逻辑会调用模块级 startup_command。
core.startup_command = startup_command


class SettingsWindow(core.SettingsWindow):
    def __init__(self, settings: core.AppSettings, icon: QIcon):
        super().__init__(settings, icon)
        self.setMinimumSize(820, 580)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        QTimer.singleShot(0, self._refresh_initial_layout)

    def _refresh_initial_layout(self) -> None:
        """Force one resize after all pages and cards have been created."""
        width = self.width()
        height = self.height()
        self.resize(width + 1, height)
        self.resize(width, height)

        for page in (self.general_page, self.appearance_page, self.about_page):
            page.expand_layout.invalidate()
            page.expand_layout.activate()
            page.scroll_widget.updateGeometry()
            page.updateGeometry()
            page.viewport().update()


class CapsLockShowApp(core.CapsLockShowApp):
    def __init__(self, icon: QIcon):
        QObject.__init__(self)
        self.settings = core.load_settings()
        core.apply_app_theme(self.settings)
        self.bridge = core.KeyboardBridge()
        self.bridge.key_released.connect(self.on_key_released)
        self.flyout = core.LockFlyout(self.settings)
        self.icon = icon
        self.settings_window = SettingsWindow(self.settings, self.icon)
        self.settings_window.changed.connect(self.refresh_tray_state)
        self.settings_window.test_requested.connect(self.test_flyout)
        self.tray = self._create_tray()
        self.hook = core.KeyboardHook(self.bridge.key_released.emit)
        self.hook.start()
        QApplication.instance().aboutToQuit.connect(self.shutdown)
        QTimer.singleShot(650, self._show_startup_feedback)

    def _show_startup_feedback(self) -> None:
        if self.settings.hide_directx_fullscreen and core.is_directx_fullscreen():
            return
        self.flyout.show_state(
            "Caps Lock",
            core.is_key_toggled(core.VK_CAPITAL),
        )


def set_windows_app_id() -> None:
    shell32 = ctypes.windll.shell32
    shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
    shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
    shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("CapsLockShow only supports Windows.")

    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(core.APP_NAME)

    icon = application_icon()
    app.setWindowIcon(icon)

    controller = CapsLockShowApp(icon)
    app.controller = controller
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

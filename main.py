from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
import winreg
from ctypes import wintypes
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QTimer, Qt, Signal, QObject
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

try:
    from qfluentwidgets import FluentIcon as FIF
    from qfluentwidgets import setTheme, setThemeColor, Theme
except Exception:
    FIF = None
    Theme = None
    setTheme = None
    setThemeColor = None


APP_NAME = "CapsLockShow"
STARTUP_VALUE_NAME = APP_NAME

WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
VK_CAPITAL = 0x14
VK_NUMLOCK = 0x90
VK_SCROLL = 0x91
QUNS_RUNNING_D3D_FULL_SCREEN = 3
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

KEYS = {
    VK_CAPITAL: ("caps_enabled", "Caps Lock"),
    VK_NUMLOCK: ("num_enabled", "Num Lock"),
    VK_SCROLL: ("scroll_enabled", "Scroll Lock"),
}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    LowLevelKeyboardProc,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = wintypes.LPARAM
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
shell32.SHQueryUserNotificationState.argtypes = [ctypes.POINTER(ctypes.c_int)]
shell32.SHQueryUserNotificationState.restype = ctypes.c_long

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080


@dataclass
class AppSettings:
    caps_enabled: bool = True
    num_enabled: bool = True
    scroll_enabled: bool = True
    duration_ms: int = 2000
    position: str = "bottom_center"
    theme: str = "system"
    startup: bool = False
    hide_directx_fullscreen: bool = True


def app_data_dir(create: bool = False) -> Path:
    base = os.environ.get("APPDATA")
    if base:
        root = Path(base) / APP_NAME
    else:
        root = Path.home() / f".{APP_NAME}"
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


CONFIG_PATH = app_data_dir() / "config.json"


def load_settings() -> AppSettings:
    if not CONFIG_PATH.exists():
        return AppSettings(startup=is_startup_enabled())

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings(startup=is_startup_enabled())

    allowed = {field.name for field in fields(AppSettings)}
    filtered = {key: value for key, value in data.items() if key in allowed}
    settings = AppSettings(**filtered)
    settings.duration_ms = max(500, min(5000, int(settings.duration_ms)))
    settings.startup = is_startup_enabled()
    return settings


def save_settings(settings: AppSettings) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{Path(__file__).resolve()}"'


def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            value, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
            return value == startup_command()
    except OSError:
        return False


def set_startup_enabled(enabled: bool) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            except FileNotFoundError:
                pass


def is_key_toggled(vk_code: int) -> bool:
    return bool(user32.GetKeyState(vk_code) & 0x0001)


def is_directx_fullscreen() -> bool:
    state = ctypes.c_int()
    result = shell32.SHQueryUserNotificationState(ctypes.byref(state))
    return result == 0 and state.value == QUNS_RUNNING_D3D_FULL_SCREEN


def system_theme_is_dark() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
    except OSError:
        return False


def accent_color() -> QColor:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\DWM",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "ColorizationColor")
            raw = int(value)
            return QColor((raw >> 16) & 0xFF, (raw >> 8) & 0xFF, raw & 0xFF)
    except OSError:
        return QColor("#0078D4")


def effective_theme(settings: AppSettings) -> str:
    if settings.theme == "dark":
        return "dark"
    if settings.theme == "light":
        return "light"
    return "dark" if system_theme_is_dark() else "light"


def apply_app_theme(settings: AppSettings) -> None:
    if setTheme and Theme:
        if settings.theme == "dark":
            setTheme(Theme.DARK)
        elif settings.theme == "light":
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.AUTO)
        if setThemeColor:
            setThemeColor(accent_color())

    app = QApplication.instance()
    if not app:
        return
    dark = effective_theme(settings) == "dark"
    bg = "#202020" if dark else "#F7F7F7"
    panel = "#2B2B2B" if dark else "#FFFFFF"
    text = "#F3F3F3" if dark else "#1F1F1F"
    sub = "#C8C8C8" if dark else "#5F5F5F"
    border = "#3A3A3A" if dark else "#E6E6E6"
    app.setStyleSheet(
        f"""
        QWidget {{
            font-family: "Segoe UI Variable", "Microsoft YaHei UI", "Segoe UI", sans-serif;
            color: {text};
            background: {bg};
            font-size: 13px;
        }}
        QFrame#Card {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        QPushButton {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 7px 12px;
        }}
        QPushButton:hover {{
            background: {"#343434" if dark else "#F2F2F2"};
        }}
        QPushButton#PrimaryButton {{
            background: {accent_color().name()};
            color: white;
            border: 1px solid {accent_color().name()};
        }}
        QLabel#Title {{
            font-size: 22px;
            font-weight: 600;
        }}
        QLabel#Subtitle {{
            color: {sub};
        }}
        QListWidget, QComboBox, QMenu {{
            background: {panel};
            border: 1px solid {border};
        }}
        QCheckBox::indicator {{
            width: 34px;
            height: 18px;
        }}
        QSlider::groove:horizontal {{
            height: 4px;
            border-radius: 2px;
            background: {"#4A4A4A" if dark else "#D8D8D8"};
        }}
        QSlider::handle:horizontal {{
            background: {accent_color().name()};
            width: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}
        """
    )


class KeyboardBridge(QObject):
    key_released = Signal(int)


class KeyboardHook(threading.Thread):
    def __init__(self, callback: Callable[[int], None]):
        super().__init__(daemon=True)
        self.callback = callback
        self.hook_id: int | None = None
        self.thread_id = 0
        self._hook_proc = LowLevelKeyboardProc(self._handle_event)

    def run(self) -> None:
        self.thread_id = kernel32.GetCurrentThreadId()
        module = kernel32.GetModuleHandleW(None)
        self.hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, module, 0)
        if not self.hook_id:
            return

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None

    def stop(self) -> None:
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)

    def _handle_event(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code == HC_ACTION and w_param in (WM_KEYUP, WM_SYSKEYUP):
            event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if event.vkCode in KEYS:
                self.callback(int(event.vkCode))
        return user32.CallNextHookEx(self.hook_id, n_code, w_param, l_param)


class LockFlyout(QWidget):
    def __init__(self, settings: AppSettings):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.settings = settings
        self.key_name = "Caps Lock"
        self.is_on = True
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_animated)
        self.position_animation = QPropertyAnimation(self, b"pos", self)
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(240, 72)
        self.setWindowOpacity(0)

    def show_state(self, key_name: str, is_on: bool) -> None:
        self.key_name = key_name
        self.is_on = is_on
        self.hide_timer.stop()
        self.update()

        target = self._target_position()
        start = QPoint(target.x(), target.y() + (20 if target.y() > 80 else -20))

        if not self.isVisible():
            self.move(start)
            self.setWindowOpacity(0)
            self.show()
            self._apply_no_activate_style()

        self.raise_()
        self._animate_to(target, 1.0, 180)
        self.hide_timer.start(self.settings.duration_ms)

    def hide_animated(self) -> None:
        if not self.isVisible():
            return
        current = self.pos()
        target = QPoint(current.x(), current.y() + (20 if current.y() > 80 else -20))
        self.position_animation.stop()
        self.opacity_animation.stop()
        self.position_animation.setStartValue(current)
        self.position_animation.setEndValue(target)
        self.position_animation.setDuration(160)
        self.position_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.opacity_animation.setStartValue(self.windowOpacity())
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.setDuration(160)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.opacity_animation.finished.connect(self.hide)
        self.position_animation.start()
        self.opacity_animation.start()

    def _animate_to(self, target: QPoint, opacity: float, duration: int) -> None:
        try:
            self.opacity_animation.finished.disconnect(self.hide)
        except RuntimeError:
            pass
        self.position_animation.stop()
        self.opacity_animation.stop()
        self.position_animation.setStartValue(self.pos())
        self.position_animation.setEndValue(target)
        self.position_animation.setDuration(duration)
        self.position_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.opacity_animation.setStartValue(self.windowOpacity())
        self.opacity_animation.setEndValue(opacity)
        self.opacity_animation.setDuration(duration)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.position_animation.start()
        self.opacity_animation.start()

    def _target_position(self) -> QPoint:
        cursor_screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = cursor_screen.availableGeometry()
        margin = 24
        if self.settings.position == "bottom_left":
            x = area.left() + margin
            y = area.bottom() - self.height() - margin
        elif self.settings.position == "bottom_right":
            x = area.right() - self.width() - margin
            y = area.bottom() - self.height() - margin
        elif self.settings.position == "top_center":
            x = area.center().x() - self.width() // 2
            y = area.top() + margin
        else:
            x = area.center().x() - self.width() // 2
            y = area.bottom() - self.height() - margin
        return QPoint(x, y)

    def _apply_no_activate_style(self) -> None:
        hwnd = int(self.winId())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dark = effective_theme(self.settings) == "dark"
        bg = QColor(32, 32, 32, 232) if dark else QColor(252, 252, 252, 235)
        border = QColor(255, 255, 255, 30) if dark else QColor(0, 0, 0, 24)
        text = QColor("#F3F3F3") if dark else QColor("#1F1F1F")
        muted = QColor(255, 255, 255, 140) if dark else QColor(0, 0, 0, 125)
        accent = accent_color()
        accent.setAlpha(255 if self.is_on else 110)

        rect = QRect(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.fillPath(path, bg)
        painter.setPen(border)
        painter.drawPath(path)

        icon_rect = QRect(20, 19, 34, 34)
        self._draw_lock_icon(painter, icon_rect, text if self.is_on else muted)

        painter.setPen(text)
        painter.setFont(QFont("Segoe UI Variable", 12, QFont.Weight.DemiBold))
        status = "已开启" if self.is_on else "已关闭"
        painter.drawText(QRect(68, 12, 154, 30), Qt.AlignmentFlag.AlignVCenter, self.key_name)
        painter.setPen(muted)
        painter.setFont(QFont("Microsoft YaHei UI", 10))
        painter.drawText(QRect(68, 38, 154, 22), Qt.AlignmentFlag.AlignVCenter, status)

        indicator_width = 96 if self.is_on else 52
        indicator = QRect((self.width() - indicator_width) // 2, self.height() - 7, indicator_width, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(indicator, 2, 2)

    def _draw_lock_icon(self, painter: QPainter, rect: QRect, color: QColor) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        body = QRect(rect.left() + 5, rect.top() + 14, 24, 17)
        painter.drawRoundedRect(body, 5, 5)

        pen = painter.pen()
        pen.setColor(color)
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        if self.is_on:
            painter.drawArc(rect.left() + 8, rect.top() + 3, 18, 22, 0, 180 * 16)
        else:
            painter.drawArc(rect.left() + 11, rect.top() + 2, 18, 22, 25 * 16, 155 * 16)
        painter.restore()


class SettingRow(QFrame):
    def __init__(self, title: str, description: str, control: QWidget):
        super().__init__()
        self.setObjectName("Card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        texts = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.DemiBold))
        desc_label = QLabel(description)
        desc_label.setObjectName("Subtitle")
        desc_label.setWordWrap(True)
        texts.addWidget(title_label)
        texts.addWidget(desc_label)
        layout.addLayout(texts, 1)
        layout.addWidget(control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


class SettingsWindow(QMainWindow):
    changed = Signal()
    test_requested = Signal(str)

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle(f"{APP_NAME} 设置")
        self.resize(760, 520)
        self.setMinimumSize(680, 460)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = QFrame()
        sidebar.setFixedWidth(190)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 18, 12, 18)
        sidebar_layout.setSpacing(8)
        app_title = QLabel(APP_NAME)
        app_title.setObjectName("Title")
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addSpacing(8)

        self.general_button = self._nav_button("常规")
        self.appearance_button = self._nav_button("外观")
        self.about_button = self._nav_button("关于")
        sidebar_layout.addWidget(self.general_button)
        sidebar_layout.addWidget(self.appearance_button)
        sidebar_layout.addWidget(self.about_button)
        sidebar_layout.addStretch(1)
        root_layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, 1)
        self.stack.addWidget(self._general_page())
        self.stack.addWidget(self._appearance_page())
        self.stack.addWidget(self._about_page())
        self.general_button.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.appearance_button.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.about_button.clicked.connect(lambda: self.stack.setCurrentIndex(2))

    def _nav_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setFixedHeight(38)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("Title")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Subtitle")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(8)
        return page, layout

    def _general_page(self) -> QWidget:
        page, layout = self._page("常规", "控制锁定键监听、显示时长、开机启动和测试浮窗。")

        self.caps_check = self._check(self.settings.caps_enabled, lambda v: self._set("caps_enabled", v))
        self.num_check = self._check(self.settings.num_enabled, lambda v: self._set("num_enabled", v))
        self.scroll_check = self._check(self.settings.scroll_enabled, lambda v: self._set("scroll_enabled", v))
        self.startup_check = self._check(self.settings.startup, self._set_startup)
        self.fullscreen_check = self._check(
            self.settings.hide_directx_fullscreen,
            lambda v: self._set("hide_directx_fullscreen", v),
        )

        layout.addWidget(SettingRow("Caps Lock", "按下大小写锁定键后显示状态浮窗。", self.caps_check))
        layout.addWidget(SettingRow("Num Lock", "按下数字锁定键后显示状态浮窗。", self.num_check))
        layout.addWidget(SettingRow("Scroll Lock", "按下滚动锁定键后显示状态浮窗。", self.scroll_check))
        layout.addWidget(SettingRow("开机自启动", "登录 Windows 后自动启动 CapsLockShow。", self.startup_check))
        layout.addWidget(SettingRow("DirectX 全屏时隐藏", "与 FluentFlyout 一致，仅 DirectX 独占全屏时不显示浮窗。", self.fullscreen_check))

        duration_box = QWidget()
        duration_layout = QHBoxLayout(duration_box)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        self.duration_label = QLabel(f"{self.settings.duration_ms / 1000:.1f} 秒")
        duration_slider = QSlider(Qt.Orientation.Horizontal)
        duration_slider.setRange(500, 5000)
        duration_slider.setSingleStep(100)
        duration_slider.setPageStep(500)
        duration_slider.setValue(self.settings.duration_ms)
        duration_slider.valueChanged.connect(self._set_duration)
        duration_layout.addWidget(duration_slider)
        duration_layout.addWidget(self.duration_label)
        layout.addWidget(SettingRow("显示时长", "浮窗自动消失前停留的时间。", duration_box))

        tests = QWidget()
        test_layout = QHBoxLayout(tests)
        test_layout.setContentsMargins(0, 0, 0, 0)
        for key in ("Caps Lock", "Num Lock", "Scroll Lock"):
            button = QPushButton(key)
            button.clicked.connect(lambda checked=False, k=key: self.test_requested.emit(k))
            test_layout.addWidget(button)
        layout.addWidget(SettingRow("测试浮窗", "无需按键即可预览三种状态提示。", tests))
        layout.addStretch(1)
        return page

    def _appearance_page(self) -> QWidget:
        page, layout = self._page("外观", "调整浮窗位置和主题。")

        theme_combo = QComboBox()
        theme_combo.addItem("跟随系统", "system")
        theme_combo.addItem("浅色", "light")
        theme_combo.addItem("深色", "dark")
        theme_combo.setCurrentIndex(max(0, theme_combo.findData(self.settings.theme)))
        theme_combo.currentIndexChanged.connect(lambda: self._set("theme", theme_combo.currentData()))

        position_combo = QComboBox()
        position_combo.addItem("底部居中", "bottom_center")
        position_combo.addItem("左下角", "bottom_left")
        position_combo.addItem("右下角", "bottom_right")
        position_combo.addItem("顶部居中", "top_center")
        position_combo.setCurrentIndex(max(0, position_combo.findData(self.settings.position)))
        position_combo.currentIndexChanged.connect(lambda: self._set("position", position_combo.currentData()))

        layout.addWidget(SettingRow("主题", "默认跟随 Windows 深浅色设置。", theme_combo))
        layout.addWidget(SettingRow("浮窗位置", "默认在鼠标所在屏幕的底部居中显示。", position_combo))
        layout.addStretch(1)
        return page

    def _about_page(self) -> QWidget:
        page, layout = self._page("关于", "只保留键盘锁定键浮窗功能。")
        text = QLabel(
            "CapsLockShow 是一个面向 Windows 11 的锁定键浮窗工具。\n"
            "项目按 GPLv3 开源，UI 使用 PySide6-Fluent-Widgets，交互参考 FluentFlyout。"
        )
        text.setWordWrap(True)
        text.setObjectName("Subtitle")
        layout.addWidget(text)
        layout.addStretch(1)
        return page

    def _check(self, checked: bool, callback: Callable[[bool], None]) -> QCheckBox:
        check = QCheckBox()
        check.setChecked(checked)
        check.toggled.connect(callback)
        return check

    def _set(self, name: str, value) -> None:
        setattr(self.settings, name, value)
        save_settings(self.settings)
        if name == "theme":
            apply_app_theme(self.settings)
        self.changed.emit()

    def _set_startup(self, enabled: bool) -> None:
        try:
            set_startup_enabled(enabled)
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, f"无法更新开机启动设置：{exc}")
            self.startup_check.blockSignals(True)
            self.startup_check.setChecked(self.settings.startup)
            self.startup_check.blockSignals(False)
            return
        self._set("startup", enabled)

    def _set_duration(self, value: int) -> None:
        value = int(round(value / 100) * 100)
        self.duration_label.setText(f"{value / 1000:.1f} 秒")
        self._set("duration_ms", value)


class CapsLockShowApp(QObject):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        apply_app_theme(self.settings)
        self.bridge = KeyboardBridge()
        self.bridge.key_released.connect(self.on_key_released)
        self.flyout = LockFlyout(self.settings)
        self.settings_window = SettingsWindow(self.settings)
        self.settings_window.changed.connect(self.refresh_tray_state)
        self.settings_window.test_requested.connect(self.test_flyout)
        self.tray = self._create_tray()
        self.hook = KeyboardHook(self.bridge.key_released.emit)
        self.hook.start()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def _create_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self._app_icon(), self)
        tray.setToolTip(APP_NAME)
        menu = QMenu()
        open_action = QAction("打开设置", menu)
        open_action.triggered.connect(self.open_settings)
        menu.addAction(open_action)

        test_menu = menu.addMenu("测试浮窗")
        for key in ("Caps Lock", "Num Lock", "Scroll Lock"):
            action = QAction(key, test_menu)
            action.triggered.connect(lambda checked=False, k=key: self.test_flyout(k))
            test_menu.addAction(action)

        menu.addSeparator()
        self.startup_action = QAction("开机自启动", menu)
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.settings.startup)
        self.startup_action.triggered.connect(self.toggle_startup_from_tray)
        menu.addAction(self.startup_action)

        menu.addSeparator()
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.activated.connect(self.on_tray_activated)
        tray.show()
        return tray

    def _app_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(accent_color())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRect(8, 8, 48, 48), 12, 12)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI Variable", 18, QFont.Weight.Bold))
        painter.drawText(QRect(8, 8, 48, 48), Qt.AlignmentFlag.AlignCenter, "A")
        painter.end()
        return QIcon(pixmap)

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()

    def open_settings(self) -> None:
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def toggle_startup_from_tray(self, checked: bool) -> None:
        self.settings_window._set_startup(checked)
        self.refresh_tray_state()

    def refresh_tray_state(self) -> None:
        self.startup_action.setChecked(self.settings.startup)
        self.settings_window.startup_check.blockSignals(True)
        self.settings_window.startup_check.setChecked(self.settings.startup)
        self.settings_window.startup_check.blockSignals(False)

    def test_flyout(self, key_name: str) -> None:
        vk_code = next((code for code, (_, name) in KEYS.items() if name == key_name), None)
        is_on = is_key_toggled(vk_code) if vk_code is not None else True
        self.flyout.show_state(key_name, is_on)

    def on_key_released(self, vk_code: int) -> None:
        QTimer.singleShot(20, lambda: self._handle_key(vk_code))

    def _handle_key(self, vk_code: int) -> None:
        enabled_attr, key_name = KEYS[vk_code]
        if not getattr(self.settings, enabled_attr):
            return
        if self.settings.hide_directx_fullscreen and is_directx_fullscreen():
            return
        self.flyout.show_state(key_name, is_key_toggled(vk_code))

    def shutdown(self) -> None:
        self.hook.stop()
        self.tray.hide()


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("CapsLockShow only supports Windows.")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    controller = CapsLockShowApp()
    app.controller = controller
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

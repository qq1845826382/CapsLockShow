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
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QWidget,
)

from qfluentwidgets import (
    ConfigItem,
    ExpandLayout,
    FluentIcon as FIF,
    MSFluentWindow,
    NavigationItemPosition,
    OptionsConfigItem,
    OptionsSettingCard,
    OptionsValidator,
    PrimaryPushSettingCard,
    PushSettingCard,
    RangeConfigItem,
    RangeSettingCard,
    RangeValidator,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    Theme,
    TitleLabel,
    setTheme,
    setThemeColor,
)


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
    if settings.theme == "dark":
        setTheme(Theme.DARK)
    elif settings.theme == "light":
        setTheme(Theme.LIGHT)
    else:
        setTheme(Theme.AUTO)
    setThemeColor(accent_color())


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
        self._draw_key_icon(
            painter,
            icon_rect,
            self.key_name,
            self.is_on,
            accent,
            muted,
        )

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

    def _draw_key_icon(
        self,
        painter: QPainter,
        rect: QRect,
        key_name: str,
        is_on: bool,
        accent: QColor,
        muted: QColor,
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        symbols = {
            "Caps Lock": "A",
            "Num Lock": "1",
            "Scroll Lock": "↕",
        }
        symbol = symbols.get(key_name, "?")
        key_rect = rect.adjusted(1, 1, -1, -1)

        foreground = QColor(accent if is_on else muted)
        fill = QColor(foreground)
        fill.setAlpha(28 if is_on else 14)
        outline = QColor(foreground)
        outline.setAlpha(210 if is_on else 100)

        painter.setBrush(fill)
        painter.setPen(QPen(outline, 1.4))
        painter.drawRoundedRect(key_rect, 7, 7)

        painter.setPen(foreground)
        painter.setFont(
            QFont(
                "Segoe UI Variable",
                14 if key_name == "Scroll Lock" else 15,
                QFont.Weight.DemiBold,
            )
        )
        painter.drawText(key_rect, Qt.AlignmentFlag.AlignCenter, symbol)
        painter.restore()


class SettingsConfigItems:
    def __init__(self, settings: AppSettings):
        self.caps_enabled = ConfigItem("LockKeys", "CapsEnabled", settings.caps_enabled)
        self.num_enabled = ConfigItem("LockKeys", "NumEnabled", settings.num_enabled)
        self.scroll_enabled = ConfigItem("LockKeys", "ScrollEnabled", settings.scroll_enabled)
        self.startup = ConfigItem("System", "Startup", settings.startup)
        self.hide_directx_fullscreen = ConfigItem(
            "System",
            "HideDirectXFullscreen",
            settings.hide_directx_fullscreen,
        )
        self.duration = RangeConfigItem(
            "Flyout",
            "DurationTenths",
            max(5, min(50, settings.duration_ms // 100)),
            RangeValidator(5, 50),
        )
        self.theme = OptionsConfigItem(
            "Appearance",
            "Theme",
            settings.theme,
            OptionsValidator(["system", "light", "dark"]),
        )
        self.position = OptionsConfigItem(
            "Appearance",
            "Position",
            settings.position,
            OptionsValidator(["bottom_center", "bottom_left", "bottom_right", "top_center"]),
        )


class SettingsPage(ScrollArea):
    def __init__(self, title: str, route_key: str, parent=None):
        super().__init__(parent=parent)

        self.setObjectName(route_key)
        self.scroll_widget = QWidget()
        self.expand_layout = ExpandLayout(self.scroll_widget)
        self.title_label = TitleLabel(title, self)

        self.setWidget(self.scroll_widget)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setViewportMargins(0, 86, 0, 18)
        self.expand_layout.setSpacing(28)
        self.expand_layout.setContentsMargins(48, 0, 48, 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.title_label.move(48, 38)

    def add_group(self, group: SettingCardGroup, *cards: QWidget) -> None:
        for card in cards:
            group.addSettingCard(card)
        self.expand_layout.addWidget(group)


class GeneralSettingsPage(SettingsPage):
    changed = Signal()
    test_requested = Signal(str)

    def __init__(self, settings: AppSettings, items: SettingsConfigItems, parent=None):
        super().__init__("常规", "generalInterface", parent)
        self.settings = settings
        self.items = items

        lock_group = SettingCardGroup("锁定键", self.scroll_widget)
        self.caps_card = SwitchSettingCard(
            FIF.FONT,
            "Caps Lock",
            "按下大小写锁定键后显示状态浮窗",
            configItem=items.caps_enabled,
            parent=lock_group,
        )
        self.num_card = SwitchSettingCard(
            FIF.CHECKBOX,
            "Num Lock",
            "按下数字锁定键后显示状态浮窗",
            configItem=items.num_enabled,
            parent=lock_group,
        )
        self.scroll_card = SwitchSettingCard(
            FIF.SCROLL,
            "Scroll Lock",
            "按下滚动锁定键后显示状态浮窗",
            configItem=items.scroll_enabled,
            parent=lock_group,
        )
        self.add_group(lock_group, self.caps_card, self.num_card, self.scroll_card)

        behavior_group = SettingCardGroup("行为", self.scroll_widget)
        self.duration_card = RangeSettingCard(
            items.duration,
            FIF.STOP_WATCH,
            "显示时长",
            "浮窗自动消失前停留的时间",
            parent=behavior_group,
        )
        self.duration_card.slider.setSingleStep(1)
        self.duration_card.slider.setPageStep(5)
        self._format_duration_label(items.duration.value)

        self.fullscreen_card = SwitchSettingCard(
            FIF.GAME,
            "DirectX 全屏时隐藏",
            "与 FluentFlyout 一致，仅 DirectX 独占全屏时不显示浮窗",
            configItem=items.hide_directx_fullscreen,
            parent=behavior_group,
        )
        self.startup_card = SwitchSettingCard(
            FIF.POWER_BUTTON,
            "开机自启动",
            "登录 Windows 后自动启动 CapsLockShow",
            configItem=items.startup,
            parent=behavior_group,
        )
        self.add_group(behavior_group, self.duration_card, self.fullscreen_card, self.startup_card)

        test_group = SettingCardGroup("预览", self.scroll_widget)
        self.test_caps_card = PushSettingCard(
            "预览",
            FIF.VIEW,
            "Caps Lock 浮窗",
            "使用当前 Caps Lock 状态显示一次浮窗",
            parent=test_group,
        )
        self.test_num_card = PushSettingCard(
            "预览",
            FIF.VIEW,
            "Num Lock 浮窗",
            "使用当前 Num Lock 状态显示一次浮窗",
            parent=test_group,
        )
        self.test_scroll_card = PushSettingCard(
            "预览",
            FIF.VIEW,
            "Scroll Lock 浮窗",
            "使用当前 Scroll Lock 状态显示一次浮窗",
            parent=test_group,
        )
        self.add_group(test_group, self.test_caps_card, self.test_num_card, self.test_scroll_card)

        self.caps_card.checkedChanged.connect(lambda v: self._set("caps_enabled", v))
        self.num_card.checkedChanged.connect(lambda v: self._set("num_enabled", v))
        self.scroll_card.checkedChanged.connect(lambda v: self._set("scroll_enabled", v))
        self.fullscreen_card.checkedChanged.connect(lambda v: self._set("hide_directx_fullscreen", v))
        self.startup_card.checkedChanged.connect(self._set_startup)
        self.duration_card.valueChanged.connect(self._set_duration)
        self.test_caps_card.clicked.connect(lambda: self.test_requested.emit("Caps Lock"))
        self.test_num_card.clicked.connect(lambda: self.test_requested.emit("Num Lock"))
        self.test_scroll_card.clicked.connect(lambda: self.test_requested.emit("Scroll Lock"))

    def _set(self, name: str, value) -> None:
        setattr(self.settings, name, value)
        save_settings(self.settings)
        self.changed.emit()

    def _set_startup(self, enabled: bool) -> None:
        try:
            set_startup_enabled(enabled)
        except OSError as exc:
            QMessageBox.warning(self.window(), APP_NAME, f"无法更新开机启动设置：{exc}")
            self.sync_startup(self.settings.startup)
            return
        self._set("startup", enabled)

    def _set_duration(self, value: int) -> None:
        self._format_duration_label(value)
        self._set("duration_ms", value * 100)

    def _format_duration_label(self, value: int) -> None:
        self.duration_card.valueLabel.setText(f"{value / 10:.1f} 秒")
        self.duration_card.valueLabel.adjustSize()

    def sync_startup(self, enabled: bool) -> None:
        self.startup_card.switchButton.blockSignals(True)
        self.startup_card.setChecked(enabled)
        self.startup_card.switchButton.blockSignals(False)


class AppearanceSettingsPage(SettingsPage):
    changed = Signal()

    def __init__(self, settings: AppSettings, items: SettingsConfigItems, parent=None):
        super().__init__("外观", "appearanceInterface", parent)
        self.settings = settings

        appearance_group = SettingCardGroup("个性化", self.scroll_widget)
        self.theme_card = OptionsSettingCard(
            items.theme,
            FIF.BRUSH,
            "应用主题",
            "更改设置窗口和浮窗的深浅色策略",
            texts=["跟随系统", "浅色", "深色"],
            parent=appearance_group,
        )
        self.position_card = OptionsSettingCard(
            items.position,
            FIF.LAYOUT,
            "浮窗位置",
            "默认显示在鼠标所在屏幕的底部居中",
            texts=["底部居中", "左下角", "右下角", "顶部居中"],
            parent=appearance_group,
        )
        self.add_group(appearance_group, self.theme_card, self.position_card)

        self.theme_card.optionChanged.connect(lambda item: self._set_theme(item.value))
        self.position_card.optionChanged.connect(lambda item: self._set("position", item.value))

    def _set(self, name: str, value) -> None:
        setattr(self.settings, name, value)
        save_settings(self.settings)
        self.changed.emit()

    def _set_theme(self, value: str) -> None:
        self._set("theme", value)
        apply_app_theme(self.settings)


class AboutSettingsPage(SettingsPage):
    def __init__(self, parent=None):
        super().__init__("关于", "aboutInterface", parent)
        about_group = SettingCardGroup("CapsLockShow", self.scroll_widget)
        description = QLabel(
            "CapsLockShow 是一个面向 Windows 11 的锁定键浮窗工具。\n"
            "项目按 GPLv3 开源，UI 使用 PySide6-Fluent-Widgets，交互参考 FluentFlyout。"
        )
        description.setWordWrap(True)
        description.setContentsMargins(20, 12, 20, 12)

        license_card = PrimaryPushSettingCard(
            "GPLv3",
            FIF.INFO,
            "开源许可",
            "公开分发时请保留源码、许可证和第三方依赖说明",
            parent=about_group,
        )
        about_group.addSettingCard(description)
        about_group.addSettingCard(license_card)
        self.expand_layout.addWidget(about_group)


class SettingsWindow(MSFluentWindow):
    changed = Signal()
    test_requested = Signal(str)

    def __init__(self, settings: AppSettings, icon: QIcon):
        super().__init__()
        self.settings = settings
        self.items = SettingsConfigItems(settings)
        self.setWindowTitle(f"{APP_NAME} 设置")
        self.setWindowIcon(icon)
        self.resize(860, 640)
        self.setMinimumSize(760, 560)
        self.setMicaEffectEnabled(True)

        self.general_page = GeneralSettingsPage(settings, self.items, self)
        self.appearance_page = AppearanceSettingsPage(settings, self.items, self)
        self.about_page = AboutSettingsPage(self)

        self.addSubInterface(self.general_page, FIF.SETTING, "常规")
        self.addSubInterface(self.appearance_page, FIF.PALETTE, "外观")
        self.addSubInterface(
            self.about_page,
            FIF.INFO,
            "关于",
            position=NavigationItemPosition.BOTTOM,
        )

        self.general_page.changed.connect(self.changed)
        self.general_page.test_requested.connect(self.test_requested)
        self.appearance_page.changed.connect(self.changed)

    def sync_startup(self, enabled: bool) -> None:
        self.general_page.sync_startup(enabled)


class CapsLockShowApp(QObject):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        apply_app_theme(self.settings)
        self.bridge = KeyboardBridge()
        self.bridge.key_released.connect(self.on_key_released)
        self.flyout = LockFlyout(self.settings)
        self.icon = self._app_icon()
        self.settings_window = SettingsWindow(self.settings, self.icon)
        self.settings_window.changed.connect(self.refresh_tray_state)
        self.settings_window.test_requested.connect(self.test_flyout)
        self.tray = self._create_tray()
        self.hook = KeyboardHook(self.bridge.key_released.emit)
        self.hook.start()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def _create_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self.icon, self)
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
        self.settings_window.sync_startup(self.settings.startup)

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

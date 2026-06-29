from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

import main as app


class KeycapLockFlyout(app.LockFlyout):
    """Lock-key flyout with distinct Fluent-style keycap icons."""

    def _draw_lock_icon(self, painter: QPainter, rect: QRect, color: QColor) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        symbols = {
            "Caps Lock": "A",
            "Num Lock": "1",
            "Scroll Lock": "↕",
        }
        symbol = symbols.get(self.key_name, "?")
        key_rect = rect.adjusted(1, 1, -1, -1)

        foreground = app.accent_color() if self.is_on else QColor(color)
        fill = QColor(foreground)
        fill.setAlpha(28 if self.is_on else 14)
        border = QColor(foreground)
        border.setAlpha(210 if self.is_on else 100)

        painter.setBrush(fill)
        painter.setPen(QPen(border, 1.4))
        painter.drawRoundedRect(key_rect, 7, 7)

        painter.setPen(foreground)
        painter.setFont(
            QFont(
                "Segoe UI Variable",
                14 if self.key_name == "Scroll Lock" else 15,
                QFont.Weight.DemiBold,
            )
        )
        painter.drawText(key_rect, Qt.AlignmentFlag.AlignCenter, symbol)
        painter.restore()


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{Path(__file__).resolve()}"'


app.LockFlyout = KeycapLockFlyout
app.startup_command = startup_command


if __name__ == "__main__":
    raise SystemExit(app.main())

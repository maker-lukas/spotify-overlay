import subprocess
from PySide6.QtWidgets import QLabel, QPushButton, QSlider
from PySide6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, Property
from PySide6.QtGui import QPainter

from .utils import load_icon


class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            value = int(event.position().x() / self.width() * self.maximum())
            self.setValue(value)
            self.sliderReleased.emit()
        super().mousePressEvent(event)

class MarqueeLabel(QLabel):
    SCROLL_PX_PER_SEC = 22    # scrolling speed
    PAUSE_DURATION = 2800     # ms to hold at each end

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.url = None
        self.setStyleSheet("padding: 0px; margin: 0px;")
        self.is_underlined = False

        self._offset = 0.0
        self._scrolling_forward = True
        self._current_text = text

        self._anim = QPropertyAnimation(self, b"scroll_offset")
        self._anim.finished.connect(self._on_anim_finished)

        self._pause_timer = QTimer(self)
        self._pause_timer.setSingleShot(True)
        self._pause_timer.timeout.connect(self._start_next_scroll)

    def _get_scroll_offset(self):
        return self._offset

    def _set_scroll_offset(self, val):
        self._offset = val
        self.update()

    scroll_offset = Property(float, _get_scroll_offset, _set_scroll_offset)

    def setText(self, text):
        if text == self._current_text:
            return
        self._current_text = text
        super().setText(text)
        self._stop_all()
        self._offset = 0.0
        self._scrolling_forward = True
        self._kick_scroll()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._stop_all()
        self._offset = 0.0
        self._scrolling_forward = True
        self._kick_scroll()

    def _text_width(self):
        return self.fontMetrics().horizontalAdvance(self.text())

    def _overflow(self):
        return max(0.0, self._text_width() - self.width())

    def _stop_all(self):
        self._anim.stop()
        self._pause_timer.stop()

    def _kick_scroll(self):
        if self._overflow() > 0:
            self._pause_timer.start(self.PAUSE_DURATION)
        else:
            self.update()

    def _start_next_scroll(self):
        overflow = self._overflow()
        if overflow <= 0:
            return

        if self._scrolling_forward:
            start, end = 0.0, overflow
        else:
            start, end = overflow, 0.0

        distance = abs(end - start)
        duration = int(distance / self.SCROLL_PX_PER_SEC * 1000)

        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setDuration(max(duration, 100))
        self._anim.start()

    def _on_anim_finished(self):
        self._scrolling_forward = not self._scrolling_forward
        self._pause_timer.start(self.PAUSE_DURATION)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        text_rect = self.rect()
        text_rect.setWidth(self._text_width())
        text_rect.moveLeft(int(-self._offset))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())
        painter.end()

    def _hit_text(self, pos):
        visible_w = min(self._text_width(), self.width())
        return 0 <= pos.x() <= visible_w

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.url and self._hit_text(event.position()):
            subprocess.Popen(["xdg-open", self.url])
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.url and self._hit_text(event.position()):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            if not self.is_underlined:
                font = self.font()
                font.setUnderline(True)
                self.setFont(font)
                self.is_underlined = True
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self.is_underlined:
                font = self.font()
                font.setUnderline(False)
                self.setFont(font)
                self.is_underlined = False
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.is_underlined:
            font = self.font()
            font.setUnderline(False)
            self.setFont(font)
            self.is_underlined = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)


class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.url = None
        self.setStyleSheet("padding: 0px; margin: 0px;")
        self.is_underlined = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        elided = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
        painter.end()

    def _hit_text(self, pos):
        visible_w = min(self.fontMetrics().horizontalAdvance(self.text()), self.width())
        return 0 <= pos.x() <= visible_w

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.url and self._hit_text(event.position()):
            subprocess.Popen(["xdg-open", self.url])
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.url and self._hit_text(event.position()):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            if not self.is_underlined:
                font = self.font()
                font.setUnderline(True)
                self.setFont(font)
                self.is_underlined = True
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self.is_underlined:
                font = self.font()
                font.setUnderline(False)
                self.setFont(font)
                self.is_underlined = False
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.is_underlined:
            font = self.font()
            font.setUnderline(False)
            self.setFont(font)
            self.is_underlined = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)


class HoverButton(QPushButton):
    def __init__(self, icon_name, size, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.base_size = size
        self.normal_color = "#a0a0a0"
        self.hover_color = "#ffffff"
        self.active_color = None
        self.setIcon(load_icon(icon_name, self.normal_color))
        self.setIconSize(QSize(size, size))
        self.setFixedSize(QSize(size + 4, size + 4))

    def set_active_color(self, color):
        self.active_color = color
        if self.underMouse():
            current_color = color if color else self.hover_color
        else:
            current_color = color if color else self.normal_color
        self.setIcon(load_icon(self.icon_name, current_color))

    def set_icon_name(self, name):
        self.icon_name = name
        if self.underMouse():
            color = self.active_color if self.active_color else self.hover_color
        else:
            color = self.active_color if self.active_color else self.normal_color
        self.setIcon(load_icon(name, color))

    def enterEvent(self, event):
        color = self.active_color if self.active_color else self.hover_color
        self.setIcon(load_icon(self.icon_name, color))
        self.setIconSize(QSize(self.base_size + 2, self.base_size + 2))
        super().enterEvent(event)

    def leaveEvent(self, event):
        color = self.active_color if self.active_color else self.normal_color
        self.setIcon(load_icon(self.icon_name, color))
        self.setIconSize(QSize(self.base_size, self.base_size))
        super().leaveEvent(event)

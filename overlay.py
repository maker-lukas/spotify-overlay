import sys
import os
import asyncio
import subprocess
import aiohttp
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QSlider
from PySide6.QtCore import Qt, QTimer, QSize, QRect
from PySide6.QtGui import QPixmap, QImage, QIcon, QKeySequence
from PySide6.QtWidgets import QApplication as QApp

from spotify_dbus import SpotifyDBus

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
ICON_SIZE = QSize(14, 14)


def load_icon(name, color=None):
    path = os.path.join(ICON_DIR, name)
    if color:
        with open(path, "r") as f:
            svg_data = f.read().replace('fill="black"', f'fill="{color}"')
        pixmap = QPixmap()
        pixmap.loadFromData(svg_data.encode())
        return QIcon(pixmap)
    return QIcon(path)


class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            value = int(event.position().x() / self.width() * self.maximum())
            self.setValue(value)
            self.sliderReleased.emit()
        super().mousePressEvent(event)

class ClickableLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.url = None
        self.setStyleSheet("padding: 0px; margin: 0px;")
        self.is_underlined = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.url:
            if self.text_rect().contains(event.pos()):
                subprocess.Popen(["xdg-open", self.url])
        super().mousePressEvent(event)

    def text_rect(self):
        """Returns the bounding rect of the actual text"""
        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(self.text())
        text_height = fm.height()
        y_offset = (self.height() - text_height) // 2
        return QRect(0, y_offset, text_width, text_height)

    def mouseMoveEvent(self, event):
        if self.url and self.text_rect().contains(event.pos()):
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
        super().enterEvent(event)

    def leaveEvent(self, event):
        color = self.active_color if self.active_color else self.normal_color
        self.setIcon(load_icon(self.icon_name, color))
        self.setIconSize(QSize(self.base_size, self.base_size))
        super().leaveEvent(event)

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.spotify = SpotifyDBus()
        self.current_art_url = None

        self.setWindowTitle("Spotify Overlay")
        self.setObjectName("spotify-overlay")
        self.setFixedSize(400, 220)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setup_ui()
        
        QApp.instance().focusChanged.connect(self.on_focus_changed)
    
    def on_focus_changed(self, old_widget, new_widget):
        """Hide overlay when focus changes to another widget/window"""
        if self.isVisible() and new_widget != self and not self.isAncestorOf(new_widget):
            self.hide()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(200, self.force_above)

    def force_above(self):
        try:
            import os
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keep_above.js")
            result = subprocess.run(
                ["qdbus6", "org.kde.KWin", "/Scripting",
                 "org.kde.kwin.Scripting.loadScript", script_path],
                capture_output=True, text=True
            )
            script_id = result.stdout.strip()
            subprocess.run(
                ["qdbus6", "org.kde.KWin", "/Scripting",
                 "org.kde.kwin.Scripting.start"],
                capture_output=True
            )
        except Exception:
            pass

    def closeEvent(self, event):
        self.hide()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.force_above()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if not self.rect().contains(event.pos()):
            self.hide()
        else:
            super().mousePressEvent(event)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QWidget()
        container.setObjectName("container")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 8)
        container_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(0)

        self.art_label = QLabel()
        self.art_label.setFixedSize(120, 120)
        self.art_label.setObjectName("albumArt")
        self.art_label.setScaledContents(True)
        top_row.addWidget(self.art_label)

        right_side = QVBoxLayout()
        right_side.setSpacing(0)
        right_side.setContentsMargins(6, 0, 0, 0)

        self.title_label = ClickableLabel("Loading...")
        self.title_label.setObjectName("trackTitle")
        self.title_label.setFixedHeight(22)
        self.title_label.setAttribute(Qt.WA_Hover, True)
        right_side.addWidget(self.title_label)

        self.artist_label = ClickableLabel("")
        self.artist_label.setObjectName("trackArtist")
        self.artist_label.setFixedHeight(18)
        self.artist_label.setAttribute(Qt.WA_Hover, True)
        right_side.addWidget(self.artist_label)

        self.album_label = ClickableLabel("")
        self.album_label.setObjectName("trackAlbum")
        self.album_label.setFixedHeight(16)
        self.album_label.setAttribute(Qt.WA_Hover, True)
        right_side.addWidget(self.album_label)

        top_row.addLayout(right_side)
        container_layout.addLayout(top_row)

        container_layout.addSpacing(12)

        controls = QHBoxLayout()
        controls.setSpacing(2)
        controls.setContentsMargins(0, 0, 0, 0)

        self.shuffle_btn = HoverButton("shuffle.svg", 16)
        self.shuffle_btn.setObjectName("controlBtn")
        self.shuffle_btn.clicked.connect(self.on_shuffle)
        controls.addWidget(self.shuffle_btn)

        self.prev_btn = HoverButton("previous.svg", 16)
        self.prev_btn.setObjectName("controlBtn")
        self.prev_btn.clicked.connect(self.on_previous)
        controls.addWidget(self.prev_btn)

        self.play_btn = QPushButton()
        self.play_btn.setIcon(load_icon("pause.svg", "#ffffff"))
        self.play_btn.setIconSize(QSize(28, 28))
        self.play_btn.setObjectName("playBtn")
        self.play_btn.clicked.connect(self.on_play_pause)
        controls.addWidget(self.play_btn)

        self.next_btn = HoverButton("next.svg", 16)
        self.next_btn.setObjectName("controlBtn")
        self.next_btn.clicked.connect(self.on_next)
        controls.addWidget(self.next_btn)

        self.repeat_btn = HoverButton("repeat.svg", 16)
        self.repeat_btn.setObjectName("controlBtn")
        self.repeat_btn.clicked.connect(self.on_repeat)
        controls.addWidget(self.repeat_btn)

        container_layout.addLayout(controls)

        timeline_row = QHBoxLayout()
        timeline_row.setSpacing(6)

        self.pos_label = QLabel("0:00")
        self.pos_label.setObjectName("timeline")
        timeline_row.addWidget(self.pos_label)

        self.timeline_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setObjectName("timelineSlider")
        self.timeline_slider.setRange(0, 1000)
        self.timeline_slider.sliderReleased.connect(self.on_seek)
        timeline_row.addWidget(self.timeline_slider)

        self.len_label = QLabel("0:00")
        self.len_label.setObjectName("timeline")
        timeline_row.addWidget(self.len_label)

        container_layout.addLayout(timeline_row)
        main_layout.addWidget(container)

    def on_play_pause(self):
        asyncio.ensure_future(self.spotify.play_pause())
    
    def on_next(self):
        asyncio.ensure_future(self.spotify.next_track())

    def on_previous(self):
        asyncio.ensure_future(self.spotify.previous_track())

    def on_shuffle(self):
        asyncio.ensure_future(self.toggle_shuffle())

    async def toggle_shuffle(self):
        current = await self.spotify.get_shuffle()
        await self.spotify.set_shuffle(not current)

    def on_repeat(self):
        asyncio.ensure_future(self.cycle_repeat())

    async def cycle_repeat(self):
        current = await self.spotify.get_loop_status()
        cycle = {"None": "Playlist", "Playlist": "Track", "Track": "None"}
        next_status = cycle[current]
        await self.spotify.set_loop_status(next_status)

    def on_seek(self):
        asyncio.ensure_future(self.do_seek())

    async def do_seek(self):
        metadata = await self.spotify.get_metadata()
        length = metadata.get("length", 0)
        fraction = self.timeline_slider.value() / 1000
        target = int(length * fraction)
        await self.spotify.set_position(metadata["track_id"], target)

    async def refresh(self):
        try:
            metadata = await self.spotify.get_metadata()
            status = await self.spotify.get_playback_status()

            self.title_label.setText(metadata["title"])
            self.artist_label.setText(metadata["artist"])

            track_id = metadata.get("track_id", "")
            is_ad = "/ad/" in track_id
            
            track_id_clean = track_id.replace("/com/spotify/track/", "")
            self.title_label.url = f"spotify:track:{track_id_clean}" if track_id_clean and not is_ad else ""

            artist_name = metadata["artist"]
            self.artist_label.url = f"spotify:search:{artist_name.replace(' ', '+')}" if not is_ad else ""

            album_name = metadata.get("album", "")
            self.album_label.setText(album_name)
            self.album_label.url = f"spotify:search:{album_name.replace(' ', '+')}" if not is_ad else ""

            if status == "Playing":
                self.play_btn.setIcon(load_icon("pause.svg", "#ffffff"))
            else:
                self.play_btn.setIcon(load_icon("play.svg", "#ffffff"))
            
            position = await self.spotify.get_position()
            length = metadata.get("length", 0)

            pos_sec = position // 1_000_000
            len_sec = length // 1_000_000
            self.pos_label.setText(f"{pos_sec // 60}:{pos_sec % 60:02d}")
            self.len_label.setText(f"{len_sec // 60}:{len_sec % 60:02d}")

            if not self.timeline_slider.isSliderDown() and length > 0:
                self.timeline_slider.setValue(int(position / length * 1000))

            shuffle = await self.spotify.get_shuffle()
            self.shuffle_btn.set_active_color("#1DB954" if shuffle else None)

            loop_status = await self.spotify.get_loop_status()
            if loop_status == "Track":
                self.repeat_btn.set_icon_name("repeat1.svg")
                self.repeat_btn.set_active_color("#1DB954")
            elif loop_status == "Playlist":
                self.repeat_btn.set_icon_name("repeat.svg")
                self.repeat_btn.set_active_color("#1DB954")
            else:
                self.repeat_btn.set_icon_name("repeat.svg")
                self.repeat_btn.set_active_color(None)

            art_url = metadata.get("art_url", "")
            if is_ad:
                self.show_ad_placeholder()
            elif art_url and art_url != self.current_art_url:
                self.current_art_url = art_url
                await self.load_album_art(art_url)

        except Exception:
            self.title_label.setText("Spotify not running")
            self.artist_label.setText("")

    def show_ad_placeholder(self):
        """Show 'AD' text as placeholder for ads"""
        pixmap = QPixmap(120, 120)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        from PySide6.QtGui import QPainter, QFont, QColor
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(0, 0, 120, 120, 20, 20)
        painter.fillPath(path, QColor("#282828"))
        
        font = QFont()
        font.setPointSize(32)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#1DB954"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AD")
        painter.end()
        
        self.art_label.setPixmap(pixmap)

    async def load_album_art(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    image_data = await response.read()
                    image = QImage()
                    image.loadFromData(image_data)
                    pixmap = QPixmap.fromImage(image)
                    pixmap = self.add_rounded_corners(pixmap, 20)
                    self.art_label.setPixmap(pixmap)
        except Exception:
            pass
    
    def add_rounded_corners(self, pixmap, radius):
        size = pixmap.size()
        rounded = QPixmap(size)
        rounded.fill(Qt.GlobalColor.transparent)
        
        from PySide6.QtGui import QPainter, QPainterPath
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        return rounded
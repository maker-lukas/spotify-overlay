import sys
import os
import asyncio
import subprocess
import aiohttp
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QSlider
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QImage

from spotify_dbus import SpotifyDBus


class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            value = int(event.position().x() / self.width() * self.maximum())
            self.setValue(value)
            self.sliderReleased.emit()
        super().mousePressEvent(event)


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.spotify = SpotifyDBus()
        self.current_art_url = None

        self.setWindowTitle("Spotify Overlay")
        self.setObjectName("spotify-overlay")
        self.setFixedSize(400, 150)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setup_ui()

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
        QApplication.instance().quit()
        event.accept()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setObjectName("container")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)

        self.art_label = QLabel()
        self.art_label.setFixedSize(96, 96)
        self.art_label.setObjectName("albumArt")
        self.art_label.setScaledContents(True)
        container_layout.addWidget(self.art_label)

        right_side = QVBoxLayout()

        self.title_label = QLabel("Loading...")
        self.title_label.setObjectName("trackTitle")
        right_side.addWidget(self.title_label)

        self.artist_label = QLabel("")
        self.artist_label.setObjectName("trackArtist")
        right_side.addWidget(self.artist_label)

        timeline_row = QHBoxLayout()

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

        right_side.addLayout(timeline_row)

        controls = QHBoxLayout()

        self.shuffle_btn = QPushButton("🔀")
        self.shuffle_btn.setObjectName("controlBtn")
        self.shuffle_btn.clicked.connect(self.on_shuffle)
        controls.addWidget(self.shuffle_btn)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("controlBtn")
        self.prev_btn.clicked.connect(self.on_previous)
        controls.addWidget(self.prev_btn)

        self.play_btn = QPushButton("⏯")
        self.play_btn.setObjectName("controlBtn")
        self.play_btn.clicked.connect(self.on_play_pause)
        controls.addWidget(self.play_btn)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("controlBtn")
        self.next_btn.clicked.connect(self.on_next)
        controls.addWidget(self.next_btn)

        self.repeat_btn = QPushButton("🔁")
        self.repeat_btn.setObjectName("controlBtn")
        self.repeat_btn.clicked.connect(self.on_repeat)
        controls.addWidget(self.repeat_btn)

        right_side.addLayout(controls)

        container_layout.addLayout(right_side)
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

            if status == "Playing":
                self.play_btn.setText("⏸")
            else:
                self.play_btn.setText("▶")
            
            position = await self.spotify.get_position()
            length = metadata.get("length", 0)

            pos_sec = position // 1_000_000
            len_sec = length // 1_000_000
            self.pos_label.setText(f"{pos_sec // 60}:{pos_sec % 60:02d}")
            self.len_label.setText(f"{len_sec // 60}:{len_sec % 60:02d}")

            if not self.timeline_slider.isSliderDown() and length > 0:
                self.timeline_slider.setValue(int(position / length * 1000))

            shuffle = await self.spotify.get_shuffle()
            self.shuffle_btn.setStyleSheet("color: #1DB954;" if shuffle else "")

            loop_status = await self.spotify.get_loop_status()
            if loop_status == "Track":
                self.repeat_btn.setText("🔂")
                self.repeat_btn.setStyleSheet("color: #1DB954;")
            elif loop_status == "Playlist":
                self.repeat_btn.setText("🔁")
                self.repeat_btn.setStyleSheet("color: #1DB954;")
            else:
                self.repeat_btn.setText("🔁")
                self.repeat_btn.setStyleSheet("")

            art_url = metadata.get("art_url", "")
            if art_url and art_url != self.current_art_url:
                self.current_art_url = art_url
                await self.load_album_art(art_url)

        except Exception:
            self.title_label.setText("Spotify not running")
            self.artist_label.setText("")

    async def load_album_art(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    image_data = await response.read()
                    image = QImage()
                    image.loadFromData(image_data)
                    self.art_label.setPixmap(QPixmap.fromImage(image))
        except Exception:
            pass
import sys
import os
import shutil
import socket
import asyncio
import signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QSocketNotifier
from PySide6.QtGui import QIcon

try:
    from qasync import QEventLoop
except ImportError:
    print("Install qasync: pip install qasync")
    sys.exit(1)

from spotify_overlay.overlay import Overlay

SOCKET_PATH = "/run/user/1000/spotify-overlay"


def get_resource_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def install_desktop_entry():
    apps_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    icons_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "icons", "hicolor", "scalable", "apps")
    os.makedirs(apps_dir, exist_ok=True)
    os.makedirs(icons_dir, exist_ok=True)

    icon_src = get_resource_path("icons/icon.svg")
    icon_dest = os.path.join(icons_dir, "spotify-overlay.svg")
    shutil.copy2(icon_src, icon_dest)

    exe_path = shutil.which("spotify-overlay") or "spotify-overlay"
    desktop_entry = f"""[Desktop Entry]
Type=Application
Name=Spotify Overlay
Comment=A minimal Spotify overlay widget
Exec={exe_path}
Icon=spotify-overlay
Terminal=false
Categories=Audio;Music;Player;
Keywords=spotify;music;overlay;
"""
    desktop_path = os.path.join(apps_dir, "spotify-overlay.desktop")
    with open(desktop_path, "w") as f:
        f.write(desktop_entry)

    print(f"Installed desktop entry: {desktop_path}")
    print(f"Installed icon: {icon_dest}")
    print("Spotify Overlay should now appear in your app launcher.")


def main():
    if "--install" in sys.argv:
        install_desktop_entry()
        return
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    overlay = Overlay()

    try:
        with open(get_resource_path("styles.qss")) as f:
            styles = f.read()
            overlay.setStyleSheet(styles)
    except FileNotFoundError:
        pass

    tray_icon = QSystemTrayIcon(QIcon(get_resource_path("icons/icon.svg")), app)

    tray_menu = QMenu()
    help_action = tray_menu.addAction("Help")
    help_action.triggered.connect(show_help)
    tray_menu.addSeparator()
    quit_action = tray_menu.addAction("Quit")
    quit_action.triggered.connect(app.quit)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.activated.connect(lambda reason: on_tray_activated(reason, overlay))
    tray_icon.setToolTip("Spotify Overlay")
    tray_icon.show()

    app.aboutToQuit.connect(lambda: loop.stop())
    overlay.show()

    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(1)
    server.setblocking(False)

    def on_toggle():
        try:
            conn, _ = server.accept()
            conn.close()
        except Exception:
            return
        toggle_overlay(overlay)

    notifier = QSocketNotifier(server.fileno(), QSocketNotifier.Type.Read)
    notifier.activated.connect(on_toggle)

    def cleanup():
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        loop.stop()

    app.aboutToQuit.connect(cleanup)

    async def start():
        while True:
            if not overlay.spotify.player:
                overlay.title_label.setText("Spotify is not open")
                overlay.artist_label.setText("")
                overlay.album_label.setText("")
                try:
                    await overlay.spotify.connect()
                except Exception:
                    await asyncio.sleep(2)
                    continue
            try:
                await overlay.refresh()
            except Exception:
                overlay.spotify.player = None
                overlay.spotify.properties = None
            await asyncio.sleep(0.25)

    asyncio.ensure_future(start())

    with loop:
        loop.run_forever()


_help_dialog = None


def show_help():
    global _help_dialog
    if _help_dialog is not None:
        _help_dialog.close()

    _help_dialog = QDialog()
    _help_dialog.setWindowTitle("Spotify Overlay — Help")
    _help_dialog.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.WindowCloseButtonHint
    )
    _help_dialog.setFixedSize(360, 320)

    layout = QVBoxLayout(_help_dialog)

    content = QLabel(
        "<h3>Keybinds</h3>"
        "<table cellpadding='4'>"
        "<tr><td><b>Space</b></td><td>Play / Pause</td></tr>"
        "<tr><td><b>→ Right</b></td><td>Next Track</td></tr>"
        "<tr><td><b>← Left</b></td><td>Previous Track</td></tr>"
        "<tr><td><b>↑ Up</b></td><td>Cycle Repeat Mode</td></tr>"
        "<tr><td><b>↓ Down</b></td><td>Toggle Shuffle</td></tr>"
        "<tr><td><b>Ctrl+F / </b></td><td>Open Search</td></tr>"
        "<tr><td><b>Enter</b></td><td>Submit Search</td></tr>"
        "<tr><td><b>Escape</b></td><td>Close Search / Hide Overlay</td></tr>"
        "</table>"
        "<br>"
        "<b>Tray Icon:</b> Left-click to toggle overlay visibility."
    )
    content.setTextFormat(Qt.TextFormat.RichText)
    content.setWordWrap(True)
    layout.addWidget(content)

    close_btn = QPushButton("Close")
    close_btn.clicked.connect(_help_dialog.close)
    layout.addWidget(close_btn)

    _help_dialog.show()
    _help_dialog.raise_()
    _help_dialog.activateWindow()


def toggle_overlay(overlay):
    if overlay.isVisible():
        overlay.hide()
    else:
        overlay.show()
        overlay.force_above()


def on_tray_activated(reason, overlay):
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        toggle_overlay(overlay)


if __name__ == "__main__":
    main()

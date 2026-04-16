import sys
import os
import shutil
import socket
import asyncio
import signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtCore import QSocketNotifier
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

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    overlay = Overlay()

    try:
        with open(get_resource_path("styles.qss")) as f:
            overlay.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    # --- System tray icon ---
    tray_icon = QSystemTrayIcon(QIcon(get_resource_path("icons/icon.svg")), app)

    tray_menu = QMenu()
    show_action = tray_menu.addAction("Show / Hide")
    show_action.triggered.connect(lambda: toggle_overlay(overlay))
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

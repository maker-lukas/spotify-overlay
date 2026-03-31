import sys
import os
import socket
import asyncio
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSocketNotifier

try:
    from qasync import QEventLoop
except ImportError:
    print("Install qasync: pip install qasync")
    sys.exit(1)

from overlay import Overlay

SOCKET_PATH = "/run/user/1000/spotify-overlay"


def main():
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    overlay = Overlay()

    try:
        with open("styles.qss") as f:
            overlay.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    app.aboutToQuit.connect(lambda: loop.stop())
    overlay.show()

    # Unix socket server for toggle hotkey
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
        if overlay.isVisible():
            overlay.hide()
        else:
            overlay.show()
            overlay.force_above()

    notifier = QSocketNotifier(server.fileno(), QSocketNotifier.Type.Read)
    notifier.activated.connect(on_toggle)

    def cleanup():
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        loop.stop()

    app.aboutToQuit.connect(cleanup)

    async def start():
        await overlay.spotify.connect()
        while True:
            if overlay.isVisible():
                await overlay.refresh()
            await asyncio.sleep(0.25)

    asyncio.ensure_future(start())

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
s
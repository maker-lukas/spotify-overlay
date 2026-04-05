import os
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QSize

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
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

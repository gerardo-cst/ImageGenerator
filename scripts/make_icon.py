"""Build multi-resolution Windows icon from the project's native SVG."""
from pathlib import Path
import os
import struct
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main() -> None:
    app = QApplication.instance() or QApplication([])
    root = Path(__file__).resolve().parents[1]
    renderer = QSvgRenderer(str(root / "assets/app.svg"))
    entries = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        payload = QByteArray()
        buffer = QBuffer(payload)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        entries.append((size, bytes(payload)))
    offset = 6 + 16 * len(entries)
    directory = bytearray(struct.pack("<HHH", 0, 1, len(entries)))
    for size, data in entries:
        directory += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    (root / "assets/app.ico").write_bytes(bytes(directory) + b"".join(data for _, data in entries))


if __name__ == "__main__":
    main()

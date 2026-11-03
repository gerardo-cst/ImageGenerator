"""Create synthetic technical drawings for local functional checks (no cloud)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter, QPen, QFont, QFontDatabase, QPdfWriter
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication([])
if Path("C:/Windows/Fonts/segoeui.ttf").exists():
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
root = Path("examples")
root.mkdir(exist_ok=True)


def drawing(painter: QPainter, side: bool = False):
    painter.setPen(QPen(Qt.GlobalColor.black, 3))
    painter.setFont(QFont("Segoe UI", 13))
    painter.drawText(35, 40, "CST RenderAI - riferimento sintetico di prova")
    painter.drawText(35, 70, "Flangia AISI 316L - Diametro esterno: 150 mm")
    painter.drawText(35, 100, "Diametro interno: 60 mm | Spessore: 15 mm | Finitura: satinata")
    if not side:
        painter.drawEllipse(175, 150, 300, 300)
        painter.drawEllipse(265, 240, 120, 120)
        for x, y in [(325, 180), (445, 300), (325, 420), (205, 300)]:
            painter.drawEllipse(x - 12, y - 12, 24, 24)
        painter.drawText(220, 500, "Vista frontale - 4 fori equidistanti")
    else:
        painter.drawRect(175, 180, 300, 30)
        painter.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.DashLine))
        painter.drawLine(265, 160, 265, 230)
        painter.drawLine(385, 160, 385, 230)
        painter.drawText(230, 290, "Vista laterale - piastra piatta")


image = QImage(720, 550, QImage.Format.Format_RGB32)
image.fill(Qt.GlobalColor.white)
painter = QPainter(image)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
drawing(painter)
painter.end()
image.save(str(root / "Flangia_DN150_frontale.jpg"), "JPG", 98)
writer = QPdfWriter(str(root / "Flangia_DN150.pdf"))
writer.setResolution(72)
painter = QPainter(writer)
painter.scale(.70, .70)
drawing(painter)
writer.newPage()
drawing(painter, True)
painter.end()
del writer
print(root.resolve())

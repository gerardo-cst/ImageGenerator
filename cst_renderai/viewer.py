from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QRubberBand


class ImageViewer(QGraphicsView):
    crop_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(Qt.GlobalColor.white)
        self.rubber = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self.crop_mode = False
        self.origin = None
        self.image_size = None

    def show_image(self, image: QImage) -> None:
        self.scene().clear()
        self.scene().addPixmap(QPixmap.fromImage(image))
        self.scene().setSceneRect(QRectF(image.rect()))
        self.image_size = image.size()
        self.fit()

    def fit(self) -> None:
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        if not self.scene().items():
            return
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        if 0.01 < self.transform().m11() * factor < 50:
            self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if self.crop_mode and self.image_size:
            self.origin = event.position().toPoint()
            self.rubber.setGeometry(self.origin.x(), self.origin.y(), 0, 0)
            self.rubber.show()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.origin is not None:
            from PySide6.QtCore import QRect
            self.rubber.setGeometry(QRect(self.origin, event.position().toPoint()).normalized())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self.origin is not None:
            rect = self.mapToScene(self.rubber.geometry()).boundingRect().intersected(self.sceneRect())
            self.rubber.hide()
            self.origin = None
            self.crop_mode = False
            if rect.width() >= 2 and rect.height() >= 2:
                self.crop_selected.emit([rect.x() / self.image_size.width(), rect.y() / self.image_size.height(), rect.width() / self.image_size.width(), rect.height() / self.image_size.height()])
        else:
            super().mouseReleaseEvent(event)

from __future__ import annotations
from dataclasses import replace
import math
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QRubberBand, QGraphicsItem
from .annotations import draw_annotations, label_position
from .models import Annotation, Variable


class AnnotationOverlay(QGraphicsItem):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.setZValue(1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def boundingRect(self):
        return self.viewer.sceneRect()

    def paint(self, painter, option, widget=None):
        v = self.viewer
        if v.image_size:
            draw_annotations(painter, v.image_size, v.annotations, v.variables, v.selected_annotation)


class ImageViewer(QGraphicsView):
    crop_selected = Signal(list)
    annotation_created = Signal(str, list)
    annotation_changed = Signal(str, list)
    annotation_selected = Signal(str)
    delete_requested = Signal()
    tool_reset = Signal()

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
        self.tool = "navigate"
        self.annotations: list[Annotation] = []
        self.variables: list[Variable] = []
        self.selected_annotation = ""
        self._drawing = None
        self._drag = None
        self.editable = True

    def show_image(self, image: QImage) -> None:
        self.cancel_gesture()
        self.scene().clear()
        self.scene().addPixmap(QPixmap.fromImage(image))
        self.scene().setSceneRect(QRectF(image.rect()))
        self.image_size = image.size()
        self.annotations = []
        self.selected_annotation = ""
        self.scene().addItem(AnnotationOverlay(self))
        self.fit()

    def set_annotations(self, annotations: list[Annotation], variables: list[Variable], selected: str = "") -> None:
        self.annotations = [replace(a) for a in annotations]
        self.variables = variables
        self.selected_annotation = selected
        self.viewport().update()

    def set_tool(self, tool: str) -> None:
        self.cancel_gesture()
        self.tool = tool
        self.crop_mode = False
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag if tool == "navigate" else QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor if tool == "navigate" else Qt.CursorShape.CrossCursor)

    def cancel_gesture(self) -> None:
        if self._drawing is not None and self._drawing in self.annotations:
            self.annotations.remove(self._drawing)
        if self._drag is not None:
            self._drag[0].points = self._drag[3]
        self.origin = None
        self._drag = None
        self._drawing = None
        self.rubber.hide()

    def fit(self) -> None:
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        if not self.scene().items():
            return
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        if 0.01 < self.transform().m11() * factor < 50:
            self.scale(factor, factor)

    def point(self, event) -> list[float]:
        pos = self.mapToScene(event.position().toPoint())
        return [min(1., max(0., pos.x() / self.image_size.width())), min(1., max(0., pos.y() / self.image_size.height()))]

    def hit_test(self, point: list[float]) -> tuple[str, int | None]:
        if not self.image_size:
            return "", None
        width, height = self.image_size.width(), self.image_size.height()
        pos = QPointF(point[0] * width, point[1] * height)
        tolerance = 12 / max(.001, self.transform().m11())
        distance = lambda p: math.hypot(pos.x() - p.x(), pos.y() - p.y())
        for note in reversed(self.annotations):
            a, b = [QPointF(p[0] * width, p[1] * height) for p in note.points]
            for index, endpoint in enumerate((a, b)):
                if distance(endpoint) <= tolerance:
                    return note.id, index
            delta = b - a
            squared = delta.x() ** 2 + delta.y() ** 2
            t = max(0., min(1., ((pos.x() - a.x()) * delta.x() + (pos.y() - a.y()) * delta.y()) / squared)) if squared else 0
            if distance(a + delta * t) <= tolerance or distance(label_position(note, self.image_size)) <= tolerance * 3:
                return note.id, None
        return "", None

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self.image_size or not self.editable:
            super().mousePressEvent(event)
            return
        if self.crop_mode:
            self.origin = event.position().toPoint()
            self.rubber.setGeometry(self.origin.x(), self.origin.y(), 0, 0)
            self.rubber.show()
            return
        point = self.point(event)
        if not self.sceneRect().contains(self.mapToScene(event.position().toPoint())):
            super().mousePressEvent(event)
            return
        if self.tool != "navigate":
            self._drawing = Annotation(kind=self.tool, points=[point, point])
            self.annotations.append(self._drawing)
            self.viewport().update()
            return
        selected, endpoint = self.hit_test(point)
        self.selected_annotation = selected
        self.annotation_selected.emit(selected)
        if selected:
            note = next(a for a in self.annotations if a.id == selected)
            self._drag = (note, endpoint, point, [p[:] for p in note.points])
            self.viewport().update()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.origin is not None:
            self.rubber.setGeometry(QRect(self.origin, event.position().toPoint()).normalized())
        elif self._drawing is not None:
            self._drawing.points[1] = self.point(event)
            self.viewport().update()
        elif self._drag is not None:
            note, endpoint, origin, before = self._drag
            current = self.point(event)
            if endpoint is not None:
                note.points = [p[:] for p in before]
                note.points[endpoint] = current
            else:
                delta = [current[axis] - origin[axis] for axis in (0, 1)]
                for axis in (0, 1):
                    delta[axis] = max(-min(p[axis] for p in before), min(delta[axis], 1 - max(p[axis] for p in before)))
                note.points = [[p[axis] + delta[axis] for axis in (0, 1)] for p in before]
            self.viewport().update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        if self.origin is not None:
            rect = self.mapToScene(self.rubber.geometry()).boundingRect().intersected(self.sceneRect())
            self.rubber.hide()
            self.origin = None
            self.crop_mode = False
            if rect.width() >= 2 and rect.height() >= 2:
                self.crop_selected.emit([rect.x() / self.image_size.width(), rect.y() / self.image_size.height(), rect.width() / self.image_size.width(), rect.height() / self.image_size.height()])
        elif self._drawing is not None:
            drawing = self._drawing
            self._drawing = None
            self.annotations.remove(drawing)
            drawing.points[1] = self.point(event)
            distance = math.hypot(*(drawing.points[1][i] - drawing.points[0][i] for i in (0, 1)))
            if drawing.kind == "note" and distance < .01:
                x, y = drawing.points[0]
                drawing.points[1] = [min(.95, x + .16), max(.05, y - .1)]
            if drawing.kind == "note" or distance >= .003:
                self.annotation_created.emit(drawing.kind, drawing.points)
            self.viewport().update()
        elif self._drag is not None:
            note = self._drag[0]
            self._drag = None
            self.annotation_changed.emit(note.id, note.points)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self._drawing in self.annotations:
                self.annotations.remove(self._drawing)
            self.cancel_gesture()
            self.set_tool("navigate")
            self.tool_reset.emit()
            self.viewport().update()
        elif event.key() == Qt.Key.Key_Delete and self.selected_annotation and self.editable:
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)

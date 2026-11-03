"""Non-destructive notes in original image coordinates, shared by preview and PNG export."""
from __future__ import annotations

from dataclasses import replace
import math
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF
from .models import Annotation, Reference, Variable


def to_display(point: list[float], reference: Reference) -> list[float]:
    x, y = point
    rotation = reference.rotation % 360
    if rotation == 90:
        x, y = 1 - y, x
    elif rotation == 180:
        x, y = 1 - x, 1 - y
    elif rotation == 270:
        x, y = y, 1 - x
    if reference.crop:
        cx, cy, width, height = reference.crop
        x, y = (x - cx) / width, (y - cy) / height
    return [x, y]


def to_original(point: list[float], reference: Reference) -> list[float]:
    x, y = point
    if reference.crop:
        cx, cy, width, height = reference.crop
        x, y = cx + x * width, cy + y * height
    rotation = reference.rotation % 360
    if rotation == 90:
        x, y = y, 1 - x
    elif rotation == 180:
        x, y = 1 - x, 1 - y
    elif rotation == 270:
        x, y = 1 - y, x
    return [min(1., max(0., x)), min(1., max(0., y))]


def display_annotations(reference: Reference) -> list[Annotation]:
    result = []
    for annotation in reference.annotations:
        points = [to_display(p, reference) for p in annotation.points]
        if any(max(p[axis] for p in points) < 0 or min(p[axis] for p in points) > 1 for axis in (0, 1)):
            continue
        # Projected endpoints can lie outside the crop; preserve original model validation.
        projected = replace(annotation)
        projected.points = points
        result.append(projected)
    return result


def annotation_label(annotation: Annotation, variables: list[Variable]) -> str:
    variable = next((v for v in variables if v.id == annotation.variable_id), None)
    parts = [variable.label()] if variable else []
    if annotation.text:
        parts.append(annotation.text)
    return " · ".join(parts)


def label_position(annotation: Annotation, size: QSize) -> QPointF:
    a, b = [QPointF(p[0] * size.width(), p[1] * size.height()) for p in annotation.points]
    if annotation.kind == "note":
        return b
    return (a + b) / 2 + QPointF(0, -max(12, min(size.width(), size.height()) * .018))


def draw_annotations(painter: QPainter, size: QSize, annotations: list[Annotation],
                     variables: list[Variable], selected: str = "") -> None:
    painter.save()
    painter.setClipRect(QRectF(0, 0, size.width(), size.height()))
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = max(.65, min(size.width(), size.height()) / 900)
    font = QFont("Segoe UI")
    font.setPixelSize(max(12, int(19 * scale)))
    painter.setFont(font)
    for annotation in annotations:
        color = QColor("#c84912" if annotation.id == selected else "#005ab5")
        painter.setPen(QPen(color, max(1.5, 2.4 * scale)))
        painter.setBrush(color)
        a, b = [QPointF(p[0] * size.width(), p[1] * size.height()) for p in annotation.points]
        painter.drawLine(a, b)
        if annotation.kind in {"dimension", "note"}:
            angle = math.atan2(b.y() - a.y(), b.x() - a.x())
            length = max(6, 10 * scale)
            tips = [(a, angle)] if annotation.kind == "note" else [(a, angle), (b, angle + math.pi)]
            for tip, direction in tips:
                painter.drawPolygon(QPolygonF([tip, tip + QPointF(math.cos(direction + .4), math.sin(direction + .4)) * length,
                                              tip + QPointF(math.cos(direction - .4), math.sin(direction - .4)) * length]))
            if annotation.kind == "dimension":
                normal = QPointF(-math.sin(angle), math.cos(angle)) * (8 * scale)
                painter.drawLine(a - normal, a + normal)
                painter.drawLine(b - normal, b + normal)
        label = annotation_label(annotation, variables)
        if label:
            anchor = label_position(annotation, size)
            rect = painter.fontMetrics().boundingRect(label)
            box = QRectF(anchor.x() - rect.width() / 2 - 5 * scale, anchor.y() - rect.height(), rect.width() + 10 * scale, rect.height() + 5 * scale)
            # Keep the label inside the raster; the underlying anchor is unchanged.
            box.moveLeft(max(0, min(box.left(), max(0, size.width() - box.width()))))
            box.moveTop(max(0, min(box.top(), max(0, size.height() - box.height()))))
            painter.fillRect(box, QColor(255, 255, 255, 238))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, label)
        if annotation.id == selected:
            painter.setBrush(QColor("white"))
            painter.drawEllipse(a, 5 * scale, 5 * scale)
            painter.drawEllipse(b, 5 * scale, 5 * scale)
    painter.restore()


def annotated_image(image: QImage, reference: Reference, variables: list[Variable]) -> QImage:
    result = image.convertToFormat(QImage.Format.Format_ARGB32)
    painter = QPainter(result)
    draw_annotations(painter, result.size(), display_annotations(reference), variables)
    painter.end()
    return result

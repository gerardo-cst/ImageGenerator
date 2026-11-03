from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import tempfile

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QImage


def data_root() -> Path:
    base = os.environ.get("CST_RENDERAI_DATA") or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    root = Path(base)
    root.mkdir(parents=True, exist_ok=True)
    return root


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def configure_logging() -> None:
    handler = RotatingFileHandler(data_root() / "diagnostics.log", maxBytes=3_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def safe_name(name: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")[:100]
    if not value or value.upper().split(".")[0] in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
        return "Oggetto"
    return value


def save_output(image_path: Path, directory: Path, name: str, extension: str = "png") -> Path:
    """Exclusive creation prevents overwrites even across concurrent app instances."""
    image = QImage(str(image_path))
    if image.isNull():
        raise ValueError("Il risultato non è un'immagine valida")
    directory.mkdir(parents=True, exist_ok=True)
    if extension not in {"png", "jpg"}:
        raise ValueError("Formato di esportazione non supportato")
    if extension == "jpg":
        from PySide6.QtGui import QPainter
        from PySide6.QtCore import Qt
        flattened = QImage(image.size(), QImage.Format.Format_RGB32)
        flattened.fill(Qt.GlobalColor.white)
        painter = QPainter(flattened)
        painter.drawImage(0, 0, image)
        painter.end()
        image = flattened
    base = safe_name(name) + "_generated"
    for index in range(100000):
        suffix = "" if index == 0 else f"_{index:02d}"
        path = directory / f"{base}{suffix}.{extension}"
        try:
            with path.open("xb"):
                pass
        except FileExistsError:
            continue
        try:
            if not image.save(str(path), extension.upper(), 96):
                raise OSError("Impossibile salvare l'immagine")
            return path
        except Exception:
            path.unlink(missing_ok=True)
            raise
    raise OSError("Troppi output con lo stesso nome")

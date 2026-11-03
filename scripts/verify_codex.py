"""Explicit live CLI test with a synthetic, non-confidential reference.

Run from repository root: python -m scripts.verify_codex
This sends only a generated drawing to Codex and uses included account limits.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
from cst_renderai.backend import CodexBackend
from cst_renderai.models import Project
from cst_renderai.documents import import_document

app = QApplication.instance() or QApplication([])
root = Path(".test-data/live-cli").resolve()
root.mkdir(parents=True, exist_ok=True)
image = QImage(640, 480, QImage.Format.Format_RGB32)
image.fill(0xffffffff)
painter = QPainter(image)
painter.drawRect(200, 150, 240, 180)
painter.drawEllipse(270, 80, 100, 100)
painter.end()
source = root / "synthetic_reference.png"
image.save(str(source))
project = Project(name="Verifica_sintetica", technical={"Materiale principale": "AISI 316L", "Finitura": "satinata"})
project.references = import_document(source, root / "references")
try:
    result = CodexBackend(timeout=180).generate(project, root / "jobs", threading.Event(), lambda message: print(message, flush=True))
    print("IMMAGINI REALI:", [str(p) for p in result.images], flush=True)
except Exception as exc:
    print("VERIFICA NON RIUSCITA:", exc, flush=True)
    raise SystemExit(1)

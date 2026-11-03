"""Offline diagnostics for a packaged Windows installation."""
from pathlib import Path
import os
import tempfile
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPdfWriter, QPainter
from .documents import load_pdf, import_document
from .models import Project
from .storage import atomic_json, save_output


def smoke(report: Path) -> int:
    from .window import MainWindow
    from PySide6.QtWidgets import QApplication
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=report.parent) as tmp:
            root = Path(tmp)
            previous_data = os.environ.get("CST_RENDERAI_DATA")
            os.environ["CST_RENDERAI_DATA"] = str(root / "appdata")
            image = QImage(160, 120, QImage.Format.Format_RGB32)
            image.fill(0xffddeeff)
            image.save(str(root / "input.jpg"), "JPG")
            writer = QPdfWriter(str(root / "drawing.pdf"))
            painter = QPainter(writer)
            painter.drawRect(100, 100, 400, 300)
            writer.newPage()
            painter.drawEllipse(100, 100, 400, 300)
            painter.end()
            del writer
            refs = import_document(root / "drawing.pdf", root / "cache", [0, 1])
            refs += import_document(root / "input.jpg", root / "cache")
            window = MainWindow()
            window.project = Project(name="Diagnostica", references=refs, technical={"Materiale principale": "AISI 316L", "Diametro esterno": "150", "Finitura": "satinata"})
            window.load_form()
            window.show()
            QApplication.processEvents()
            result = save_output(root / "input.jpg", root / "outputs", "Diagnostica")
            window.output_view.show_image(QImage(str(result)))
            QApplication.processEvents()
            # Avoid persisting diagnostic fixtures into the user's current project.
            window.project = Project()
            window.close()
            if previous_data is None:
                os.environ.pop("CST_RENDERAI_DATA", None)
            else:
                os.environ["CST_RENDERAI_DATA"] = previous_data
            atomic_json(report, {"ok": True, "references": len(refs), "pdf_pages": 2, "output": result.name, "gui": True})
            return 0
    except Exception as exc:
        atomic_json(report, {"ok": False, "error": str(exc)})
        return 1

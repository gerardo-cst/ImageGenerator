import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from cst_renderai.window import MainWindow
from cst_renderai.models import Project, Variable
from cst_renderai.backend import AssistedBackend
from cst_renderai.documents import import_document

app = QApplication.instance() or QApplication([])


class GuiTests(unittest.TestCase):
    def test_form_history_output_and_batch(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CST_RENDERAI_DATA": tmp}):
            window = MainWindow()
            window.show()
            app.processEvents()
            source = Path(tmp) / "Valvola.jpg"
            image = QImage(120, 100, QImage.Format.Format_RGB32)
            image.fill(0xffaabbcc)
            image.save(str(source))
            window.project.references = import_document(source, Path(tmp) / "references")
            window.load_form()
            window.name.setText("Valvola_DN150")
            window.fields["Materiale principale"].setText("AISI 316L")
            window.project.variables = [Variable("Diametro esterno", "150", "mm")]
            window.load_form()
            window.name.setText("Valvola_DN150")
            window.fields["Materiale principale"].setText("AISI 316L")
            window.fields["Finitura"].setText("satinata")
            window.sync_form()
            window.enqueue()
            self.assertEqual(len(window.queue), 1)
            window.queue.clear()
            snapshot = window.project.to_dict()
            result = AssistedBackend().generate(window.project, Path(tmp) / "jobs", threading.Event(), lambda _: None)
            attempt = {"time": "test", "status": "Importato", "outputs": [], "parameters": snapshot, "job": str(result.job)}
            window.project.attempts.append(attempt)
            window.accept_output(source, attempt)
            window.persist()
            window.load_form()
            window.history.setCurrentRow(0)
            app.processEvents()
            self.assertEqual(window.last_result.name, "Valvola_DN150_generated.png")
            self.assertEqual(len(attempt["outputs"]), 1)
            window.restore_attempt()
            self.assertEqual(window.fields["Materiale principale"].text(), "AISI 316L")
            self.assertTrue((Path(tmp) / "projects" / (window.project.id + ".json")).exists())
            window.close()


if __name__ == "__main__":
    unittest.main()

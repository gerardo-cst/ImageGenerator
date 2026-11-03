import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

from PySide6.QtCore import QSizeF
from PySide6.QtGui import QImage, QPainter, QPdfWriter, QPageSize, QFontDatabase, QFont
from PySide6.QtWidgets import QApplication

from cst_renderai.models import Project, Reference
from cst_renderai.documents import import_document, prepare_image, page_selection, validate
from cst_renderai.prompts import build_prompt, warnings
from cst_renderai.storage import save_output, safe_name
from cst_renderai.backend import AssistedBackend, CodexBackend, child_environment

app = QApplication.instance() or QApplication([])
if Path("C:/Windows/Fonts/segoeui.ttf").exists():
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    app.setFont(QFont("Segoe UI", 10))


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root / "Valvola.jpg"
        image = QImage(400, 240, QImage.Format.Format_RGB32)
        image.fill(0xffdddddd)
        image.save(str(self.image), "JPG")

    def tearDown(self):
        self.temp.cleanup()

    def project(self):
        p = Project(name="Valvola_DN150")
        p.references = import_document(self.image, self.root / "cache")
        p.technical = {"Materiale principale": "AISI 316L", "Diametro esterno": "150", "Finitura": "satinata"}
        return p

    def test_image_reference_crop_rotate(self):
        ref = self.project().references[0]
        ref.rotation = 90
        ref.crop = [0, 0, .5, 1]
        result = prepare_image(ref)
        self.assertEqual((result.width(), result.height()), (120, 400))
        self.assertEqual(QImage(ref.image).width(), 400)

    def test_pages(self):
        self.assertEqual(page_selection("1,3-5,3", 5), [0, 2, 3, 4])
        for invalid in ["0", "2-1", "1-6", "abc", "1-2-3"]:
            with self.assertRaises(ValueError):
                page_selection(invalid, 5)

    def make_pdf(self):
        path = self.root / "Valvola_DN150.pdf"
        writer = QPdfWriter(str(path))
        writer.setResolution(72)
        writer.setPageSize(QPageSize(QSizeF(100, 80), QPageSize.Unit.Millimeter))
        painter = QPainter(writer)
        painter.drawText(20, 40, "Diametro esterno: 150 mm")
        painter.drawRect(30, 60, 130, 90)
        writer.newPage()
        painter.drawText(20, 40, "AISI 316L vista superiore")
        painter.end()
        del writer
        return path

    def test_pdf_multiple_pages_and_jpg_end_to_end_assisted(self):
        p = Project(name="Valvola_DN150")
        p.references = import_document(self.make_pdf(), self.root / "cache", [0, 1])
        p.references += import_document(self.image, self.root / "cache")
        self.assertEqual(len(p.references), 3)
        self.assertIn("150", p.references[0].context)
        p.technical = {"Materiale principale": "AISI 316L", "Diametro esterno": "150", "Finitura": "satinata"}
        result = AssistedBackend().generate(p, self.root / "jobs", threading.Event(), lambda _: None)
        self.assertEqual(len(list(result.job.glob("reference_*.png"))), 3)
        prompt = (result.job / "prompt.txt").read_text(encoding="utf-8")
        for text in ["AISI 316L", "150", "satinata", "Bianco"]:
            self.assertIn(text, prompt)
        self.assertEqual(result.images, [])  # never claim the package is a render
        first = save_output(self.image, self.root, p.name)
        second = save_output(self.image, self.root, p.name)
        self.assertEqual(first.name, "Valvola_DN150_generated.png")
        self.assertEqual(second.name, "Valvola_DN150_generated_01.png")
        p.notes = "Luce più morbida, mantenere geometria"
        next_result = AssistedBackend().generate(p, self.root / "jobs", threading.Event(), lambda _: None)
        self.assertNotEqual(result.job, next_result.job)
        self.assertIn(p.notes, (next_result.job / "prompt.txt").read_text(encoding="utf-8"))

    def test_docx_embedded_images(self):
        path = self.root / "oggetto.docx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Acciaio satinato</w:t></w:r></w:p></w:body></w:document>')
            z.write(self.image, "word/media/image1.jpeg")
        refs = import_document(path, self.root / "cache")
        self.assertEqual(len(refs), 1)
        self.assertIn("Acciaio", refs[0].context)

    def test_corrupt_and_unsupported(self):
        for name in ["bad.pdf", "bad.jpg", "bad.docx", "bad.exe"]:
            path = self.root / name
            path.write_bytes(b"not a document")
            with self.assertRaises(Exception):
                import_document(path, self.root / "cache")

    def test_prompt_roles_and_conflict(self):
        p = self.project()
        p.references[0].context = "Diametro esterno: 180 mm"
        self.assertTrue(warnings(p))
        p.references[0].role = "Materiale / stile"
        self.assertIn("geometrico", warnings(p)[0])
        self.assertIn("MAI la geometria", build_prompt(p))

    def test_project_roundtrip(self):
        p = self.project()
        p.custom = [["Guarnizioni", "PTFE"]]
        path = self.root / "project.json"
        p.save(path)
        self.assertEqual(p.to_dict(), Project.load(path).to_dict())

    def test_portable_project_keeps_references_after_move(self):
        import shutil
        p = self.project()
        snapshot = p.to_dict()
        p.attempts = [{"parameters": snapshot, "outputs": [str(self.image)], "archived_outputs": [str(self.image)]}]
        destination = self.root / "portable"
        destination.mkdir()
        p.export(destination / "object.cst.json")
        moved = self.root / "moved"
        shutil.move(str(destination), moved)
        loaded = Project.load(moved / "object.cst.json")
        self.assertTrue(Path(loaded.references[0].image).is_file())
        self.assertTrue(Path(loaded.attempts[0]["archived_outputs"][0]).is_file())
        self.assertTrue(Path(loaded.attempts[0]["parameters"]["references"][0]["image"]).is_file())

    def test_project_id_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            Project.from_dict({"id": "../../other"})

    def test_cancel_preparation_cleans_partial_job(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(InterruptedError):
            AssistedBackend().generate(self.project(), self.root / "jobs", cancel, lambda _: None)
        self.assertEqual(list((self.root / "jobs").iterdir()), [])

    def test_output_jpeg_alpha(self):
        png = self.root / "alpha.png"
        img = QImage(12, 12, QImage.Format.Format_ARGB32)
        img.fill(0)
        img.save(str(png))
        out = save_output(png, self.root, "alpha", "jpg")
        self.assertGreater(QImage(str(out)).pixelColor(0, 0).red(), 245)
        self.assertEqual(safe_name("CON"), "Oggetto")
        self.assertNotIn("/", safe_name("../valvola"))

    def test_environment_does_not_pass_api_keys(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake", "CODEX_API_KEY": "fake"}):
            self.assertNotIn("OPENAI_API_KEY", child_environment())
            self.assertNotIn("CODEX_API_KEY", child_environment())

    def test_cli_missing_does_not_simulate(self):
        with patch("cst_renderai.backend.codex_command", side_effect=RuntimeError("CLI non trovata")):
            with self.assertRaisesRegex(RuntimeError, "CLI non trovata"):
                CodexBackend().generate(self.project(), self.root / "jobs", threading.Event(), lambda _: None)
        self.assertFalse(list((self.root / "jobs").glob("*/result_*.png")))


if __name__ == "__main__":
    unittest.main()

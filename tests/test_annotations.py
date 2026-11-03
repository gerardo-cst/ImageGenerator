import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from cst_renderai.models import Project, Reference, Annotation, Variable
from cst_renderai.annotations import to_display, to_original, display_annotations, annotated_image, annotation_label
from cst_renderai.backend import AssistedBackend, GenerationResult
from cst_renderai.documents import import_document, prepare_image
from cst_renderai.prompts import build_prompt, warnings
from cst_renderai.window import MainWindow
from cst_renderai.viewer import ImageViewer
from cst_renderai.storage import save_png_exclusive

app = QApplication.instance() or QApplication([])


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"CST_RENDERAI_DATA": str(self.root / "data")})
        self.env.start()
        self.image = QImage(800, 600, QImage.Format.Format_RGB32)
        self.image.fill(0xffffffff)
        self.source = self.root / "reference.png"
        self.image.save(str(self.source))
        self.variable = Variable("Diametro esterno", "150", "mm")
        self.project = Project(name="Test", variables=[self.variable])
        self.project.references = import_document(self.source, self.root / "references")
        self.ref = self.project.references[0]
        self.note = Annotation("dimension", [[.2, .5], [.8, .5]], self.variable.id)
        self.ref.annotations.append(self.note)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_rotate_crop_coordinates_preserve_original(self):
        for rotation in (0, 90, 180, 270):
            self.ref.rotation = rotation
            self.ref.crop = [.1, .2, .7, .6]
            original = [.3, .4]
            result = to_original(to_display(original, self.ref), self.ref)
            self.assertAlmostEqual(result[0], original[0])
            self.assertAlmostEqual(result[1], original[1])
        self.assertEqual(self.note.points, [[.2, .5], [.8, .5]])

    def test_annotation_does_not_modify_original_and_updates_value(self):
        original = prepare_image(self.ref)
        first = annotated_image(original, self.ref, self.project.variables)
        self.assertNotEqual(first, original)
        self.assertEqual(original.pixelColor(400, 300).name(), "#ffffff")
        self.variable.value = "180"
        self.assertIn("180 mm", annotation_label(self.note, self.project.variables))
        second = annotated_image(original, self.ref, self.project.variables)
        self.assertNotEqual(first, second)
        self.assertEqual(QImage(str(self.source)), original)

    def test_job_has_clean_and_annotated_references_with_correct_order(self):
        self.project.references += import_document(self.source, self.root / "other")
        result = AssistedBackend().generate(self.project, self.root / "jobs", threading.Event(), lambda _: None)
        self.assertEqual([p.name for p in sorted(result.job.glob("reference_*.png"))], ["reference_01.png", "reference_01_notes.png", "reference_02.png"])
        self.assertEqual(QImage(str(result.job / "reference_01.png")), self.image)
        self.assertNotEqual(QImage(str(result.job / "reference_01_notes.png")), self.image)
        prompt = (result.job / "prompt.txt").read_text(encoding="utf-8")
        for text in ["Immagine 2 (reference_01_notes.png)", "Immagine 3 (reference_02.png)", "150 mm", "NON riprodurre quote", "fotografia reale"]:
            self.assertIn(text, prompt)

    def test_persistence_retains_links_and_migrates_legacy(self):
        path = self.root / "project.json"
        self.project.save(path)
        loaded = Project.load(path)
        self.assertEqual(loaded.references[0].annotations[0].variable_id, loaded.variables[0].id)
        self.assertEqual(loaded.references[0].annotations[0].points, self.note.points)
        legacy = Project.from_dict({"technical": {"Altezza": "200", "Materiale principale": "AISI 316L"}, "custom": [["Guarnizione", "PTFE"]]})
        self.assertNotIn("Altezza", legacy.technical)
        self.assertEqual([v.name for v in legacy.variables], ["Altezza", "Guarnizione"])
        self.assertEqual(legacy.technical["Materiale principale"], "AISI 316L")

    def test_invalid_annotations_and_broken_links_are_rejected(self):
        with self.assertRaises(ValueError):
            Annotation(points=[[float('nan'), 0], [1, 1]])
        self.note.variable_id = "missing"
        self.assertTrue(any("scollegata" in message for message in warnings(self.project)))

    def test_export_does_not_overwrite(self):
        image = annotated_image(self.image, self.ref, self.project.variables)
        first = save_png_exclusive(image, self.root / "notes.png")
        second = save_png_exclusive(image, self.root / "notes.png")
        self.assertEqual(first.name, "notes.png")
        self.assertEqual(second.name, "notes_01.png")

    def test_viewer_mouse_draw_and_drag_endpoints(self):
        viewer = ImageViewer()
        viewer.resize(800, 600)
        viewer.show_image(self.image)
        viewer.show()
        app.processEvents()
        viewer.fit()
        created = []
        viewer.annotation_created.connect(lambda kind, points: created.append((kind, points)))
        viewer.set_tool("dimension")
        start = viewer.mapFromScene(QPointF(160, 300))
        end = viewer.mapFromScene(QPointF(640, 300))
        QTest.mousePress(viewer.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(viewer.viewport(), end)
        QTest.mouseRelease(viewer.viewport(), Qt.MouseButton.LeftButton, pos=end)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0][0], "dimension")
        self.assertAlmostEqual(created[0][1][1][0], .8, places=2)
        viewer.set_annotations([self.note], [self.variable])
        viewer.set_tool("navigate")
        moved = []
        viewer.annotation_changed.connect(lambda note_id, points: moved.append((note_id, points)))
        new_end = viewer.mapFromScene(QPointF(720, 300))
        QTest.mousePress(viewer.viewport(), Qt.MouseButton.LeftButton, pos=end)
        QTest.mouseMove(viewer.viewport(), new_end)
        QTest.mouseRelease(viewer.viewport(), Qt.MouseButton.LeftButton, pos=new_end)
        self.assertEqual(moved[0][0], self.note.id)
        self.assertAlmostEqual(moved[0][1][1][0], .9, places=2)
        viewer.close()

    def test_gui_variable_rename_link_undo_and_one_click_generation(self):
        window = MainWindow()
        window.project = self.project
        window.load_form()
        window.show()
        app.processEvents()
        self.assertNotIn("Altezza", window.fields)
        self.assertEqual(window.backend.currentIndex(), 1)
        window.custom.item(0, 0).setText("Diametro piastra")
        window.custom.item(0, 1).setText("175")
        self.assertIn("Diametro piastra = 175 mm", annotation_label(self.note, self.project.variables))
        self.assertEqual(self.note.variable_id, self.project.variables[0].id)
        window.annotation_variable.setCurrentIndex(1)
        window.create_annotation("note", [[.4, .3], [.7, .2]])
        self.assertEqual(len(self.ref.annotations), 2)
        window.undo_annotation()
        self.assertEqual(len(self.ref.annotations), 1)
        window.redo_annotation()
        self.assertEqual(len(self.ref.annotations), 2)
        def fake_service(project, jobs, cancel, progress):
            result = AssistedBackend().generate(project, jobs, cancel, progress)
            return GenerationResult(result.job, [self.source], "Test backend")
        with patch("cst_renderai.window.CodexBackend.generate", side_effect=fake_service) as backend, patch("cst_renderai.window.QMessageBox.question") as question:
            QTest.mouseClick(window.generate_button, Qt.MouseButton.LeftButton)
            for _ in range(200):
                app.processEvents()
                if window.worker is None:
                    break
                QTest.qWait(10)
            self.assertIsNone(window.worker)
            backend.assert_called_once()
            question.assert_not_called()
            self.assertTrue(window.last_result.exists())
            self.assertEqual(window.project.attempts[-1]["status"], "Generato")
        window.close()

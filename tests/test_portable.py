import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from cst_renderai.storage import data_root, portable_profile, asset_path
from cst_renderai.window import MainWindow

app = QApplication.instance() or QApplication([])


class PortableTests(unittest.TestCase):
    def test_portable_data_is_inside_application_for_each_pc_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "portable.ini").write_text("[CST RenderAI]\nportable=true")
            environment = {k: v for k, v in os.environ.items() if k != "CST_RENDERAI_DATA"}
            with patch.dict(os.environ, environment, clear=True), patch("cst_renderai.storage.application_directory", return_value=root):
                with patch("cst_renderai.storage.socket.gethostname", return_value="PC-1"), patch("cst_renderai.storage.getpass.getuser", return_value="mario"):
                    first = data_root()
                    self.assertEqual(first.parent, root / "data")
                    self.assertTrue(first.exists())
                with patch("cst_renderai.storage.socket.gethostname", return_value="PC-2"), patch("cst_renderai.storage.getpass.getuser", return_value="mario"):
                    self.assertNotEqual(first, data_root())

    def test_environment_override_still_supported(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CST_RENDERAI_DATA": tmp}):
            self.assertEqual(data_root(), Path(tmp))

    def test_maximized_can_be_restored_and_resized_with_icon(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CST_RENDERAI_DATA": tmp}):
            app.setWindowIcon(QIcon(str(asset_path("app.ico"))))
            window = MainWindow()
            window.showMaximized()
            app.processEvents()
            self.assertTrue(window.isMaximized())
            self.assertFalse(window.windowIcon().isNull())
            self.assertTrue(window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint)
            window.showNormal()
            window.resize(1100, 700)
            app.processEvents()
            self.assertFalse(window.isMaximized())
            self.assertEqual(window.width(), 1100)
            self.assertEqual(Path(window.settings.fileName()).parent, Path(tmp))
            window.close()

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from cst_renderai.models import Project
from cst_renderai.documents import import_document
from cst_renderai.backend import CodexBackend

app = QApplication.instance() or QApplication([])


class BackendTests(unittest.TestCase):
    def test_api_login_is_rejected_before_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = QImage(64, 64, QImage.Format.Format_RGB32)
            image.fill(0xffffffff)
            image.save(str(root / "source.png"))
            p = Project(references=import_document(root / "source.png", root / "refs"))
            with patch("cst_renderai.backend.codex_command", return_value=["codex"]), patch("cst_renderai.backend.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "Logged in using an API key", "")), patch("cst_renderai.backend.subprocess.Popen") as run:
                with self.assertRaisesRegex(RuntimeError, "ChatGPT non confermata"):
                    CodexBackend().generate(p, root / "jobs", threading.Event(), lambda _: None)
                run.assert_not_called()

    def test_cli_success_without_image_is_error(self):
        class Input:
            def write(self, value): pass
            def close(self): pass
        class Process:
            stdin = Input()
            returncode = 0
            def poll(self): return 0
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = QImage(64, 64, QImage.Format.Format_RGB32)
            image.fill(0xffffffff)
            image.save(str(root / "source.png"))
            p = Project(references=import_document(root / "source.png", root / "refs"))
            with patch("cst_renderai.backend.codex_command", return_value=["codex"]), patch("cst_renderai.backend.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "Logged in using ChatGPT", "")), patch("cst_renderai.backend.subprocess.Popen", return_value=Process()):
                with self.assertRaisesRegex(RuntimeError, "non ha prodotto un'immagine"):
                    CodexBackend().generate(p, root / "jobs", threading.Event(), lambda _: None)


if __name__ == "__main__":
    unittest.main()

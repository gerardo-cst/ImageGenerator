from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import QLockFile
from .storage import configure_logging, data_root, asset_path


def main() -> int:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CST.RenderAI")
    app = QApplication(sys.argv)
    app.setApplicationName("CST RenderAI")
    app.setOrganizationName("CST")
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(asset_path("app.ico"))))
    try:
        configure_logging()
    except OSError as exc:
        QMessageBox.critical(None, "Cartella dati non scrivibile", "Impossibile scrivere i dati dell'applicazione. Per l'uso portatile in rete concedere accesso in lettura e scrittura alla cartella deploy/data.\n\n" + str(exc))
        return 1
    if "--diagnostics" in sys.argv:
        from pathlib import Path
        from .diagnostics import smoke
        index = sys.argv.index("--diagnostics")
        if index + 1 >= len(sys.argv):
            return 2
        return smoke(Path(sys.argv[index + 1]).resolve())
    instance_lock = QLockFile(str(data_root() / "application.lock"))
    if not instance_lock.tryLock(0):
        QMessageBox.information(None, "CST RenderAI già aperto", "CST RenderAI è già aperto per questo utente su questo PC, oppure la cartella dati non è scrivibile.")
        return 1
    from .window import MainWindow
    window = MainWindow()
    # Maximized keeps the native title bar, restore button and resizable borders.
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

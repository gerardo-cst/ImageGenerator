from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from .storage import configure_logging


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CST RenderAI")
    app.setOrganizationName("CST")
    app.setStyle("Fusion")
    configure_logging()
    if "--diagnostics" in sys.argv:
        from pathlib import Path
        from .diagnostics import smoke
        index = sys.argv.index("--diagnostics")
        if index + 1 >= len(sys.argv):
            return 2
        return smoke(Path(sys.argv[index + 1]).resolve())
    from .window import MainWindow
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

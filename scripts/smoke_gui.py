import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CST_RENDERAI_DATA"] = str(__import__('pathlib').Path('.test-data/gui').resolve())
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont
from cst_renderai.window import MainWindow
from cst_renderai.documents import import_document
from cst_renderai.models import Project
from cst_renderai.prompts import build_prompt

app = QApplication([])
if Path("C:/Windows/Fonts/segoeui.ttf").exists():
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    app.setFont(QFont("Segoe UI", 10))
window = MainWindow()
window.project = Project(name="Flangia_DN150", technical={"Materiale principale": "AISI 316L", "Diametro esterno": "150", "Diametro interno": "60", "Spessore": "15", "Finitura": "satinata"})
window.project.references = import_document(Path("examples/Flangia_DN150.pdf"), Path(os.environ["CST_RENDERAI_DATA"]) / "references", [0, 1])
window.project.references += import_document(Path("examples/Flangia_DN150_frontale.jpg"), Path(os.environ["CST_RENDERAI_DATA"]) / "references")
window.project.references[0].role = "Frontale"
window.project.references[1].role = "Laterale"
window.project.references[2].role = "Frontale"
window.project.output_dir = str(Path(".test-data/gui/outputs").resolve())
window.load_form()
actual_render = Path("examples/Flangia_DN150_generated.png")
if actual_render.exists():
    window.sync_form()
    snapshot = window.project.to_dict()
    snapshot["attempts"] = []
    attempt = {"time": "2026-11-03", "status": "Importato · image_gen integrato", "backend": "Assistito", "parameters": snapshot, "outputs": [], "prompt": build_prompt(window.project)}
    window.project.attempts.append(attempt)
    window.accept_output(actual_render, attempt)
    window.persist()
    window.project.export(Path("examples/Flangia_DN150.cst.json").resolve())
window.show()
app.processEvents()
window.fit_views()
output = Path("docs/screenshots")
output.mkdir(parents=True, exist_ok=True)
window.grab().save(str(output / "desktop.png"))
window.close()
print("Qt smoke e screenshot completati")

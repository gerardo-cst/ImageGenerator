from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import shutil

from PySide6.QtCore import Qt, QSettings, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QImage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit, QPlainTextEdit,
    QComboBox, QFormLayout, QScrollArea, QCheckBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QTabWidget, QFileDialog, QMessageBox, QInputDialog,
    QProgressBar, QGroupBox,
)

from .backend import AssistedBackend, CodexBackend, GenerationResult
from .documents import import_document, load_pdf, page_selection, prepare_image, checked_image
from .models import Project, Reference, ROLES, MODES, TECH_FIELDS
from .prompts import build_prompt, warnings
from .storage import data_root, save_output
from .viewer import ImageViewer
from .workers import Worker

STYLE = """
QMainWindow, QWidget { background:#f5f6f8; color:#202630; font-family:'Segoe UI'; font-size:12px; }
QMenuBar, QToolBar { background:#fff; border-bottom:1px solid #dce0e6; spacing:6px; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QListWidget, QTableWidget { background:#fff; border:1px solid #cdd3dd; border-radius:4px; padding:4px; selection-background-color:#dcecff; selection-color:#173658; }
QPushButton { background:#fff; border:1px solid #cbd2dc; border-radius:4px; padding:6px 9px; }
QPushButton:hover { background:#e5effc; border-color:#5b9ad6; }
QPushButton:disabled { color:#9298a1; }
QPushButton#primary { background:#0067b8; color:white; border:0; font-weight:600; }
QGroupBox { border:1px solid #dce0e6; border-radius:5px; margin-top:12px; padding:8px; }
QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 4px; font-weight:600; }
QTabBar::tab { padding:8px 12px; background:#edf0f4; }
QTabBar::tab:selected { background:#fff; border-bottom:2px solid #0067b8; }
QSplitter::handle { background:#dce0e6; width:2px; }
QStatusBar { background:#e9f1fa; } QProgressBar { max-height:10px; border:0; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CST RenderAI")
        self.resize(1440, 900)
        self.setMinimumSize(1040, 680)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE)
        self.settings = QSettings("CST", "RenderAI")
        self.project = Project()
        self.project_path: Path | None = None
        self.worker: Worker | None = None
        self.last_result: Path | None = None
        self.queue: list[dict] = []
        self.pending_imports: list[tuple[Path, list[int] | None]] = []
        self.current_job: Path | None = None
        self.current_attempt: dict | None = None
        self._building = False
        self._build()
        self._menus()
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        autosave = data_root() / "autosave.json"
        if autosave.exists():
            try:
                self.project = Project.load(autosave)
            except Exception:
                logging.exception("Ripristino autosave fallito")
        self.load_form()
        self.statusBar().showMessage("Pronto · elaborazione locale finché non avvii esplicitamente Codex")

    def button(self, text: str, callback, layout) -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(callback)
        layout.addWidget(b)
        return b

    def combo(self, values: list[str], editable: bool = False) -> QComboBox:
        box = QComboBox()
        box.addItems(values)
        box.setEditable(editable)
        return box

    def _build(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(8, 6, 8, 6)
        header = QHBoxLayout()
        title = QLabel("CST RenderAI")
        title.setStyleSheet("font-size:20px;font-weight:600;color:#005a9e")
        header.addWidget(title)
        header.addWidget(QLabel("Render industriali da documentazione tecnica"), 1)
        self.button("Nuovo oggetto", self.new_project, header)
        self.button("Apri progetto", self.open_project, header)
        self.button("Salva progetto", self.save_project, header)
        outer.addLayout(header)
        splitter = QSplitter()
        outer.addWidget(splitter, 1)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(2, 2, 6, 2)
        ll.addWidget(QLabel("RIFERIMENTI · spunta quelli da utilizzare"))
        row = QHBoxLayout()
        self.button("+ Importa", self.choose_files, row)
        self.button("Rimuovi", self.remove_reference, row)
        ll.addLayout(row)
        self.refs = QListWidget()
        self.refs.currentRowChanged.connect(self.reference_changed)
        self.refs.itemChanged.connect(self.reference_checked)
        ll.addWidget(self.refs, 1)
        ll.addWidget(QLabel("Ruolo della vista selezionata"))
        self.role = self.combo(ROLES)
        self.role.currentTextChanged.connect(self.role_changed)
        ll.addWidget(self.role)
        self.button("Usa come documento principale", self.set_primary, ll)
        info = QLabel("PDF: scegli pagine e poi ritaglia.\nWord: seleziona le immagini estratte.\nTrascina qui PDF, DOCX o immagini.")
        info.setWordWrap(True)
        ll.addWidget(info)
        splitter.addWidget(left)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(4, 2, 4, 2)
        self.tabs = QTabWidget()
        cl.addWidget(self.tabs)
        compare = QWidget()
        vl = QVBoxLayout(compare)
        vl.setContentsMargins(2, 2, 2, 2)
        controls = QHBoxLayout()
        self.button("Adatta", self.fit_views, controls)
        self.button("Ruota 90°", self.rotate_reference, controls)
        self.button("Ritaglia regione", self.start_crop, controls)
        self.button("Ripristina", self.reset_reference, controls)
        self.compare_check = QCheckBox("Confronta affiancati")
        self.compare_check.setChecked(True)
        self.compare_check.toggled.connect(lambda enabled: self.output_container.setVisible(enabled))
        controls.addWidget(self.compare_check)
        vl.addLayout(controls)
        viewers = QSplitter()
        input_container = QWidget()
        il = QVBoxLayout(input_container)
        il.setContentsMargins(0, 0, 0, 0)
        il.addWidget(QLabel("DOCUMENTO · rotella per zoom, trascina per spostare"))
        self.input_view = ImageViewer()
        self.input_view.crop_selected.connect(self.apply_crop)
        il.addWidget(self.input_view)
        viewers.addWidget(input_container)
        self.output_container = QWidget()
        ol = QVBoxLayout(self.output_container)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(QLabel("RENDER · fedeltà visiva, geometria non certificata"))
        self.output_view = ImageViewer()
        self.output_choices = QComboBox()
        self.output_choices.currentTextChanged.connect(self.select_output)
        ol.addWidget(self.output_choices)
        ol.addWidget(self.output_view)
        viewers.addWidget(self.output_container)
        vl.addWidget(viewers)
        self.tabs.addTab(compare, "Anteprima e confronto")
        self.prompt_view = QPlainTextEdit()
        self.prompt_view.setReadOnly(True)
        self.tabs.addTab(self.prompt_view, "Istruzioni generate")
        self.context_view = QPlainTextEdit()
        self.context_view.setReadOnly(True)
        self.tabs.addTab(self.context_view, "Contesto documento")
        self.history = QListWidget()
        self.history.currentRowChanged.connect(self.history_selected)
        self.tabs.addTab(self.history, "Cronologia")
        batch = QWidget()
        bl = QVBoxLayout(batch)
        self.batch_list = QListWidget()
        bl.addWidget(self.batch_list)
        br = QHBoxLayout()
        self.button("Accoda oggetto corrente", self.enqueue, br)
        self.button("Aggiungi progetti…", self.enqueue_projects, br)
        self.button("Rimuovi selezionato", self.dequeue, br)
        self.button("Avvia coda", self.start_batch, br)
        bl.addLayout(br)
        self.tabs.addTab(batch, "Batch oggetti")
        splitter.addWidget(center)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(7, 2, 4, 2)
        obj = QGroupBox("Oggetto e vincoli tecnici")
        form = QFormLayout(obj)
        form.setSpacing(5)
        self.name = QLineEdit()
        form.addRow("Nome output", self.name)
        self.unit = self.combo(["mm", "cm", "m", "in"])
        form.addRow("Unità quote", self.unit)
        self.fields: dict[str, QLineEdit] = {}
        for field in TECH_FIELDS:
            edit = QLineEdit()
            edit.setPlaceholderText("Facoltativo")
            self.fields[field] = edit
            form.addRow(field, edit)
        rl.addWidget(obj)
        custom = QGroupBox("Caratteristiche personalizzate")
        cu = QVBoxLayout(custom)
        self.custom = QTableWidget(0, 2)
        self.custom.setHorizontalHeaderLabels(["Caratteristica", "Valore"])
        self.custom.horizontalHeader().setStretchLastSection(True)
        self.custom.setMaximumHeight(125)
        cu.addWidget(self.custom)
        cr = QHBoxLayout()
        self.button("+ Riga", lambda: self.custom.insertRow(self.custom.rowCount()), cr)
        self.button("− Riga", lambda: self.custom.removeRow(self.custom.currentRow()), cr)
        cu.addLayout(cr)
        rl.addWidget(custom)
        photo = QGroupBox("Resa fotografica")
        pf = QFormLayout(photo)
        self.mode = self.combo(MODES)
        self.view = self.combo(["Isometrica", "Frontale", "Laterale", "Superiore", "Prospettica"], True)
        self.background = self.combo(["Bianco", "Trasparente", "Industriale"])
        self.lighting = self.combo(["Studio", "Naturale"])
        self.resolution = self.combo(["Massima disponibile", "1024×1024", "2048×2048", "3840×2160"], True)
        self.aspect = self.combo(["1:1", "3:2", "16:9", "2:3", "9:16"])
        for label, box in [("Modalità", self.mode), ("Vista", self.view), ("Sfondo", self.background), ("Luce", self.lighting), ("Risoluzione richiesta", self.resolution), ("Rapporto", self.aspect)]:
            pf.addRow(label, box)
        self.shadows = QCheckBox("Ombre realistiche")
        self.pbr = QCheckBox("Materiali PBR")
        self.shadows.setChecked(True)
        self.pbr.setChecked(True)
        pf.addRow(self.shadows)
        pf.addRow(self.pbr)
        self.variants = QSpinBox()
        self.variants.setRange(1, 8)
        pf.addRow("Varianti", self.variants)
        pf.addRow(QLabel("Qualità: massima disponibile nel servizio"))
        rl.addWidget(photo)
        rl.addWidget(QLabel("Descrizione tecnica / modifiche per rigenerare"))
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(110)
        rl.addWidget(self.notes)
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Automatico: cartella documento principale")
        rl.addWidget(self.output_dir)
        self.button("Scegli cartella output…", self.choose_output, rl)
        rl.addStretch()
        scroll.setWidget(right)
        splitter.addWidget(scroll)
        splitter.setSizes([260, 760, 370])
        splitter.setStretchFactor(1, 1)

        bottom = QHBoxLayout()
        self.backend = self.combo(["Assistito · prepara pacchetto locale", "Codex CLI · ChatGPT (disponibilità da verificare)"])
        self.backend.setCurrentIndex(int(self.settings.value("backend", 0)))
        bottom.addWidget(self.backend)
        self.button("Aggiorna istruzioni", self.refresh_prompt, bottom)
        self.generate_button = self.button("Genera / prepara", self.generate, bottom)
        self.generate_button.setObjectName("primary")
        self.cancel_button = self.button("Annulla", self.cancel_operation, bottom)
        self.cancel_button.setEnabled(False)
        self.button("Importa risultato", self.import_result, bottom)
        self.button("Esporta PNG/JPG", self.export_result, bottom)
        outer.addLayout(bottom)
        notice = QLabel("Cloud: avviando Codex invii i riferimenti selezionati al servizio. Nessun invio durante l'importazione. Accuratezza dimensionale non garantita.")
        notice.setWordWrap(True)
        outer.addWidget(notice)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.statusBar().addPermanentWidget(self.progress)
        self.setCentralWidget(root)

    def _menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        for text, shortcut, callback in [("Nuovo", "Ctrl+N", self.new_project), ("Apri progetto", "Ctrl+O", self.open_project), ("Salva progetto", "Ctrl+S", self.save_project), ("Importa documenti", "Ctrl+I", self.choose_files)]:
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            file_menu.addAction(action)
        help_menu = self.menuBar().addMenu("Aiuto")
        for text, callback in [("Istruzioni d'uso", self.help), ("Apri dati e diagnostica", lambda: self.open_folder(data_root())), ("Apri ultimo pacchetto", self.open_job), ("Copia prompt", self.copy_prompt), ("Ripristina parametri tentativo", self.restore_attempt), ("Pulisci file temporanei", self.clean_cache)]:
            action = QAction(text, self)
            action.triggered.connect(callback)
            help_menu.addAction(action)

    def sync_form(self) -> None:
        p = self.project
        p.name = self.name.text().strip()
        p.technical = {k: v.text().strip() for k, v in self.fields.items()}
        p.unit = self.unit.currentText()
        p.custom = [[self.custom.item(row, col).text() if self.custom.item(row, col) else "" for col in range(2)] for row in range(self.custom.rowCount())]
        for name in ["mode", "view", "background", "lighting", "resolution", "aspect"]:
            setattr(p, name, getattr(self, name).currentText())
        p.shadows, p.pbr = self.shadows.isChecked(), self.pbr.isChecked()
        p.notes, p.variants = self.notes.toPlainText(), self.variants.value()
        p.output_dir = self.output_dir.text().strip()

    def load_form(self) -> None:
        self._building = True
        p = self.project
        self.name.setText(p.name)
        self.unit.setCurrentText(p.unit)
        for k, edit in self.fields.items():
            edit.setText(p.technical.get(k, ""))
        self.custom.setRowCount(len(p.custom))
        for row, values in enumerate(p.custom):
            for col, value in enumerate(values):
                self.custom.setItem(row, col, QTableWidgetItem(value))
        for name in ["mode", "view", "background", "lighting", "resolution", "aspect"]:
            getattr(self, name).setCurrentText(getattr(p, name))
        self.shadows.setChecked(p.shadows)
        self.pbr.setChecked(p.pbr)
        self.notes.setPlainText(p.notes)
        self.variants.setValue(p.variants)
        self.output_dir.setText(p.output_dir)
        self.refs.clear()
        for ref in p.references:
            item = QListWidgetItem(ref.label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if ref.selected else Qt.CheckState.Unchecked)
            item.setToolTip(ref.source + "\n" + ref.role)
            self.refs.addItem(item)
        self.history.clear()
        for attempt in p.attempts:
            self.history.addItem(f"{attempt['time']} · {attempt['status']} · {len(attempt.get('outputs', []))} output")
        self._building = False
        if p.references:
            self.refs.setCurrentRow(0)
        else:
            self.input_view.scene().clear()
            self.context_view.clear()
        self.prompt_view.setPlainText(build_prompt(p))

    def persist(self) -> None:
        self.sync_form()
        self.project.save(data_root() / "autosave.json")
        # Retain every batch object even after the next object replaces the form.
        self.project.save(data_root() / "projects" / (self.project.id + ".json"))

    def busy(self) -> bool:
        if self.worker is not None and self.worker.isRunning():
            self.statusBar().showMessage("Operazione in corso: attendere o annullare")
            return True
        return False

    def run_worker(self, action, done) -> None:
        if self.busy():
            return
        worker = Worker(action, self)
        self.worker = worker
        self.setAcceptDrops(False)
        self.generate_button.setEnabled(False)
        self.backend.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, 0)
        worker.progress.connect(self.statusBar().showMessage)
        # Only release/reuse a worker after its thread has actually finished.
        result: dict = {}
        worker.completed.connect(lambda value: result.update(value=value))
        worker.failed.connect(lambda message: result.update(error=message))
        def finished():
            self.worker = None
            self.setAcceptDrops(True)
            self.generate_button.setEnabled(True)
            self.backend.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            worker.deleteLater()
            if "error" in result:
                self.operation_failed(result["error"])
            elif "value" in result:
                try:
                    done(result["value"])
                except Exception as exc:
                    logging.exception("Completamento operazione fallito")
                    self.error(str(exc))
        worker.finished.connect(finished)
        worker.start()

    def error(self, text: str) -> None:
        self.statusBar().showMessage(text)
        QMessageBox.warning(self, "CST RenderAI", text)

    def operation_failed(self, text: str) -> None:
        self.queue.clear()
        self.pending_imports.clear()
        self.batch_list.clear()
        if self.current_attempt and self.current_attempt.get("status") == "In corso":
            self.current_attempt["status"] = "Annullato" if "annull" in text.lower() else "Errore"
            self.current_attempt["error"] = text
            self.persist()
            self.load_form()
        self.error(text)

    def cancel_operation(self) -> None:
        self.queue.clear()
        self.pending_imports.clear()
        self.batch_list.clear()
        if self.worker:
            self.worker.cancel.set()
            self.statusBar().showMessage("Annullamento richiesto… il lavoro cloud già inviato potrebbe proseguire")

    def choose_files(self) -> None:
        if self.busy():
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Importa riferimenti", "", "Documenti (*.pdf *.docx *.png *.jpg *.jpeg *.webp)")
        self.add_files([Path(p) for p in paths])

    def add_files(self, paths: list[Path]) -> None:
        if self.busy():
            return
        for path in paths:
            pages = None
            if path.suffix.lower() == ".pdf":
                try:
                    doc = load_pdf(path)
                    count = doc.pageCount()
                    doc.close()
                    value, ok = QInputDialog.getText(self, "Selezione pagine PDF", f"{path.name}: {count} pagine. Specifica es. 1,3-5", text="1")
                    if not ok:
                        continue
                    pages = page_selection(value, count)
                except Exception as exc:
                    self.error(str(exc))
                    continue
            self.pending_imports.append((path, pages))
        self.import_next()

    def import_next(self) -> None:
        if not self.pending_imports:
            return
        self.sync_form()
        path, pages = self.pending_imports.pop(0)
        cache = data_root() / "references"
        def done(refs):
            self.project.references.extend(refs)
            if not self.project.name:
                self.project.name = path.stem
            self.load_form()
            self.persist()
            self.statusBar().showMessage(f"Importati {len(refs)} riferimenti da {path.name}")
            self.import_next()
        self.run_worker(lambda cancel, progress: import_document(path, cache, pages, cancel.is_set, progress), done)

    def selected_ref(self) -> Reference | None:
        row = self.refs.currentRow()
        return self.project.references[row] if 0 <= row < len(self.project.references) else None

    def reference_changed(self, row: int) -> None:
        if self._building:
            return
        ref = self.selected_ref()
        if ref:
            self.role.blockSignals(True)
            self.role.setCurrentText(ref.role)
            self.role.blockSignals(False)
            self.context_view.setPlainText(ref.context or "Nessun testo estraibile. Le quote raster non sono lette automaticamente tramite OCR.")
            try:
                self.input_view.show_image(prepare_image(ref))
            except Exception as exc:
                self.error(str(exc))

    def reference_checked(self, item) -> None:
        if not self._building:
            row = self.refs.row(item)
            self.project.references[row].selected = item.checkState() == Qt.CheckState.Checked

    def role_changed(self, value: str) -> None:
        ref = self.selected_ref()
        if ref and not self._building:
            ref.role = value

    def remove_reference(self) -> None:
        if self.busy():
            return
        row = self.refs.currentRow()
        if row >= 0:
            self.sync_form()
            del self.project.references[row]
            self.load_form()

    def set_primary(self) -> None:
        if self.busy():
            return
        ref = self.selected_ref()
        if ref:
            self.sync_form()
            self.project.references.remove(ref)
            self.project.references.insert(0, ref)
            self.project.name = Path(ref.source).stem
            self.load_form()

    def rotate_reference(self) -> None:
        ref = self.selected_ref()
        if ref and not self.busy():
            ref.rotation = (ref.rotation + 90) % 360
            ref.crop = None
            self.reference_changed(self.refs.currentRow())

    def start_crop(self) -> None:
        ref = self.selected_ref()
        if ref and not self.busy():
            ref.crop = None
            self.reference_changed(self.refs.currentRow())
            self.input_view.crop_mode = True
            self.statusBar().showMessage("Trascina un rettangolo sull'anteprima per ritagliare; originale conservato")

    def apply_crop(self, crop: list) -> None:
        ref = self.selected_ref()
        if ref:
            ref.crop = crop
            self.reference_changed(self.refs.currentRow())

    def reset_reference(self) -> None:
        ref = self.selected_ref()
        if ref and not self.busy():
            ref.crop, ref.rotation = None, 0
            self.input_view.crop_mode = False
            self.reference_changed(self.refs.currentRow())

    def fit_views(self) -> None:
        self.input_view.fit()
        self.output_view.fit()

    def refresh_prompt(self) -> None:
        self.sync_form()
        self.prompt_view.setPlainText(build_prompt(self.project))
        self.tabs.setCurrentIndex(1)

    def copy_prompt(self) -> None:
        self.sync_form()
        QApplication.clipboard().setText(build_prompt(self.project))
        self.statusBar().showMessage("Istruzioni copiate")

    def output_directory(self) -> Path:
        if self.project.output_dir:
            return Path(self.project.output_dir)
        if self.project.references:
            return Path(self.project.references[0].source).parent
        return data_root() / "outputs"

    def generate(self, batch: bool = False) -> None:
        if self.busy():
            return
        self.sync_form()
        problems = warnings(self.project)
        if problems:
            self.error("\n".join(problems) + "\nCorreggere o chiarire i conflitti prima di procedere. Il controllo non comprende OCR o verifica CAD.")
            return
        if self.project.mode.startswith("C") and self.project.background != "Industriale":
            self.error("La modalità ambientata richiede sfondo Industriale: selezionarlo per evitare istruzioni contrastanti.")
            return
        if self.backend.currentIndex() == 1 and not batch:
            answer = QMessageBox.question(self, "Invio al servizio cloud", "Inviare ora a Codex i riferimenti selezionati e i parametri?\nUsa l'autenticazione ChatGPT della CLI e i relativi limiti. Non usa API a pagamento.")
            if answer != QMessageBox.StandardButton.Yes:
                return
        snapshot = self.project.to_dict()
        snapshot["attempts"] = []
        self.current_attempt = {"time": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "status": "In corso", "backend": self.backend.currentText(), "outputs": [], "parameters": snapshot, "prompt": build_prompt(self.project)}
        self.project.attempts.append(self.current_attempt)
        self.persist()
        p = Project.from_dict(snapshot)
        engine = AssistedBackend() if self.backend.currentIndex() == 0 else CodexBackend()
        self.run_worker(lambda cancel, progress: engine.generate(p, data_root() / "jobs", cancel, progress), self.generation_done)

    def generation_done(self, result: GenerationResult) -> None:
        self.current_job = result.job
        attempt = self.current_attempt
        assert attempt is not None
        attempt["job"] = str(result.job)
        attempt["status"] = "Generato" if result.images else "In attesa importazione"
        for image in result.images:
            self.accept_output(image, attempt)
        self.persist()
        self.load_form()
        self.statusBar().showMessage(result.message)
        if self.queue:
            self.next_batch()
        elif not result.images:
            self.open_folder(result.job)
            QMessageBox.information(self, "Pacchetto pronto", result.message + "\n\n" + str(result.job) + "\nConsulta LEGGIMI.txt. Non è ancora stato generato un render.")
        else:
            self.tabs.setCurrentIndex(0)

    def accept_output(self, image: Path, attempt: dict) -> None:
        # Store the original result with the attempt even if the source folder is not writable.
        original = checked_image(image)
        archive = data_root() / "results"
        archive.mkdir(exist_ok=True)
        from uuid import uuid4
        saved = archive / (uuid4().hex + ".png")
        if not original.save(str(saved), "PNG"):
            raise OSError("Impossibile archiviare il risultato")
        parameters = Project.from_dict(attempt["parameters"])
        directory = Path(parameters.output_dir) if parameters.output_dir else Path(parameters.references[0].source).parent
        try:
            output = save_output(saved, directory, parameters.name or Path(parameters.references[0].source).stem)
        except OSError:
            output = save_output(saved, data_root() / "outputs", parameters.name)
            self.statusBar().showMessage(f"Cartella sorgente non scrivibile. Output salvato in {output}")
            attempt["save_notice"] = f"Cartella originale non scrivibile; usata {output.parent}"
        attempt["outputs"].append(str(output))
        attempt.setdefault("archived_outputs", []).append(str(saved))
        attempt.setdefault("actual_sizes", []).append([original.width(), original.height(), original.hasAlphaChannel()])
        self.last_result = output
        self.output_choices.addItem(str(output))
        self.output_choices.setCurrentText(str(output))
        self.output_view.show_image(original)

    def select_output(self, value: str) -> None:
        if value and Path(value).exists():
            try:
                self.last_result = Path(value)
                self.output_view.show_image(checked_image(self.last_result))
            except Exception as exc:
                self.error(str(exc))

    def import_result(self) -> None:
        if self.busy():
            return
        self.sync_form()
        if not self.project.attempts:
            self.error("Preparare prima un tentativo, così il risultato conserva i parametri corretti.")
            return
        row = self.history.currentRow()
        if row < 0:
            row = len(self.project.attempts) - 1
        attempt = self.project.attempts[row]
        paths, _ = QFileDialog.getOpenFileNames(self, f"Importa render nel tentativo {row + 1}", "", "Immagini (*.png *.jpg *.jpeg *.webp)")
        try:
            for path in paths:
                self.accept_output(Path(path), attempt)
            if paths:
                attempt["status"] = "Importato"
                self.persist()
                self.load_form()
                self.tabs.setCurrentIndex(0)
        except Exception as exc:
            self.error(str(exc))

    def history_selected(self, row: int) -> None:
        if self._building or not 0 <= row < len(self.project.attempts):
            return
        attempt = self.project.attempts[row]
        self.prompt_view.setPlainText(attempt.get("prompt", ""))
        self.current_job = Path(attempt["job"]) if attempt.get("job") else None
        outputs = attempt.get("outputs", [])
        archives = attempt.get("archived_outputs", [])
        self.output_choices.clear()
        self.output_choices.addItems([str(Path(out) if Path(out).exists() else Path(archives[i])) for i, out in enumerate(outputs) if Path(out).exists() or i < len(archives)])
        if outputs:
            path = Path(outputs[-1])
            if not path.exists() and archives:
                path = Path(archives[-1])
            try:
                self.last_result = path
                self.output_view.show_image(checked_image(path))
            except Exception as exc:
                self.error(str(exc))
        self.statusBar().showMessage(attempt.get("error") or attempt.get("save_notice") or f"Tentativo {row + 1}: {attempt['status']}")

    def restore_attempt(self) -> None:
        if self.busy():
            return
        row = self.history.currentRow()
        if 0 <= row < len(self.project.attempts):
            attempts = self.project.attempts
            restored = Project.from_dict(attempts[row]["parameters"])
            restored.attempts = attempts
            self.project = restored
            self.load_form()

    def export_result(self) -> None:
        if not self.last_result:
            self.error("Nessun risultato da esportare")
            return
        path, selected = QFileDialog.getSaveFileName(self, "Esporta copia", str(self.output_directory() / ((self.project.name or "Oggetto") + ".png")), "PNG (*.png);;JPEG (*.jpg)")
        if path:
            try:
                destination = Path(path)
                extension = "jpg" if "JPEG" in selected else "png"
                # Exclusive output naming also protects an existing export selected in the dialog.
                target = save_output(self.last_result, destination.parent, destination.stem, extension)
                self.statusBar().showMessage(f"Esportato: {target}")
            except Exception as exc:
                self.error(str(exc))

    def enqueue(self) -> None:
        if self.busy():
            return
        self.sync_form()
        self.queue.append(self.project.to_dict())
        self.batch_list.addItem(self.project.name or "Oggetto senza nome")

    def enqueue_projects(self) -> None:
        if self.busy():
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Accoda progetti", "", "CST RenderAI (*.cst.json *.json)")
        for path in paths:
            try:
                p = Project.load(Path(path))
                self.queue.append(p.to_dict())
                self.batch_list.addItem(p.name or Path(path).stem)
            except Exception as exc:
                self.error(str(exc))

    def dequeue(self) -> None:
        if self.busy():
            return
        row = self.batch_list.currentRow()
        if row >= 0:
            del self.queue[row]
            self.batch_list.takeItem(row)

    def start_batch(self) -> None:
        if self.busy() or not self.queue:
            return
        for item in self.queue:
            p = Project.from_dict(item)
            issues = warnings(p)
            if p.mode.startswith("C") and p.background != "Industriale":
                issues.append("Modalità ambientata richiede sfondo industriale")
            if issues:
                self.error(f"Oggetto {p.name}: " + "\n".join(issues))
                return
        if self.backend.currentIndex() == 1:
            answer = QMessageBox.question(self, "Invio batch al cloud", f"Inviare a Codex tutti i {len(self.queue)} oggetti in coda con i rispettivi riferimenti? Ogni variante consuma i limiti del piano.")
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.persist()
        self.next_batch()

    def next_batch(self) -> None:
        if self.queue:
            self.project = Project.from_dict(self.queue.pop(0))
            self.project_path = None
            self.batch_list.takeItem(0)
            self.load_form()
            self.generate(batch=True)

    def new_project(self) -> None:
        if self.busy():
            return
        self.persist()
        self.project = Project()
        self.project_path = None
        self.last_result = None
        self.current_attempt = None
        self.current_job = None
        self.output_view.scene().clear()
        self.output_choices.clear()
        self.load_form()

    def save_project(self) -> None:
        if self.busy():
            return
        self.sync_form()
        path, _ = QFileDialog.getSaveFileName(self, "Salva progetto", str(self.project_path or Path.cwd() / ((self.project.name or "progetto") + ".cst.json")), "CST RenderAI (*.cst.json)")
        if path:
            try:
                self.project.export(Path(path))
                self.project_path = Path(path)
                self.statusBar().showMessage(f"Progetto salvato: {path}")
            except Exception as exc:
                self.error(str(exc))

    def open_project(self) -> None:
        if self.busy():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Apri progetto", "", "CST RenderAI (*.cst.json *.json)")
        if path:
            try:
                p = Project.load(Path(path))
                self.persist()
                self.project = p
                self.project_path = Path(path)
                self.last_result = None
                self.output_view.scene().clear()
                self.load_form()
            except Exception as exc:
                self.error(str(exc))

    def choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Cartella output")
        if path:
            self.output_dir.setText(path)

    def open_folder(self, path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_job(self) -> None:
        if self.current_job:
            self.open_folder(self.current_job)
        else:
            self.open_folder(data_root() / "jobs")

    def clean_cache(self) -> None:
        if self.busy():
            return
        count = 0
        for path in data_root().glob("*.tmp"):
            path.unlink(missing_ok=True)
            count += 1
        self.statusBar().showMessage(f"Rimossi {count} temporanei. Riferimenti, progetti e tentativi conservati.")

    def help(self) -> None:
        QMessageBox.information(self, "Guida rapida", "1. Importa PDF e scegli pagine (es. 1,3-5), aggiungi JPG/DOCX.\n2. Spunta i riferimenti utili e assegna i ruoli. Ruota/ritaglia se necessario.\n3. Inserisci quote, materiale e finitura; scegli modalità e sfondo.\n4. Assistito: prepara pacchetto, allegalo manualmente in Codex/ChatGPT e importa il render.\n5. CLI: avvia l'agente ufficiale; se image_gen non è disponibile usa il pacchetto assistito.\n6. Modifica le istruzioni e premi Genera per un nuovo tentativo.\n\nCronologia: seleziona un tentativo per il risultato e usa Aiuto → Ripristina parametri.\nOgni progetto è archiviato automaticamente nei dati locali. Quando salvi un progetto, conserva anche la cartella .assets accanto al JSON.\nNessun OCR automatico; verifica manualmente quote e conflitti nelle immagini.\nRisoluzione e rapporto sono richieste al modello, non garanzie. Nessuna verifica CAD.")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and not self.busy():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self.add_files([Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def closeEvent(self, event) -> None:
        if self.busy():
            self.cancel_operation()
            self.statusBar().showMessage("Annullamento in corso. Chiudere nuovamente quando l'operazione termina.")
            event.ignore()
            return
        try:
            self.persist()
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("backend", self.backend.currentIndex())
        except Exception:
            logging.exception("Salvataggio chiusura fallito")
        event.accept()

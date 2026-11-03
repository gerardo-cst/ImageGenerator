from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
import hashlib
import zipfile
import xml.etree.ElementTree as ET

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QImage, QImageReader, QTransform
from PySide6.QtPdf import QPdfDocument

from .models import Reference

SUPPORTED = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE = 512 * 1024 * 1024
MAX_PIXELS = 60_000_000


def validate(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Formato non supportato: {path.suffix}. Word: usare .docx, non .doc")
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_FILE:
        raise ValueError("File assente, vuoto o superiore a 512 MB")


def load_pdf(path: Path) -> QPdfDocument:
    validate(path)
    doc = QPdfDocument(None)
    if doc.load(str(path)) != QPdfDocument.Error.None_:
        raise ValueError("PDF danneggiato, protetto da password o non leggibile")
    if not 0 < doc.pageCount() <= 2000:
        raise ValueError("PDF vuoto o superiore al limite di 2000 pagine; dividerlo prima dell'importazione")
    return doc


def page_selection(text: str, count: int) -> list[int]:
    pages: set[int] = set()
    for part in text.split(","):
        bounds = part.strip().split("-")
        if len(bounds) not in (1, 2):
            raise ValueError("Usare pagine come 1,3-5")
        start, end = int(bounds[0]), int(bounds[-1])
        if not 1 <= start <= end <= count:
            raise ValueError(f"Intervallo non valido: {part}")
        pages.update(range(start - 1, end))
    if len(pages) > 80:
        raise ValueError("Importare al massimo 80 pagine alla volta")
    return sorted(pages)


def checked_image(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if not size.isValid() or size.width() * size.height() > MAX_PIXELS:
        raise ValueError("Immagine non valida o superiore a 60 megapixel")
    image = reader.read()
    if image.isNull():
        raise ValueError("Immagine danneggiata o codec non disponibile")
    return image


def import_document(path: Path, cache: Path, pages: list[int] | None = None,
                    cancelled: Callable[[], bool] = lambda: False,
                    progress: Callable[[str], None] = lambda _: None) -> list[Reference]:
    validate(path)
    path = path.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    # Content hash prevents stale cached images after a source is replaced.
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            if cancelled():
                raise InterruptedError("Importazione annullata")
            digest.update(block)
    prefix = digest.hexdigest()[:20]
    results: list[Reference] = []

    def store(image: QImage, index: int, label: str, context: str = "", page: int | None = None) -> None:
        if cancelled():
            raise InterruptedError("Importazione annullata")
        target = cache / f"{prefix}_{index}.png"
        if image.isNull() or not image.save(str(target), "PNG"):
            raise ValueError("Impossibile preparare il riferimento")
        results.append(Reference(str(path), str(target), label, context=context, page=page))
        progress(label)

    if path.suffix.lower() == ".pdf":
        doc = load_pdf(path)
        selected = pages if pages is not None else [0]
        for page in selected:
            if cancelled():
                raise InterruptedError("Importazione annullata")
            if not 0 <= page < doc.pageCount():
                raise ValueError("Pagina inesistente")
            points = doc.pagePointSize(page)
            factor = min(300 / 72, 6000 / max(points.width(), points.height()))
            image = doc.render(page, QSize(max(1, int(points.width() * factor)), max(1, int(points.height() * factor))))
            context = doc.getAllText(page).text()[:16000]
            store(image, page, f"{path.name} · pagina {page + 1}", context, page + 1)
        doc.close()
    elif path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if sum(e.file_size for e in entries) > 250_000_000:
                raise ValueError("Word troppo grande dopo decompressione (250 MB)")
            xml = archive.read("word/document.xml")
            if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                raise ValueError("XML Word non supportato")
            root = ET.fromstring(xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            context = "\n".join("".join(p.itertext()) for p in root.findall(".//w:p", ns))[:24000]
            for index, entry in enumerate(e for e in entries if e.filename.startswith("word/media/")):
                if index >= 100:
                    raise ValueError("Word con più di 100 immagini: dividere il documento")
                if cancelled():
                    raise InterruptedError("Importazione annullata")
                payload = archive.read(entry)
                from PySide6.QtCore import QBuffer, QIODevice
                buffer = QBuffer()
                buffer.setData(QByteArray(payload))
                buffer.open(QIODevice.OpenModeFlag.ReadOnly)
                reader = QImageReader(buffer)
                size = reader.size()
                if size.width() * size.height() > MAX_PIXELS:
                    raise ValueError("Immagine Word troppo grande")
                image = reader.read()
                if not image.isNull():
                    store(image, index, f"{path.name} · {Path(entry.filename).name}", context)
            if not results:
                raise ValueError("Nessuna immagine raster estraibile dal Word (EMF/WMF possono richiedere conversione)")
    else:
        store(checked_image(path), 0, path.name)
    return results


def prepare_image(reference: Reference) -> QImage:
    image = checked_image(Path(reference.image))
    if reference.rotation:
        image = image.transformed(QTransform().rotate(reference.rotation), Qt.TransformationMode.SmoothTransformation)
    if reference.crop:
        x, y, w, h = reference.crop
        if not (0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x + w <= 1.00001 and y + h <= 1.00001):
            raise ValueError("Ritaglio non valido")
        image = image.copy(int(x * image.width()), int(y * image.height()), max(1, int(w * image.width())), max(1, int(h * image.height())))
    return image

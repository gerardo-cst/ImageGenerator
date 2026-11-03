from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import uuid

ROLES = ["Prospettica", "Frontale", "Laterale", "Superiore", "Dettaglio", "Sezione", "Materiale / stile"]
MODES = ["A — Fedeltà tecnica massima", "B — Fotorealistico standard", "C — Render ambientato", "D — Interpretazione tecnica"]
TECH_FIELDS = ["Lunghezza", "Larghezza", "Altezza", "Diametro esterno", "Diametro interno", "Spessore", "Scala", "Materiale principale", "Materiali secondari", "Finitura", "Colore RAL", "Rugosità"]
DIMENSION_FIELDS = TECH_FIELDS[:7]
MATERIAL_FIELDS = TECH_FIELDS[7:]


@dataclass
class Variable:
    name: str = ""
    value: str = ""
    unit: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def label(self) -> str:
        return f"{self.name} = {self.value} {self.unit}".strip()


@dataclass
class Annotation:
    kind: str = "dimension"
    points: list[list[float]] = field(default_factory=lambda: [[.2, .5], [.8, .5]])
    variable_id: str = ""
    text: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        import math
        if self.kind not in {"dimension", "line", "note"}:
            raise ValueError("Tipo annotazione non valido")
        if len(self.points) != 2 or any(len(p) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in p) for p in self.points):
            raise ValueError("Coordinate annotazione non valide")


@dataclass
class Reference:
    source: str
    image: str
    label: str
    role: str = "Prospettica"
    selected: bool = True
    context: str = ""
    page: int | None = None
    rotation: int = 0
    crop: list[float] | None = None
    annotations: list[Annotation] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.annotations = [Annotation(**a) if isinstance(a, dict) else a for a in self.annotations]


@dataclass
class Project:
    name: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    references: list[Reference] = field(default_factory=list)
    technical: dict[str, str] = field(default_factory=dict)
    custom: list[list[str]] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    notes: str = ""
    unit: str = "mm"
    mode: str = MODES[0]
    view: str = "Isometrica"
    background: str = "Bianco"
    lighting: str = "Studio"
    shadows: bool = True
    pbr: bool = True
    resolution: str = "Massima disponibile"
    aspect: str = "1:1"
    variants: int = 1
    output_dir: str = ""
    attempts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        self.migrate_legacy()
        return asdict(self)

    def migrate_legacy(self) -> None:
        """Keep existing projects: fixed dimensions/custom pairs become editable variables."""
        names = {v.name.casefold() for v in self.variables}
        for key in DIMENSION_FIELDS:
            value = self.technical.pop(key, "")
            if value.strip() and key.casefold() not in names:
                self.variables.append(Variable(key, value, "" if key == "Scala" else self.unit))
                names.add(key.casefold())
        for pair in self.custom:
            if len(pair) >= 2 and pair[0].strip() and pair[0].casefold() not in names:
                self.variables.append(Variable(pair[0], pair[1]))
                names.add(pair[0].casefold())
        self.custom = []

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        import re
        if not isinstance(data, dict):
            raise ValueError("Struttura progetto non valida")
        data = dict(data)
        if "id" in data and not re.fullmatch(r"[a-f0-9]{32}", data["id"]):
            raise ValueError("Identificativo progetto non valido")
        if not 1 <= data.get("variants", 1) <= 8:
            raise ValueError("Numero varianti non valido")
        data["references"] = [Reference(**r) for r in data.get("references", [])]
        data["variables"] = [Variable(**v) for v in data.get("variables", [])]
        project = cls(**data)
        project.migrate_legacy()
        return project

    def save(self, path: Path) -> None:
        from .storage import atomic_json
        atomic_json(path, self.to_dict())

    @classmethod
    def load(cls, path: Path) -> Project:
        if path.stat().st_size > 20_000_000:
            raise ValueError("Progetto troppo grande")
        project = cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        def resolve_refs(refs: list[Reference]) -> None:
            for ref in refs:
                image = Path(ref.image)
                if not image.is_absolute():
                    resolved = (path.parent / image).resolve()
                    if not resolved.is_relative_to(path.parent.resolve()):
                        raise ValueError("Riferimento relativo esterno alla cartella progetto")
                    ref.image = str(resolved)
        resolve_refs(project.references)
        for attempt in project.attempts:
            if "parameters" in attempt:
                refs = [Reference(**r) for r in attempt["parameters"].get("references", [])]
                resolve_refs(refs)
                attempt["parameters"]["references"] = [asdict(r) for r in refs]
            attempt["archived_outputs"] = [str((path.parent / value).resolve()) if not Path(value).is_absolute() else value for value in attempt.get("archived_outputs", [])]
        return project

    def export(self, path: Path) -> None:
        """Portable JSON plus a companion directory with all historical references."""
        import hashlib
        import shutil
        copy = self.to_dict()
        asset_dir = path.parent / (path.stem + ".assets")
        asset_dir.mkdir(parents=True, exist_ok=True)
        groups = [copy["references"]] + [a["parameters"].get("references", []) for a in copy["attempts"] if "parameters" in a]
        for refs in groups:
            for ref in refs:
                source = Path(ref["image"])
                checksum = hashlib.sha256(source.read_bytes()).hexdigest()[:24]
                target = asset_dir / (checksum + ".png")
                if not target.exists():
                    shutil.copyfile(source, target)
                ref["image"] = target.relative_to(path.parent).as_posix()
        # Include archived results so the history also survives transport to another PC.
        for attempt in copy["attempts"]:
            archived = []
            for output in attempt.get("archived_outputs", attempt.get("outputs", [])):
                source = Path(output)
                if source.exists():
                    checksum = hashlib.sha256(source.read_bytes()).hexdigest()[:24]
                    target = asset_dir / (checksum + ".png")
                    if not target.exists():
                        shutil.copyfile(source, target)
                    archived.append(target.relative_to(path.parent).as_posix())
            attempt["archived_outputs"] = archived
        from .storage import atomic_json
        atomic_json(path, copy)

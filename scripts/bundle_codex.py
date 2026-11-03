"""Redistribute the installed official native Codex package, never user configuration/auth."""
from pathlib import Path
import json
import os
import shutil
from cst_renderai.backend import codex_command


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    override = os.environ.get("CST_CODEX_VENDOR")
    if override:
        vendor = Path(override).resolve()
    else:
        command = codex_command()
        launcher = Path(command[-1])
        if launcher.suffix == ".js":
            vendor = launcher.parent.parent / "node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc"
        else:
            vendor = Path(command[0]).parent.parent
    if not (vendor / "bin/codex.exe").is_file() or not (vendor / "codex-package.json").is_file():
        raise SystemExit("Pacchetto Codex nativo non trovato. Installare la CLI ufficiale o impostare CST_CODEX_VENDOR alla cartella vendor della distribuzione Windows x64.")
    target = root / "deploy/tools/codex"
    shutil.copytree(vendor, target, dirs_exist_ok=True)
    shutil.copyfile(root / "packaging/CODEX_LICENSE.txt", target / "LICENSE.txt")
    metadata = json.loads((vendor / "codex-package.json").read_text(encoding="utf-8"))
    (target / "DISTRIBUTION.txt").write_text(
        "Official OpenAI Codex CLI, unmodified native Windows x64 distribution.\n"
        "Source: https://github.com/openai/codex\nLicense: Apache-2.0 (LICENSE.txt).\n"
        "Package metadata: " + json.dumps(metadata, ensure_ascii=False) + "\n"
        "No credentials or user configuration are bundled. Login is performed separately on each PC.\n", encoding="utf-8")
    print("Motore Codex ufficiale incluso:", target)


if __name__ == "__main__":
    main()

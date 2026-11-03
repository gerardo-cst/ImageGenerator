"""Fail before copying a release if Windows has locked the current executable."""
from pathlib import Path


def main() -> None:
    executable = Path(__file__).resolve().parents[1] / "deploy/CST_RenderAI.exe"
    if executable.exists():
        try:
            # No writes: opening a loaded Windows executable for write is denied.
            with executable.open("r+b"):
                pass
        except PermissionError:
            raise SystemExit("CST RenderAI e aperto oppure deploy non e scrivibile. Salvare il lavoro e chiudere l'app prima dell'aggiornamento. Nessun file del programma e stato sostituito.")


if __name__ == "__main__":
    main()

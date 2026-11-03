# CST RenderAI

Applicazione desktop Python/PySide6, interfaccia italiana. Separare GUI, documenti,
prompt, backend e persistenza. Non introdurre API con fatturazione separata,
endpoint privati, lettura credenziali o automazione browser. Il backend Codex usa
solo CLI ufficiale e autenticazione ChatGPT verificata con `codex login status`.
Non dichiarare riuscita una generazione senza un'immagine valida nuova.
Eseguire `python -m unittest discover -s tests -v` e smoke Qt offscreen.
Aggiornare README.md e TASKS.md con limiti e verifiche effettive.

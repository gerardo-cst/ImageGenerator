# Risultati delle verifiche

Eseguiti su Windows 11, Python 3.13.3, PySide6 6.9.0, PyInstaller 6.13.0,
il 3 novembre 2026.

## Test automatici

`python -m unittest discover -s tests -v`: **16 test, tutti superati**.

Copertura: PDF multipagina e testo, JPG aggiuntivo, DOCX con immagini e contesto,
quote/materiali nel prompt, riferimenti stile, conflitti testuali, rotazione,
ritaglio, documenti danneggiati e formati errati, annullamento preparazione,
roundtrip progetti e portabilità dopo spostamento, ID progetto non valido,
output non sovrascritto, JPEG con alpha composto su bianco, ambiente senza chiavi
API, rifiuto autenticazione API, CLI assente, CLI conclusa senza immagine,
GUI con form, accodamento, risultato importato, cronologia e ripristino.

`python -m compileall -q cst_renderai scripts tests`: completato.

## GUI e packaging

`python -m scripts.smoke_gui`: completato. Screenshot
`docs/screenshots/desktop.png` ispezionato con anteprima documentale e render.

Build PyInstaller `onedir` completata. Eseguibile avviato senza console,
con piattaforma Qt offscreen e dati di prova isolati:

```json
{
  "ok": true,
  "references": 3,
  "pdf_pages": 2,
  "output": "Diagnostica_generated.png",
  "gui": true
}
```

Exit code dell'eseguibile: **0**. Non è stata effettuata un'installazione su un
secondo PC pulito; distribuire tutta la cartella con le DLL e verificare lì.

## Generazione reale

- CLI: prova inviata all'eseguibile ufficiale, login ChatGPT confermato;
  avvio app-server negato dai permessi locali. Nessuna generazione CLI dichiarata.
- Tool `image_gen` di questa conversazione: generazione reale riuscita con JPG
  sintetico come riferimento. Output salvato in `examples/Flangia_DN150_generated.png`.
- Render reale importato attraverso `MainWindow.accept_output`, archiviato,
  salvato automaticamente, visualizzato ed esportato nel progetto dimostrativo.
- Controllo visivo: flangia satinata con foro centrale e quattro fori periferici,
  fondo bianco. Non è una verifica metrologica delle dimensioni o di un CAD.

Per limiti del piano e procedura di verifica CLI interattiva vedere CAPABILITIES.md.

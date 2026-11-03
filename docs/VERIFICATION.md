# Risultati delle verifiche

## Aggiornamento variabili, editor e generazione diretta

**27 test superati.** Nuove verifiche: migrazione dimensioni/custom in variabili,
collegamenti stabili dopo rinomina, coordinate con rotazione/ritaglio, annotazione
PNG non distruttiva, esportazione senza sovrascrittura, copia pulita e annotata
nell'ordine giusto, prompt fotografico senza note nel render, persistenza,
annulla/ripeti, disegno col mouse e trascinamento degli estremi.

Test GUI del clic Genera foto: una chiamata al backend, nessuna conferma intermedia,
risultato acquisito e salvato. Il backend di questa prova è controllato: **non è
una generazione cloud reale**. La prova CLI live con tool immagini abilitato resta
negata dai permessi dell'app-server prima della generazione. Nessun bypass usato.

Screenshot aggiornato in `docs/screenshots/desktop.png`: annotazioni e variabili
accanto al render reale precedentemente generato. Motore ufficiale incluso nel
pacchetto, con licenza e risorse originali, senza autenticazione distribuita.

Eseguibile aggiornato in `dist/CST_RenderAI` verificato con diagnostica offline:
exit code 0, `gui`, `maximized`, `icon`, `annotation_editor`, `annotated_reference`
e `direct_default` tutti true, due pagine PDF + JPG e salvataggio PNG validi.

La sostituzione dell'EXE in deploy è stata completata dopo che l'utente ha chiuso
l'istanza che bloccava EXE e DLL. Nessun processo utente terminato forzatamente;
i dati portatili esistenti sono stati conservati. Il packaging ora controlla
questo caso prima di copiare.

Diagnostica sul nuovo `deploy/CST_RenderAI.exe` da una directory di lavoro diversa:
exit code 0, tutti i controlli sopra confermati. Hash dell'EXE identico alla build
in dist. Guida d'uso aggiornata e distribuzione nativa Codex incluse in deploy.

## Aggiornamento deploy portatile

Suite aggiornata: **19 test superati**, compresi icona, massimizzazione,
ripristino/ridimensionamento, impostazioni INI nel profilo e separazione dati
per PC/utente. Eseguibile `deploy/CST_RenderAI.exe` ricompilato con icona ICO.

Prova dell'eseguibile avviato da una directory di lavoro diversa e senza override
della cartella dati: **exit code 0**. Report: `ok=true`, `references=3`,
`pdf_pages=2`, `gui=true`, `maximized=true`, `icon=true`. Il log iniziale è stato
creato nella cartella portatile `deploy/data/<profilo-PC-utente>`.

La prova non usa un secondo PC né una condivisione SMB reale: permessi di rete
e policy di esecuzione vanno verificati nell'ambiente di destinazione.

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

# CST RenderAI

Applicazione desktop Windows in Python/PySide6 per preparare render fotorealistici
da documenti tecnici. Interfaccia italiana, stile Fluent Light, importazione locale,
viste affiancate, vincoli tecnici, prompt, cronologia e batch.

**Nessuna OpenAI API a pagamento è implementata.** Il piano ChatGPT non viene
trattato come una chiave API. La generazione richiede un servizio cloud disponibile
nel proprio account: l'app non include un modello locale.

## Avvio Windows

Se disponibile, aprire `dist/CST_RenderAI/CST_RenderAI.exe`. Conservare **tutta** la
cartella `CST_RenderAI`, compresa `_internal`. Non serve Python per questa versione.
L'eseguibile non è firmato digitalmente.

Da sorgente, con Python 3.11 o successivo:

```powershell
cd C:\Coding\ImageGenerator
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

Successivamente si può usare `Avvia CST RenderAI.bat`. L'unica dipendenza runtime
è PySide6: Qt PDF rende le pagine, Qt legge e trasforma le immagini, la libreria
standard Python estrae le immagini DOCX. Non servono Microsoft Word o AutoCAD.

## Due backend, con limiti espliciti

### Assistito — funzionamento di base senza CLI

1. Importare documenti e definire i parametri.
2. Selezionare **Assistito** e premere **Genera / prepara**.
3. Nella cartella aperta leggere `LEGGIMI.txt`. Allegare **tutti** i
   `reference_01.png`, `reference_02.png`, ecc., in ordine, in una conversazione
   Codex/ChatGPT con generazione immagini e incollare `prompt.txt`.
4. Avviare la generazione in quella conversazione. Per più varianti richiederle
   separatamente. Se sono troppi riferimenti, selezionarne meno nell'app e preparare
   un nuovo tentativo: l'app non li riduce o scarta silenziosamente.
5. Scaricare le immagini. Nell'app selezionare il tentativo nella **Cronologia**,
   poi **Importa risultato**. Se non è selezionato un tentativo viene usato l'ultimo.

La preparazione è locale, **non è una generazione**. Non si apre né controlla il
browser automaticamente. L'allegato manuale è l'azione che invia i file al cloud.

### Codex CLI — collegamento all'agente ufficiale

La CLI deve essere installata e autenticata con `codex login` usando ChatGPT.
`codex login status` deve riportare autenticazione ChatGPT. La documentazione
ufficiale descrive `$imagegen`, gli input `--image` e `codex exec` da script.
L'app chiama la CLI come sottoprocesso senza shell e passa i prompt via stdin.
Ogni variante è una chiamata separata; timeout 20 minuti per variante.

L'app chiede conferma dell'invio cloud al clic **Genera**, o una sola conferma
per tutti gli oggetti di un batch. Usa sandbox `workspace-write`, nessun bypass
dei permessi, nessuna lettura delle credenziali. Le variabili API note sono escluse
dall'ambiente del sottoprocesso. Un login tramite API key viene rifiutato.

**Disponibilità non garantita:** la presenza della skill non garantisce che
`image_gen` sia esposto nella sessione CLI. Non esiste qui un SDK immagini Python
incluso nel piano Plus: questo backend coordina l'agente CLI. Considera riuscito
il tentativo solo se l'agente salva un nuovo file immagine valido nella cartella
del job. Errori, limiti del piano o assenza del tool sono mostrati senza immagini
simulate. Il pacchetto locale resta disponibile per il flusso assistito.

**Verifica su questo PC (3 novembre 2026):** CLI 0.163.0, login ChatGPT confermato;
la prova live di `codex exec` è stata fermata da `Access is denied` durante
l'inizializzazione dell'app-server e da accessi in sola lettura ai dati Codex.
Non è stata verificata una generazione automatica dalla CLI. Non sono stati
aggirati i permessi. Vedere [verifica capacità](docs/CAPABILITIES.md).

## Procedura completa di esempio

Sono inclusi `examples/Flangia_DN150.pdf` (due viste sintetiche) e
`examples/Flangia_DN150_frontale.jpg`. Questi sono disegni di prova, non documenti
costruttivi certificati.

È incluso anche `examples/Flangia_DN150_generated.png`: render autentico ottenuto
con il tool `image_gen` integrato in questa conversazione, dal JPG sintetico,
e importato attraverso la gestione risultati dell'app. Prompt e provenienza sono
in `examples/render_prompt.txt`. Questa prova ha prodotto un'immagine 1254×1254
e conferma il flusso assistito, senza dimostrare la disponibilità del tool nella CLI.
Il progetto `examples/Flangia_DN150.cst.json` permette di riaprire la dimostrazione;
se si sposta il progetto, scegliere una cartella output accessibile.

1. Avviare l'app. **Importa** → PDF → pagine `1-2`.
2. Importare anche il JPG. Assegnare **Frontale** alla pagina 1 e al JPG,
   **Laterale** alla pagina 2. Spuntare i riferimenti da utilizzare.
3. Inserire materiale principale `AISI 316L`, diametro esterno `150`, diametro
   interno `60`, spessore `15`, unità `mm`, finitura `satinata`.
4. Scegliere modalità **B**, sfondo **Bianco**, luce **Studio**. Le impostazioni
   fotografiche sono più in basso nel pannello destro: scorrere il pannello.
5. Avviare il backend scelto e seguire le istruzioni sopra.
6. Importare/visualizzare il risultato: viene salvato automaticamente come
   `Flangia_DN150_generated.png` accanto al documento principale.
7. Cambiare note, vista o materiali e premere nuovamente **Genera / prepara**.
   Si crea un nuovo tentativo senza cancellare il precedente.

## Documenti e immagini

- **PDF:** selezione pagine con `1,3-5`, ogni pagina diventa un riferimento separato.
  Per selezionare altre pagine reimportare lo stesso PDF. Rendering a 300 DPI;
  bordo massimo 6000 pixel per contenere memoria e tempi. Il file originale rimane
  intatto. Rotella per zoom, trascinamento per spostare, **Adatta** per ripristinare.
- **Ritaglio:** selezionare una vista, **Ritaglia regione**, trascinare un rettangolo.
  Il ritaglio parte dalla vista intera ruotata; **Ripristina** elimina ritaglio e
  rotazione. **Ruota 90°** azzera il ritaglio per evitare coordinate ambigue.
- **DOCX:** estrazione di immagini raster da `word/media`; testo dei paragrafi
  conservato come contesto del documento, senza associazione semantica automatica
  a ogni immagine. EMF/WMF non leggibili vengono esclusi; `.doc` richiede conversione
  a DOCX. Se non ci sono immagini utilizzabili viene mostrato un errore.
- **PNG/JPEG/WebP:** decodifica con orientamento EXIF, preparazione lossless PNG
  senza riduzione della risoluzione. I metadati del file originale non vengono
  propagati nel PNG preparato. Originali conservati.
- Massimo 512 MB per file, 2000 pagine PDF, 80 pagine per importazione, 60 megapixel
  per immagine, 250 MB di contenuto DOCX decompresso, 100 elementi immagine DOCX.
  Limiti dichiarati, senza troncamento silenzioso delle pagine selezionate.
- Non è implementato OCR: le quote nelle scansioni vengono interpretate solo
  dal generatore durante la fase cloud. L'anteprima **Contesto documento** mostra
  il testo effettivamente estratto.

## Vincoli e fedeltà

Le viste geometriche sono rappresentazioni dello stesso oggetto. Il ruolo
**Materiale / stile** influenza soltanto aspetto e finiture. Tutti i parametri
compilati e le caratteristiche personalizzate vengono inseriti nel prompt.

Le modalità A/B/C preservano la geometria visibile; D consente ipotesi e richiede
che vengano dichiarate separatamente. C richiede sfondo industriale, evitando
istruzioni contraddittorie. La segnalazione effettiva delle ipotesi dipende dalla
risposta del servizio; l'app conserva anche il log della CLI.

Il controllo locale dei conflitti rileva dichiarazioni testuali esplicite come
`Diametro esterno: 180 mm` discordanti con i parametri o tra documenti. È un
controllo limitato, non un analizzatore CAD, non converte unità contrastanti e
non legge quote raster. I conflitti rilevati bloccano l'avvio: correggere i dati,
escludere il riferimento errato o chiarire la fonte. Verificare sempre le tavole.

La priorità del prompt è la fedeltà. **Risoluzione, rapporto, qualità e materiali
sono richieste al servizio, non garanzie né parametri di una API immagine.**
Non viene applicato upscaling artificiale per dichiarare raggiunta una risoluzione.
La cronologia registra dimensioni reali e presenza del canale alpha. Sfondo
trasparente significa richiesta di alpha reale; verificare il risultato.

Un render generativo non certifica quote, tolleranze o conformità geometrica.

## Output, progetti, cronologia e batch

- Documento principale: primo riferimento in elenco; usare **Usa come documento
  principale** per cambiarlo. Nome output modificabile.
- Output automatico nella sua cartella, oppure nella cartella esplicitamente
  scelta. Se la cartella non è scrivibile, fallback nei dati applicazione e avviso
  conservato nella cronologia. I risultati originali sono archiviati anche lì.
- Prima immagine `nome_generated.png`; successive `_generated_01.png`, `_02`, ecc.
  Creazione esclusiva: nessuna sovrascrittura, anche con due istanze aperte.
- **Esporta PNG/JPG** crea una copia con lo stesso schema protetto. JPEG viene
  composto su fondo bianco per preservare correttamente la trasparenza.
- La combo sopra il render permette di scegliere tra le varianti. Cronologia
  conserva snapshot parametri, prompt, percorsi, stato, errori e dimensioni reali.
  **Aiuto → Ripristina parametri tentativo** prepara una rigenerazione coerente.
- Salvataggio automatico su operazioni e chiusura. Ogni oggetto batch viene
  archiviato separatamente in `projects/<id>.json`. **Salva progetto** esporta
  un JSON e una cartella `.assets`: trasferire entrambi per mantenere i riferimenti
  e i risultati archiviati. Le cartelle sorgenti e le destinazioni output originali
  rimangono indicate nel progetto; su un altro PC scegliere una nuova destinazione.
- Batch: accodare l'oggetto corrente, creare un nuovo oggetto e accodarlo, oppure
  aggiungere progetti salvati. **Avvia coda** lavora in sequenza. Assistito prepara
  un pacchetto per oggetto; CLI genera e salva. Un errore ferma la coda per evitare
  altri invii. **Annulla** ferma anche gli oggetti successivi. La coda in attesa
  non è persistita tra riavvii: salvare i progetti prima di chiudere.

## Privacy, dati e diagnostica

Importare, visualizzare, ritagliare e preparare il pacchetto sono operazioni locali.
Premere Genera con backend CLI invia i riferimenti selezionati e il loro contesto
testuale al servizio cloud dopo conferma. Con Assistito l'invio avviene quando
si allegano manualmente i file nella conversazione. Valutare la riservatezza dei
documenti prima di inviarli.

**Aiuto → Apri dati e diagnostica** apre la cartella dati locale Qt, normalmente
`%LOCALAPPDATA%/CST/CST RenderAI`. Per un percorso diverso impostare
`CST_RENDERAI_DATA`. Contiene:

| Percorso | Contenuto |
|---|---|
| `references/` | Riferimenti preparati, condivisi tra progetti |
| `jobs/<timestamp_id>/` | Prompt, immagini selezionate, snapshot, istruzioni, log CLI |
| `results/` | Copie PNG archiviate dei render importati/generati |
| `projects/` | Snapshot dei singoli oggetti |
| `autosave.json` | Ultimo oggetto aperto |
| `diagnostics.log` | Errori, rotazione a 3 MB con 3 backup |

Questi dati possono contenere disegni e informazioni riservate; non sono cifrati.
I pacchetti sono artefatti persistenti utili alla cronologia, non temporanei.
I file `.tmp` del salvataggio atomico vengono rimossi; una preparazione annullata
rimuove il job parziale. La cache dei riferimenti è conservativa per non rompere
progetti salvati. Per liberare spazio archiviare i progetti con `.assets`, chiudere
l'app ed eliminare manualmente i job e i dati non più necessari.

Annullare interrompe il sottoprocesso CLI; richieste cloud già accettate possono
completarsi e consumare limiti. Una chiamata nativa di rendering PDF può terminare
prima di recepire l'annullamento. La GUI resta in un thread separato dall'operazione.
In chiusura durante un lavoro, l'app richiede l'annullamento e aspetta che termini:
chiudere di nuovo al termine, senza terminare un thread attivo.

## Test e packaging

```powershell
python -m unittest discover -s tests -v
python -m scripts.make_examples
python -m scripts.smoke_gui
python -m compileall -q cst_renderai scripts tests
python -m pip install pyinstaller
powershell -NoProfile -File scripts/build.ps1
```

La prova live è opzionale e invia un disegno sintetico al cloud, consumando i limiti
Codex: `python -m scripts.verify_codex`. Nessuna chiave API richiesta.

Lo smoke GUI crea `docs/screenshots/desktop.png` e usa dati isolati in `.test-data`.
I test di importazione risultati usano immagini di fixture: non rappresentano una
prova di fedeltà del generatore. Stato delle verifiche in [TASKS.md](TASKS.md).

L'eseguibile supporta inoltre una diagnostica locale isolata:
`CST_RenderAI.exe --diagnostics report.json`. Verifica GUI, importazione PDF
a due pagine, JPG e salvataggio PNG; scrive il risultato nel report senza invii cloud.

## Struttura

| Modulo | Responsabilità |
|---|---|
| `app.py`, `window.py`, `viewer.py`, `workers.py` | GUI, stato, zoom/ritaglio, operazioni asincrone |
| `documents.py` | Validazione, PDF, DOCX, immagini, preparazione |
| `models.py` | Oggetto, riferimenti, ruoli, parametri, progetti |
| `prompts.py` | Istruzioni tecniche e controlli conflitti |
| `backend.py` | Protocollo sostituibile, Assistito, Codex CLI |
| `storage.py` | Salvataggi atomici, output esclusivi, log |

Un futuro motore locale potrà implementare `GenerationBackend.generate` restituendo
`GenerationResult`. Non è stato implementato un motore locale o un backend API.

## Fonti e licenze dipendenze

Verifica capacità al 3 novembre 2026, con documentazione ufficiale OpenAI:
[immagini](https://learn.chatgpt.com/docs/image-generation),
[CLI](https://learn.chatgpt.com/docs/cli/reference),
[modalità non interattiva](https://learn.chatgpt.com/docs/non-interactive-mode).

PySide6/Qt sono distribuiti con le rispettive licenze LGPLv3/GPLv3 o commerciali;
consultare [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html).
Il packaging mantiene librerie dinamiche separate in `_internal`. Per distribuire
commercialmente verificare gli obblighi delle licenze e includere gli avvisi Qt.

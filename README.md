# CST RenderAI

Applicazione desktop Windows/PySide6 per ottenere fotografie di prodotto da
disegni, documenti tecnici e immagini, con variabili e annotazioni sul documento.

**Avvio pronto:** `deploy/CST_RenderAI.exe`. Guida operativa completa:
`deploy/GUIDA_USO.txt`. Copiare tutta `deploy`, incluse `_internal` e `tools`.
Non occorre installare Python, Word, AutoCAD o Node sul PC client.

La finestra parte massimizzata con barra titolo Windows: Ripristina o trascina
la barra per spostarla e ridimensionarla. Interfaccia italiana Fluent Light,
documenti a sinistra, confronto al centro, materiali/variabili e resa a destra.

## Flusso principale: genera direttamente dall'app

1. **Accedi a ChatGPT** una volta sul PC: il motore ufficiale Codex apre il proprio
   accesso nel browser. L'app non legge, esporta o copia credenziali. **Connessione**
   verifica il login; non certifica la disponibilità del tool immagini.
2. **Importa** PDF, DOCX, PNG, JPG/JPEG o WebP. Spunta le viste utili e assegna ruoli.
3. Imposta materiali e finiture. Aggiungi variabili e annotale sulla vista.
4. Lascia **Diretto · Codex / ChatGPT**, scegli vista/sfondo e premi **Genera foto
   (cloud)**. Quel clic avvia esplicitamente l'invio dei riferimenti selezionati e
   delle note, la generazione e il salvataggio; nessun copia-incolla o allegato manuale.
5. Il risultato valido compare nell'app e viene salvato automaticamente con
   suffisso `_generated`. Modifica i parametri e premi nuovamente per rigenerare.

**Vincolo reale:** il tool immagini deve essere disponibile nella sessione Codex,
con account abilitato, Internet e limiti del piano sufficienti. Il motore incluso
è la CLI ufficiale 0.163.0: viene invocata con `codex exec`, `--enable
image_generation`, riferimenti `--image` e sandbox `workspace-write`. Non esiste
qui un SDK Python per immagini incluso in Plus: l'app coordina l'agente ufficiale.

**Prova live in questa sessione:** login ChatGPT confermato, ma l'app-server Codex
non si avvia per `Access is denied` e restrizioni sul suo database locale. La nuova
prova con generazione immagini abilitata è fallita prima del generatore. Non è
quindi verificata una generazione automatica reale dalla CLI su questo PC.
L'app mostra l'errore e non produce immagini sostitutive. Va verificata avviando
normalmente `deploy/CST_RenderAI.exe` dal desktop, fuori dalla sessione di sviluppo.

**Nessuna API a pagamento implementata**, nessun endpoint privato o automazione
del browser. Le variabili d'ambiente API note non vengono passate al motore e
un login tramite API key viene rifiutato. I servizi cloud restano necessari:
non è implementato un generatore locale.

## Variabili, quote, linee e note sul documento

I campi dimensionali fissi sono stati rimossi. Usa **+ Variabile** per definire
qualsiasi vincolo: per esempio `Diametro piastra | 150 | mm`, `Interasse | 90 | mm`,
`Numero fori | 4 |` oppure `Guarnizione | PTFE |`. Materiali, finitura, RAL e rugosità
restano nel pannello destro. I vecchi progetti vengono migrati automaticamente.

1. Seleziona una vista e una variabile nella barra **Annota**.
2. Scegli **Quota**, **Linea** o **Nota con richiamo** e trascina sulla vista.
   Quota usa due estremi con frecce; Nota collega un punto alla posizione del testo.
   Una nota senza variabile può contenere testo libero; una linea può essere libera.
3. Cambia nome, valore o unità nella tabella: tutte le etichette collegate si
   aggiornano. Il collegamento usa un ID stabile, non il nome o il numero di riga.
4. **Naviga / modifica**: seleziona e trascina corpo o estremi. Seleziona anche
   dalla lista delle annotazioni a destra; doppio clic per il testo aggiuntivo.
5. **Collega** applica la variabile scelta all'annotazione selezionata. Elimina con
   il pulsante o Canc sulla vista. Ctrl+Z annulla, Ctrl+Shift+Z ripete le operazioni
   sulle annotazioni. Esc annulla il gesto e torna a Naviga.
6. **PNG annotato** esporta una copia con linee e note. Non sovrascrive né modifica
   il riferimento originale. Salva progetto conserva annotazioni modificabili.

Una variabile usata da annotazioni va ricollegata o rimossa dalle note prima di
eliminarla. Nome e valore sono obbligatori; nomi duplicati sono segnalati.
Le variabili possono anche essere usate come vincoli generali senza disegnarle.

Le coordinate sono normalizzate sull'immagine originale: rotazione e ritaglio
preservano la posizione fisica delle note. Le note fuori dal ritaglio restano nel
progetto e tornano visibili ripristinando la vista. La posizione grafica della quota
non misura millimetri dai pixel: è il valore della variabile a definire il vincolo.

Il motore riceve l'immagine pulita `reference_01.png` e, quando contiene annotazioni
visibili, una copia `reference_01_notes.png`. Il prompt identifica ordine, ruoli,
stesso oggetto, posizione e valore di ogni nota. **Il render finale è richiesto
come fotografia pulita, senza quote, frecce o etichette.**

## Fedeltà e qualità fotografica

La modalità iniziale è **A — Fedeltà tecnica massima**. B mantiene l'oggetto e
migliora la resa; C richiede un ambiente industriale e sfondo Industriale; D consente
ipotesi che il servizio deve dichiarare. Le immagini materiale/stile influenzano
solo l'aspetto, non la geometria.

I prompt richiedono sempre la massima qualità effettivamente disponibile, aspetto
da fotografia reale, materiali plausibili, microstruttura coerente, riflessi,
illuminazione e ombre realistiche. Vietano geometrie arbitrarie, usura inventata,
aspetto stilizzato e annotazioni nel risultato. Materiali e dimensioni dichiarati
sono vincoli prioritari. Le varianti sono richieste con chiamate separate.

Risoluzione, rapporto e trasparenza sono richieste al servizio, **non garanzie né
parametri di una API**. Non viene simulata una risoluzione tramite upscaling.
La cronologia registra dimensioni reali e presenza del canale alpha. Nessuna
garanzia di miglioramento progressivo o conformità dimensionale CAD: controllare
sempre geometria, quote e dettagli dell'immagine prodotta.

Il controllo locale segnala conflitti in dichiarazioni testuali esplicite di quote
con lo stesso nome. Non è OCR, non converte automaticamente unità contrastanti e
non verifica CAD o tolleranze. I conflitti rilevati bloccano l'invio.

## Esempio pronto

Apri `examples/Flangia_DN150.cst.json` con la cartella `.assets` accanto: include
viste, variabili e note di esempio. Scegli una destinazione output accessibile.
Oppure importa `Flangia_DN150.pdf` (pagine `1-2`) e il JPG frontale, assegna ruoli
Frontale/Laterale e aggiungi `Diametro esterno=150 mm`, `Diametro interno=60 mm`,
`Spessore=15 mm`, materiale `AISI 316L` e finitura `satinata`. Disegna le note e genera.

`examples/Flangia_DN150_generated.png` è un render autentico già generato con il
tool integrato di questa conversazione, dal disegno sintetico. Prompt e provenienza
sono in `examples/render_prompt.txt`. Non dimostra la disponibilità della CLI.

## Documenti e limiti tecnici

- PDF: selezione pagine `1,3-5`; reimportare per aggiungere altre pagine. Rendering
  a 300 DPI, lato massimo 6000 pixel per le tavole grandi. PDF protetti: fornire
  una copia sbloccata. Rotella per zoom, trascina per pan, Adatta per ripristinare.
- DOCX: estrazione di immagini raster incorporate e contesto testuale generale.
  Non viene dedotta l'associazione semantica tra paragrafi e singola immagine.
  DOC, EMF e WMF richiedono conversione se non leggibili.
- Immagini: orientamento EXIF, preparazione PNG senza riduzione della risoluzione,
  rotazione e ritaglio non distruttivi; metadati originali non propagati.
- Limiti: 512 MB per file; 2000 pagine PDF, 80 per importazione; 60 megapixel per
  immagine; 250 MB DOCX decompresso e 100 elementi immagine. Errori espliciti.
- Le quote raster non sono lette da OCR locale. Il contesto testuale effettivamente
  estratto è visibile nella scheda Contesto documento.

## Output, cronologia e batch

Il primo riferimento è il documento principale: **Usa come documento principale**
per cambiarlo. Nome output modificabile. La destinazione automatica è la cartella
del documento, oppure quella scelta. Se non scrivibile, viene usata `data/…/outputs`
con avviso nella cronologia. Gli originali dei risultati sono archiviati anche lì.

Primo risultato `nome_generated.png`, poi `nome_generated_01.png`, `_02`, ecc.
Creazione esclusiva, nessuna sovrascrittura anche tra istanze diverse. Esporta
PNG/JPG crea copie protette; JPEG viene composto su bianco se presente alpha.
La lista sopra il render seleziona le varianti, Confronta mostra input/output.

Cronologia conserva snapshot, note modificabili, prompt, stato/errori e output.
**Aiuto > Ripristina parametri tentativo** riprende un tentativo per rigenerarlo.
Salva progetto esporta JSON + cartella `.assets`: spostare entrambi. Oggetti
archiviati automaticamente in `projects/<id>.json` ai punti di salvataggio e chiusura.

Batch: accoda oggetti o progetti salvati; **Avvia coda (cloud se diretto)** è l'azione
esplicita che autorizza la sequenza di invii. Un errore o Annulla ferma i successivi.
La coda in attesa non è persistita: salvare i progetti prima di chiudere.

## Modalità manuale opzionale

Resta disponibile **Manuale · solo pacchetto** per ambienti senza tool immagini
nella CLI. È una scelta esplicita, non un fallback silenzioso. Prepara i file e
`prompt.txt`, allega tutti i `reference_*.png` nell'ordine lessicografico indicato
nel prompt (comprese le copie `_notes`) in una conversazione abilitata, genera e
usa Importa risultato sul tentativo corrispondente. Preparare non significa generare.

## Portabilità, rete e privacy

`deploy` include runtime, icona, documenti e motore nativo ufficiale Codex con la
sua licenza Apache-2.0 e risorse. Su ogni PC serve il proprio accesso ChatGPT.
Nessun token viene distribuito: **Codex conserva autenticazione, configurazione e
propri dati interni nel profilo utente**, fuori dai dati portatili dell'app.

Puoi copiare tutta `deploy` in `\\SERVER\Applicazioni\CST_RenderAI` e aprire l'EXE
da un PC Windows x64. Il codice gira sul client, non sul server. Servono lettura
ed esecuzione sulla condivisione, scrittura su `data` e accesso ai documenti/output.
Le policy aziendali possono bloccare eseguibili di rete: verificare con l'IT.
Non è stata effettuata una prova SMB da un secondo PC reale.

`portable.ini` mantiene i dati dell'app in `deploy/data/<profilo-PC-utente>`:
`references/`, `jobs/`, `results/`, `projects/`, `autosave.json`, `settings.ini` e
`diagnostics.log` ruotato (3 MB + 3 backup). Una sola istanza per profilo.
`CST_RENDERAI_DATA` può indicare un percorso diverso. I profili evitano collisioni,
non sono una protezione di accesso: usare permessi appropriati sulla condivisione.

Editing e importazione sono locali. **Genera foto** invia immagini selezionate,
copie annotate e contesto al cloud: usare documenti autorizzati alla condivisione.
Dati e pacchetti non sono cifrati. Aiuto > Apri dati e diagnostica apre i log;
ogni job CLI conserva eventi, risposta e snapshot. I pacchetti sono persistenti,
non temporanei. Pulisci file temporanei non elimina progetti o riferimenti.

Annulla termina la CLI; richieste cloud già accettate possono completarsi e
consumare limiti. Una chiamata PDF nativa può finire prima di recepire l'annullamento.
Chiudendo durante un lavoro, attendere l'annullamento e chiudere di nuovo.

## Sviluppo, test e packaging

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
python -m unittest discover -s tests -v
python -m scripts.smoke_gui
python -m compileall -q cst_renderai scripts tests
python -m pip install pyinstaller
powershell -NoProfile -File scripts/deploy.ps1
```

Il packaging richiede la distribuzione Codex ufficiale Windows x64 installata
nel PC di sviluppo; `CST_CODEX_VENDOR` può indicare la cartella vendor alternativa.
Lo script la copia senza modifiche in `deploy/tools/codex`, senza leggere dati utente,
e conserva `deploy/data` durante gli aggiornamenti. I client non richiedono Node.

27 test passano, incluse annotazioni, coordinate, migrazione, esportazione, GUI,
gesti mouse e orchestrazione a un clic con backend di test. Questa prova non è
una generazione live. `python -m scripts.verify_codex` esegue invece un vero test
cloud con riferimento sintetico e consuma limiti del piano se parte.
`CST_RenderAI.exe --diagnostics report.json` esegue la diagnostica locale offline
di GUI, PDF/JPG, annotazioni e salvataggio. [Verifiche](docs/VERIFICATION.md).

| Modulo | Responsabilità |
|---|---|
| `app`, `window`, `viewer`, `workers` | GUI, stato, gesti, asincronia |
| `models`, `annotations` | Variabili, collegamenti, coordinate e disegno PNG |
| `documents`, `prompts` | Documenti, preparazione e istruzioni conservative |
| `backend`, `storage` | Motore ufficiale/alternativa manuale, output, dati e log |

Il protocollo GenerationBackend permette backend futuri. Motori locali e API a
pagamento non sono implementati. PySide6/Qt restano soggetti alle rispettive
licenze LGPL/GPL o commerciali; DLL separate in `_internal`.

Fonti ufficiali: [immagini](https://learn.chatgpt.com/docs/image-generation),
[CLI](https://learn.chatgpt.com/docs/cli/reference),
[esecuzione da script](https://learn.chatgpt.com/docs/non-interactive-mode).
Dettagli di disponibilità e prova negata: [CAPABILITIES.md](docs/CAPABILITIES.md).

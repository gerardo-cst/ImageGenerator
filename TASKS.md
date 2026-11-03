# Stato CST RenderAI

Aggiornato: 3 novembre 2026.

- [x] Verifica documentazione ufficiale, skill imagegen e CLI locale.
- [x] Distinzione tra piano ChatGPT, tool integrato e API a pagamento.
- [x] Architettura modulare, protocollo backend sostituibile.
- [x] GUI PySide6 italiana Fluent Light, tre pannelli, stato, drag/drop.
- [x] Zoom, rotazione, ritaglio, confronto affiancato.
- [x] Importazione PDF multipagina con selezione e rendering alta risoluzione.
- [x] DOCX: immagini raster e contesto testuale; PNG/JPG/JPEG/WebP.
- [x] Ruoli geometrici e materiale/stile, selezione riferimenti.
- [x] Parametri dimensionali/materiali, unità, caratteristiche personalizzate.
- [x] Modalità A/B/C/D e parametri fotografici, istruzioni conservative.
- [x] Segnalazione conflitti testuali espliciti (nessun OCR/CAD automatico).
- [x] Backend assistito con pacchetti pronti e importazione risultati autentici.
- [x] Ponte CLI ufficiale con verifica login ChatGPT, timeout, annullamento e log.
- [x] Salvataggio automatico, fallback, protezione sovrascrittura, export PNG/JPG.
- [x] Cronologia snapshot, rigenerazione, risultati e selezione varianti.
- [x] Archiviazione per oggetto e batch sequenziale con stop su errore.
- [x] Progetti esportabili con cartella asset associata.
- [x] Validazione, limiti documenti, eccezioni, log ruotati, pulizia temporanei.
- [x] Esempi PDF/JPG sintetici e screenshot GUI offscreen.
- [x] Test funzionali core, backend e GUI: 16 test superati.
- [x] Render autentico tramite image_gen integrato della conversazione, salvato in
  `examples/Flangia_DN150_generated.png`; prompt e provenienza conservati.
- [x] Importazione di questo render nell'app, salvataggio automatico, progetto
  dimostrativo esportato e screenshot con confronto input/output.
- [x] Prova live CLI eseguita: fallita prima del generatore per permessi app-server.
- [x] Script packaging Windows PyInstaller.
- [x] Eseguibile creato in `dist/CST_RenderAI/CST_RenderAI.exe`.
- [x] Smoke test eseguibile impacchettato: exit code 0, GUI valida, due pagine PDF
  + JPG (3 riferimenti), output `Diagnostica_generated.png` verificato.
- [x] Documentazione installazione, flusso Plus, privacy, limiti e troubleshooting.
- [ ] Verifica interattiva della generazione CLI da desktop normale: non eseguibile
  con i permessi di questa sessione; nessun risultato automatico dichiarato.
- [ ] Controllo umano di fedeltà del render su un documento industriale reale.

## Criteri di accettazione

Test automatico copre apertura GUI, PDF a due pagine, JPG aggiuntivo, AISI 316L,
diametro 150 mm, satinatura, prompt con fondo bianco, preparazione backend,
importazione immagine di fixture, anteprima, `_generated` e rigenerazione senza
sovrascrittura. Una fixture non è un render AI: la fase cloud va eseguita nel
servizio effettivamente disponibile. Il flusso assistito la prevede esplicitamente.

## Limiti intenzionali

Nessuna API a pagamento, browser automation, endpoint privato, motore locale,
OCR, parsing CAD o certificazione dimensionale. I PDF protetti richiedono una
copia sbloccata. DOC/EMF/WMF richiedono conversione. Le istruzioni di qualità e
risoluzione non equivalgono a parametri garantiti del servizio.

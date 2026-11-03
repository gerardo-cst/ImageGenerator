# Verifica Codex e ChatGPT Plus — 3 novembre 2026

## Evidenze locali

- Codex CLI installato: `codex-cli 0.163.0`.
- `codex login status`: `Logged in using ChatGPT`.
- Skill locale `imagegen` letta: modalità integrata senza `OPENAI_API_KEY`;
  fallback `scripts/image_gen.py` richiede API key ed è escluso dal progetto.
- In questa conversazione è esposto lo strumento integrato `image_gen` per creare
  e modificare immagini con riferimenti. È una capacità dell'host della chat,
  **non una funzione Python pubblica chiamabile direttamente dal desktop**.
- `codex exec --help`: modalità non interattiva, riferimenti multipli `--image`,
  prompt da stdin, `--json`, sandbox `workspace-write`, directory di lavoro `-C`.
- Prova effettiva tramite `scripts/verify_codex.py`, con un'immagine sintetica:
  autenticazione confermata, ma inizializzazione fallita con `Access is denied`
  sull'app-server e avvisi di database Codex in sola lettura. Nessun render prodotto.
  Log locale: `.test-data/live-cli/jobs/*/events_01.jsonl`.
- Prova live del tool `image_gen` in questa conversazione: riuscita su una flangia
  sintetica di riferimento. Immagine 1254×1254 salvata in
  `examples/Flangia_DN150_generated.png`, importata tramite la gestione output
  dell'app e archiviata nel progetto dimostrativo. Quattro fori periferici e foro
  centrale visivamente presenti; nessuna conformità dimensionale certificata.
  Prompt completo in `examples/render_prompt.txt`.

Il problema osservato è nei permessi dell'ambiente di esecuzione, prima della
generazione: non prova né che il tool immagini sia disponibile nella CLI né che
sia assente. Non sono stati modificati permessi, copiati token o aggirata la sandbox.

## Documentazione ufficiale consultata

1. https://learn.chatgpt.com/docs/image-generation
   Descrive generazione/modifica nella CLI, invocazione `$imagegen`, immagine
   allegata con `-i`/`--image`, riferimenti multipli con ruoli espliciti. Indica
   `gpt-image-2` per la funzione integrata e consumo dei limiti generali Codex.
   La qualità e dimensione influenzano il consumo. L'app non promette quote fisse.
2. https://learn.chatgpt.com/docs/non-interactive-mode
   Documenta `codex exec` per script, ereditarietà dell'autenticazione CLI,
   JSONL, prompt stdin e sandbox. Non definisce un contratto dedicato immagini
   per Python o garantisce che il tool integrato sia presente in ogni esecuzione.
3. https://learn.chatgpt.com/docs/cli/reference
   Riferimento dei comandi e input immagine.

## Decisione implementativa

- Backend assistito predefinito e sempre utilizzabile per preparare i riferimenti
  localmente. Invio e generazione espliciti in una conversazione supportata;
  importazione del render, archiviazione e salvataggio automatizzati nell'app.
- Backend CLI basato soltanto su comandi ufficiali, autenticazione ChatGPT
  obbligatoria e nessuna chiave API. Chiede all'agente il tool integrato e la copia
  dell'output autentico nel job. Se non c'è un file immagine valido, errore.
- Massima qualità richiesta nelle istruzioni. Nessun parametro fittizio per
  qualità, formato o 4K; il servizio determina capacità effettive. Il prompt
  richiede alpha reale quando si seleziona Trasparente.
- Ogni riferimento resta un PNG indipendente e con ruolo esplicito, senza collage.
  Il numero effettivamente accettato dipende dall'host e dai limiti del servizio.
- Una chiamata per variante. Nessuna conversione automatica al backend API per
  errori, limiti o batch. Nessun costo API separato provocato dall'app.

## Operazione da verificare fuori da questa sessione

Aprire normalmente l'eseguibile dal desktop Windows e provare **Codex CLI**
con i file sintetici di `examples/`. Se l'app-server non parte, verificare che
la CLI funzioni da un normale terminale utente con `codex login status` e una
sessione interattiva `$imagegen`. Consultare il log del job e le policy locali.
Non è necessario cambiare permessi dei file dall'app: il flusso assistito evita
questa dipendenza. Questa verifica interattiva rimane necessaria per dichiarare
funzionante la generazione CLI sul PC dell'utente.

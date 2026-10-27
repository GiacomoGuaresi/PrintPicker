# Selezioni per stampa

Il concetto centrale dell'app è la **selezione per stampa**: una cartella sul PC che contiene le foto scelte da mandare in stampa **e** tutti i dati di lavoro di quella selezione.

## Avvio

- All'avvio l'app mostra la **home**: una griglia di **schede**, una per selezione, ordinate dalla più recente.
- Ogni scheda mostra:
  - una **copertina** con le prime foto scelte (fino a 4, a mosaico);
  - il **nome**;
  - il **numero di foto** e il **costo stimato**, calcolato con il listino delle impostazioni;
  - **quando è stata modificata** l'ultima volta ("oggi", "ieri", "3 giorni fa", oppure la data).
- La prima scheda è sempre **Nuova selezione**: si inserisce solo il nome (proposto: `Stampa <data di oggi>`, es. `Stampa 2026-10-12`) e la cartella viene creata nella posizione base.
- Le selezioni stanno in una **posizione nota**: `Documenti/PrintPicker/`. La cartella base si cambia nelle impostazioni ed è indicata sotto il titolo.
- **Click** (o Invio) su una scheda apre la selezione; l'app **riprende da dove si era rimasti** (primo gruppo non ancora visto).
- Il pulsante **⋯** sulla scheda, il tasto destro o il tasto menu danno accesso a:
  - **Apri**;
  - **Apri cartella**;
  - **Rinomina…** (anche con `F2`);
  - **Elimina…** (anche con `Canc` / `Backspace`).
- Senza selezioni la home mostra un breve **benvenuto** che spiega cos'è una selezione.

## Origini

- **Più origini**: in una selezione si possono aggiungere nel tempo più cartelle sorgente (es. foto da Devero e da Camaggiore nella stessa stampa). L'avanzamento è tracciato per ciascuna origine.
- **Cartella padre**: se l'origine contiene sottocartelle, le foto vengono proposte cartella per cartella con una pausa tra l'una e l'altra; il [riepilogo](grouping-workflow.md#riepilogo) mostra le foto scelte per origine e per sottocartella.
- **Origine non trovata** (disco scollegato o percorso cambiato, es. lettera di unità diversa su Windows): l'app avvisa e permette di ricollegare il disco e riprovare, oppure di indicare la nuova posizione della cartella. L'avanzamento resta valido perché le foto sono identificate dal percorso **relativo** all'origine.

## Dati della selezione

Ogni selezione è **autocontenuta**. Dentro la sua cartella c'è una cartella nascosta `.printpicker/` con:

- un database SQLite con
  - cartelle di origine,
  - punto di avanzamento (gruppi visti, scelte fatte),
  - hash delle foto, soglia usata, ecc.;
- le **miniature**.

I dati stanno in una cartella nascosta così che, caricando la cartella sul sito di stampa, non vengano caricati per errore.

Struttura indicativa:

```
Documenti/PrintPicker/
└── Stampa Natale 2026/
    ├── .printpicker/          # nascosta
    │   ├── selection.db       # SQLite: origini, avanzamento, hash, scelte
    │   └── thumbs/            # miniature
    ├── ALPE DEVERO 2026 - 20260101_171918.jpg
    └── ...
```

## Eliminazione

- **Eliminare la cartella = eliminare la selezione**: nessun dato residuo altrove.
- **Elimina…** dal menu ⋯ della scheda: sposta la cartella nel Cestino, previa conferma.
- **Rinomina…** cambia il nome della cartella; origini e avanzamento restano validi.

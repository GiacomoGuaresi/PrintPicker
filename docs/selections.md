# Selezioni per stampa

Il concetto centrale dell'app è la **selezione per stampa**: una cartella sul PC che contiene le foto scelte da mandare in stampa **e** tutti i dati di lavoro di quella selezione.

## Avvio

- All'avvio l'app chiede: **nuova selezione** oppure **apri una selezione esistente**.
- Le selezioni stanno in una **posizione nota**: `Documenti/PrintPicker/` (cartella base modificabile nelle impostazioni), elencate nella schermata iniziale.
- **Nuova selezione**: si inserisce solo il nome (proposto: `Stampa <data di oggi>`, es. `Stampa 2026-10-12`); la cartella viene creata nella posizione base.
- Riaprendo una selezione esistente l'app **riprende da dove si era rimasti** (primo gruppo non ancora visto).

## Origini

- **Più origini**: in una selezione si possono aggiungere nel tempo più cartelle sorgente (es. foto da Devero e da Camaggiore nella stessa stampa). L'avanzamento è tracciato per ciascuna origine.
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
- **Elimina selezione** dalla schermata iniziale: sposta la cartella nel Cestino, previa conferma.

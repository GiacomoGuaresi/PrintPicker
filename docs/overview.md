# Panoramica

PrintPicker è una piccola applicazione di utility per selezionare foto da un archivio e raccoglierle in una cartella sul PC, pronte da mandare in stampa.

## Contesto

- Le foto sono conservate su un hard disk esterno, organizzate in cartelle e sottocartelle (es. per luogo/evento e anno).
- L'obiettivo è sfogliare l'archivio, scegliere le foto da stampare e copiarle in una cartella di destinazione sul PC.
- Dopo la stampa la cartella di destinazione non serve più e viene cancellata.

## Requisiti generali

- **Multipiattaforma**: macOS, Windows e Linux.
- **Semplice e veloce da usare**: poche schermate, interazione immediata, uso completo da tastiera.
- **Non distruttiva**: l'archivio originale non viene mai modificato (solo lettura + copia).

## Feature principali

1. [Selezione per gruppi di foto simili](grouping-workflow.md)
2. [Anteprima costi di stampa](cost-estimate.md)

Entrambe lavorano all'interno di una [selezione per stampa](selections.md).

## Menu e informazioni

- **File**: nuova selezione (Ctrl/⌘+N), mostra la cartella delle selezioni, impostazioni (⌘, su macOS), esci.
- **Aiuto**: guida (README su GitHub), note di rilascio, segnala un problema (apre una issue con versione e sistema già compilati), controlla aggiornamenti, informazioni.
- Su macOS *Informazioni*, *Impostazioni* ed *Esci* stanno nel menu dell'app, come nelle app native.
- La finestra **Informazioni** mostra versione, link (GitHub, segnalazione, licenza), le informazioni di sistema con un pulsante *Copia* da incollare nelle segnalazioni, e i crediti delle librerie usate.

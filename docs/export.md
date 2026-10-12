# Copia ed export

Come le foto scelte vengono scritte nella cartella della [selezione](selections.md).

## Nomi dei file

- **Struttura piatta con prefisso cartella**: il prefisso è il **percorso completo** relativo alla cartella sorgente, con ` - ` come separatore.
  - `2026/ALPE DEVERO/foto.jpg` → `2026 - ALPE DEVERO - foto.jpg`
  - Il percorso è relativo alla cartella sorgente da cui proviene la foto (una selezione può averne più di una).
  - Le foto direttamente nella cartella sorgente usano il **nome della cartella sorgente** come prefisso (es. `Foto 2026 - 20260101_171918.jpg`).
- **Nomi duplicati**: se il file esistente è identico (stesso contenuto) la copia viene saltata; se è diverso si aggiunge un suffisso (`_2`, `_3`, …).

## Formati

- **Conversione in JPG**: HEIC / RAW / TIFF / WebP vengono salvati come JPG ad alta qualità, perché molti servizi di stampa accettano solo JPG.
- JPG e PNG vengono copiati identici.

## Rimozione

- Se una foto viene deselezionata tornando a un gruppo già confermato, il file corrispondente viene rimosso dalla cartella della selezione.

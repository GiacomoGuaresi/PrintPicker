# Sviluppo e test

## Dati di test

Per lo sviluppo si usa una chiavetta USB con un campione dell'archivio reale (su macOS montata in `/Volumes/<nome chiavetta>`):

- ~527 file, ~2.5 GB
- 509 `.jpg`, 18 `.mp4` (i video devono essere ignorati)
- Struttura mista: alcune foto nella root (nomi tipo `20260101_171918.jpg`) e cartelle per evento (`ALPE CAMAGGIORE 2026`, `ALPE DEVERO 2026`)
- Nomi cartella con spazi e maiuscole → da gestire correttamente

Il campione non contiene ancora HEIC, RAW, TIFF o WebP: per testare quei formati servono file aggiuntivi.

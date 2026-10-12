# Architettura

## Stack

- **Linguaggio / UI**: Python + Qt (PySide6).
- **Packaging**: PyInstaller → eseguibili per macOS, Windows, Linux.
- **Librerie immagini** (previste):
  - [Pillow](https://python-pillow.org/) – lettura/scrittura immagini, miniature
  - [NumPy](https://numpy.org/) – perceptual hash (pHash) implementato direttamente, per evitare la dipendenza da `imagehash` + SciPy (~40 MB in più negli eseguibili)
  - [pillow-heif](https://github.com/bigcat88/pillow_heif) – supporto HEIC
  - [rawpy](https://github.com/letmaik/rawpy) – supporto RAW (anteprima e conversione)

## Lingua

- Interfaccia in **italiano e inglese**, scelta in base alla lingua del sistema (traduzioni Qt).

## Somiglianza

- Perceptual hash (pHash a 64 bit: DCT di un'immagine 32×32 in scala di grigi, 8×8 frequenze basse confrontate con la mediana) + distanza di Hamming tra gli hash.
- L'hash si calcola su una versione ridotta (max 256 px, decodifica JPEG in modalità *draft*): sulla chiavetta di test ~230 ms/foto, dominati dalla lettura del file.
- Confronto solo tra foto della stessa cartella.
- La soglia è la distanza massima ammessa ed è regolabile dal cursore live.
- Alternativa futura, se servisse una somiglianza più "semantica": embedding di immagini (più lenti e pesanti).

## Prestazioni

- Analisi in background, per mantenere l'interfaccia reattiva.
- Cache di hash e miniature, per restare veloci anche con centinaia di foto da un disco esterno lento.

## Dati

- Dati, cache e stato stanno tutti dentro la cartella della selezione (`.printpicker/`, SQLite + miniature). Vedi [Selezioni per stampa](selections.md).
- Nulla viene scritto nell'archivio delle foto.
- **Impostazioni globali** (cartella base delle selezioni, listino prezzi) nella cartella di configurazione dell'utente (`QStandardPaths` / `QSettings`): `~/Library/Application Support/PrintPicker` su macOS, `%APPDATA%\PrintPicker` su Windows, `~/.config/PrintPicker` su Linux.

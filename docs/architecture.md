# Architettura

## Stack

- **Linguaggio / UI**: Python + Qt (PySide6).
- **Packaging**: PyInstaller → eseguibili per macOS, Windows, Linux.
- **Librerie immagini** (previste):
  - [Pillow](https://python-pillow.org/) – lettura/scrittura immagini, miniature
  - [imagehash](https://github.com/JohannesBuchner/imagehash) – perceptual hash (pHash/dHash) per la somiglianza
  - [pillow-heif](https://github.com/bigcat88/pillow_heif) – supporto HEIC
  - [rawpy](https://github.com/letmaik/rawpy) – supporto RAW (anteprima e conversione)

## Somiglianza

- Perceptual hash + distanza di Hamming tra gli hash.
- Confronto solo tra foto della stessa cartella.
- La soglia è la distanza massima ammessa ed è regolabile dal cursore live.
- Alternativa futura, se servisse una somiglianza più "semantica": embedding di immagini (più lenti e pesanti).

## Prestazioni

- Analisi in background, per mantenere l'interfaccia reattiva.
- Cache di hash e miniature, per restare veloci anche con centinaia di foto da un disco esterno lento.

## Dati

- Dati, cache e stato stanno tutti dentro la cartella della selezione (`.printpicker/`, SQLite + miniature). Vedi [Selezioni per stampa](selections.md).
- Nulla viene scritto nell'archivio delle foto.

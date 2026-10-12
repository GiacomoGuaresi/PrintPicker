# Sviluppo e test

## Dati di test

Per lo sviluppo si usa una chiavetta USB con un campione dell'archivio reale (su macOS montata in `/Volumes/<nome chiavetta>`):

- ~527 file, ~2.5 GB
- 509 `.jpg`, 18 `.mp4` (i video devono essere ignorati)
- Struttura mista: alcune foto nella root (nomi tipo `20260101_171918.jpg`) e cartelle per evento (`ALPE CAMAGGIORE 2026`, `ALPE DEVERO 2026`)
- Nomi cartella con spazi e maiuscole → da gestire correttamente

Il campione non contiene ancora HEIC, RAW, TIFF o WebP: per testare quei formati servono file aggiuntivi.

## Ambiente di sviluppo

Il progetto usa [uv](https://docs.astral.sh/uv/) per gestire Python (3.12) e le dipendenze.

```sh
uv sync                    # crea .venv e installa le dipendenze
uv run pytest              # test
uv run ruff check .        # lint
uv run ruff format .       # formattazione
```

## CLI di debug

Analizza una cartella e stampa i gruppi, utile per tarare la soglia:

```sh
uv run python -m printpicker.cli /Volumes/<chiavetta> -t 14 --cache hashes.json --sheets fogli/
```

- `-t` soglia (distanza di Hamming massima, 0–64)
- `--cache` riusa gli hash tra un'esecuzione e l'altra (la prima analisi della chiavetta richiede ~2 minuti)
- `--sheets` salva un foglio provini per ogni gruppo con 2+ foto

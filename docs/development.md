# Sviluppo e test

## Dati di test

Per lo sviluppo si usa una chiavetta USB con un campione dell'archivio reale (su macOS montata in `/Volumes/<nome chiavetta>`):

- ~527 file, ~2.5 GB
- 509 `.jpg`, 18 `.mp4` (i video devono essere ignorati)
- Struttura mista: alcune foto nella root (nomi tipo `20260101_171918.jpg`) e cartelle per evento (`ALPE CAMAGGIORE 2026`, `ALPE DEVERO 2026`)
- Nomi cartella con spazi e maiuscole → da gestire correttamente

Il campione non contiene ancora HEIC, RAW, TIFF o WebP: per testare quei formati servono file aggiuntivi.

### Foto di esempio

Un set di foto libere, utilizzabile anche per gli screenshot del README, si genera con:

```sh
uv run python scripts/make_samples.py          # --force per rigenerarlo
```

Scarica ~45 foto da [Lorem Picsum](https://picsum.photos) (licenza Unsplash) e crea in
`samples/` (ignorata da git, ~100 MB) 102 foto in cartelle-viaggio: raffiche di scatti quasi
identici (spostamenti, esposizione, uno sfocato) che formano 21 gruppi con la soglia 14,
foto verticali, 4:3 e quadrate per l'anteprima di ritaglio, HEIC/PNG/WebP/TIFF e una cartella
`Edge cases` (orientamento EXIF, panorama, file illeggibili, video e file nascosti da ignorare).
Gli autori sono in `samples/CREDITS.md`. RAW non incluso.

Per misurare il raggruppamento ci sono anche:

- `Hard cases`: lo stesso scatto reinquadrato, col telefono girato, con un altro bilanciamento
  del bianco o col soggetto spostato, accanto a foto diverse che si somigliano (due scogliere,
  due ponti di notte, …), anche scattate a pochi secondi di distanza;
- `Work desk`: una sessione fotografica vera, etichettata a mano;
- `samples/truth.json`: per ogni cartella i gruppi attesi (`groups`) e le coppie da tenere
  separate (`must_not`). Con `"complete": true` ogni coppia fuori dallo stesso gruppo va tenuta
  separata; altrimenti le coppie non elencate sono ambigue e non si misurano.

Il benchmark confronta i metodi di raggruppamento con questa verità:

```sh
uv run python scripts/eval_grouping.py -v     # --fresh per misurare i tempi senza cache
```

Per ogni metodo cerca la soglia con il richiamo più alto (meno doppioni rimasti separati) a
precisione ≥ 0,9 (poche foto diverse nello stesso gruppo), e dà i numeri su tutte le cartelle
e su quelle difficili (`Hard cases`, `Work desk`); con `-v` elenca le coppie sbagliate.

Gli screenshot del README (`docs/screenshots/`) si rigenerano dall'app vera, con le foto di
esempio, in inglese e con tema chiaro (le impostazioni dell'utente non vengono toccate):

```sh
uv run python scripts/make_screenshots.py
```

## Ambiente di sviluppo

Il progetto usa [uv](https://docs.astral.sh/uv/) per gestire Python (3.12) e le dipendenze.

```sh
uv sync                    # crea .venv e installa le dipendenze
uv run python scripts/fetch_model.py   # modello per il raggruppamento (~44 MB, non in git)
uv run pytest              # test
uv run ruff check .        # lint
uv run ruff format .       # formattazione
```

Il modello (DINOv2, vedi [architettura](architecture.md)) finisce in
`src/printpicker/resources/models/`; senza, l'app funziona lo stesso raggruppando solo con il
perceptual hash e i test che lo usano vengono saltati (in CI sono obbligatori).

## CLI di debug

Analizza una cartella e stampa i gruppi, utile per tarare la soglia:

```sh
uv run python -m printpicker.cli /Volumes/<chiavetta> -t 14 --cache hashes.json --sheets fogli/
```

- `-t` soglia (distanza di Hamming massima, 0–64)
- `--cache` riusa gli hash tra un'esecuzione e l'altra (la prima analisi della chiavetta richiede ~2 minuti)
- `--sheets` salva un foglio provini per ogni gruppo con 2+ foto

## Traduzioni

L'interfaccia è scritta in inglese (`self.tr("...")`) e tradotta in italiano con i file Qt
in `src/printpicker/i18n/`. Dopo aver aggiunto o cambiato testi nell'interfaccia:

1. aggiungere la traduzione nel dizionario `ITALIAN` di `scripts/update_translations.py`;
2. eseguire `uv run python scripts/update_translations.py` (aggiorna `.ts` e compila `.qm`).

Un test verifica che ogni testo sia tradotto e che i file siano aggiornati.

## Build dell'eseguibile

```sh
uv sync --all-groups
uv run pyinstaller packaging/printpicker.spec --noconfirm
```

Risultato in `dist/`: `PrintPicker.app` su macOS, cartella `PrintPicker/` su Windows e Linux
(~250 MB: Qt, onnxruntime ~70 MB e il modello ~44 MB, che va scaricato prima con
`scripts/fetch_model.py`). Per verificare che l'eseguibile contenga tutto (formati HEIC/RAW,
modello, traduzioni, interfaccia):

```sh
dist/PrintPicker.app/Contents/MacOS/PrintPicker --self-test   # macOS
dist/PrintPicker/PrintPicker --self-test                      # Linux (PrintPicker.exe su Windows)
```

# Roadmap

Sviluppo a **piccoli incrementi**: ogni step è piccolo, testabile e lascia il progetto funzionante. Alla fine di ogni step si fa **commit e push**.

## Regole di lavoro

- **Uno step = un commit = un push.** Se uno step si rivela troppo grande, si divide in sotto-step (`3a`, `3b`, …), ognuno con il suo commit.
- **Definition of done** di ogni step:
  1. la funzionalità dello step funziona (verificata sulla chiavetta di test, quando ha senso);
  2. test automatici verdi (`pytest`) e lint pulito (`ruff`);
  3. documentazione in `docs/` aggiornata se è cambiato qualcosa;
  4. commit con messaggio [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, …);
  5. `git push` e CI verde.
- **Branch**: lavoro diretto su `main` finché il progetto è personale; ogni milestone completata viene marcata con un tag (`v0.1.0`, `v0.2.0`, …).
- La logica (scansione, hash, selezioni, export, costi) vive in moduli **senza dipendenze dalla UI**, così è testabile senza Qt.

Legenda stato: ⬜ da fare · 🔄 in corso · ✅ fatto

---

## M0 — Fondamenta del progetto

| # | Step | Commit | Stato |
|---|---|---|---|
| 0.1 | Repo GitHub pubblico, `LICENSE`, `README.md`, `docs/`, primo push | `first commit` | ✅ |
| 0.1b | `.gitignore` Python, aggiornamenti documentazione e roadmap | `docs: roadmap and spec updates` | ✅ |
| 0.2 | `pyproject.toml`, struttura `src/printpicker/` + `tests/`, dipendenze di sviluppo (`pytest`, `ruff`), un test segnaposto | `chore: python project skeleton` | ✅ |
| 0.3 | GitHub Actions: lint + test su macOS, Windows, Linux | `ci: lint and test on all platforms` | ✅ |

## M1 — Motore di analisi (senza interfaccia) → `v0.1.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 1.1 | **Scanner**: scansione ricorsiva, filtro formati supportati, video ignorati, ordine per cartella e nome file | `feat(core): recursive photo scanner` | ✅ |
| 1.2 | **Caricamento immagini**: JPG/PNG/TIFF/WebP con Pillow, orientamento EXIF applicato | `feat(core): image loader with EXIF orientation` | ✅ |
| 1.3 | Supporto **HEIC** (pillow-heif) | `feat(core): HEIC support` | ✅ |
| 1.4 | Supporto **RAW** (rawpy, usando l'anteprima incorporata quando disponibile) | `feat(core): RAW support` | ✅ |
| 1.5 | **Perceptual hash** delle foto | `feat(core): perceptual hashing` | ✅ |
| 1.6 | **Raggruppamento** per cartella con soglia (distanza di Hamming), foto singole come gruppi da 1 | `feat(core): similarity grouping` | ✅ |
| 1.7 | **CLI di debug** (`python -m printpicker.cli <cartella> --threshold N`) che stampa i gruppi: serve a tarare la soglia sulla chiavetta | `feat(cli): debug command to inspect groups` | ✅ |

## M2 — Selezioni ed export (senza interfaccia) → `v0.2.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 2.1 | **Selezione**: creazione / apertura cartella, `.printpicker/selection.db` SQLite con schema versionato | `feat(selection): create and open selections` | ✅ |
| 2.2 | **Origini**: aggiunta di più cartelle sorgente, foto identificate da percorso relativo, rilevamento origine non trovata | `feat(selection): multiple sources with relative paths` | ✅ |
| 2.3 | **Cache hash** nel database (ricalcolo solo se il file cambia: dimensione + data modifica) | `feat(selection): cache hashes in selection db` | ✅ |
| 2.4 | **Nomi in uscita**: prefisso con percorso completo, nome cartella sorgente per i file nella root | `feat(export): output file naming` | ⬜ |
| 2.5 | **Copia**: duplicati identici saltati, suffisso `_2`, `_3` per nomi in conflitto | `feat(export): copy with duplicate handling` | ⬜ |
| 2.6 | **Conversione JPG** per HEIC / RAW / TIFF / WebP | `feat(export): convert non-JPG formats to JPG` | ⬜ |
| 2.7 | **Rimozione** di una foto deselezionata dalla cartella della selezione | `feat(export): remove deselected photos` | ⬜ |
| 2.8 | **Avanzamento**: salvataggio delle scelte per foto e del punto raggiunto per ogni origine | `feat(selection): persist progress and choices` | ⬜ |

> Nota 2.8: le scelte vanno salvate **per foto**, non per indice di gruppo, perché cambiando la soglia i gruppi si ricalcolano.

## M3 — Interfaccia base: il flusso completo → `v0.3.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 3.1 | Scheletro app PySide6, finestra principale, avvio con `python -m printpicker` | `feat(ui): application skeleton` | ⬜ |
| 3.2 | **Schermata iniziale**: elenco selezioni, nuova (nome proposto con data), apri | `feat(ui): start screen` | ⬜ |
| 3.3 | **Elimina selezione** con conferma (spostamento nel Cestino) | `feat(ui): delete selection to trash` | ⬜ |
| 3.4 | **Aggiungi origine** + analisi in background con barra di avanzamento | `feat(ui): add source with background analysis` | ⬜ |
| 3.5 | **Miniature** generate in background e salvate in `.printpicker/thumbs/` | `feat(ui): thumbnail cache` | ⬜ |
| 3.6 | **Vista gruppo**: griglia, click e Ctrl/Cmd+click, conferma → copia → gruppo successivo | `feat(ui): group view with selection and confirm` | ⬜ |
| 3.7 | **Navigazione avanti / indietro**, modifica di un gruppo già confermato | `feat(ui): back and forward navigation` | ⬜ |
| 3.8 | **Ripresa** dal primo gruppo non visto alla riapertura | `feat(ui): resume from last unseen group` | ⬜ |
| 3.9 | **Messaggio di fine origine** con totale e pulsante "apri cartella" | `feat(ui): end of source message` | ⬜ |

## M4 — Velocità d'uso → `v0.4.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 4.1 | **Scorciatoie da tastiera** per selezione e navigazione | `feat(ui): keyboard shortcuts` | ⬜ |
| 4.2 | **Cursore soglia live** con ricalcolo dei gruppi al volo | `feat(ui): live similarity threshold slider` | ⬜ |
| 4.3 | **Anteprima a schermo intero** con frecce tra le foto del gruppo | `feat(ui): full-screen preview` | ⬜ |
| 4.4 | **Zoom e spostamento** (adatta, 100%, zoom libero) | `feat(ui): zoom and pan` | ⬜ |
| 4.5 | **Rotazione della vista** | `feat(ui): view rotation` | ⬜ |
| 4.6 | **Avviso proporzioni** (icona) e **anteprima ritaglio** 3:2 | `feat(ui): aspect ratio warning and crop preview` | ⬜ |

## M5 — Costi e impostazioni → `v0.5.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 5.1 | **Motore prezzi**: scaglioni, costi fissi, listino PhotoSì 10×15 predefinito (solo logica + test) | `feat(pricing): tiered price calculation` | ⬜ |
| 5.2 | **Contatore live** nella barra in basso (`34 foto · ~10,20 €`) | `feat(ui): live photo count and cost` | ⬜ |
| 5.3 | **Impostazioni globali**: cartella base delle selezioni | `feat(settings): base folder setting` | ⬜ |
| 5.4 | **Editor del listino** (tabella scaglioni + costi fissi) nelle impostazioni | `feat(settings): price list editor` | ⬜ |

## M6 — Robustezza e lingue → `v0.6.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 6.1 | **Origine non trovata**: finestra per riprovare o indicare la nuova posizione | `feat(ui): relink missing source` | ⬜ |
| 6.2 | **Traduzioni** italiano / inglese in base alla lingua di sistema | `feat(i18n): italian and english translations` | ⬜ |
| 6.3 | Gestione errori: file corrotti o illeggibili, disco scollegato durante l'analisi | `fix: handle unreadable files and disconnected drives` | ⬜ |

## M7 — Distribuzione → `v1.0.0`

| # | Step | Commit | Stato |
|---|---|---|---|
| 7.1 | **Build PyInstaller** locale per il sistema corrente | `build: pyinstaller packaging` | ⬜ |
| 7.2 | **GitHub Actions**: build per macOS, Windows, Linux e allegati alla release al push di un tag | `ci: build and release executables` | ⬜ |
| 7.3 | **Icona** dell'app e metadati | `chore: app icon and metadata` | ⬜ |
| 7.4 | **README**: screenshot, download, istruzioni d'uso | `docs: usage guide and screenshots` | ⬜ |

---

## Dopo la v1.0 (idee)

- Più formati di stampa (7×10, 13×19, 15×20…) con scelta del formato per foto.
- Somiglianza "semantica" con embedding di immagini.
- Più listini, uno per provider.

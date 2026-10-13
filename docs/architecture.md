# Architettura

## Stack

- **Linguaggio / UI**: Python + Qt (PySide6).
- **Packaging**: PyInstaller → eseguibili per macOS, Windows, Linux.
- **Librerie immagini** (previste):
  - [Pillow](https://python-pillow.org/) – lettura/scrittura immagini, miniature
  - [NumPy](https://numpy.org/) – perceptual hash (pHash) implementato direttamente, per evitare la dipendenza da `imagehash` + SciPy (~40 MB in più negli eseguibili)
  - [pillow-heif](https://github.com/bigcat88/pillow_heif) – supporto HEIC
  - [rawpy](https://github.com/letmaik/rawpy) – supporto RAW (anteprima e conversione)
  - [ONNX Runtime](https://onnxruntime.ai/) – esegue il modello di embedding ([DINOv2](https://github.com/facebookresearch/dinov2) ViT-S/14, fp16, ~44 MB, Apache 2.0) in locale sulla CPU: le foto non lasciano mai il computer

## Lingua

- Interfaccia in **italiano e inglese**, scelta in base alla lingua del sistema (traduzioni Qt).

## Somiglianza

Ogni foto ha una **firma** con due misure, calcolate dalla stessa decodifica della miniatura:

- **Perceptual hash** (pHash a 64 bit: DCT di un'immagine 32×32 in scala di grigi, 8×8 frequenze basse confrontate con la mediana), distanza di Hamming. Riconosce le **copie** della stessa foto (ridimensionata, in bianco e nero, ricompressa) e le raffiche quasi identiche.
- **Embedding DINOv2** (vettore di 384 numeri, distanza coseno): riconosce la **stessa scena scattata di nuovo** anche se reinquadrata, col telefono girato, con un'altra luce o col soggetto spostato, dove il pHash fallisce. L'immagine intera è schiacciata a 224×224 (non ritagliata), così una reinquadratura conserva quasi tutto il contenuto.

La **distanza** tra due foto è la **minore** delle due, espressa in bit di hash: una distanza coseno di 0,15 vale 14 bit (`EMBEDDING_PER_BIT`). Così:

- soglia, cursore (0–24) e selezioni esistenti mantengono lo stesso significato;
- senza modello (o se non si carica) il raggruppamento è identico a prima, solo pHash.

Raggruppamento:

- Confronto solo tra foto della stessa cartella; per ogni cartella la matrice delle distanze si calcola una volta (`PhotoIndex`), il cursore rifà solo l'assegnazione ai gruppi (2000 foto: ~50 ms).
- **Complete linkage**: una foto entra in un gruppo solo se è entro la soglia da **tutte** le foto del gruppo (scegliendo il gruppo col membro più lontano più vicino). Con il *single linkage* i gruppi si "concatenavano" (a soglia 20 un gruppo di 65 foto scattate in ore diverse).
- **Soglia predefinita 14**. Solo pHash era stata tarata sulla chiavetta di test (fino a ~14 raffiche vere, da ~18 abbinamenti sbagliati tra paesaggi con la stessa struttura cielo/terra); con gli embedding è confermata dal benchmark sulle foto di esempio (intervallo buono 12–21,5).

### Come è stato scelto (benchmark)

`scripts/eval_grouping.py` misura i metodi sulle foto di esempio con la verità `samples/truth.json` (vedi [sviluppo](development.md)), privilegiando il richiamo (meno doppioni stampati) a precisione ≥ 0,9. Sui casi difficili (reinquadratura, telefono girato, luce diversa, soggetto spostato, una sessione fotografica vera, foto diverse che si somigliano):

| Metodo | Precisione | Richiamo | Note |
|---|---|---|---|
| pHash | 1,00 | 0,55 | separa reinquadrature, verticali, stessa posa |
| pHash + istogramma colore | 0,90 | 0,82 | unisce skyline e spiaggia: fragile |
| pHash + data di scatto / clustering agglomerativo / pHash 256 bit | 1,00 | ≤ 0,64 | nessun guadagno |
| CLIP ViT-B/32 | 0,62 | 0,45 | troppo "semantico": stesso tema ≠ stessa scena |
| **DINOv2-small + pHash (app)** | **1,00** | **1,00** | ~50 ms/foto; int8 più veloce ma con margine più stretto |

Sulle foto di esempio realistiche le coppie della stessa scena stanno sotto 0,14 di distanza coseno, le foto diverse sopra 0,166 (le più vicine: due ponti di Brooklyn di notte da punti diversi).

## Prestazioni

- Analisi in background, per mantenere l'interfaccia reattiva.
- Cache di firme (hash ed embedding float16) e miniature, per restare veloci anche con centinaia di foto da un disco esterno lento. Le foto analizzate prima che il modello fosse disponibile ricevono l'embedding alla prossima analisi.
- L'analisi usa più thread (uno per core, ONNX Runtime a un thread ciascuno): ~50 ms/foto in tutto sulle foto di esempio, meno della sola lettura da una chiavetta (~230 ms/foto).

## Dati

- Dati, cache e stato stanno tutti dentro la cartella della selezione (`.printpicker/`, SQLite + miniature). Vedi [Selezioni per stampa](selections.md).
- Nulla viene scritto nell'archivio delle foto.
- **Impostazioni globali** (cartella base delle selezioni, listino prezzi) nella cartella di configurazione dell'utente (`QStandardPaths` / `QSettings`): `~/Library/Application Support/PrintPicker` su macOS, `%APPDATA%\PrintPicker` su Windows, `~/.config/PrintPicker` su Linux.

## Metadati dell'app

- `src/printpicker/about.py` è l'unica fonte di nome, versione, autore, copyright e link GitHub: li usano l'interfaccia, la build PyInstaller (`packaging/printpicker.spec`) e i test.
- La versione sta solo in `src/printpicker/__init__.py`; il `pyproject.toml` la legge da lì (`dynamic = ["version"]`). Per una nuova release basta cambiarla lì e creare il tag.

## Aspetto

- **Un solo tema scuro**, uguale su macOS, Windows e Linux: le foto risaltano meglio su un fondo scuro, come nei programmi di fotoritocco. Stile Qt *Fusion* + palette + un foglio di stile globale (`src/printpicker/ui/theme.py`); anche la barra del titolo è scura dove il sistema lo permette.
- I colori sono **token** presi dal logo: teal (`ACCENT`) per azioni, focus e selezione, ambra (`PICK`) per le foto scelte. Nessun colore scritto a mano fuori da `theme.py` (lo controlla un test); i widget scelgono una variante con `set_role` (`primary`, `muted`, `title`…).
- Font **Inter** (SIL OFL) incluso nell'app; se manca resta il font di sistema.
- **Icone** [Lucide](https://lucide.dev) (ISC) in `resources/icons/`, colorate al volo con `theme.icon(nome, colore)`; il logo dell'app (`resources/logo.svg`) con `theme.logo(dimensione)`. Il self-test della build verifica che le icone SVG vengano disegnate.
- **Stati visivi** coerenti ovunque: foto scelta = anello e spunta **ambra** (vista gruppo, anteprima, striscia); cursore della tastiera = anello **teal** sottile; passaggio del mouse = anello grigio. Le pagine senza foto (nessuna origine, analisi, errore, fine) hanno icona, titolo, testo e pulsanti.
- La finestra ricorda posizione e dimensione (`window/geometry` nelle impostazioni).
- **Aggiornamenti**: le regole stanno in `core/updates.py` (senza Qt: confronto versioni, lettura della release, una volta al giorno, versione saltata); `ui/update_checker.py` fa la richiesta con QtNetwork (TLS del sistema; il self-test della build verifica che ci sia). Senza release pubblicate GitHub risponde 404, che vale come "nessun aggiornamento".

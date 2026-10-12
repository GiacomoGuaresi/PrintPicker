"""Refresh the translation files: extract strings, fill Italian translations, compile.

    uv run python scripts/update_translations.py

1. ``pyside6-lupdate`` extracts the strings of ``src/printpicker/ui`` into ``.ts`` files;
2. the Italian translations in ``ITALIAN`` (below) are written into ``printpicker_it.ts``;
3. ``pyside6-lrelease`` compiles the ``.qm`` file loaded at run time.

New strings without a translation are reported and the script exits with an error.
"""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "src" / "printpicker" / "ui"
I18N = ROOT / "src" / "printpicker" / "i18n"
TS = I18N / "printpicker_it.ts"

# source text -> translation; plural forms (with %n) as (singular, plural).
ITALIAN: dict[str, str | tuple[str, str]] = {
    # Group view / viewer
    "Click": "Clic",
    "Space": "Spazio",
    "pick": "scegli",
    "all / none": "tutte / nessuna",
    "groups": "gruppi",
    "photos": "foto",
    "preview": "anteprima",
    "crop": "ritaglio",
    "browse": "sfoglia",
    "zoom": "zoom",
    "fit": "adatta",
    "rotate": "ruota",
    "close": "chiudi",
    "%1\nWill be cropped to fit a 10×15 print": "%1\nVerrà ritagliata per la stampa 10×15",
    "Unreadable": "Illeggibile",
    "Preview": "Anteprima",
    "Picked": "Scelta",
    "Previous photo (←)": "Foto precedente (←)",
    "Next photo (→)": "Foto successiva (→)",
    "Close (Esc)": "Chiudi (Esc)",
    "Pick": "Scegli",
    "Pick (Space)": "Scegli (Spazio)",
    "Zoom out (−)": "Riduci (−)",
    "Fit": "Adatta",
    "Fit to screen (0)": "Adatta allo schermo (0)",
    "Zoom in (+)": "Ingrandisci (+)",
    "Rotate (R)": "Ruota (R)",
    "will be cropped to 10×15": "verrà ritagliata per il 10×15",
    # Session
    "← Selections": "← Selezioni",
    "Add source…": "Aggiungi origine…",
    "Source:": "Origine:",
    "Settings…": "Impostazioni…",
    "Add a folder of your photo archive to start choosing photos.": (
        "Aggiungi una cartella del tuo archivio di foto per iniziare a scegliere."
    ),
    "Cancel": "Annulla",
    "Retry": "Riprova",
    "The folder has moved: choose it…": "La cartella è stata spostata: indicala…",
    "Choose a folder of photos": "Scegli una cartella di foto",
    "Where is “%1” now?": "Dove si trova ora “%1”?",
    "Different folder?": "Cartella diversa?",
    "None of the photos analysed before are in “%1”.\nUse this folder for “%2” anyway?": (
        "Nessuna delle foto analizzate in precedenza si trova in “%1”.\n"
        "Usare comunque questa cartella per “%2”?"
    ),
    "Source": "Origine",
    "This folder is already another source of the selection.": (
        "Questa cartella è già un'altra origine della selezione."
    ),
    "The folder “%1” cannot be found.\n\n"
    "Connect the drive and press Retry, or choose where the folder is now.": (
        "La cartella “%1” non è stata trovata.\n\n"
        "Collega il disco e premi Riprova, oppure indica dove si trova ora la cartella."
    ),
    "Analysing “%1”…": "Analisi di “%1”…",
    "Analysis interrupted. Photos analysed so far are kept.": (
        "Analisi interrotta. Le foto analizzate finora restano salvate."
    ),
    "%1 of %2 photos": "%1 di %2 foto",
    "The analysis failed:\n%1": "L'analisi non è riuscita:\n%1",
    "Next group →": "Gruppo successivo →",
    "← Previous group": "← Gruppo precedente",
    "← or Backspace · your picks are kept": "← o Backspace · le scelte restano salvate",
    "→ or Enter · your picks are kept": "→ o Invio · le scelte restano salvate",
    "How different two photos can be to end up in the same group": (
        "Quanto possono essere diverse due foto per finire nello stesso gruppo"
    ),
    "Grouping: strict": "Raggruppamento: rigido",
    "loose": "permissivo",
    "<b>%1</b> — group %2 of %3 · %n photo(s)": (
        "<b>%1</b> — gruppo %2 di %3 · %n foto",
        "<b>%1</b> — gruppo %2 di %3 · %n foto",
    ),
    "Copy failed": "Copia non riuscita",
    "Could not copy the photo:\n%1": "Impossibile copiare la foto:\n%1",
    "Open the selection folder": "Apri la cartella della selezione",
    "Add another source…": "Aggiungi un'altra origine…",
    "<h2>Done!</h2>All the photos of “%1” have been reviewed.<br><br>%2": (
        "<h2>Fatto!</h2>Hai visto tutte le foto di “%1”.<br><br>%2"
    ),
    "Photos to print: <b>%1</b>": "Foto da stampare: <b>%1</b>",
    "Estimate with “%1”: %2 per photo": "Stima con “%1”: %2 a foto",
    "Selected in this group: %1": "Scelte in questo gruppo: %1",
    # Settings
    "Settings": "Impostazioni",
    "Browse…": "Sfoglia…",
    "Default": "Predefinita",
    "New selections are created here. Existing ones are not moved.": (
        "Le nuove selezioni vengono create qui. Quelle esistenti non vengono spostate."
    ),
    "Selections folder:": "Cartella delle selezioni:",
    "Selections folder": "Cartella delle selezioni",
    "Print price list (for the cost estimate)": "Listino di stampa (per la stima dei costi)",
    "From photos": "Da foto",
    "Price per photo": "Prezzo a foto",
    "Fixed cost": "Costo fisso",
    "Amount": "Importo",
    "Add": "Aggiungi",
    "Remove": "Rimuovi",
    "Restore PhotoSì 10×15 prices": "Ripristina prezzi PhotoSì 10×15",
    "Shipping": "Spedizione",
    "Name:": "Nome:",
    "The price of the tier reached applies to all the photos "
    "(e.g. 120 photos all at the “from 100” price).": (
        "Il prezzo dello scaglione raggiunto vale per tutte le foto "
        "(es. 120 foto tutte al prezzo “da 100”)."
    ),
    "Row %1 of the tiers is not valid.": "La riga %1 degli scaglioni non è valida.",
    "Row %1 of the fixed costs is not valid.": "La riga %1 dei costi fissi non è valida.",
    "Price list": "Listino",
    "The tiers must start from 1 photo, with different quantities and non-negative prices.": (
        "Gli scaglioni devono partire da 1 foto, con quantità diverse e prezzi non negativi."
    ),
    "%1 photos ≈ %2": "%1 foto ≈ %2",
    "Examples: ": "Esempi: ",
    # Start screen
    "Selections in %1": "Selezioni in %1",
    "<b>Welcome!</b> A print selection is a folder on your computer where the "
    "photos you choose from your archive are copied, ready to be sent to print. "
    "Create your first one to start.": (
        "<b>Benvenuto!</b> Una selezione per la stampa è una cartella sul tuo computer in cui "
        "vengono copiate le foto che scegli dal tuo archivio, pronte da mandare in stampa. "
        "Crea la prima per iniziare."
    ),
    "Create a new print selection": "Crea una nuova selezione per la stampa",
    "No photos yet": "Ancora nessuna foto",
    "%n photo(s)": ("%n foto", "%n foto"),
    "Updated today": "Modificata oggi",
    "Updated yesterday": "Modificata ieri",
    "Updated %n day(s) ago": ("Modificata %n giorno fa", "Modificata %n giorni fa"),
    "Updated on %1": "Modificata il %1",
    "Open": "Apri",
    "Open folder": "Apri cartella",
    "Rename…": "Rinomina…",
    "Delete…": "Elimina…",
    "Rename selection": "Rinomina selezione",
    "New name:": "Nuovo nome:",
    "Could not rename the selection: %1": "Impossibile rinominare la selezione: %1",
    "Print": "Stampa",
    "New selection": "Nuova selezione",
    "Name of the selection:": "Nome della selezione:",
    "A selection with this name already exists.": "Esiste già una selezione con questo nome.",
    "This name cannot be used for a folder.": "Questo nome non può essere usato per una cartella.",
    "Could not create the selection: %1": "Impossibile creare la selezione: %1",
    "Delete selection": "Elimina selezione",
    "Move the selection “%1” and the photos it contains to the trash?\n\n"
    "The original photos in your archive are not touched.": (
        "Spostare nel Cestino la selezione “%1” e le foto che contiene?\n\n"
        "Le foto originali del tuo archivio non vengono toccate."
    ),
    "Could not move “%1” to the trash.": "Impossibile spostare “%1” nel Cestino.",
}


def run(*args: str) -> None:
    subprocess.run(args, check=True, cwd=ROOT, stdout=subprocess.DEVNULL)


def fill(ts: Path) -> list[str]:
    tree = ET.parse(ts)
    missing = []
    for message in tree.getroot().iter("message"):
        source = message.find("source").text or ""
        translation = message.find("translation")
        value = ITALIAN.get(source)
        if value is None:
            missing.append(source)
            continue
        translation.attrib.pop("type", None)
        if message.get("numerus") == "yes":
            for child in list(translation):
                translation.remove(child)
            translation.text = None
            for form in value if isinstance(value, tuple) else (value, value):
                ET.SubElement(translation, "numerusform").text = form
        else:
            translation.text = value
    tree.write(ts, encoding="utf-8", xml_declaration=True)
    return missing


def main() -> int:
    I18N.mkdir(parents=True, exist_ok=True)
    sources = sorted(str(p.relative_to(ROOT)) for p in UI.glob("*.py"))
    run("pyside6-lupdate", *sources, "-no-obsolete", "-target-language", "it_IT", "-ts", str(TS))
    missing = fill(TS)
    run("pyside6-lrelease", str(TS), "-qm", str(TS.with_suffix(".qm")))
    if missing:
        print("Missing Italian translations:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

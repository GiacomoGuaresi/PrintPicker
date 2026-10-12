# Selezione per gruppi di foto simili

Flusso principale dell'app.

## Flusso

1. Nella [selezione](selections.md) corrente l'utente aggiunge o riprende una **cartella sorgente** dell'archivio.
2. L'app analizza le foto e le raggruppa in **gruppi di foto visivamente simili** (somiglianza oltre una soglia).
3. I gruppi vengono proposti **uno alla volta**.
4. Per ogni gruppo l'utente può selezionare:
   - **nessuna** foto,
   - **una** foto (click),
   - **più** foto (Ctrl+click / Cmd+click su macOS).
5. Confermando, le foto selezionate vengono [copiate](export.md) nella cartella della selezione e l'app **passa al gruppo successivo**.

## Scansione e raggruppamento

- **Scansione ricorsiva**: la cartella scelta e tutte le sue sottocartelle.
- **Gruppi per cartella**: foto di cartelle diverse non finiscono mai nello stesso gruppo.
- **Foto singole** (senza foto simili): proposte comunque, **una alla volta**, come gruppi da 1.
- **Ordine**: per cartella, poi per nome file (alfabetico, come in Finder / Esplora risorse).
- **Formati supportati**: JPG, PNG, HEIC, RAW (CR2, NEF, ARW, DNG, …), TIFF, WebP.
- **Video ignorati** (`.mp4`, `.mov`, …).

## Soglia di somiglianza

- **Cursore live** sempre visibile ("più rigido ↔ più permissivo"): i gruppi si ricalcolano al volo.

## Navigazione e revisione

- **Avanti / indietro** tra i gruppi; si può modificare la scelta di un gruppo già confermato.
  - Se si deseleziona una foto già copiata, viene **rimossa dalla cartella della selezione**.
- **Anteprima a schermo intero** (doppio click o tasto) con zoom al 100% e frecce per confrontare le foto del gruppo.

### Scorciatoie da tastiera (proposta)

| Tasto | Azione |
|---|---|
| Frecce | Spostarsi tra le foto del gruppo |
| Spazio | Seleziona / deseleziona la foto corrente |
| Invio | Conferma e passa al gruppo successivo |
| Backspace | Torna al gruppo precedente |
| `F` / `Z` | Anteprima a schermo intero |

## Schermata di selezione

Griglia delle foto del gruppo al centro, barra in basso con navigazione, slider soglia e contatori (incluso il [costo stimato](cost-estimate.md)):

```
+--------------------------------------------+
| ALPE DEVERO 2026      Gruppo 12 / 87       |
+--------------------------------------------+
|  [foto1]   [foto2]*   [foto3]              |
|  [foto4]*  [foto5]                         |
+--------------------------------------------+
| < Indietro  Soglia [---o----]  Avanti >    |
| Selezionate: 2   34 foto · ~10,20 €        |
+--------------------------------------------+
```

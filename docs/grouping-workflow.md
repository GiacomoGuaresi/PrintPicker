# Selezione per gruppi di foto simili

Flusso principale dell'app.

## Flusso

1. Nella [selezione](selections.md) corrente l'utente aggiunge o riprende una **cartella sorgente** dell'archivio.
2. L'app analizza le foto e le raggruppa in **gruppi di foto visivamente simili** (somiglianza oltre una soglia).
3. I gruppi vengono proposti **uno alla volta**.
4. Per ogni gruppo l'utente può selezionare:
   - **nessuna** foto,
   - **una o più** foto: un **click** sceglie o toglie la foto (nessun Ctrl/Shift); ogni miniatura ha una **casella di spunta** sempre visibile.
5. Passando al gruppo successivo (→ o Invio) **o tornando indietro** (←), le scelte del gruppo vengono salvate: le foto scelte sono [copiate](export.md) nella cartella della selezione, nulla va perso.

## Scansione e raggruppamento

- **Scansione ricorsiva**: la cartella scelta e tutte le sue sottocartelle.
- **Gruppi per cartella**: foto di cartelle diverse non finiscono mai nello stesso gruppo.
- **Foto singole** (senza foto simili): proposte comunque, **una alla volta**, come gruppi da 1.
- **Ordine**: per cartella, poi per nome file (alfabetico, come in Finder / Esplora risorse).
- **Formati supportati**: JPG, PNG, HEIC, RAW (CR2, NEF, ARW, DNG, …), TIFF, WebP.
- **Video ignorati** (`.mp4`, `.mov`, …).
- **Foto identiche in cartelle diverse** (es. backup doppi): nessuna logica speciale, compaiono nei gruppi della rispettiva cartella.

## Soglia di somiglianza

- **Cursore live** sempre visibile ("più rigido ↔ più permissivo"): i gruppi si ricalcolano al volo.

## Navigazione e revisione

- **Avanti / indietro** tra i gruppi con le frecce ← →; si può modificare la scelta di un gruppo già visto.
  - Se si deseleziona una foto già copiata, viene **rimossa dalla cartella della selezione**.
- **Anteprima a schermo intero** (doppio click, tasto `F` o lente 🔍 che compare sulla miniatura al passaggio del mouse; il doppio click non cambia la scelta) con frecce per confrontare le foto del gruppo:
  - le foto vicine sono **precaricate**, così sfogliando si vede subito la foto a piena risoluzione;
  - una foto scelta ha una **cornice colorata** e il badge **✓ Scelta** in alto a destra;
  - **controlli col mouse**: ‹ › ai lati e ✕ in alto, che si nascondono col cursore dopo 2 s di mouse fermo; nella barra in basso *Scegli*, zoom e rotazione;
  - **striscia delle miniature** del gruppo (corrente incorniciata, scelte con la spunta): un clic salta a quella foto;
  - doppio click sulla foto: adatta ↔ 100% sul punto cliccato.

### Strumenti di visualizzazione

Servono solo a **guardare bene** le foto e scegliere la migliore: **non modificano** né l'originale né la copia salvata nella selezione.

- Zoom (adatta alla finestra, 100%, zoom libero) e spostamento sull'immagine ingrandita.
- Rotazione della vista (90° a sinistra / destra).
- Orientamento EXIF applicato automaticamente.

### Avviso proporzioni e ritaglio

- Le foto con proporzioni diverse dal formato di stampa (10×15 = **3:2**) mostrano un'**icona d'avviso** nella griglia.
- Un'**anteprima del ritaglio** sovrappone alla foto l'area che verrà effettivamente stampata (parti escluse oscurate).
- È solo un'indicazione: la foto viene copiata intera, il ritaglio lo fa il servizio di stampa.

### Fine dell'origine

- Visti tutti i gruppi di un'origine, l'app mostra un **messaggio di fine** con il totale (foto e costo stimato) e un pulsante per **aprire la cartella** della selezione.

### Scorciatoie da tastiera

| Tasto | Azione |
|---|---|
| Click | Seleziona / deseleziona la foto |
| → / Invio | Gruppo successivo (scelte salvate) |
| ← / Backspace | Gruppo precedente (scelte salvate) |
| ↑ ↓ / Tab | Spostarsi tra le foto del gruppo |
| Spazio | Seleziona / deseleziona la foto corrente |
| `1`–`9` | Seleziona / deseleziona la foto n-esima del gruppo |
| `A` | Seleziona tutte / nessuna |
| Tasti avanti / indietro del mouse | Gruppo successivo / precedente |
| `F` / `Z` | Anteprima a schermo intero |
| `R` / `Shift+R` | Ruota la vista a destra / sinistra |
| `+` / `-` / `0` | Zoom avanti / indietro / adatta |
| `C` | Mostra / nascondi anteprima ritaglio |

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

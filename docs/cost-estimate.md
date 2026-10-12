# Anteprima costi di stampa

L'app mostra una **stima indicativa** del numero di foto e del costo totale della selezione, in base a un listino configurabile. Il listino deve restare generico e modificabile (il provider potrebbe cambiare).

## Comportamento

- **Contatore sempre visibile**: numero di foto nella selezione + costo stimato, aggiornati a ogni scelta (es. nella barra in basso: `34 foto · ~10,20 €`).
- **Listino a scaglioni configurabile** (tabella modificabile dall'utente).
- **Costi fissi** opzionali (es. spedizione, costo ordine minimo) da sommare al totale.
- La stima è **approssimativa**: è un aiuto per decidere quante foto tenere, non un preventivo.

## Listino predefinito

PhotoSì, stampe **10×15** (prezzi rilevati il 2026-10-12):

| Da | A | Prezzo per foto |
|---:|---:|---:|
| 1 | 19 | 0,35 € |
| 20 | 99 | 0,30 € |
| 100 | 199 | 0,25 € |
| 200 | 399 | 0,19 € |
| 400 | — | 0,16 € |

## Calcolo

Il prezzo dello scaglione raggiunto si applica a **tutte** le foto, come negli "sconti quantità" di PhotoSì:

```
totale = numero_foto × prezzo_scaglione(numero_foto) + costi_fissi
```

Esempio: 120 foto → 120 × 0,25 € = 30,00 €.

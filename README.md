# Radar bandi PA – Trirevi Consulting / Davide Vulpetti

Ogni mattina interroga la **Piattaforma di Pubblicità a Valore Legale dell'ANAC**, dove dal
1° gennaio 2024 vengono pubblicati tutti i bandi e gli avvisi di gara italiani, e salva le
opportunità adatte a:

- **profilo A – Davide Vulpetti**: revisione legale, collegio sindacale, OIV, OdV 231, consulenza fiscale;
- **profilo B – Trirevi Consulting S.r.l.**: supporto amministrativo-contabile, paghe, controllo di
  gestione, rendicontazione PNRR/fondi UE, informatica, formazione.

Filtri: codici CPV (lato ANAC), territorio (provincia di Trapani → Sicilia → resto d'Italia solo
per incarichi del profilo A o da remoto), parole chiave, esclusioni (tesoreria, assicurazioni,
pulizie…). Esiti, forniture, lavori e avvisi scaduti vengono scartati.

## Cosa produce

| File | Contenuto |
|---|---|
| `data/ultimi.md` | tabella leggibile delle opportunità aperte (🆕 = nuove da ieri) |
| `data/ultimi.json` | gli stessi dati, letti dalla ricerca programmata di Claude |
| `data/storico.json` | gli avvisi già visti, per riconoscere le novità |

La ricerca programmata di Claude (lunedì e giovedì) legge `ultimi.json`, aggiunge ciò che ANAC
non copre (nomine di sindaci e revisori, albi fornitori, avvisi sui siti degli enti), confronta i
requisiti con il profilo, aggiorna il registro bandi e manda la notifica.

## Messa in funzione (10 minuti, una volta sola)

1. Crea un account su **github.com** (gratuito), se non ce l'hai.
2. In alto a destra **+ → New repository**: nome `radar-bandi-trirevi`, visibilità **Public**
   (i bandi sono dati pubblici e così Claude può leggere i risultati senza password; nel
   repository non ci sono dati riservati). Crea il repository vuoto.
3. Nella pagina del repository: **uploading an existing file** → trascina tutto il contenuto
   della cartella estratta dallo zip (comprese le cartelle `radar`, `data`, `tests` e `.github`)
   → **Commit changes**.
   *Se la cartella `.github` non viene caricata* (alcuni sistemi nascondono le cartelle che
   iniziano col punto): **Add file → Create new file**, nome `.github/workflows/radar.yml`,
   incolla il contenuto del file e salva.
4. **Settings → Actions → General → Workflow permissions → Read and write permissions** → Save.
5. **Actions → Radar bandi PA → Run workflow** per il primo giro. Dopo un paio di minuti in
   `data/ultimi.md` trovi i risultati. Da lì in poi gira da solo ogni mattina.

Il primo giro marca tutto come "nuovo": serve a costruire lo storico.

## Come affinarlo

Tutto il vocabolario sta in `radar/config.py`: codici CPV, parole chiave per profilo,
esclusioni, punteggi, soglia di importo oltre cui segnalare i requisiti di fatturato.
Dopo una modifica: `python tests/test_radar.py`.

## Note

- Nessuna dipendenza esterna: solo la libreria standard di Python 3.
- L'endpoint ANAC (`/api/v0/avvisi-full-text-specializzata`) è quello usato dalla ricerca
  avanzata del portale PVL; non è un'API documentata ufficialmente, quindi se ANAC lo cambia
  il workflow fallisce e GitHub manda una mail all'account.
- Elenco dei comuni siciliani da dati ISTAT (licenza CC BY 3.0 IT), tramite
  `matteocontrini/comuni-json`, con l'aggiunta di Misiliscemi.

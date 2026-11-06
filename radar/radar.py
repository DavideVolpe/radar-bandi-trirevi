"""
Radar bandi PA per Trirevi Consulting S.r.l. e Davide Vulpetti.

Interroga la Piattaforma di Pubblicità a Valore Legale (PVL) dell'ANAC, dove dal
1° gennaio 2024 vengono pubblicati tutti i bandi e gli avvisi di gara italiani,
filtra per codici CPV, territorio e parole chiave e salva:

    data/ultimi.json   le opportunità aperte, con punteggio e profilo
    data/ultimi.md     la stessa lista in forma leggibile
    data/storico.json  gli ID già visti, per marcare le novità

Uso:
    python radar/radar.py                  # ultimi 10 giorni (default)
    python radar/radar.py --giorni 30
    python radar/radar.py --input campione.json   # prova offline su un JSON salvato
"""

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as C  # noqa: E402

BASE = "https://pubblicitalegale.anticorruzione.it"
ENDPOINT = f"{BASE}/api/v0/avvisi-full-text-specializzata"
RADICE = Path(__file__).resolve().parent.parent
DATI = RADICE / "data"
PAGE_SIZE = 100
TENTATIVI = 3
PAUSA = 0.8


# ---------------------------------------------------------------------------
# Utilità di testo
# ---------------------------------------------------------------------------
def pulisci(testo):
    """Minuscolo, senza accenti, spazi normalizzati."""
    t = unicodedata.normalize("NFKD", str(testo or "")).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def _regex(termine):
    t = pulisci(termine)
    fine = r"\b" if len(t) <= 4 else ""
    return re.compile(r"(?<![a-z0-9])" + re.escape(t) + fine)


def trova(termini, testo):
    return [t for t in termini if _regex(t).search(testo)]


# ---------------------------------------------------------------------------
# Territorio
# ---------------------------------------------------------------------------
_COMUNI = json.loads((Path(__file__).parent / "comuni_sicilia.json").read_text(encoding="utf-8"))
COMUNI_TP = {pulisci(c) for c in _COMUNI["TP"]}
COMUNI_SICILIA = {pulisci(c) for c in _COMUNI["SICILIA"]}
PROVINCE_SICILIA = {"agrigento", "caltanissetta", "catania", "enna", "messina",
                    "palermo", "ragusa", "siracusa", "trapani"}


def territorio(luogo, ente):
    """'TP', 'SICILIA' oppure 'ALTRO'. Guarda il luogo di esecuzione e il nome dell'ente."""
    l, e = pulisci(luogo), pulisci(ente)
    if l.upper().startswith("ITG11") or l in COMUNI_TP:
        return "TP"
    # "Comune di Erice", "Libero Consorzio comunale di Trapani", "ASP Trapani" ...
    for c in COMUNI_TP:
        if len(c) > 4 and re.search(r"(?<![a-z])" + re.escape(c) + r"(?![a-z])", e):
            return "TP"
    if re.search(r"\b(comune|citta) di vita\b", e):
        return "TP"
    if l.upper().startswith("ITG1") or l in COMUNI_SICILIA or l in PROVINCE_SICILIA:
        return "SICILIA"
    if "sicilia" in e or "siciliana" in e:
        return "SICILIA"
    for p in PROVINCE_SICILIA:
        if re.search(r"(?<![a-z])" + p + r"(?![a-z])", e):
            return "SICILIA"
    return "ALTRO"


# ---------------------------------------------------------------------------
# Chiamata all'API ANAC
# ---------------------------------------------------------------------------
def _chiama(params):
    url = ENDPOINT + "?" + urllib.parse.urlencode(params, safe=",/")
    errore = None
    for n in range(1, TENTATIVI + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (radar-bandi-trirevi)",
                "Accept": "application/json",
                "Accept-Language": "it-IT,it;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            errore = e
            time.sleep(2 * n)
    raise RuntimeError(f"ANAC non raggiungibile: {errore}\n{url}")


def scarica(da, a):
    """Tutti gli avvisi grezzi nella finestra, per i gruppi CPV configurati."""
    grezzi = {}
    pref = C.CPV_PREFISSI
    gruppi = [pref[i:i + C.CPV_PER_CHIAMATA] for i in range(0, len(pref), C.CPV_PER_CHIAMATA)]
    for g in gruppi:
        pagina, totale = 0, None
        while True:
            risp = _chiama({
                "page": pagina, "pageSize": PAGE_SIZE,
                "dataPubblicazioneStart": da, "dataPubblicazioneEnd": a,
                "cpv": ",".join(g), "sortField": "dataPubblicazione",
                "sortDirection": "desc", "operatore": "AND",
            })
            contenuto = risp.get("content") or []
            if totale is None:
                totale = int(risp.get("count") or 0)
                print(f"[anac] CPV {g[0]}…{g[-1]}: {totale} avvisi", file=sys.stderr)
            for av in contenuto:
                if av.get("idAvviso"):
                    grezzi[av["idAvviso"]] = av
            pagina += 1
            if not contenuto or pagina * PAGE_SIZE >= totale or pagina > 50:
                break
            time.sleep(PAUSA)
    return list(grezzi.values())


# ---------------------------------------------------------------------------
# Normalizzazione di un avviso PVL
# ---------------------------------------------------------------------------
def _sezione(template, prefisso):
    for s in template.get("sections") or []:
        if str(s.get("name", "")).upper().startswith(prefisso):
            return s
    return {}


def _data(valore):
    if not valore:
        return None
    s = str(valore)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return s[:10] if len(s) >= 10 else None


def _primo(*valori):
    for v in valori:
        if v not in (None, "", []):
            return v
    return None


def normalizza(av):
    tpl = ((av.get("templates") or [{}])[0] or {}).get("template") or {}
    meta = tpl.get("metadata") or {}
    sez_a = _sezione(tpl, "SEZ. A").get("fields") or {}
    sez_b = _sezione(tpl, "SEZ. B").get("fields") or {}
    items = _sezione(tpl, "SEZ. C").get("items") or []
    primo = items[0] if items else {}
    soggetti = sez_a.get("soggetti_sa") or [{}]

    descr = _primo(meta.get("descrizione"), primo.get("descrizione")) or ""
    titolo = " ".join(str(_primo(meta.get("titolo"), descr) or "(senza titolo)").split())
    stimati = [i.get("valore_complessivo_stimato") for i in items
               if isinstance(i.get("valore_complessivo_stimato"), (int, float))]
    momento = C.MOMENTI.get(av.get("tipologia"), "altro")
    rotta = {"gara": "bandi", "esito": "esiti"}.get(momento, "avvisi")
    luogo = _primo(*[i.get("luogo_nuts") or i.get("luogo_istat") for i in items]) or ""

    return {
        "id": av.get("idAvviso"),
        "cig": _primo(*[i.get("cig") for i in items]),
        "titolo": titolo[:300],
        "descrizione": " ".join(str(descr).split())[:1500],
        "ente": soggetti[0].get("denominazione_amministrazione"),
        "cf_ente": soggetti[0].get("codice_fiscale"),
        "natura": (primo.get("natura_principale") or "").lower(),
        "cpv": [i.get("cpv") for i in items if i.get("cpv")],
        "tipologia_anac": av.get("tipologia"),
        "momento": momento,
        "importo": sum(stimati) if stimati else None,
        "luogo": luogo,
        "pubblicazione": _data(av.get("dataPubblicazione")),
        "scadenza": _primo(_data(av.get("dataScadenza")), _data(primo.get("termine_invito")),
                           _data(primo.get("termine_ricezione_offerte"))),
        "url": f"{BASE}/{rotta}/{av.get('idAvviso')}",
        "documenti": _primo(primo.get("documenti_di_gara_link"), sez_b.get("documenti_di_gara_link")),
    }


# ---------------------------------------------------------------------------
# Valutazione
# ---------------------------------------------------------------------------
def valuta(r):
    """Aggiunge territorio, profilo, punteggio e motivazioni. Ritorna None se va scartato."""
    if r["momento"] not in C.MOMENTI_UTILI:
        return None
    if r["natura"] and r["natura"] not in ("servizi", ""):
        return None  # forniture e lavori
    testo = pulisci(f"{r['titolo']} {r['descrizione']} {' '.join(r['cpv'])}")
    esclusi = trova(C.ESCLUSIONI, testo)
    if esclusi:
        return None

    terr = territorio(r["luogo"], r["ente"])
    punteggi, motivi, forti_per = {}, {}, {}
    for k, prof in C.PROFILI.items():
        forti = trova(prof["forti"], testo)
        deboli = trova(prof["deboli"], testo)
        p = C.PUNTI_CPV + C.PUNTI_FORTE * min(len(forti), 2) + C.PUNTI_DEBOLE * min(len(deboli), 3)
        punteggi[k], motivi[k], forti_per[k] = p, forti + deboli, forti

    profilo = max(punteggi, key=punteggi.get)
    p = punteggi[profilo]
    if r["momento"] == "manifestazione":
        p += C.PUNTI_MANIFESTAZIONE
    p += {"TP": C.PUNTI_TP, "SICILIA": C.PUNTI_SICILIA}.get(terr, 0)

    if terr == "ALTRO":
        remoto = bool(trova(C.TERMINI_REMOTO, testo))
        forti_a = trova(C.PROFILI["A"]["forti"], testo)
        if not (remoto or forti_a):
            return None

    entrambi = [k for k in punteggi if k != profilo and forti_per[k] and forti_per[profilo]]
    avvisi = []
    if r["importo"] and r["importo"] > C.IMPORTO_ATTENZIONE:
        avvisi.append(f"importo oltre {C.IMPORTO_ATTENZIONE:,.0f} €: verificare requisiti di fatturato".replace(",", "."))

    r.update({
        "territorio": terr,
        "profilo": profilo if not entrambi else "A+B",
        "punteggio": min(p, 100),
        "parole_chiave": sorted(set(motivi[profilo] + sum((motivi[k] for k in entrambi), []))),
        "attenzione": avvisi,
    })
    return r if r["punteggio"] >= C.SOGLIA_REPORT else None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def scrivi_md(record, path, da, a):
    righe = [f"# Radar bandi PA – Trirevi / Vulpetti",
             f"Finestra di pubblicazione {da} → {a} · aggiornato "
             f"{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC · {len(record)} opportunità",
             "", "| Nuovo | Punti | Profilo | Territorio | Ente | Oggetto | Procedura | Importo | Scadenza | Link |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in record:
        imp = f"{r['importo']:,.0f} €".replace(",", ".") if r["importo"] else "n.d."
        ogg = r["titolo"].replace("|", "/")[:140]
        righe.append(f"| {'🆕' if r['nuovo'] else ''} | {r['punteggio']} | {r['profilo']} | {r['territorio']} | "
                     f"{(r['ente'] or '').replace('|', '/')} | {ogg} | {r['momento']} | {imp} | "
                     f"{r['scadenza'] or 'n.d.'} | [ANAC]({r['url']}) |")
    path.write_text("\n".join(righe) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Radar bandi PA (ANAC PVL)")
    ap.add_argument("--giorni", type=int, default=10)
    ap.add_argument("--input", help="file JSON di avvisi grezzi (prova offline)")
    ap.add_argument("--out", default=str(DATI))
    args = ap.parse_args()

    oggi = date.today()
    da = (oggi - timedelta(days=args.giorni)).strftime("%d/%m/%Y")
    a = oggi.strftime("%d/%m/%Y")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.input:
        grezzi = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        grezzi = scarica(da, a)

    storico_path = out / "storico.json"
    storico = json.loads(storico_path.read_text(encoding="utf-8")) if storico_path.exists() else {}

    tenuti = []
    for av in grezzi:
        try:
            r = valuta(normalizza(av))
        except Exception as e:  # un avviso malformato non deve fermare il run
            print(f"[warn] avviso {av.get('idAvviso')} ignorato: {e}", file=sys.stderr)
            continue
        if not r:
            continue
        if r["scadenza"] and r["scadenza"] < oggi.isoformat():
            continue  # già scaduto
        r["nuovo"] = r["id"] not in storico
        storico.setdefault(r["id"], oggi.isoformat())
        r["prima_vista"] = storico[r["id"]]
        tenuti.append(r)

    ordine = {"TP": 0, "SICILIA": 1, "ALTRO": 2}
    tenuti.sort(key=lambda r: (not r["nuovo"], ordine[r["territorio"]], -r["punteggio"], r["scadenza"] or "9999"))

    meta = {"generato": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "finestra": [da, a], "avvisi_scaricati": len(grezzi), "opportunita": len(tenuti),
            "nuove": sum(r["nuovo"] for r in tenuti)}
    (out / "ultimi.json").write_text(json.dumps({"meta": meta, "record": tenuti}, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    storico_path.write_text(json.dumps(storico, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    scrivi_md(tenuti, out / "ultimi.md", da, a)
    print(f"[radar] {len(grezzi)} avvisi scaricati → {len(tenuti)} opportunità ({meta['nuove']} nuove)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

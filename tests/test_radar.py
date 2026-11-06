"""
Test offline del radar: avvisi costruiti nella stessa forma restituita dall'API PVL.

    python tests/test_radar.py
"""
import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "radar"))
from radar import normalizza, valuta, territorio  # noqa: E402

FUTURO = (date.today() + timedelta(days=12)).isoformat() + "T12:00:00Z"
PASSATO = (date.today() - timedelta(days=2)).isoformat() + "T12:00:00Z"


def avviso(id_, tipologia, descr, ente, luogo, *, natura="Servizi", valore=None,
           scadenza=FUTURO, cpv="Servizi di contabilità"):
    item = {"cig": "B000" + id_, "natura_principale": natura, "descrizione": descr,
            "cpv": cpv, "luogo_nuts": luogo, "termine_invito": scadenza}
    if valore:
        item["valore_complessivo_stimato"] = valore
    return {"idAvviso": id_, "tipologia": tipologia,
            "dataPubblicazione": date.today().isoformat() + "T08:00:00.000+00:00",
            "templates": [{"template": {"metadata": {"titolo": descr[:120], "descrizione": descr},
                                        "sections": [
                {"name": "SEZ. A - Committente", "fields": {"soggetti_sa": [
                    {"codice_fiscale": "00000000000", "denominazione_amministrazione": ente}]}},
                {"name": "SEZ. B - Dati Generali", "fields": {}},
                {"name": "SEZ. C - Oggetto", "items": [item]}]}}]}


CASI = [
    # (avviso, atteso: None = scartato, oppure (profilo, territorio))
    (avviso("tp1", "INDAGINI_DI_MERCATO_SOTTO_SOGLIA",
            "Avviso di indagine di mercato per l'affidamento del servizio di supporto amministrativo-contabile "
            "e tenuta della contabilità IVA", "COMUNE DI ERICE", "Erice"), ("B", "TP")),
    (avviso("pa1", "BANDI", "Servizio di assistenza alla rendicontazione PNRR e controllo di gestione",
            "COMUNE DI PALERMO", "Palermo", valore=450000), ("B", "SICILIA")),
    (avviso("tp2", "BANDI", "Affidamento del servizio di tesoreria comunale", "COMUNE DI MARSALA",
            "Marsala"), None),
    (avviso("mi1", "BANDI", "Servizi di consulenza informatica e sviluppo software gestionale",
            "COMUNE DI MILANO", "Milano", cpv="Servizi di consulenza software"), None),
    (avviso("rm1", "INDAGINI_DI_MERCATO_SOTTO_SOGLIA",
            "Avviso per la nomina dell'Organismo Indipendente di Valutazione (OIV) in forma monocratica",
            "ISTITUTO NAZIONALE XYZ", "Roma"), ("A", "ALTRO")),
    (avviso("tp3", "RISULTATI", "Esito servizio elaborazione paghe", "ASP TRAPANI", "Trapani"), None),
    (avviso("tp4", "BANDI", "Fornitura di toner e cancelleria per uffici contabili", "COMUNE DI TRAPANI",
            "Trapani", natura="Forniture"), None),
    (avviso("tp5", "BANDI", "Servizio di elaborazione paghe e cedolini", "TRAPANI SERVIZI S.P.A.",
            "Trapani", scadenza=PASSATO), None),  # scaduto: tolto in main()
    (avviso("ct1", "INDAGINI_DI_MERCATO_SOTTO_SOGLIA",
            "Corso di formazione del personale sulla digitalizzazione e intelligenza artificiale",
            "UNIVERSITA DEGLI STUDI DI CATANIA", "Catania", cpv="Servizi di formazione"), ("B", "SICILIA")),
    (avviso("tp6", "BANDI", "Incarico di revisione legale dei conti e consulenza fiscale",
            "LIBERO CONSORZIO COMUNALE DI TRAPANI", "ITG11"), ("A", "TP")),
]


def main():
    errori = 0
    for av, atteso in CASI:
        r = valuta(normalizza(av))
        ottenuto = (r["profilo"].split("+")[0], r["territorio"]) if r else None
        if av["idAvviso"] == "tp5":
            continue  # verificato sotto, nel run completo
        esito = "ok " if ottenuto == atteso else "ERR"
        errori += ottenuto != atteso
        print(f"{esito} {av['idAvviso']:4} atteso={atteso} ottenuto={ottenuto}"
              + (f" punti={r['punteggio']} kw={r['parole_chiave']} {r['attenzione']}" if r else ""))

    assert territorio("Vita", "COMUNE DI VITA") == "TP"
    assert territorio("Roma", "AZIENDA VITA SERENA") == "ALTRO"
    assert territorio("Mazara del Vallo", "") == "TP"

    # Run completo offline: scaduti esclusi, file scritti, novità marcate
    with tempfile.TemporaryDirectory() as tmp:
        campione = Path(tmp) / "campione.json"
        campione.write_text(json.dumps([c[0] for c in CASI]), encoding="utf-8")
        cmd = [sys.executable, str(RADICE / "radar" / "radar.py"), "--input", str(campione), "--out", tmp]
        subprocess.run(cmd, check=True)
        dati = json.loads((Path(tmp) / "ultimi.json").read_text(encoding="utf-8"))
        ids = [r["id"] for r in dati["record"]]
        assert "tp5" not in ids, "lo scaduto non doveva entrare"
        assert all(r["nuovo"] for r in dati["record"])
        subprocess.run(cmd, check=True)  # secondo giro: niente più novità
        dati2 = json.loads((Path(tmp) / "ultimi.json").read_text(encoding="utf-8"))
        assert not any(r["nuovo"] for r in dati2["record"]), "al secondo giro nulla è nuovo"
        print((Path(tmp) / "ultimi.md").read_text(encoding="utf-8"))

    print("TUTTO OK" if not errori else f"{errori} ERRORI")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())

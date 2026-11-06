"""
Configurazione del radar bandi: cosa cercare e come valutarlo.

Tutto il "vocabolario" sta qui. Per affinare il radar si modifica questo file,
non radar.py.
"""

# ---------------------------------------------------------------------------
# Prefissi CPV inviati all'API ANAC (3-8 cifre). ANAC filtra lato server,
# quindi arrivano solo gli avvisi classificati sotto questi codici.
# ---------------------------------------------------------------------------
CPV_PREFISSI = [
    # Contabilità, revisione, fiscale
    "7920",    # servizi contabili, di revisione dei conti e fiscali
    "7921",    # contabilità e revisione dei conti (tenuta contabilità, paghe, revisione)
    "7922",    # consulenza fiscale, dichiarazioni
    # Consulenza gestionale e progetti
    "7941",    # consulenza commerciale e di gestione (incl. gestione finanziaria, sviluppo aziendale)
    "7942",    # servizi connessi alla gestione (gestione progetti)
    "79419",   # consulenza in materia di valutazione
    # Supporto amministrativo
    "7511",    # servizi amministrativi generali
    "7513",    # servizi di supporto alla pubblica amministrazione
    # Informatica e dati
    "7221",    # consulenza e programmazione software
    "7222",    # consulenza sistemi e assistenza tecnica
    "7226",    # servizi connessi al software
    "7231",    # elaborazione dati
    "7232",    # servizi di banche dati
    # Formazione
    "8050",    # servizi di formazione
    "8051",    # formazione specialistica / del personale
    "8053",    # formazione professionale
    "7963",    # formazione del personale
]
CPV_PER_CHIAMATA = 8

# ---------------------------------------------------------------------------
# Profili. Ogni parola chiave "forte" vale da sola; le "deboli" contano poco.
# Le ricerche sono su titolo + descrizione, in minuscolo, senza accenti.
# ---------------------------------------------------------------------------
PROFILI = {
    "A": {
        "nome": "Davide Vulpetti (professionista)",
        "forti": [
            "revisione legale", "revisore", "revisori dei conti", "collegio sindacale",
            "sindaco unico", "organo di controllo", "organismo indipendente di valutazione",
            "oiv", "nucleo di valutazione", "organismo di vigilanza", "231/2001",
            "consulenza fiscale", "consulenza tributaria", "assistenza fiscale",
            "esperto contabile", "commercialista", "dottore commercialista",
            "certificazione della spesa", "controllo di primo livello", "controlli di primo livello",
            "finanza agevolata",
        ],
        "deboli": ["incentivi", "fiscale", "tributari", "iva", "dichiarazion", "bilancio", "asseverazione"],
    },
    "B": {
        "nome": "Trirevi Consulting S.r.l.",
        "forti": [
            "tenuta della contabilita", "tenuta contabilita", "servizi contabili",
            "supporto contabile", "supporto amministrativo", "supporto amministrativo-contabile",
            "elaborazione paghe", "elaborazione stipendi", "cedolini", "gestione del personale",
            "controllo di gestione", "contabilita analitica", "budget", "reporting",
            "rendicontazione", "pnrr", "fesr", "fse+", "fondi europei", "fondi strutturali",
            "piano economico finanziario", "piano economico-finanziario", "business plan",
            "supporto al rup", "supporto rup",
            "formazione del personale", "formazione dei dipendenti", "corso di formazione",
            "digitalizzazione", "intelligenza artificiale", "elaborazione dati", "banca dati",
            "consulenza informatica", "consulenza aziendale", "consulenza gestionale",
        ],
        "deboli": ["contabil", "amministrativ", "formazione", "software", "informatic",
                   "consulenza", "supporto", "monitoraggio", "progetto",
                   "assistenza tecnica"],
    },
}

# Se compare uno di questi termini il record viene scartato: non sono
# opportunità per noi anche se il CPV coincide.
ESCLUSIONI = [
    "sponsorizzazion", "servizio di tesoreria", "tesoreria comunale", "brokeraggio",
    "assicurativ", "vigilanza armata", "servizio di vigilanza", "pulizia", "mensa",
    "refezione", "trasporto scolastico", "riscossione coattiva", "accertamento e riscossione",
    "pubbliche affissioni", "noleggio", "fornitura di hardware", "licenze software",
    "manutenzione impianti", "lavori di",
]

# Tipologie ANAC → momento del ciclo d'acquisto
MOMENTI = {
    "INDAGINI_DI_MERCATO_SOTTO_SOGLIA": "manifestazione",
    "CONSULTAZIONI_PRELIMINARI_DI_MERCATO": "manifestazione",
    "AVVISI_DI_PREINFORMAZIONE": "preavviso",
    "BANDI": "gara",
    "RISULTATI": "esito",
    "MODIFICHE_CONTRATTUALI": "modifica",
    "AVVISI_DI_PROROGA": "modifica",
}
# Gli esiti e le modifiche non sono opportunità: li teniamo fuori dal report
MOMENTI_UTILI = {"manifestazione", "preavviso", "gara", "altro"}

# ---------------------------------------------------------------------------
# Punteggio
# ---------------------------------------------------------------------------
PUNTI_FORTE = 30          # per ogni parola chiave forte (max 2 contate)
PUNTI_DEBOLE = 5          # per ogni parola debole (max 3 contate)
PUNTI_CPV = 15            # il CPV è già filtrato a monte
PUNTI_MANIFESTAZIONE = 10 # le indagini di mercato sono il vero punto di ingresso
PUNTI_TP = 25
PUNTI_SICILIA = 10
SOGLIA_REPORT = 45        # sotto questo punteggio non entra nel report

# Oltre questo importo è probabile che i requisiti di fatturato superino
# quelli di Trirevi (ricavi 2023-2025: 269k, 228k, 197k). Non scarta: segnala.
IMPORTO_ATTENZIONE = 300_000

# Fuori dalla Sicilia teniamo solo le opportunità del profilo A con almeno
# una parola forte (es. elenchi OIV, revisori), o quelle svolgibili da remoto.
TERMINI_REMOTO = ["da remoto", "in modalita remota", "modalita telematica", "smart working"]

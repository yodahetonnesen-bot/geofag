#!/usr/bin/env python3
"""Deler geofag-kildeteksten opp i strukturert JSON, ett dokument per kapittel.

Kildeteksten er en ren tekstdump av laereboka. Sidetall er limt inntil slutten av
linja de star pa ("Jordas oppbygningSide 16"), og overskriftsmarkorene star som
egne linjer i versaler. Parseren gjenskaper strukturen: kapittel -> del -> blokk.

Fasitfeltene ("f") skrives tomme her og fylles ut for hand i content/kNN.json.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
KILDE = ROOT / "kilde" / "geofag-kildetekst.txt"
UT = ROOT / "content"

# Markorer som apner en ny blokktype
MARKOR = {
    "SPØRSMÅL": "sporsmal",
    "HVA TROR DU?": "hvatrordu",
    "OPPGAVE": "oppgave",
    "OPPGAVER": "oppgave",
    "KAPITTELOPPGAVER": "kapitteloppgave",
    "SAMMENDRAG": "sammendrag",
    "HVA SIER LÆREPLANEN I GEOFAG?": "laereplan",
}

# Rester av tidligere chat-instruksjoner som ble limt inn i kildeteksten
STOY = re.compile(
    r"\s*(ta å skriv alt dette inn i en html fil.*"
    r"|lag en nettside for geofag.*"
    r"|ikke gjør noen feil og husk.*)$",
    re.IGNORECASE,
)

SIDE = re.compile(r"^(.*?)Side (\d+)$")
FIGUR = re.compile(r"^(\d+\.\d+)\s+(.*)$")
KAPITTEL = re.compile(r"^/?(?:.*?)Kapittel (\d+)$")
LAEREPLANVERB = re.compile(
    r"^(gjennomføre|gjøre rede for|sammenligne|utforske|vurdere|bruke|drøfte"
    r"|beskrive|presentere|bearbeide|forklare|analysere|planlegge)\b"
)
SLUTTTEGN = tuple(".?!:;»)")

# Mange oppgaver i boka er formulert som imperativ og ender med punktum. Uten
# en OPPGAVE-markor foran seg ville de blitt lest som vanlig brodtekst.
IMPERATIV = re.compile(
    r"^(Lag |Forklar |Finn |Bruk |Studer |Beskriv |Søk |Gå inn på |Gå til "
    r"|Diskuter |Velg |Undersøk |Vurder |Tegn |Skriv |Regn |Klikk |Se på "
    r"|Sammenlign |Marker |Noter |Drøft |Presenter |Zoom )"
)

# ... og noen begynner med en innledende setning for selve oppdraget kommer.
OPPDRAG = re.compile(
    r"(?:^|[.?!] )(Sammenlign |Undersøk |Finn ut |Let deg fram |Studer |Forklar "
    r"|Beskriv |Tegn |Regn ut |Marker |Diskuter |Vurder |Begrunn |Bruk figur "
    r"|Bruk kartet |Bruk Google |Gi noen eksempler|Gi et eksempel )"
)


def del_opp_sidetall(linje: str) -> tuple[str, int | None]:
    """Skiller ut sidetallet som er limt inntil slutten av linja."""
    m = SIDE.match(linje)
    if not m:
        return linje, None
    tekst, side = m.group(1).rstrip(), int(m.group(2))
    return tekst, side


# En linje med likhetstegn er en formel fra boka, ikke en overskrift.
FORMEL = re.compile(r"=")

# Bildetekster star ofte som frittstaende linjer uten sluttegn, og ser derfor
# ut som overskrifter. De kjennes igjen pa hva de begynner med, eller pa at de
# beskriver hva et kart eller bilde viser.
BILDESTART = re.compile(
    r"^(Kart|Verdenskart|Norgeskart|Tidslinje|Tverrsnitt|Skisse|Flyfoto|Nærbilde"
    r"|Satelittbilde|Satellittbilde|Illustrasjon|Diagram|Grafikk|Foto)\b"
)
BILDEORD = re.compile(r" som viser | er merket av$| er markert$|, sett fra ")

# Lange, ubestemte beskrivelser med «som» er ogsa bildetekster
# («En steinblokk med sma krusninger i patinaen som kunne minnet om …»).
BILDELANG = re.compile(r"^(En|Et|To|Tre|Fire|Flere) .+ som ")


def er_formel(tekst: str) -> bool:
    return bool(tekst) and len(tekst) < 90 and bool(FORMEL.search(tekst))


def er_bildetekst(tekst: str) -> bool:
    if BILDESTART.match(tekst) or BILDEORD.search(tekst):
        return True
    return len(tekst) > 55 and bool(BILDELANG.match(tekst))


def er_overskrift(tekst: str) -> bool:
    """Korte linjer uten sluttegn leses som overskrifter, ikke som brodtekst."""
    if not tekst or len(tekst) > 90:
        return False
    if tekst.endswith(SLUTTTEGN):
        return False
    # «De storste vannmagasinene er» og liknende er innledninger til en liste,
    # ikke overskrifter.
    if tekst.endswith(" er") or tekst.endswith(" ="):
        return False
    return tekst[0].isupper() or tekst[0].isdigit()


# Kapittelmarkoren er ofte limt bakpa siste setning i forrige kapittel
# («… store basaltprovinser.Kapittel 1»). Da ma linja deles, ellers henger
# «Kapittel 1» igjen midt i sammendraget til kapitlet foran.
KAPITTELDELING = re.compile(r"^(/?.*?)(Kapittel \d+)$")


def les_kilde() -> list[str]:
    linjer = []
    for rad in KILDE.read_text(encoding="utf-8").split("\n"):
        rad = STOY.sub("", rad.strip())
        if not rad:
            continue
        m = KAPITTELDELING.match(rad)
        if m:
            foran = m.group(1).lstrip("/").strip()
            if foran:
                linjer.append(foran)
            linjer.append(m.group(2))
            continue
        linjer.append(rad)
    return linjer


def finn_kapitler(linjer: list[str]) -> list[tuple[int, int]]:
    """Returnerer (linjeindeks for kapittelmarkoren, kapittelnummer)."""
    treff = []
    for i, rad in enumerate(linjer):
        m = KAPITTEL.match(rad)
        if m:
            treff.append((i, int(m.group(1))))
    return treff


def parse_kapittel(linjer: list[str], start: int, slutt: int, nr: int) -> dict:
    # Linja med kapittelmarkoren kan ha brodtekst foran markoren; den hores til
    # forrige kapittel og er allerede tatt med der.
    i = start + 1
    tittel_rad = linjer[i]
    tittel, forsteside = del_opp_sidetall(tittel_rad)
    i += 1

    kap = {
        "nr": nr,
        "tittel": tittel,
        "forsteside": forsteside,
        "sisteside": None,
        "laereplan": [],
        "deler": [],
        "oppgaveblokker": [],
        "sammendrag": [],
    }

    gjeldende_del = {"tittel": "Innledning", "side": forsteside, "blokker": []}
    modus = "brodtekst"
    blokk: dict | None = None

    forelopig: list[str] = []

    def lagre_del():
        """Tar vare pa overskrifter som aldri fikk innhold (bildetekster o.l.)."""
        if gjeldende_del["blokker"]:
            if forelopig:
                gjeldende_del["blokker"][0:0] = [
                    {"t": "bilde", "tekst": t} for t in forelopig
                ]
                forelopig.clear()
            kap["deler"].append(gjeldende_del)
        elif gjeldende_del["tittel"]:
            forelopig.append(gjeldende_del["tittel"])

    def lukk_blokk():
        nonlocal blokk
        if blokk and blokk["poster"]:
            kap["oppgaveblokker"].append(blokk)
        blokk = None

    while i < slutt:
        rad = linjer[i]
        i += 1
        tekst, side = del_opp_sidetall(rad)
        if side is not None:
            kap["sisteside"] = max(kap["sisteside"] or 0, side)

        naken = tekst.rstrip("?").strip() if tekst.rstrip("?").strip() in (
            "HVA TROR DU",
        ) else tekst

        if tekst in MARKOR:
            ny = MARKOR[tekst]
            if ny == "laereplan":
                lukk_blokk()
                modus = "laereplan"
                continue
            if ny == "sammendrag":
                lukk_blokk()
                lagre_del()
                gjeldende_del = {"tittel": None, "side": side, "blokker": []}
                modus = "sammendrag"
                continue
            lukk_blokk()
            modus = "oppgaver"
            blokk = {
                "art": ny,
                "overskrift": tekst,
                "side": side,
                "del": gjeldende_del["tittel"],
                "poster": [],
            }
            continue

        if modus == "laereplan":
            if tekst == "Elevene skal kunne":
                continue
            # Skiller de kapittelspesifikke malene fra de gjennomgaende.
            # Beholdes i lista og gjengis som mellomtekst av build.py.
            if tekst == "I tillegg skal de":
                kap["laereplan"].append(tekst)
                continue
            # Kompetansemalene er formulert som infinitiver med liten
            # forbokstav. Forste linje som ikke er det, avslutter lista.
            if LAEREPLANVERB.match(tekst):
                kap["laereplan"].append(tekst)
                continue
            modus = "brodtekst"

        if modus == "sammendrag":
            kap["sammendrag"].append(tekst)
            continue

        if modus == "oppgaver" and blokk is not None:
            # KAPITTELOPPGAVER lober alltid fram til SAMMENDRAG, og har egne
            # gruppeoverskrifter inni seg. Andre oppgaveblokker avsluttes av
            # neste overskrift i brodteksten.
            if blokk["art"] == "kapitteloppgave":
                korttittel = (
                    tekst.endswith("?")
                    and len(tekst) < 45
                    and i < slutt
                    and not linjer[i].rstrip().endswith("?")
                )
                if er_overskrift(tekst) or korttittel:
                    blokk["poster"].append({"gruppe": tekst})
                else:
                    blokk["poster"].append({"q": tekst, "f": ""})
                continue
            if er_overskrift(tekst):
                lukk_blokk()
                modus = "brodtekst"
                # En bildetekst avslutter oppgaveboksen, men skal ikke bli
                # en ny del med egen overskrift.
                if er_bildetekst(tekst):
                    gjeldende_del["blokker"].append({"t": "bilde", "tekst": tekst})
                    continue
                lagre_del()
                gjeldende_del = {"tittel": tekst, "side": side, "blokker": []}
                continue
            blokk["poster"].append({"q": tekst, "f": ""})
            continue

        # --- brodtekst ---
        mf = FIGUR.match(tekst)
        if mf:
            gjeldende_del["blokker"].append(
                {"t": "figur", "nr": mf.group(1), "tekst": mf.group(2)}
            )
            continue

        if er_formel(tekst):
            gjeldende_del["blokker"].append({"t": "formel", "tekst": tekst})
            continue

        if er_overskrift(tekst):
            # Beskrivelser av kart og bilder er bildetekster, ikke nye deler.
            if er_bildetekst(tekst):
                gjeldende_del["blokker"].append({"t": "bilde", "tekst": tekst})
                continue
            # En overskriftslignende linje rett foran en figurtekst er
            # alt-teksten til bildet, ikke en ny del.
            neste_er_figur = i < slutt and FIGUR.match(del_opp_sidetall(linjer[i])[0])
            # ... og en overskrift uten sidetall rett etter en overskrift med
            # sidetall er ogsa en bildetekst.
            rett_etter_overskrift = not gjeldende_del["blokker"] and side is None
            if neste_er_figur or rett_etter_overskrift:
                gjeldende_del["blokker"].append({"t": "bilde", "tekst": tekst})
                continue
            lagre_del()
            gjeldende_del = {"tittel": tekst, "side": side, "blokker": []}
            continue

        if tekst.endswith("?") and len(tekst) < 240:
            gjeldende_del["blokker"].append({"t": "tenk", "tekst": tekst, "f": ""})
            continue

        if (IMPERATIV.match(tekst) or OPPDRAG.search(tekst)) and len(tekst) < 400:
            gjeldende_del["blokker"].append({"t": "oppg", "tekst": tekst, "f": ""})
            continue

        gjeldende_del["blokker"].append({"t": "p", "tekst": tekst})

    lukk_blokk()
    lagre_del()
    if forelopig:
        # Overskrifter helt sist i kapitlet har ingen etterfolgende del a hore til.
        hale = kap["deler"][-1] if kap["deler"] else None
        if hale is None:
            hale = {"tittel": None, "side": None, "blokker": []}
            kap["deler"].append(hale)
        hale["blokker"].extend({"t": "bilde", "tekst": t} for t in forelopig)
        forelopig.clear()
    return kap


def er_fragment(d: dict) -> bool:
    """Sann for «deler» som egentlig er enkeltceller fra en tabell i boka."""
    if not d.get("tittel") or len(d["tittel"]) > 44:
        return False
    if len(d["blokker"]) > 3:
        return False
    for b in d["blokker"]:
        if b["t"] not in ("bilde", "p"):
            return False
        if len(b.get("tekst", "")) > 90:
            return False
    return True


def slaa_sammen_tabeller(kap: dict, minst: int = 5) -> None:
    """Lange rekker av fragmenter samles til én tabellblokk.

    Tabellene i laereboka kommer ut av tekstdumpen som én linje per celle.
    Uten dette blir hver celle til sin egen overskrift i fagstoffet.
    """
    deler, ut, i = kap["deler"], [], 0
    while i < len(deler):
        j = i
        while j < len(deler) and er_fragment(deler[j]):
            j += 1
        if j - i >= minst:
            celler = []
            for d in deler[i:j]:
                celler.append(d["tittel"])
                celler.extend(b["tekst"] for b in d["blokker"] if b.get("tekst"))
            ut.append({
                "tittel": None,
                "side": deler[i].get("side"),
                "blokker": [{"t": "tabell", "celler": celler}],
            })
            i = j
        else:
            ut.append(deler[i])
            i += 1
    kap["deler"] = ut


def main() -> int:
    linjer = les_kilde()
    treff = finn_kapitler(linjer)
    if not treff:
        print("fant ingen kapittelmarkorer", file=sys.stderr)
        return 1

    UT.mkdir(exist_ok=True)
    kapitler = []
    for idx, (i, nr) in enumerate(treff):
        # Markorlinja hores ikke til kapitlet foran — brodteksten som sto
        # limt foran den, er allerede skilt ut som egen linje i les_kilde().
        slutt = treff[idx + 1][0] if idx + 1 < len(treff) else len(linjer)
        kap = parse_kapittel(linjer, i, min(slutt, len(linjer)), nr)
        slaa_sammen_tabeller(kap)
        kapitler.append(kap)

    kapitler.sort(key=lambda k: k["nr"])
    for kap in kapitler:
        sti = UT / f"k{kap['nr']:02d}.json"
        sti.write_text(
            json.dumps(kap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"skrev {len(kapitler)} kapitler til {UT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def del_opp_sidetall(linje: str) -> tuple[str, int | None]:
    """Skiller ut sidetallet som er limt inntil slutten av linja."""
    m = SIDE.match(linje)
    if not m:
        return linje, None
    tekst, side = m.group(1).rstrip(), int(m.group(2))
    return tekst, side


def er_overskrift(tekst: str) -> bool:
    """Korte linjer uten sluttegn leses som overskrifter, ikke som brodtekst."""
    if not tekst or len(tekst) > 90:
        return False
    if tekst.endswith(SLUTTTEGN):
        return False
    return tekst[0].isupper() or tekst[0].isdigit()


def les_kilde() -> list[str]:
    linjer = []
    for rad in KILDE.read_text(encoding="utf-8").split("\n"):
        rad = STOY.sub("", rad.strip())
        if rad:
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
            if tekst in ("Elevene skal kunne", "I tillegg skal de"):
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
                if er_overskrift(tekst) or (
                    tekst.endswith("?") and len(tekst) < 40 and i < slutt
                    and not linjer[i].endswith("?")
                    and len(linjer[i]) > 160
                ):
                    blokk["poster"].append({"gruppe": tekst})
                else:
                    blokk["poster"].append({"q": tekst, "f": ""})
                continue
            if er_overskrift(tekst):
                lukk_blokk()
                modus = "brodtekst"
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

        if er_overskrift(tekst):
            lagre_del()
            gjeldende_del = {"tittel": tekst, "side": side, "blokker": []}
            continue

        if tekst.endswith("?") and len(tekst) < 240:
            gjeldende_del["blokker"].append({"t": "tenk", "tekst": tekst, "f": ""})
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


def main() -> int:
    linjer = les_kilde()
    treff = finn_kapitler(linjer)
    if not treff:
        print("fant ingen kapittelmarkorer", file=sys.stderr)
        return 1

    UT.mkdir(exist_ok=True)
    kapitler = []
    for idx, (i, nr) in enumerate(treff):
        slutt = treff[idx + 1][0] + 1 if idx + 1 < len(treff) else len(linjer)
        kap = parse_kapittel(linjer, i, min(slutt, len(linjer)), nr)
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

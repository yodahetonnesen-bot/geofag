#!/usr/bin/env python3
"""Lager og oppdaterer fasitmalene i fasit/kNN.json.

Malen inneholder ett innslag per oppgave og per refleksjonssporsmal, med en
stabil id utledet av sporsmalsteksten. Svar som allerede er skrevet, beholdes.
Kjor dette pa nytt hver gang content/ er parset om.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
FASIT = ROOT / "fasit"


def nokkel(tekst: str) -> str:
    return hashlib.sha1(tekst.strip().encode("utf-8")).hexdigest()[:10]


def samle_sporsmal(kap: dict) -> list[dict]:
    ut = []
    for d in kap["deler"]:
        for b in d["blokker"]:
            if b["t"] in ("tenk", "oppg"):
                art = "tenk" if b["t"] == "tenk" else "oppgave-i-tekst"
                ut.append({"id": nokkel(b["tekst"]), "art": art, "q": b["tekst"], "f": ""})
    for blokk in kap["oppgaveblokker"]:
        for post in blokk["poster"]:
            if "q" not in post:
                continue
            ut.append({"id": nokkel(post["q"]), "art": blokk["art"], "q": post["q"], "f": ""})
    return ut


def main() -> int:
    FASIT.mkdir(exist_ok=True)
    nye = beholdt = 0
    for sti in sorted(CONTENT.glob("k*.json")):
        kap = json.loads(sti.read_text(encoding="utf-8"))
        mal = FASIT / f"k{kap['nr']:02d}.json"

        gamle: dict[str, str] = {}
        if mal.exists():
            for rad in json.loads(mal.read_text(encoding="utf-8")):
                if rad.get("f"):
                    gamle[rad["id"]] = rad["f"]

        rader = []
        sett = set()
        for rad in samle_sporsmal(kap):
            if rad["id"] in sett:      # samme sporsmal kan sta flere steder
                continue
            sett.add(rad["id"])
            if rad["id"] in gamle:
                rad["f"] = gamle[rad["id"]]
                beholdt += 1
            else:
                nye += 1
            rader.append(rad)

        mal.write_text(json.dumps(rader, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"fasitmaler oppdatert — {beholdt} svar beholdt, {nye} står tomme")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

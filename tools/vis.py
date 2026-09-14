#!/usr/bin/env python3
"""Viser oppgavene i et kapittel som mangler fasit, med id og art."""
import json, pathlib, sys
FASIT = pathlib.Path(__file__).resolve().parent.parent / "fasit"
nr = int(sys.argv[1])
bare_tomme = "--alle" not in sys.argv
for r in json.loads((FASIT / f"k{nr:02d}.json").read_text(encoding="utf-8")):
    if bare_tomme and r["f"]:
        continue
    print(f'{r["id"]}  [{r["art"]:16s}] {r["q"]}')

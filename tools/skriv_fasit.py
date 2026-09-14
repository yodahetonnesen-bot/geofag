#!/usr/bin/env python3
"""Skriver svar inn i fasit/kNN.json.

Leser JSON fra stdin: {"id": "svartekst", ...}. Ukjente id-er meldes fra om.

    echo '{"e7465c5599":"..."}' | python3 tools/skriv_fasit.py 2
"""
from __future__ import annotations

import json
import pathlib
import sys

FASIT = pathlib.Path(__file__).resolve().parent.parent / "fasit"


def main() -> int:
    if len(sys.argv) < 2:
        print("bruk: skriv_fasit.py <kapittelnummer>", file=sys.stderr)
        return 2
    sti = FASIT / f"k{int(sys.argv[1]):02d}.json"
    rader = json.loads(sti.read_text(encoding="utf-8"))
    svar = json.load(sys.stdin)

    kjente = {r["id"] for r in rader}
    ukjente = [k for k in svar if k not in kjente]
    skrevet = 0
    for r in rader:
        if r["id"] in svar:
            r["f"] = svar[r["id"]].strip()
            skrevet += 1

    sti.write_text(json.dumps(rader, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mangler = sum(1 for r in rader if not r["f"])
    print(f"k{int(sys.argv[1]):02d}: skrev {skrevet} svar — {mangler} av {len(rader)} står igjen")
    if ukjente:
        print("  ukjente id-er: " + ", ".join(ukjente), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

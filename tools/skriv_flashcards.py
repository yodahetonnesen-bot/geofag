#!/usr/bin/env python3
"""Fletter flashcards inn i ekstra/kNN.json uten a rore resten av fila.

    python3 - <<'EOF' | python3 tools/skriv_flashcards.py 6
    [ {"t": "Mineral", "d": "Fast stoff bygd opp av ...", "k": "Grunnbegreper"} ]
    EOF
"""
import json
import pathlib
import sys

EKSTRA = pathlib.Path(__file__).resolve().parent.parent / "ekstra"


def main() -> int:
    if len(sys.argv) != 2:
        print("bruk: skriv_flashcards.py <kapittelnummer>", file=sys.stderr)
        return 2
    nr = int(sys.argv[1])
    sti = EKSTRA / f"k{nr:02d}.json"
    data = json.loads(sti.read_text(encoding="utf-8")) if sti.exists() else {}

    kort = json.load(sys.stdin)
    sett = set()
    for i, k in enumerate(kort):
        for felt in ("t", "d"):
            if not k.get(felt):
                print(f"kort {i + 1} mangler «{felt}»", file=sys.stderr)
                return 1
        if k["t"] in sett:
            print(f"kort {i + 1}: «{k['t']}» star to ganger", file=sys.stderr)
            return 1
        sett.add(k["t"])

    data["flashcards"] = kort
    sti.parent.mkdir(exist_ok=True)
    sti.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"k{nr:02d}: skrev {len(kort)} flashcards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

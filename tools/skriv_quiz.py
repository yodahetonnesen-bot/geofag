#!/usr/bin/env python3
"""Fletter quizdata inn i ekstra/kNN.json uten a rore resten av fila.

    python3 - <<'EOF' | python3 tools/skriv_quiz.py 13
    [ {"q": "...", "alt": ["a","b","c","d"], "rett": 0, "f": "...", "k": "..."} ]
    EOF
"""
import json
import pathlib
import sys

EKSTRA = pathlib.Path(__file__).resolve().parent.parent / "ekstra"


def main() -> int:
    if len(sys.argv) != 2:
        print("bruk: skriv_quiz.py <kapittelnummer>", file=sys.stderr)
        return 2
    nr = int(sys.argv[1])
    sti = EKSTRA / f"k{nr:02d}.json"
    data = json.loads(sti.read_text(encoding="utf-8")) if sti.exists() else {}

    quiz = json.load(sys.stdin)
    for i, sp in enumerate(quiz):
        for felt in ("q", "alt", "rett", "f"):
            if felt not in sp:
                print(f"sporsmal {i + 1} mangler «{felt}»", file=sys.stderr)
                return 1
        if len(sp["alt"]) < 3:
            print(f"sporsmal {i + 1} har for fa svaralternativer", file=sys.stderr)
            return 1
        if not 0 <= sp["rett"] < len(sp["alt"]):
            print(f"sporsmal {i + 1} har ugyldig «rett»", file=sys.stderr)
            return 1
        if len(set(sp["alt"])) != len(sp["alt"]):
            print(f"sporsmal {i + 1} har to like svaralternativer", file=sys.stderr)
            return 1

    data["quiz"] = quiz
    sti.parent.mkdir(exist_ok=True)
    sti.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"k{nr:02d}: skrev {len(quiz)} quizsporsmal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

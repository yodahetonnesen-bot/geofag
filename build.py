#!/usr/bin/env python3
"""Bygger den statiske nettsiden for Geofag 1 ut fra content/kNN.json.

    python3 build.py

Skriver index.html og kapittel/kNN.html. Alt annet (CSS, JS) ligger ferdig i
assets/ og kopieres ikke — sidene lenker rett til det.
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = ROOT / "content"
FASIT = ROOT / "fasit"
EKSTRA = ROOT / "ekstra"
UT_KAP = ROOT / "kapittel"

NETTSTED = "Geofag 1"
UNDERTITTEL = "Naturkatastrofer, geologi og landskap"

ART_NAVN = {
    "sporsmal": "Spørsmål",
    "hvatrordu": "Hva tror du?",
    "oppgave": "Oppgaver",
    "kapitteloppgave": "Kapitteloppgaver",
}

FANER = [
    ("oversikt", "OV", "Oversikt"),
    ("fagstoff", "FS", "Fagstoff"),
    ("oppgaver", "OP", "Oppgaver og fasit"),
    ("sammendrag", "SM", "Sammendrag"),
    ("flashcards", "FC", "Flashcards"),
    ("quiz", "QZ", "Quiz"),
]


def e(t: str) -> str:
    return html.escape(t or "", quote=True)


def slugg(t: str) -> str:
    t = (t or "").lower()
    for a, b in (("æ", "ae"), ("ø", "o"), ("å", "a"), ("é", "e"), ("–", "-")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "del"


def nokkel(tekst: str) -> str:
    return hashlib.sha1((tekst or "").strip().encode("utf-8")).hexdigest()[:10]


def flett_fasit(kap: dict) -> None:
    """Henter de handskrevne svarene fra fasit/kNN.json inn i kapitteldata."""
    sti = FASIT / f"k{kap['nr']:02d}.json"
    if not sti.exists():
        return
    svar = {r["id"]: r["f"] for r in json.loads(sti.read_text(encoding="utf-8")) if r.get("f")}
    for d in kap["deler"]:
        for b in d["blokker"]:
            if b["t"] == "tenk":
                b["f"] = svar.get(nokkel(b["tekst"]), "")
    for blokk in kap["oppgaveblokker"]:
        for post in blokk["poster"]:
            if "q" in post:
                post["f"] = svar.get(nokkel(post["q"]), "")


def les_kapitler() -> list[dict]:
    kap = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CONTENT.glob("k*.json"))]
    kap.sort(key=lambda k: k["nr"])
    for k in kap:
        flett_fasit(k)
        flett_ekstra(k)
    return kap


def flett_ekstra(kap: dict) -> None:
    """Flashcards, quiz og ingress ligger i ekstra/kNN.json nar de er skrevet."""
    sti = EKSTRA / f"k{kap['nr']:02d}.json"
    if not sti.exists():
        return
    data = json.loads(sti.read_text(encoding="utf-8"))
    for felt in ("ingress", "flashcards", "quiz"):
        if data.get(felt):
            kap[felt] = data[felt]

    # Noen linjer i KAPITTELOPPGAVER er innledninger eller gruppetitler, ikke
    # oppgaver. De listes opp her og merkes om for visningen.
    intro = set(data.get("intro") or [])
    grupper = set(data.get("grupper") or [])
    if not intro and not grupper:
        return
    for blokk in kap["oppgaveblokker"]:
        nye = []
        for post in blokk["poster"]:
            if "q" in post and nokkel(post["q"]) in intro:
                nye.append({"intro": post["q"]})
            elif "q" in post and nokkel(post["q"]) in grupper:
                nye.append({"gruppe": post["q"]})
            else:
                nye.append(post)
        blokk["poster"] = nye


def tell_oppgaver(kap: dict) -> int:
    return sum(1 for b in kap["oppgaveblokker"] for p in b["poster"] if "q" in p)


def tell_fasit(kap: dict) -> int:
    n = sum(1 for b in kap["oppgaveblokker"] for p in b["poster"] if p.get("f"))
    n += sum(1 for d in kap["deler"] for b in d["blokker"] if b["t"] == "tenk" and b.get("f"))
    return n


def sider(kap: dict) -> str:
    a, b = kap.get("forsteside"), kap.get("sisteside")
    if a and b:
        return f"s. {a}–{b}"
    return f"s. {a}" if a else ""


# --------------------------------------------------------------------------- skall
def skall(tittel: str, beskrivelse: str, side_id: str, sidemeny: str,
          brodsmule: str, innhold: str, dybde: int, ekstra_js: str = "") -> str:
    opp = "../" if dybde else ""
    return f"""<!DOCTYPE html>
<html lang="nb">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{e(beskrivelse)}">
<meta name="color-scheme" content="light dark">
<title>{e(tittel)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&amp;family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;1,8..60,400&amp;family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500;600&amp;display=swap" rel="stylesheet">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%230b1a14'/%3E%3Ccircle cx='50' cy='52' r='27' fill='none' stroke='%234cc79a' stroke-width='8'/%3E%3Cpath d='M23 52h54M50 25c11 8 11 46 0 54M50 25c-11 8-11 46 0 54' fill='none' stroke='%234cc79a' stroke-width='5'/%3E%3C/svg%3E">
<link rel="stylesheet" href="{opp}assets/geofag.css">
</head>
<body data-side="{e(side_id)}">
<a class="skiplink" href="#hovedinnhold">Hopp til innholdet</a>
<div class="scrim" id="skygge" aria-hidden="true"></div>
<div class="app">
  <aside class="sidebar" id="sidemeny">
    <div class="sidebar__brand">
      <a href="{opp}index.html">
        <span class="brandmark" aria-hidden="true">
          <svg viewBox="0 0 100 100" fill="none">
            <circle cx="50" cy="50" r="34" stroke="rgba(255,255,255,.95)" stroke-width="8"/>
            <path d="M16 50h68M50 16c13 10 13 58 0 68M50 16c-13 10-13 58 0 68" stroke="rgba(255,255,255,.7)" stroke-width="5"/>
          </svg>
        </span>
        <span class="brandtext">
          <b>{NETTSTED}</b>
          <span>{e(brodsmule)}</span>
        </span>
      </a>
    </div>
    <nav class="sidebar__scroll" aria-label="Innholdsnavigasjon">
{sidemeny}
    </nav>
    <div class="sidebar__foot">
      <div class="ringwrap">
        <span class="ring" aria-hidden="true">
          <svg width="46" height="46" viewBox="0 0 46 46">
            <circle class="ring__bg" cx="23" cy="23" r="19"></circle>
            <circle class="ring__fg" cx="23" cy="23" r="19" id="ringFg" stroke-dasharray="119.4" stroke-dashoffset="119.4"></circle>
          </svg>
          <b id="ringPst">0%</b>
        </span>
        <div>
          <small>Framdrift</small>
          <span id="ringTekst">0 av 0 punkter</span>
        </div>
      </div>
    </div>
  </aside>
  <div class="main">
    <header class="topbar">
      <button class="iconbtn burger" id="burger" aria-label="Meny">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      </button>
      <div class="topbar__crumb">
        <span class="kicker">{e(brodsmule)}</span>
        <span class="sep">/</span>
        <span class="now" id="noNa">Oversikt</span>
      </div>
      <div class="topbar__prog" role="status" aria-label="Framdrift i sjekklista">
        <span class="bar"><i id="topFyll"></i></span>
        <span id="topPst">0 %</span>
      </div>
      <button class="iconbtn" id="temaBtn" aria-label="Bytt mellom lyst og mørkt tema" title="Lyst / mørkt tema">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path id="temaIkon" d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
      </button>
    </header>
    <main class="content wrap" id="hovedinnhold" tabindex="-1">
{innhold}
    </main>
    <button id="tilTopp" class="totop" aria-label="Til toppen av siden" title="Til toppen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
    </button>
    <footer class="sitefoot">
      <div class="wrap">
        <p>Læringsside for {NETTSTED} — {UNDERTITTEL}. Fagstoff, oppgaver og sammendrag følger kapittelstrukturen i læreverket.</p>
        <p>Framdrift og flashcard-statistikk lagres lokalt i nettleseren din og sendes ingen steder.</p>
      </div>
    </footer>
  </div>
</div>
{ekstra_js}<script src="{opp}assets/geofag.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------------- innhold
def render_blokk(b: dict, teller: list[int]) -> str:
    t = b["t"]
    if t == "p":
        return f"<p>{e(b['tekst'])}</p>"
    if t == "figur":
        return (
            '<figure class="figur">'
            f'<span class="figur__nr">Figur {e(b["nr"])}</span>'
            f'<figcaption class="figur__tekst">{e(b["tekst"])}</figcaption>'
            "</figure>"
        )
    if t == "bilde":
        return f'<p class="bildetekst">Bilde: {e(b["tekst"])}</p>'
    if t == "tabell":
        celler = "".join(f"<li>{e(c)}</li>" for c in b["celler"])
        return (
            '<div class="tabellflat"><span class="tabellflat__tit">Tabell fra boka</span>'
            f"<ol>{celler}</ol></div>"
        )
    if t == "tenk":
        teller[0] += 1
        fasit = b.get("f")
        svar = (
            f'<div class="opg__body">{avsnitt(fasit)}</div>'
            if fasit else
            '<div class="opg__body"><p>Tenk gjennom dette selv før du leser videre — '
            "spørsmålet har ikke ett fasitsvar.</p></div>"
        )
        klasse = "opg" if fasit else "opg opg--aapen"
        return (
            f'<details class="{klasse}">'
            f'<summary><span class="opg__num">Tenk</span>'
            f'<span class="opg__q">{e(b["tekst"])}</span></summary>'
            f"{svar}</details>"
        )
    return ""


def avsnitt(tekst: str) -> str:
    """Fasittekst deles pa linjeskift; «- » i starten av linja blir punktliste."""
    if not tekst:
        return ""
    ut, punkter = [], []

    def tom_punkter():
        if punkter:
            ut.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in punkter) + "</ul>")
            punkter.clear()

    for rad in tekst.split("\n"):
        rad = rad.strip()
        if not rad:
            continue
        if rad.startswith("- "):
            punkter.append(rad[2:].strip())
        else:
            tom_punkter()
            ut.append(f"<p>{e(rad)}</p>")
    tom_punkter()
    return "".join(ut)


def panel_fagstoff(kap: dict) -> tuple[str, int]:
    teller = [0]
    ut = ['<section class="panel" id="panel-fagstoff">']
    ut.append('<h2 style="margin-top:0">Fagstoff</h2>')
    ut.append(
        '<p class="lede">Hele kapittelteksten, del for del. '
        "Refleksjonsspørsmålene underveis er merket <em>Tenk</em>.</p>"
    )

    lenker = [
        f'<a href="#{slugg(d["tittel"])}">{e(d["tittel"])}</a>'
        for d in kap["deler"] if d.get("tittel")
    ]
    if lenker:
        ut.append('<nav class="subnav" aria-label="Deler i kapitlet">' + "".join(lenker) + "</nav>")

    ut.append('<div class="brodtekst">')
    for d in kap["deler"]:
        if d.get("tittel"):
            sidetall = f' <span class="pill">s. {d["side"]}</span>' if d.get("side") else ""
            ut.append(f'<h3 id="{slugg(d["tittel"])}">{e(d["tittel"])}{sidetall}</h3>')
        for b in d["blokker"]:
            ut.append(render_blokk(b, teller))
    ut.append("</div>")
    ut.append("</section>")
    return "\n".join(ut), teller[0]


def panel_oppgaver(kap: dict) -> str:
    ut = ['<section class="panel" id="panel-oppgaver">']
    ut.append('<h2 style="margin-top:0">Oppgaver og fasit</h2>')
    n = tell_oppgaver(kap)
    ut.append(
        f'<p class="lede">Alle {n} oppgavene i kapitlet. '
        "Klikk på en oppgave for å se fasiten.</p>"
    )
    ut.append(
        '<div class="opgverktoy">'
        '<button type="button" class="knapp" data-handling="apne-alle">Vis all fasit</button>'
        '<button type="button" class="knapp" data-handling="lukk-alle">Skjul all fasit</button>'
        "</div>"
    )

    nr = 0
    for blokk in kap["oppgaveblokker"]:
        art = blokk["art"]
        kilde = f's. {blokk["side"]}' if blokk.get("side") else ""
        del_navn = blokk.get("del") or ""
        ut.append(f'<div class="opgblokk opgblokk--{art}">')
        ut.append('<div class="opgblokk__hode">')
        ut.append(f'<span class="opgblokk__art">{e(ART_NAVN.get(art, art))}</span>')
        if del_navn and del_navn != "Innledning":
            ut.append(f'<span class="pill">{e(del_navn)}</span>')
        if kilde:
            ut.append(f'<span class="opgblokk__kilde">{e(kilde)}</span>')
        ut.append("</div>")

        for post in blokk["poster"]:
            if "gruppe" in post:
                ut.append(f'<h3 class="opggruppe">{e(post["gruppe"])}</h3>')
                continue
            if "intro" in post:
                ut.append(f'<p class="opgintro">{e(post["intro"])}</p>')
                continue
            nr += 1
            fasit = post.get("f", "")
            if fasit:
                kropp = f'<div class="opg__body">{avsnitt(fasit)}</div>'
                klasse = "opg"
            else:
                kropp = (
                    '<div class="opg__body"><p>Fasit er ikke skrevet inn for denne '
                    "oppgaven ennå.</p></div>"
                )
                klasse = "opg opg--aapen"
            ut.append(
                f'<details class="{klasse}">'
                f'<summary><span class="opg__num">{nr}</span>'
                f'<span class="opg__q">{e(post["q"])}</span></summary>'
                f"{kropp}</details>"
            )
        ut.append("</div>")

    ut.append("</section>")
    return "\n".join(ut)


def panel_oversikt(kap: dict, forrige: dict | None, neste: dict | None) -> str:
    n_opg = tell_oppgaver(kap)
    n_del = sum(1 for d in kap["deler"] if d.get("tittel"))
    ut = ['<section class="panel active" id="panel-oversikt">']
    ut.append('<div class="hero">')
    ut.append(f'<span class="eyebrow">Kapittel {kap["nr"]}</span>')
    ut.append(f"<h1>{e(kap['tittel'])}</h1>")
    ingress = kap.get("ingress") or forste_avsnitt(kap)
    ut.append(f'<p class="lede">{e(ingress)}</p>')
    ut.append('<div class="hero__meta">')
    ut.append(f'<span class="pill pill--accent">{sider(kap)}</span>')
    ut.append(f'<span class="pill">{n_del} deler</span>')
    ut.append(f'<span class="pill">{n_opg} oppgaver med fasit</span>')
    ut.append(f'<span class="pill">{len(kap["sammendrag"])} punkter i sammendraget</span>')
    ut.append("</div></div>")

    if kap["laereplan"]:
        ut.append('<div class="callout callout--lp">')
        ut.append('<span class="callout__tit">Hva sier læreplanen i geofag?</span>')
        ut.append("<p>Elevene skal kunne</p><ul>")
        for m in kap["laereplan"]:
            ut.append(f"<li>{e(m)}</li>")
        ut.append("</ul></div>")

    if kap["sammendrag"]:
        ut.append("<h2>Hva bør du få til etter dette kapitlet?</h2>")
        ut.append(
            '<p class="lede">Kryss av når du sitter med punktet. '
            "Avkryssingen lagres lokalt i nettleseren din.</p>"
        )
        ut.append('<ul class="sjekk">')
        for i, s in enumerate(kap["sammendrag"]):
            boks_id = f"k{kap['nr']:02d}-s{i}"
            ut.append(
                f'<li><input type="checkbox" id="{boks_id}">'
                f'<label for="{boks_id}">{e(s)}</label></li>'
            )
        ut.append("</ul>")

    ut.append(kapnav(forrige, neste))
    ut.append("</section>")
    return "\n".join(ut)


def forste_avsnitt(kap: dict) -> str:
    for d in kap["deler"]:
        for b in d["blokker"]:
            if b["t"] == "p" and len(b["tekst"]) > 90:
                tekst = b["tekst"]
                return tekst if len(tekst) <= 300 else tekst[:297].rsplit(" ", 1)[0] + " …"
    return f"Kapittel {kap['nr']} i Geofag 1."


def panel_sammendrag(kap: dict) -> str:
    ut = ['<section class="panel" id="panel-sammendrag">']
    ut.append('<h2 style="margin-top:0">Sammendrag</h2>')
    ut.append(
        '<p class="lede">Alt du trenger fra kapitlet på én side. '
        "Skriv den ut, eller les gjennom den før en prøve.</p>"
    )
    if kap["sammendrag"]:
        ut.append('<div class="kort"><ul>')
        for s in kap["sammendrag"]:
            ut.append(f"<li>{e(s)}</li>")
        ut.append("</ul></div>")
    else:
        ut.append("<p>Læreboka har ikke et eget sammendrag for dette kapitlet.</p>")
    ut.append("</section>")
    return "\n".join(ut)


def panel_flashcards(kap: dict) -> str:
    kort = kap.get("flashcards") or []
    ut = ['<section class="panel" id="panel-flashcards">']
    ut.append('<h2 style="margin-top:0">Flashcards</h2>')
    if not kort:
        ut.append("<p>Det er ikke laget flashcards for dette kapitlet ennå.</p></section>")
        return "\n".join(ut)
    ut.append(
        f'<p class="lede">{len(kort)} begreper fra kapitlet. Klikk på kortet for å snu det, '
        "og merk hvert kort som lett eller vanskelig — vanskelige kort kommer oftere igjen.</p>"
    )
    ut.append("""
<div class="fc-scene">
  <div class="flashcard" id="flashcard" tabindex="0" role="button" aria-label="Snu kortet">
    <div class="flashcard__inner">
      <div class="flashcard__face flashcard__front">
        <div class="flashcard__kat" id="fcKat"></div>
        <div class="flashcard__term" id="fcTerm"></div>
        <div class="flashcard__hint">Klikk eller trykk mellomrom for å snu</div>
      </div>
      <div class="flashcard__face flashcard__back">
        <div class="flashcard__kat">Forklaring</div>
        <div class="flashcard__def" id="fcDef"></div>
      </div>
    </div>
  </div>
</div>
<div class="fc-kontroll">
  <button type="button" class="knapp knapp--lett" id="fcLett">Lett</button>
  <button type="button" class="knapp knapp--primar" id="fcNeste">Neste kort</button>
  <button type="button" class="knapp knapp--vanskelig" id="fcVanskelig">Vanskelig</button>
</div>
<p class="fc-stat" id="fcStat"></p>
<div class="opgverktoy" style="justify-content:center">
  <button type="button" class="knapp" id="fcNullstill">Nullstill statistikken</button>
</div>
""")
    ut.append("</section>")
    return "\n".join(ut)


def panel_quiz(kap: dict) -> str:
    q = kap.get("quiz") or []
    ut = ['<section class="panel" id="panel-quiz">']
    ut.append('<h2 style="margin-top:0">Quiz</h2>')
    if not q:
        ut.append("<p>Det er ikke laget quiz for dette kapitlet ennå.</p></section>")
        return "\n".join(ut)
    ut.append(
        f'<p class="lede">{len(q)} flervalgsspørsmål fra kapitlet, i tilfeldig rekkefølge. '
        "Du får en forklaring til hvert svar.</p>"
    )
    ut.append('<p class="quiz-poeng" id="quizPoeng"></p>')
    ut.append('<div id="quizRot"></div>')
    ut.append("</section>")
    return "\n".join(ut)


def kapnav(forrige: dict | None, neste: dict | None) -> str:
    if not forrige and not neste:
        return ""
    ut = ['<nav class="kapnav" aria-label="Forrige og neste kapittel">']
    if forrige:
        ut.append(
            f'<a href="k{forrige["nr"]:02d}.html"><small>Forrige kapittel</small>'
            f'<b>{forrige["nr"]}. {e(forrige["tittel"])}</b></a>'
        )
    else:
        ut.append('<a href="../index.html"><small>Tilbake</small><b>Alle kapitler</b></a>')
    if neste:
        ut.append(
            f'<a class="neste" href="k{neste["nr"]:02d}.html"><small>Neste kapittel</small>'
            f'<b>{neste["nr"]}. {e(neste["tittel"])}</b></a>'
        )
    else:
        ut.append('<a class="neste" href="../index.html"><small>Tilbake</small><b>Alle kapitler</b></a>')
    ut.append("</nav>")
    return "".join(ut)


def sidemeny_kapittel(kap: dict, alle: list[dict]) -> str:
    ut = ['      <div class="navgroup">', '        <span class="navgroup__label">Dette kapitlet</span>']
    for i, (navn, merke, tittel) in enumerate(FANER):
        if navn == "flashcards" and not kap.get("flashcards"):
            continue
        if navn == "quiz" and not kap.get("quiz"):
            continue
        aktiv = " active" if i == 0 else ""
        ut.append(
            f'        <button class="tab{aktiv}" data-tab="{navn}" data-tittel="{e(tittel)}">'
            f'<span class="tab__dot" aria-hidden="true">{merke}</span>'
            f'<span class="tab__txt">{e(tittel)}</span></button>'
        )
    ut.append("      </div>")
    ut.append('      <div class="navgroup">')
    ut.append('        <span class="navgroup__label">Alle kapitler</span>')
    for k in alle:
        aktiv = " active" if k["nr"] == kap["nr"] else ""
        ut.append(
            f'        <a class="tab{aktiv}" href="k{k["nr"]:02d}.html">'
            f'<span class="tab__dot" aria-hidden="true">{k["nr"]:02d}</span>'
            f'<span class="tab__txt">{e(k["tittel"])}</span></a>'
        )
    ut.append("      </div>")
    return "\n".join(ut)


def bygg_kapittel(kap: dict, alle: list[dict]) -> str:
    i = [k["nr"] for k in alle].index(kap["nr"])
    forrige = alle[i - 1] if i > 0 else None
    neste = alle[i + 1] if i < len(alle) - 1 else None

    fagstoff, _ = panel_fagstoff(kap)
    innhold = "\n".join([
        panel_oversikt(kap, forrige, neste),
        fagstoff,
        panel_oppgaver(kap),
        panel_sammendrag(kap),
        panel_flashcards(kap),
        panel_quiz(kap),
    ])

    data = []
    if kap.get("flashcards"):
        data.append("window.GEOFAG_FLASHCARDS=" + json.dumps(kap["flashcards"], ensure_ascii=False) + ";")
    if kap.get("quiz"):
        data.append("window.GEOFAG_QUIZ=" + json.dumps(kap["quiz"], ensure_ascii=False) + ";")
    ekstra = "<script>" + "".join(data) + "</script>\n" if data else ""

    return skall(
        tittel=f"{NETTSTED} — Kapittel {kap['nr']}: {kap['tittel']}",
        beskrivelse=(
            f"Kapittel {kap['nr']} i Geofag 1: {kap['tittel']}. "
            f"Fagstoff, {tell_oppgaver(kap)} oppgaver med fasit, sammendrag, flashcards og quiz."
        ),
        side_id=f"k{kap['nr']:02d}",
        sidemeny=sidemeny_kapittel(kap, alle),
        brodsmule=f"Kapittel {kap['nr']}",
        innhold=innhold,
        dybde=1,
        ekstra_js=ekstra,
    )


def bygg_index(alle: list[dict]) -> str:
    sum_opg = sum(tell_oppgaver(k) for k in alle)
    sum_fasit = sum(tell_fasit(k) for k in alle)

    ut = ['<section class="panel active" id="panel-kapitler">']
    ut.append('<div class="hero">')
    ut.append('<span class="eyebrow">Læringsside</span>')
    ut.append(f"<h1>{NETTSTED}</h1>")
    ut.append(
        f'<p class="lede">{UNDERTITTEL}. Hele pensumet delt opp i {len(alle)} kapitler — '
        f"med fagstoff, sammendrag og {sum_opg} oppgaver med fasit.</p>"
    )
    ut.append('<div class="hero__meta">')
    ut.append(f'<span class="pill pill--accent">{len(alle)} kapitler</span>')
    ut.append(f'<span class="pill">{sum_opg} oppgaver</span>')
    ut.append(f'<span class="pill">{sum_fasit} med fasit</span>')
    ut.append("</div></div>")

    ut.append("""
<div class="sok">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
  <input type="search" id="sokFelt" placeholder="Søk i kapitlene — prøv «skred», «bre», «vann» …" aria-label="Søk i kapitlene">
</div>
""")
    ut.append(f'<p class="sok__treff" id="sokTreff">{len(alle)} kapitler</p>')

    ut.append('<div class="grid grid--2" style="margin-top:20px">')
    for k in alle:
        n_opg = tell_oppgaver(k)
        sokeord = " ".join([
            k["tittel"], " ".join(k["sammendrag"]),
            " ".join(d["tittel"] or "" for d in k["deler"]),
        ]).lower()
        ut.append(
            f'<a class="kort kapkort" href="kapittel/k{k["nr"]:02d}.html" data-sok="{e(sokeord)}">'
            f'<span class="kapkort__nr">Kapittel {k["nr"]}</span>'
            f"<h3>{e(k['tittel'])}</h3>"
            f"<p>{e(kortbeskrivelse(k))}</p>"
            f'<div class="kapkort__tall"><span>{sider(k)}</span>'
            f"<span>{n_opg} oppgaver</span>"
            f'<span>{len(k["sammendrag"])} sammendragspunkter</span></div>'
            "</a>"
        )
    ut.append("</div>")

    ut.append("""
<h2>Slik bruker du siden</h2>
<div class="grid grid--3">
  <div class="kort"><h3>Les fagstoffet</h3><p>Hvert kapittel har hele kapittelteksten delt opp i deler, med figurtekster og refleksjonsspørsmål underveis.</p></div>
  <div class="kort"><h3>Løs oppgavene</h3><p>Alle spørsmål, «Hva tror du?»-oppgaver og kapitteloppgaver ligger samlet. Fasiten er skjult til du klikker.</p></div>
  <div class="kort"><h3>Test deg selv</h3><p>Flashcards for begrepene og en quiz med forklaring til hvert svar. Framdriften lagres lokalt.</p></div>
</div>
""")
    ut.append("</section>")

    meny = ['      <div class="navgroup">', '        <span class="navgroup__label">Alle kapitler</span>']
    for k in alle:
        meny.append(
            f'        <a class="tab" href="kapittel/k{k["nr"]:02d}.html">'
            f'<span class="tab__dot" aria-hidden="true">{k["nr"]:02d}</span>'
            f'<span class="tab__txt">{e(k["tittel"])}</span></a>'
        )
    meny.append("      </div>")

    return skall(
        tittel=f"{NETTSTED} — {UNDERTITTEL}",
        beskrivelse=(
            f"Læringsside for Geofag 1: {len(alle)} kapitler med fagstoff, sammendrag "
            f"og {sum_opg} oppgaver med fasit."
        ),
        side_id="index",
        sidemeny="\n".join(meny),
        brodsmule="Alle kapitler",
        innhold="\n".join(ut),
        dybde=0,
    )


def kortbeskrivelse(kap: dict) -> str:
    if kap.get("ingress"):
        return kap["ingress"]
    for s in kap["sammendrag"]:
        if 60 <= len(s) <= 190:
            return s
    tekst = forste_avsnitt(kap)
    return tekst if len(tekst) <= 190 else tekst[:187].rsplit(" ", 1)[0] + " …"


def main() -> int:
    alle = les_kapitler()
    UT_KAP.mkdir(exist_ok=True)
    for kap in alle:
        (UT_KAP / f"k{kap['nr']:02d}.html").write_text(bygg_kapittel(kap, alle), encoding="utf-8")
    (ROOT / "index.html").write_text(bygg_index(alle), encoding="utf-8")

    sum_opg = sum(tell_oppgaver(k) for k in alle)
    sum_fasit = sum(tell_fasit(k) for k in alle)
    print(f"bygde index.html + {len(alle)} kapittelsider")
    print(f"oppgaver: {sum_fasit}/{sum_opg} har fasit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

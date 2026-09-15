/* ==========================================================================
   GEOFAG 1 — grensesnitt
   Alt kjorer i nettleseren. Framdrift og flashcard-statistikk ligger lagret
   lokalt i nettleseren og sendes ingen steder.
   ========================================================================== */
(function () {
  "use strict";

  /* ---------- lagring som aldri kaster ---------- */
  var lager = {
    get: function (n, fallback) {
      try {
        var v = localStorage.getItem(n);
        return v === null ? fallback : JSON.parse(v);
      } catch (e) {
        return fallback;
      }
    },
    set: function (n, v) {
      try {
        localStorage.setItem(n, JSON.stringify(v));
      } catch (e) {
        /* privat vindu e.l. — vi klarer oss uten */
      }
    }
  };

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- tema ---------- */
  var SOL = 'M12 3v2M12 19v2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M3 12h2M19 12h2M5.6 18.4 7 17M17 7l1.4-1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z';
  var MANE = 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z';

  function settTema(t) {
    document.documentElement.setAttribute('data-theme', t);
    var ikon = $('#temaIkon');
    if (ikon) ikon.setAttribute('d', t === 'dark' ? SOL : MANE);
    lager.set('geofag:tema', t);
  }

  var temaBtn = $('#temaBtn');
  if (temaBtn) {
    temaBtn.addEventListener('click', function () {
      settTema(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }
  settTema(lager.get('geofag:tema', window.matchMedia &&
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  /* ---------- sidemeny pa smale skjermer ---------- */
  var meny = $('#sidemeny'), skygge = $('#skygge'), burger = $('#burger');
  function lukkMeny() {
    if (meny) meny.classList.remove('open');
    if (skygge) skygge.classList.remove('on');
  }
  if (burger) {
    burger.addEventListener('click', function () {
      if (!meny) return;
      var apen = meny.classList.toggle('open');
      if (skygge) skygge.classList.toggle('on', apen);
    });
  }
  if (skygge) skygge.addEventListener('click', lukkMeny);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') lukkMeny();
  });

  /* ---------- faner ---------- */
  /* Sidene kan bygges pa to mater: en fil per kapittel, eller alt i en fil.
     I enkeltfil-versjonen ligger hvert kapittel i <div class="kapittel">, og
     bare ett av dem er synlig av gangen. Derfor slar vi opp faner, paneler og
     avkryssingsbokser pa nytt hver gang, avgrenset til det aktive kapitlet.
     Finnes ingen slike containere, faller vi tilbake til hele dokumentet, og
     oppforselen blir nøyaktig som for. */
  var noNa = $('#noNa');

  function rotKap() {
    return document.querySelector('.kapittel[data-kap]:not([hidden])');
  }
  function faneListe() {
    var m = document.querySelector('[data-kapmeny]:not([hidden])');
    return $$('.tab[data-tab]', m || document);
  }
  function panelListe() {
    return $$('.panel[id^="panel-"]', rotKap() || document);
  }
  function sideNokkel() {
    return document.body.dataset.side || 'global';
  }

  function visFane(navn, skrivHistorikk) {
    // Finn treffet forst. Uten treff rorer vi ikke panelene, slik at siden
    // aldri ender opp med alt skjult.
    var paneler = panelListe();
    var traff = paneler.some(function (p) { return p.id === 'panel-' + navn; });
    if (!traff) return false;
    paneler.forEach(function (p) {
      p.classList.toggle('active', p.id === 'panel-' + navn);
    });
    faneListe().forEach(function (f) {
      var pa = f.dataset.tab === navn;
      f.classList.toggle('active', pa);
      if (pa && noNa) noNa.textContent = f.dataset.tittel || f.textContent.trim();
    });
    if (skrivHistorikk && history.replaceState) {
      history.replaceState(null, '', '#' + navn);
    }
    lager.set('geofag:fane:' + sideNokkel(), navn);
    lukkMeny();
    return true;
  }

  // Delegert, slik at faner som byttes ut ved kapittelbytte ogsa virker.
  document.addEventListener('click', function (ev) {
    var f = ev.target.closest ? ev.target.closest('.tab[data-tab]') : null;
    if (!f) return;
    visFane(f.dataset.tab, true);
    var innhold = $('#hovedinnhold');
    if (innhold) innhold.scrollIntoView({ block: 'start' });
  });

  function startFane() {
    var faner = faneListe();
    if (!faner.length || !panelListe().length) return;
    var fraHash = (location.hash || '').replace('#', '');
    var husket = lager.get('geofag:fane:' + sideNokkel(), null);
    if (!visFane(fraHash, false) && !visFane(husket, false)) {
      visFane(faner[0].dataset.tab, false);
    }
  }

  /* ---------- fasit: apne og lukke alle ---------- */
  $$('[data-handling="apne-alle"]').forEach(function (kn) {
    kn.addEventListener('click', function () {
      var rot = kn.closest('.panel') || document;
      $$('details.opg', rot).forEach(function (d) { d.open = true; });
    });
  });
  $$('[data-handling="lukk-alle"]').forEach(function (kn) {
    kn.addEventListener('click', function () {
      var rot = kn.closest('.panel') || document;
      $$('details.opg', rot).forEach(function (d) { d.open = false; });
    });
  });

  /* ---------- sok ---------- */
  var sokFelt = $('#sokFelt');
  if (sokFelt) {
    var treffTekst = $('#sokTreff');
    var mal = $$('[data-sok]');
    sokFelt.addEventListener('input', function () {
      var q = sokFelt.value.trim().toLowerCase();
      var n = 0;
      mal.forEach(function (el) {
        var vis = !q || el.dataset.sok.indexOf(q) !== -1;
        el.style.display = vis ? '' : 'none';
        if (vis) n++;
      });
      if (treffTekst) {
        treffTekst.textContent = q
          ? n + (n === 1 ? ' treff' : ' treff') + ' på «' + sokFelt.value.trim() + '»'
          : mal.length + ' kapitler';
      }
    });
  }

  /* ---------- flashcards ---------- */
  var fcData = window.GEOFAG_FLASHCARDS;
  var fcKort = $('#flashcard');
  if (fcKort && fcData && fcData.length) {
    var fcNokkel = 'geofag:fc:' + (document.body.dataset.side || 'global');
    var kjent = lager.get(fcNokkel, {});
    var koe = [], nr = -1;

    function byggKoe() {
      // Kort merket «vanskelig» kommer oftere; kort merket «lett» sjeldnere.
      koe = [];
      fcData.forEach(function (k, i) {
        var vekt = kjent[i] === 'lett' ? 1 : (kjent[i] === 'vanskelig' ? 3 : 2);
        for (var j = 0; j < vekt; j++) koe.push(i);
      });
      for (var a = koe.length - 1; a > 0; a--) {
        var b = Math.floor(Math.random() * (a + 1));
        var t = koe[a]; koe[a] = koe[b]; koe[b] = t;
      }
    }

    function tegnKort() {
      if (!koe.length) byggKoe();
      nr = (nr + 1) % koe.length;
      var k = fcData[koe[nr]];
      fcKort.classList.remove('flipped');
      $('#fcKat').textContent = k.k || 'Begrep';
      $('#fcTerm').textContent = k.t;
      $('#fcDef').textContent = k.d;
      var lett = 0, vansk = 0;
      Object.keys(kjent).forEach(function (n) {
        if (kjent[n] === 'lett') lett++; else if (kjent[n] === 'vanskelig') vansk++;
      });
      var stat = $('#fcStat');
      if (stat) {
        stat.textContent = 'Kort ' + (nr + 1) + ' av ' + koe.length +
          ' · ' + fcData.length + ' begreper · ' + lett + ' lette · ' + vansk + ' vanskelige';
      }
    }

    function merk(verdi) {
      kjent[koe[nr]] = verdi;
      lager.set(fcNokkel, kjent);
      tegnKort();
    }

    fcKort.addEventListener('click', function () { fcKort.classList.toggle('flipped'); });
    fcKort.addEventListener('keydown', function (e) {
      if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); fcKort.classList.toggle('flipped'); }
    });
    var nesteBtn = $('#fcNeste'); if (nesteBtn) nesteBtn.addEventListener('click', tegnKort);
    var lettBtn = $('#fcLett'); if (lettBtn) lettBtn.addEventListener('click', function () { merk('lett'); });
    var vanskBtn = $('#fcVanskelig'); if (vanskBtn) vanskBtn.addEventListener('click', function () { merk('vanskelig'); });
    var nullBtn = $('#fcNullstill');
    if (nullBtn) {
      nullBtn.addEventListener('click', function () {
        kjent = {}; lager.set(fcNokkel, kjent); byggKoe(); nr = -1; tegnKort();
      });
    }
    byggKoe(); tegnKort();
  }

  /* ---------- quiz ---------- */
  var qData = window.GEOFAG_QUIZ;
  var qRot = $('#quizRot');
  if (qRot && qData && qData.length) {
    var qNr = 0, qPoeng = 0, qRekke = [];

    function stokk() {
      qRekke = qData.map(function (_, i) { return i; });
      for (var a = qRekke.length - 1; a > 0; a--) {
        var b = Math.floor(Math.random() * (a + 1));
        var t = qRekke[a]; qRekke[a] = qRekke[b]; qRekke[b] = t;
      }
    }

    function tegnQuiz() {
      if (qNr >= qRekke.length) return tegnResultat();
      var q = qData[qRekke[qNr]];
      var kort = document.createElement('div');
      kort.className = 'quiz-kort';

      var kat = document.createElement('div');
      kat.className = 'quiz-kat';
      kat.textContent = 'Spørsmål ' + (qNr + 1) + ' av ' + qRekke.length + (q.k ? ' · ' + q.k : '');
      kort.appendChild(kat);

      var sp = document.createElement('div');
      sp.className = 'quiz-q';
      sp.textContent = q.q;
      kort.appendChild(sp);

      var valg = document.createElement('div');
      valg.className = 'quiz-valg';
      q.alt.forEach(function (tekst, i) {
        var kn = document.createElement('button');
        kn.type = 'button';
        kn.className = 'quiz-alt';
        kn.textContent = tekst;
        kn.addEventListener('click', function () { svar(kort, valg, q, i); });
        valg.appendChild(kn);
      });
      kort.appendChild(valg);

      qRot.innerHTML = '';
      qRot.appendChild(kort);
      oppdaterPoeng();
    }

    function svar(kort, valg, q, valgt) {
      var knapper = $$('button', valg);
      knapper.forEach(function (kn, i) {
        kn.disabled = true;
        if (i === q.rett) kn.classList.add('rett');
        else if (i === valgt) kn.classList.add('feil');
      });
      if (valgt === q.rett) qPoeng++;

      var svarBoks = document.createElement('div');
      svarBoks.className = 'quiz-svar';
      svarBoks.textContent = (valgt === q.rett ? 'Riktig. ' : 'Ikke riktig. ') + (q.f || '');
      kort.appendChild(svarBoks);

      var neste = document.createElement('button');
      neste.type = 'button';
      neste.className = 'knapp knapp--primar';
      neste.style.marginTop = '16px';
      neste.textContent = qNr + 1 >= qRekke.length ? 'Se resultat' : 'Neste spørsmål';
      neste.addEventListener('click', function () { qNr++; tegnQuiz(); });
      kort.appendChild(neste);
      neste.focus();
      oppdaterPoeng();
    }

    function tegnResultat() {
      var andel = Math.round((qPoeng / qRekke.length) * 100);
      var dom = ['Her er det mer å hente — les kapitlet en gang til.',
                 'Godt i gang. Gå tilbake til delene du bommet på.',
                 'Solid. Du sitter med det meste.',
                 'Meget bra. Du kan dette kapitlet.'][Math.min(3, Math.floor(andel / 26))];
      qRot.innerHTML = '';
      var kort = document.createElement('div');
      kort.className = 'quiz-kort';
      var h = document.createElement('h3');
      h.style.marginTop = '0';
      h.textContent = qPoeng + ' av ' + qRekke.length + ' riktige (' + andel + ' %)';
      var p = document.createElement('p');
      p.textContent = dom;
      var kn = document.createElement('button');
      kn.type = 'button';
      kn.className = 'knapp knapp--primar';
      kn.textContent = 'Ta quizen på nytt';
      kn.addEventListener('click', function () { qNr = 0; qPoeng = 0; stokk(); tegnQuiz(); });
      kort.appendChild(h); kort.appendChild(p); kort.appendChild(kn);
      qRot.appendChild(kort);
      oppdaterPoeng();
    }

    function oppdaterPoeng() {
      var el = $('#quizPoeng');
      if (el) el.textContent = qPoeng + ' av ' + Math.min(qNr, qRekke.length) + ' riktige så langt';
    }

    stokk();
    tegnQuiz();
  }

  /* ---------- kapittelbytte (bare i enkeltfil-versjonen) ----------
     Hvert kapittel ligger i <div class="kapittel" data-kap="kNN">, og
     sidemenyen har en tilhorende <div data-kapmeny="kNN"> med fanene.
     Adressen styrer alt: #k13 apner kapittel 13, #k13-oppgaver apner
     oppgavefanen i kapittel 13. */
  var kapitler = $$('.kapittel[data-kap]');

  if (!kapitler.length) {
    startFane();
  } else {
    var kapmenyer = $$('[data-kapmeny]');
    var merke = $('#merkeUnder');
    var kicker = $('.topbar__crumb .kicker');

    var visKapittel = function (id, skrivHistorikk) {
      var akt = null;
      kapitler.forEach(function (k) {
        var pa = k.dataset.kap === id;
        k.hidden = !pa;
        if (pa) akt = k;
      });
      if (!akt) {
        kapitler.forEach(function (k) { k.hidden = k.dataset.kap !== kapitler[0].dataset.kap; });
        return false;
      }
      kapmenyer.forEach(function (m) { m.hidden = m.dataset.kapmeny !== id; });
      $$('[data-gakap]').forEach(function (a) {
        a.classList.toggle('active', a.dataset.gakap === id);
      });

      var navn = akt.dataset.navn || 'Oversikt';
      if (merke) merke.textContent = navn;
      if (kicker) kicker.textContent = navn;
      document.title = akt.dataset.tittel || document.title;
      document.body.dataset.side = id;

      startFane();
      lukkMeny();
      if (skrivHistorikk && history.replaceState) {
        history.replaceState(null, '', '#' + id);
      }
      return true;
    };

    var fraAdresse = function () {
      var h = (location.hash || '').replace('#', '');
      var m = /^(k\d\d)/.exec(h);
      if (!m || !visKapittel(m[1], false)) return false;
      if (h !== m[1]) visFane(h, false);
      return true;
    };

    window.addEventListener('hashchange', function () {
      if (!fraAdresse()) return;
      var innhold = $('#hovedinnhold');
      if (innhold) innhold.scrollIntoView({ block: 'start' });
    });

    if (!fraAdresse()) visKapittel(kapitler[0].dataset.kap, false);
  }

  /* ---------- til toppen ---------- */
  var topp = $('#tilTopp');
  if (topp) {
    topp.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    window.addEventListener('scroll', function () {
      topp.classList.toggle('on', window.scrollY > 500);
    }, { passive: true });
  }
})();

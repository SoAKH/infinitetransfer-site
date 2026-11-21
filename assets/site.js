// Infinite Transfer : scripts partagés par toutes les pages
(function () {
  const $ = id => document.getElementById(id);
  const store = {
    get(k) { try { return JSON.parse(sessionStorage.getItem(k)); } catch (e) { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  // Menu mobile
  const menu = $('menu'), menuBtn = $('menuBtn');
  if (menu && menuBtn) {
    menuBtn.addEventListener('click', () => {
      const o = menu.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', o);
    });
  }
  // Sous-menu Services
  document.querySelectorAll('.has-sub > button').forEach(b => {
    b.addEventListener('click', () => {
      const li = b.parentElement, o = li.classList.toggle('open');
      b.setAttribute('aria-expanded', o);
    });
  });
  document.addEventListener('click', e => {
    document.querySelectorAll('.has-sub.open').forEach(li => {
      if (!li.contains(e.target) && window.innerWidth > 1060) {
        li.classList.remove('open');
        li.querySelector('button').setAttribute('aria-expanded', 'false');
      }
    });
  });

  // Dates minimales
  const today = new Date().toISOString().slice(0, 10);
  ['date', 'qDate'].forEach(id => { if ($(id)) $(id).min = today; });

  // Réservation rapide (accueil) : mémorise le trajet puis ouvre la page Contact
  const quick = $('quick');
  if (quick) {
    quick.addEventListener('submit', e => {
      e.preventDefault();
      store.set('it-trajet', { from: $('qFrom').value, to: $('qTo').value, date: $('qDate').value, time: $('qTime').value });
      window.location.href = quick.getAttribute('action');
    });
  }
  // Liens « destination » : mémorise la destination choisie
  document.querySelectorAll('[data-to]').forEach(a => {
    a.addEventListener('click', () => store.set('it-trajet', Object.assign(store.get('it-trajet') || {}, { to: a.dataset.to })));
  });
  document.querySelectorAll('[data-from]').forEach(a => {
    a.addEventListener('click', () => store.set('it-trajet', Object.assign(store.get('it-trajet') || {}, { from: a.dataset.from })));
  });

  // Formulaire de devis (page Contact)
  const form = $('quote');
  if (!form) return;
  const saved = store.get('it-trajet');
  if (saved) ['from', 'to', 'date', 'time'].forEach(k => { if (saved[k] && $(k)) $(k).value = saved[k]; });

  const err = $('err'), res = $('result'), sum = $('summary');
  const ACCESS_KEY = '7a45e768-a1f8-49e4-bf84-8dd053508275'; // Web3Forms : demandes reçues sur infinite.transfer.vtc@gmail.com
  const v = id => $(id).value.trim();
  function check() {
    const missing = [['from', 'le lieu de prise en charge'], ['to', 'la destination'], ['date', 'la date'], ['time', "l'heure"], ['name', 'votre nom'], ['phone', 'votre téléphone']]
      .filter(([id]) => !v(id)).map(x => x[1]);
    if (v('email') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v('email'))) missing.push('une adresse e-mail valide');
    if (missing.length) { err.textContent = "Merci d'indiquer " + missing.join(', ') + '.'; err.hidden = false; return null; }
    err.hidden = true;
    const dt = new Date(v('date') + 'T00:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    let txt = `Bonjour, je souhaite un devis pour un transfert.\n\nDépart : ${v('from')}\nDestination : ${v('to')}\nDate : ${dt} à ${v('time')}\nPassagers : ${v('pax')} · Valises : ${v('bags')}\nNom : ${v('name')}\nTéléphone : ${v('phone')}`;
    if (v('email')) txt += `\nE-mail : ${v('email')}`;
    if ($('seat').checked) txt += `\nSiège auto : oui`;
    if (v('msg')) txt += `\nPrécisions : ${v('msg')}`;
    return txt;
  }
  // Envoi WhatsApp : le message part du compte WhatsApp du client
  $('waBtn').addEventListener('click', () => {
    const txt = check(); if (!txt) return;
    const url = 'https://wa.me/33767123512?text=' + encodeURIComponent(txt);
    const w = window.open(url, '_blank', 'noopener'); if (!w) window.location.href = url;
  });
  // Envoi par e-mail via Web3Forms
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const txt = check(); if (!txt) { res.classList.remove('show'); return; }
    const btn = $('sendBtn'); btn.disabled = true; const label = btn.firstChild.textContent; btn.firstChild.textContent = 'Envoi en cours… ';
    const data = { access_key: ACCESS_KEY, subject: 'Demande de devis – ' + v('name'), from_name: 'Site Infinite Transfer',
      botcheck: $('botcheck').checked, nom: v('name'), telephone: v('phone'), message: txt };
    if (v('email')) data.email = v('email');
    try {
      const r = await fetch('https://api.web3forms.com/submit', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(data) });
      const j = await r.json();
      if (!r.ok || !j.success) throw new Error(j.message || r.status);
      sum.textContent = txt; res.classList.add('show'); res.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      ['from', 'to', 'date', 'time', 'msg'].forEach(id => $(id).value = ''); $('seat').checked = false;
      try { sessionStorage.removeItem('it-trajet'); } catch (x) {}
    } catch (x) {
      err.textContent = "L'envoi n'a pas abouti. Réessayez, utilisez le bouton WhatsApp ou appelez-nous au +33 7 67 12 35 12.";
      err.hidden = false;
    } finally { btn.disabled = false; btn.firstChild.textContent = label; }
  });
})();

// Suggestions d'adresses (service gratuit de la Géoplateforme IGN, France entière, résultats proches de Marseille en premier)
(function () {
  const FAV = [
    'Aéroport Marseille Provence, 13700 Marignane',
    'Gare Marseille Saint-Charles, 13001 Marseille',
    'Gare Aix-en-Provence TGV, 13100 Aix-en-Provence',
    'Terminal de croisière MPCT, 13016 Marseille'
  ];
  const API = 'https://data.geopf.fr/geocodage/search?autocomplete=1&lat=43.2965&lon=5.3698&q=';
  const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  function attach(input) {
    const box = document.createElement('ul');
    box.className = 'ac-list'; box.id = input.id + '-ac'; box.setAttribute('role', 'listbox'); box.hidden = true;
    input.parentElement.classList.add('ac-wrap');
    input.parentElement.appendChild(box);
    input.setAttribute('role', 'combobox'); input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', box.id); input.setAttribute('aria-expanded', 'false'); input.autocomplete = 'off';
    let items = [], active = -1, timer, seq = 0;

    function render(list) {
      items = list; active = -1;
      box.innerHTML = list.map((t, i) => {
        const parts = t.split(/, (?=\d{5} )/);
        return `<li role="option" id="${box.id}-${i}" data-i="${i}"><span>${parts[0]}</span>${parts[1] ? `<small>${parts[1]}</small>` : ''}</li>`;
      }).join('');
      box.hidden = !list.length; input.setAttribute('aria-expanded', String(!!list.length));
    }
    function pick(i) {
      if (i < 0 || !items[i]) return;
      input.value = items[i]; render([]);
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function highlight(i) {
      active = (i + items.length) % items.length;
      [...box.children].forEach((li, k) => li.classList.toggle('on', k === active));
      input.setAttribute('aria-activedescendant', box.id + '-' + active);
    }
    async function search(q) {
      const my = ++seq, nq = norm(q);
      const fav = FAV.filter(f => norm(f).includes(nq));
      if (q.length < 3) { render(q ? fav : FAV); return; }
      try {
        const [a, p] = await Promise.all([
          fetch(API + encodeURIComponent(q) + '&limit=5').then(r => r.json()),
          fetch(API + encodeURIComponent(q) + '&limit=3&index=poi').then(r => r.json())
        ]);
        if (my !== seq) return;
        const poi = (p.features || []).map(f => {
          const pr = f.properties, city = [].concat(pr.city || [])[0], pc = [].concat(pr.postcode || [])[0];
          return pr.toponym ? `${pr.toponym}${pc && city ? `, ${pc} ${city}` : ''}` : null;
        }).filter(Boolean);
        const addr = (a.features || []).map(f => {
          const pr = f.properties;
          return pr.type === 'municipality' ? `${pr.city}, ${pr.postcode}` : (pr.postcode ? `${pr.name}, ${pr.postcode} ${pr.city}` : pr.label);
        });
        const seen = new Set();
        render([...fav, ...poi, ...addr].filter(t => !seen.has(norm(t)) && seen.add(norm(t))).slice(0, 8));
      } catch (e) { render(fav); }
    }
    input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => search(input.value.trim()), 220); });
    input.addEventListener('focus', () => { if (!input.value.trim()) render(FAV); });
    input.addEventListener('keydown', e => {
      if (box.hidden) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); highlight(active + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(active - 1); }
      else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); pick(active); }
      else if (e.key === 'Escape') { render([]); }
    });
    box.addEventListener('mousedown', e => { const li = e.target.closest('li'); if (li) { e.preventDefault(); pick(+li.dataset.i); } });
    input.addEventListener('blur', () => setTimeout(() => render([]), 120));
  }
  ['qFrom', 'qTo', 'from', 'to'].forEach(id => { const el = document.getElementById(id); if (el) attach(el); });
})();

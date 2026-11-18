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
  form.addEventListener('submit', e => {
    e.preventDefault();
    const v = id => $(id).value.trim();
    const missing = [['from', 'le lieu de prise en charge'], ['to', 'la destination'], ['date', 'la date'], ['time', "l'heure"], ['name', 'votre nom'], ['phone', 'votre téléphone']]
      .filter(([id]) => !v(id)).map(x => x[1]);
    if (missing.length) {
      err.textContent = "Merci d'indiquer " + missing.join(', ') + '.';
      err.hidden = false; res.classList.remove('show'); return;
    }
    err.hidden = true;
    const dt = new Date(v('date') + 'T00:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    let txt = `Bonjour, je souhaite un devis pour un transfert.\n\nDépart : ${v('from')}\nDestination : ${v('to')}\nDate : ${dt} à ${v('time')}\nPassagers : ${v('pax')} · Valises : ${v('bags')}\nNom : ${v('name')}\nTéléphone : ${v('phone')}`;
    if ($('seat').checked) txt += `\nSiège auto : oui`;
    if (v('msg')) txt += `\nPrécisions : ${v('msg')}`;
    sum.textContent = txt;
    $('waLink').href = 'https://wa.me/33767123512?text=' + encodeURIComponent(txt);
    $('mailLink').href = 'mailto:contact@infinitetransfer.eu?subject=' + encodeURIComponent('Demande de devis – ' + v('name')) + '&body=' + encodeURIComponent(txt);
    res.classList.add('show');
    res.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
  $('copyBtn').addEventListener('click', async e => {
    const b = e.currentTarget;
    try { await navigator.clipboard.writeText(sum.textContent); b.textContent = 'Texte copié'; }
    catch (x) { b.textContent = 'Sélectionnez le texte'; }
  });
})();

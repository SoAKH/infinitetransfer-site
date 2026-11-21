# Infinite Transfer – site web

Site du service de chauffeur privé VTC Infinite Transfer (Marseille & Provence).

- `build.py` génère le site complet dans `public/` (aucune dépendance, Python 3).
- `services.py` : contenu des 6 pages services.
- `templates/` : corps des pages Accueil et Contact.
- `content/articles/` : un fichier Markdown par article (voir l'en-tête de `build.py`).
- `old_urls.txt` : adresses de l'ancien site, redirigées (301) via `public/_redirects`.
- `assets/` : feuille de style et scripts partagés.

Hébergement : Cloudflare Pages (commande `python3 build.py`, dossier `public`, variable `SITE_URL` = adresse publique du site). Chaque commit sur `main` met le site à jour. Sans `SITE_URL`, le site est masqué à Google (noindex).

Aperçu : chaque mise à jour est visible sur l’adresse Netlify du projet avant le branchement du domaine.

# Rapport des corrections — 18 septembre 2026

Ce document explique **tout ce qui a changé** dans le projet E-commune Horison
avec la Pull Request n°1
(https://github.com/1998Jules/projet_horieon/pull/1), **pourquoi**, et **ce que
vous devez faire** de votre côté.

Il s'adresse d'abord au propriétaire du projet, mais chaque point commence par
une explication simple (« En clair »), compréhensible sans être développeur.

Pour le fonctionnement général du projet, voir [DOCUMENTATION.md](DOCUMENTATION.md).

---

## Sommaire

1. [En bref](#1-en-bref)
2. [À faire de votre côté](#2-à-faire-de-votre-côté)
3. [Failles de sécurité corrigées](#3-failles-de-sécurité-corrigées)
4. [Installation et configuration](#4-installation-et-configuration)
5. [Géoportail](#5-géoportail)
6. [Module agriculture](#6-module-agriculture)
7. [Données reconstruites à partir de sources ouvertes](#7-données-reconstruites-à-partir-de-sources-ouvertes)
8. [Documentation](#8-documentation)
9. [Tests et vérifications](#9-tests-et-vérifications)
10. [Ce qui reste à faire](#10-ce-qui-reste-à-faire)
11. [Fichiers modifiés](#11-fichiers-modifiés)

---

## 1. En bref

| Domaine | Avant | Après |
|---|---|---|
| Sécurité | Mots de passe Gmail en clair dans le code ; calendrier cultural modifiable par n'importe qui ; deux failles web (CSRF, XSS) | Secrets dans `.env` ; modifications réservées aux administrateurs ; failles corrigées |
| Installation | Impossible sur un autre ordinateur (`requirements.txt` illisible par `pip`, chemins `D:\Horison` écrits en dur, plantage avec Django 6) | Installation documentée pas à pas, testée sur un poste neuf |
| Géoportail | Page d'accueil en erreur 404, fond de carte bloqué (403), liste des cantons vide, trois couches inaccessibles | Tout fonctionne |
| Agriculture | Carte centrée sur Aného, couches jamais chargées, trois API en erreur 500 | Carte centrée sur Blitta 2, régions, préfectures et commune affichées |
| Données | Uniquement dans votre base de données | Commande `import_blitta2` qui reconstruit les couches à partir de sources ouvertes |
| Documentation | Aucune | `README.md`, `DOCUMENTATION.md` (35 sections), version PDF |
| Tests | Aucun | 12 tests automatisés |

Les commits de la PR ne changent pas le comportement attendu de l'application,
sauf là où c'était nécessaire pour corriger un défaut. Chaque changement de
comportement est signalé ci-dessous par ⚠️.

---

## 2. À faire de votre côté

### 2.1 Tout de suite (sécurité)

1. **Révoquer les mots de passe d'application Gmail** qui étaient écrits dans
   le code (`settings.py`, `horison/settings.py`, `.env.exemple`). Le dépôt est
   public : ils restent lisibles dans l'historique Git, même après cette PR.
   Compte Google › Sécurité › Mots de passe des applications › supprimer, puis
   en créer un nouveau et le mettre **uniquement** dans votre fichier `.env`.
2. **Générer une nouvelle `SECRET_KEY`** pour votre serveur de production :

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
   ```

### 2.2 Au moment de fusionner la PR

3. **Sauvegardez votre `.env` avant `git pull`.** Les fichiers `.env` et
   `db.sqlite3` ne sont plus suivis par Git : le `git pull` les **supprimera de
   votre ordinateur**. Faites-en une copie avant, ou récupérez-les ensuite :

   ```bash
   git show cd34855:.env > .env   # cd34855 = dernier commit avant la PR
   ```

4. **Complétez votre `.env`** à partir du nouveau modèle `.env.exemple`
   (voir [section 4](#4-installation-et-configuration)). En particulier :
   `DEBUG=True` sur votre ordinateur de développement ⚠️ (la valeur par défaut
   est maintenant `False`, plus sûre en production).
5. **Réinstallez les dépendances** : `pip install -r requirements.txt`.

### 2.3 Selon votre utilisation

6. ⚠️ **Frontend (application React)** : toute requête qui **modifie** des
   données sur `/agriculture/api/…` doit envoyer l'en-tête
   `Authorization: Token <clé>`. La session du navigateur seule ne suffit plus
   ([section 3.2](#32-faille-csrf-sur-lapi-agriculture)). Les lectures (GET)
   ne changent pas.
7. ⚠️ **Calendrier cultural** : seuls les comptes administrateurs
   (`is_staff`) peuvent désormais ajouter, modifier ou supprimer une culture
   ([section 3.1](#31-calendrier-cultural-modifiable-par-nimporte-qui)).
8. ⚠️ **Alertes planifiées** : si votre environnement Python est
   `D:\Horison\hori`, définissez la variable d'environnement
   `HORIEON_VENV=D:\Horison\hori`. Sinon `run_alerts.bat` utilise le dossier
   `.venv` du projet ([section 6.4](#64-scripts-dalertes-planifiées)).
9. **Earth Engine** : vous pouvez garder votre fichier
   `ee-koutoumbogajules-c99000ca569e.json` à la racine du projet, rien ne
   change. Vous pouvez aussi indiquer un autre emplacement dans `.env` avec
   `GEE_SERVICE_ACCOUNT_KEY`.
10. ⚠️ **Ne lancez pas `python manage.py import_blitta2` sur votre base de
    production** : cette commande **remplace** le contenu des couches par des
    données ouvertes. Elle est faite pour une nouvelle installation, sans vos
    relevés de terrain ([section 7](#7-données-reconstruites-à-partir-de-sources-ouvertes)).

---

## 3. Failles de sécurité corrigées

### 3.1 Calendrier cultural modifiable par n'importe qui

> **En clair** : n'importe quel internaute pouvait ajouter, modifier ou
> effacer les cultures du calendrier, sans compte.

- **Problème** : les vues `add_crop_calendar`, `update_crop_calendar` et
  `delete_crop_calendar` (`agriculture/views.py`) n'avaient aucun contrôle
  d'accès et étaient exemptées de la protection CSRF.
- **Correction** : nouveau décorateur `require_staff_user` : jeton obligatoire
  (401 sinon) et compte `is_staff` (403 sinon). Les données invalides
  renvoient maintenant 400 et une culture inexistante 404, au lieu d'une erreur
  500.
- **Lecture** (`GET /agriculture/api/crop-calendar/`) : inchangée, publique.
- **Vérifié par** : 9 tests dans `agriculture/tests.py`.

### 3.2 Faille CSRF sur l'API agriculture

> **En clair** : un site piégé visité par un utilisateur connecté pouvait,
> à son insu, créer des champs ou lancer des évaluations en son nom.

- **Problème** : `require_api_user` acceptait la session du navigateur alors
  que les vues sont exemptées de CSRF (`@csrf_exempt`).
- **Correction** : la session n'est plus acceptée qu'en **lecture** (GET, HEAD,
  OPTIONS). Toute écriture exige l'en-tête `Authorization: Token <clé>`, qu'un
  autre site ne peut pas envoyer à la place de l'utilisateur.
- **Vérifié par** : 2 tests (`SessionCsrfTests`).

### 3.3 Faille XSS dans les bulles des cartes

> **En clair** : un nom piégé dans les données (par exemple un nom de lieu
> importé d'OpenStreetMap) pouvait exécuter du code dans le navigateur des
> visiteurs de la carte.

- **Problème** : les bulles (popups) des deux cartes inséraient les valeurs
  telles quelles en HTML (`${value}`).
- **Correction** : fonction `escapeHtml()` appliquée à toutes les valeurs
  affichées, dans `geoportail/static/js/script.js` et
  `agriculture/static/js/main.js`.

### 3.4 Secrets écrits dans le code

> **En clair** : les mots de passe étaient visibles par tous sur GitHub.

- **Problème** : mots de passe d'application Gmail, `SECRET_KEY` et fichier
  `.env` enregistrés dans le dépôt public.
- **Correction** : `horison/settings.py` lit tous les réglages sensibles dans
  le fichier `.env` (via `python-dotenv`) ou dans les variables
  d'environnement. `.env`, `db.sqlite3`, `*.log`, `__pycache__/`,
  `staticfiles/` et les clés `ee-*.json` sont exclus de Git. `.env.exemple`
  ne contient plus aucun secret.
- ⚠️ **Reste à faire par vous** : révoquer les anciens mots de passe
  ([section 2.1](#21-tout-de-suite-sécurité)).

---

## 4. Installation et configuration

| Problème | Conséquence | Correction |
|---|---|---|
| `requirements.txt` était un export conda **encodé en UTF-16** | `pip install -r requirements.txt` échouait sur tout autre ordinateur | Fichier UTF-8 avec les seules dépendances réellement utilisées (+ Pillow, python-dotenv, openpyxl) |
| Chemin `D:\Horison\.venv` écrit en dur dans `settings.py` | Le projet ne démarrait que sur votre ordinateur ; plantage sous Linux | Recherche de GDAL dans l'environnement Python actif, seulement sous Windows |
| Import `OSMGeoAdmin` dans `geoportail/admin.py` | Supprimé depuis Django 5 : le projet **ne démarrait pas** avec Django 6 | Import inutilisé retiré |
| Doublons `settings.py` (racine) et `horison/requirements.txt` | Confusion, secrets en double | Supprimés (tout pointe vers `horison/settings.py`) |
| `__init__.py` vide à la racine | Les tests automatiques ne pouvaient pas se lancer | Supprimé |

**Nouveaux réglages** du fichier `.env` (tous décrits dans `.env.exemple`) :

| Variable | Rôle |
|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Sécurité Django (⚠️ `DEBUG` vaut `False` par défaut) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Base PostGIS (valeurs par défaut identiques à avant) |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `ALERT_RECIPIENT_EMAIL` | Envoi des alertes |
| `GEE_SERVICE_ACCOUNT_KEY`, `GEE_PROJECT` | Google Earth Engine (facultatifs) |

---

## 5. Géoportail

| Problème | Conséquence | Correction |
|---|---|---|
| Pas de page à la racine | `http://…/` affichait une erreur 404 | `/` redirige vers `/geoportail/` |
| Tuiles OpenStreetMap sans en-tête Referer (politique par défaut de Django) | **Fond de carte remplacé par des cases « Access blocked » (403)** | Option `referrerPolicy` sur les couches de tuiles, dans les deux cartes |
| La liste « Choisir canton » lisait `properties.cant`, l'API renvoie `canton` | Liste toujours vide | Liste remplie ; choisir un canton zoome dessus et le surligne |
| Vues des terrains, coopératives et magasins d'intrants sans route | Données inaccessibles ; thèmes « Sport et loisirs » et « Agriculture » vides | Routes `geojson/terrain/`, `geojson/cooperative/`, `geojson/magasin/` ; couches rattachées aux thèmes |
| Champs inexistants demandés (`code_canton`, `type_terrain`, `nom_locali` des bornes-fontaines) | Code du canton et type de terrain absents des bulles | Noms de champs corrigés (`code_canto`, `terrain`) |
| Réponses GeoJSON sans jeu de caractères | Accents mal affichés par certains clients | `application/json; charset=utf-8` |

---

## 6. Module agriculture

### 6.1 Carte

- **Problème** : `main.js` appelait `/agriculture/geojson/region/` (et les
  équivalents pour les préfectures et les communes), des adresses qui
  **n'existent pas**. La carte était centrée sur Aného, contenait une adresse
  GeoServer locale inutilisée et une couche Earth Engine dont le jeton avait
  expiré.
- **Correction** : bonnes adresses (`/agriculture/api/regions/`, etc.),
  centrage et zoom automatique sur Blitta 2, éléments obsolètes retirés.

### 6.2 API régions, préfectures, communes (erreur 500)

- **Problème** : les tables `region`, `couche_prefecture_utm` et
  `communes_togo_utm` n'existaient que dans votre base.
- **Correction** : `import_blitta2` les crée et les remplit à partir des
  limites officielles (OCHA COD-AB) : **5 régions, 40 préfectures, la commune
  de Blitta 2**. Sur votre base existante, rien ne change tant que vous ne
  lancez pas la commande.

### 6.3 Clé Google Earth Engine

- **Problème** : le chemin du fichier clé était relatif au dossier depuis
  lequel on lançait le serveur ; lancé ailleurs, Earth Engine ne trouvait pas
  la clé.
- **Correction** : chemin configurable (`GEE_SERVICE_ACCOUNT_KEY`), sinon
  chemin absolu vers le fichier habituel à la racine du projet ; projet Cloud
  configurable (`GEE_PROJECT`).

### 6.4 Scripts d'alertes planifiées

- **Problème** : `run_alerts.bat` et `install_alerts_task.ps1` contenaient
  `D:\Horison\horison` et `D:\Horison\hori` : ils ne fonctionnaient que sur
  votre ordinateur.
- **Correction** : les scripts trouvent seuls le dossier du projet.
  L'environnement Python est `.venv`, ou celui indiqué par `HORIEON_VENV`. Le
  journal est écrit dans `alerts.log` à la racine du projet.
- **Vérifié** : `run_alerts.bat` s'exécute jusqu'au bout (code de retour 0).

---

## 7. Données reconstruites à partir de sources ouvertes

> **En clair** : sur un nouvel ordinateur, la carte était vide parce que vos
> données de terrain ne sont pas dans le code. Une commande remplit
> maintenant la carte avec des données publiques.

`python manage.py import_blitta2` :

| Donnée | Source |
|---|---|
| Limites des 4 cantons, de la commune, des régions et préfectures | OCHA COD-AB Togo (Nations unies, janvier 2026) |
| Composition de Blitta 2 (Agbandi, Langabou, Koffiti, Tcharè-Baou) | Décret publié au *Journal officiel* du 8 janvier 2018 |
| Routes, écoles, marchés, santé, eau, terrains | OpenStreetMap (© contributeurs OpenStreetMap, licence ODbL) |
| Compléments sur les formations sanitaires publiques | Inventaire OMS/KEMRI |

Résultat sur Blitta 2 : 207 tronçons de route, 2 lycées, 2 collèges,
4 marchés, 4 formations sanitaires, 2 bornes-fontaines, 9 terrains. Les
informations inconnues sont marquées « Non renseigné » plutôt qu'inventées.

⚠️ La commande **remplace** le contenu des couches : **ne pas la lancer sur la
base qui contient vos relevés de terrain.**

---

## 8. Documentation

| Fichier | Contenu |
|---|---|
| `README.md` | Présentation courte et démarrage rapide |
| `DOCUMENTATION.md` | Documentation complète en 4 parties et 35 sections : comprendre, installer pas à pas, architecture technique, améliorer (limites connues et feuille de route) |
| `docs/Documentation_E-commune.pdf` | La même documentation mise en page (PDF) |
| `docs/index.html` | Version web, publiable avec GitHub Pages (Settings › Pages › `main` / `docs`) |
| `docs/generer_pdf.py` | Regénère le PDF et la version web après modification |
| Ce rapport | Détail des corrections |

---

## 9. Tests et vérifications

**Tests automatisés** (nouveaux) :

```bash
python manage.py test agriculture geoportail
```

12 tests, tous réussis : droits sur le calendrier cultural (lecture publique,
refus sans jeton, refus pour un non-administrateur, ajout, modification,
suppression, données invalides, culture inexistante), protection CSRF,
redirection de la page d'accueil.

**Vérifications manuelles**, effectuées sous Windows 11, Python 3.14,
PostgreSQL 16 + PostGIS 3.5 :

- `python manage.py check` : aucune erreur ; aucune migration manquante ;
- installation complète depuis un clone neuf, en suivant `DOCUMENTATION.md` ;
- chaque adresse du géoportail et de l'API répond (200), y compris les trois
  nouvelles couches et les trois API agriculture ;
- géoportail et carte agriculture contrôlés dans Chrome (fond de carte,
  couches, liste des cantons, zoom) ;
- ajout anonyme au calendrier cultural refusé (401).

**Non testé** (identifiants nécessaires) : les calculs Earth Engine (NDVI,
sécheresse) et l'envoi réel des e-mails.

---

## 10. Ce qui reste à faire

| Sujet | Détail |
|---|---|
| CORS | `CORS_ALLOW_ALL_ORIGINS = True` : à restreindre en production (`CORS_ALLOWED_ORIGINS`) |
| Quartiers | Pas de couche de quartiers : la liste « Choisir un quartier » reste vide |
| Communes | La table des communes ne contient que Blitta 2 (116 autres à importer) |
| Tuiles NDVI | `api/ndvi-tiles/` renvoie des adresses Earth Engine écrites en dur, dont les jetons ont expiré : à générer à la demande |
| `api/champs/` | Pointe vers la même vue que `api/ndvi-timeseries/` (copier-coller probable) : à vérifier côté frontend |
| Alertes | Par e-mail seulement ; WhatsApp prévu dans les modèles mais pas branché |
| Tests | À étendre (vues GeoJSON, moteur de risque, import) et à lancer automatiquement (GitHub Actions) |

La liste complète, avec l'emplacement dans le code, est dans
[DOCUMENTATION.md, section 33](DOCUMENTATION.md#33-limites-connues).

---

## 11. Fichiers modifiés

| Fichier | Changement |
|---|---|
| `horison/settings.py` | Réglages lus dans `.env` ; détection GDAL limitée à Windows |
| `horison/urls.py` | Redirection de `/` vers `/geoportail/` |
| `agriculture/views.py` | Contrôle d'accès du calendrier cultural ; session limitée à la lecture ; `charset` |
| `agriculture/gee_utils.py` | Chemin de la clé et projet Earth Engine configurables |
| `agriculture/static/js/main.js` | Carte agriculture réparée ; échappement HTML |
| `agriculture/tests.py`, `geoportail/tests.py` | Tests automatisés |
| `geoportail/views.py` | Noms de champs corrigés ; `charset` |
| `geoportail/urls.py` | Routes terrains, coopératives, magasins |
| `geoportail/static/js/script.js` | Fond OSM, liste des cantons, nouvelles couches et thèmes, échappement HTML |
| `geoportail/static/js/scripts.js` | Fond OSM (ancienne version, non chargée) |
| `geoportail/admin.py` | Import incompatible avec Django 6 retiré |
| `geoportail/management/commands/import_blitta2.py` | Nouvelle commande d'import des données ouvertes |
| `run_alerts.bat`, `install_alerts_task.ps1` | Chemins indépendants de l'ordinateur |
| `requirements.txt` | Réécrit en UTF-8, dépendances réelles |
| `.env.exemple`, `.gitignore` | Modèle sans secret ; fichiers générés et secrets exclus |
| `README.md`, `DOCUMENTATION.md`, `docs/`, ce rapport | Documentation |
| Supprimés du suivi Git | `.env`, `db.sqlite3`, `alerts.log`, `__pycache__/`, `staticfiles/`, `settings.py` (racine), `horison/requirements.txt`, `__init__.py` (racine) |

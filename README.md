# E-commune Horison — Géoportail de la commune de Blitta 2 (Togo)

**E-commune** est une application web qui affiche sur une carte interactive les
infrastructures d'une commune togolaise (écoles, centres de santé, marchés,
points d'eau, routes…) et qui aide les agriculteurs à **surveiller leurs champs
par satellite** (santé de la végétation, sécheresse, pluie, alertes par e-mail).

La commune couverte est **Blitta 2** (préfecture de Blitta, région Centrale),
formée des cantons d'**Agbandi** (chef-lieu), **Langabou**, **Koffiti** et
**Tcharè-Baou**.

---

## En deux phrases, pour tout le monde

- **Le géoportail** : c'est comme Google Maps, mais pour la mairie. On y voit,
  sur une carte, où se trouvent les écoles, les centres de santé, les marchés,
  les points d'eau et les routes de la commune, et on peut cliquer dessus pour
  avoir des informations.
- **Le module agriculture** : un agriculteur dessine son champ sur la carte ;
  l'application consulte les satellites et la météo, calcule un « score de
  risque » (sécheresse, manque d'eau, excès de pluie…) et envoie une alerte par
  e-mail quand la situation se dégrade.

---

## Démarrage rapide (développeurs)

Prérequis : Python 3.12+, Docker, Git. Détails pas à pas, y compris pour les
débutants : [docs/2-INSTALLER-ET-LANCER.md](docs/2-INSTALLER-ET-LANCER.md).

```bash
git clone https://github.com/1998Jules/projet_horieon.git
cd projet_horieon

# 1. Base de données PostGIS (Docker)
docker run -d --name horieon-postgis -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=Ecommune \
  -p 127.0.0.1:5440:5432 -v horieon-pgdata:/var/lib/postgresql/data postgis/postgis:16-3.5

# 2. Environnement Python
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS : source .venv/bin/activate)
pip install -r requirements.txt
# Windows uniquement : installer aussi la roue GDAL (voir le guide d'installation)

# 3. Configuration
copy .env.exemple .env            # Linux/macOS : cp .env.exemple .env
#   puis éditer .env : SECRET_KEY, DEBUG=True, DB_PASSWORD=1234, DB_HOST=127.0.0.1, DB_PORT=5440

# 4. Base, données, compte admin
python manage.py migrate
python manage.py loaddata cartotheque/fixtures/initial_domaines.json
python manage.py import_blitta2   # couches du géoportail à partir de données ouvertes
python manage.py createsuperuser

# 5. Lancer
python manage.py runserver
```

Puis ouvrir :

| Page | Adresse |
|---|---|
| Géoportail (carte de la commune) | http://127.0.0.1:8000/geoportail/ |
| Module agriculture | http://127.0.0.1:8000/agriculture/ |
| Administration | http://127.0.0.1:8000/admin/ |
| API cartothèque | http://127.0.0.1:8000/api/cartotheque/ |

> La racine `http://127.0.0.1:8000/` affiche une erreur 404 : c'est normal, il
> n'y a pas de page d'accueil. Utilisez les adresses ci-dessus.

---

## Documentation

📄 **Version PDF prête à lire ou à imprimer** :
[docs/Documentation_E-commune.pdf](docs/Documentation_E-commune.pdf)
(regénérée par `python docs/generer_pdf.py`).

| Guide | Pour qui | Contenu |
|---|---|---|
| [1. Comprendre le projet](docs/1-COMPRENDRE.md) | Tout le monde | À quoi sert l'application, comment l'utiliser, lexique (NDVI, SPI, SIG…) |
| [2. Installer et lancer](docs/2-INSTALLER-ET-LANCER.md) | Débutants et développeurs | Installation pas à pas sous Windows et Linux, dépannage |
| [3. Architecture technique](docs/3-ARCHITECTURE.md) | Développeurs | Structure du code, base de données, API, système d'alertes, configuration |
| [4. Améliorer le projet](docs/4-AMELIORER.md) | Contributeurs | Proposer une modification, ajouter une couche, limites connues, feuille de route |

---

## Technologies

Django 6 · Django REST Framework · PostgreSQL + PostGIS · GDAL · Leaflet ·
Turf.js · Google Earth Engine · CHIRPS / CHIRPS-GEFS · Open-Meteo.

## Données

Les données de terrain d'origine (relevés de l'équipe du projet) ne sont pas
dans ce dépôt. La commande `import_blitta2` reconstruit les couches à partir de
sources ouvertes : limites **OCHA COD-AB**, décret de création des communes
(**Journal officiel du 08/01/2018**), infrastructures **OpenStreetMap**
(© contributeurs OpenStreetMap, licence ODbL) et inventaire **OMS/KEMRI** des
formations sanitaires. Voir [docs/3-ARCHITECTURE.md](docs/3-ARCHITECTURE.md#7-données-et-sources).

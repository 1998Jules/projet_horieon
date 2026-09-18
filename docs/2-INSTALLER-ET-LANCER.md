# 2. Installer et lancer le projet

> Ce guide part de zéro. Si vous n'avez jamais installé de logiciel de
> développement, suivez-le dans l'ordre : chaque étape explique **quoi faire**
> et **comment vérifier que ça a marché**. Les développeurs expérimentés
> peuvent sauter directement au [démarrage rapide du README](../README.md#démarrage-rapide-développeurs).

## Sommaire

1. [Ce qu'il faut installer](#1-ce-quil-faut-installer)
2. [Récupérer le code](#2-récupérer-le-code)
3. [Lancer la base de données](#3-lancer-la-base-de-données)
4. [Préparer Python](#4-préparer-python)
5. [Configurer le fichier .env](#5-configurer-le-fichier-env)
6. [Créer la base, charger les données, créer un compte admin](#6-créer-la-base-charger-les-données-créer-un-compte-admin)
7. [Lancer le serveur](#7-lancer-le-serveur)
8. [Activer le module agriculture (Google Earth Engine)](#8-activer-le-module-agriculture-google-earth-engine)
9. [Activer les e-mails d'alerte](#9-activer-les-e-mails-dalerte)
10. [Automatiser les alertes quotidiennes](#10-automatiser-les-alertes-quotidiennes)
11. [Relancer le projet les jours suivants](#11-relancer-le-projet-les-jours-suivants)
12. [Installation sous Linux](#12-installation-sous-linux)
13. [Dépannage](#13-dépannage)

---

## 1. Ce qu'il faut installer

| Logiciel | À quoi il sert | Où le trouver |
|---|---|---|
| **Python 3.12 ou plus récent** | Le langage dans lequel l'application est écrite | https://www.python.org/downloads/ |
| **Git** | Télécharger le code et suivre les modifications | https://git-scm.com/downloads |
| **Docker Desktop** | Faire tourner la base de données sans l'installer « à la main » | https://www.docker.com/products/docker-desktop/ |
| Un éditeur de code (conseillé) | Modifier les fichiers | https://code.visualstudio.com/ |

> ⚠️ **Python** : pendant l'installation sous Windows, **cochez la case
> « Add python.exe to PATH »** en bas de la première fenêtre. Django 6 exige
> **Python 3.12 minimum** : les versions 3.10 et 3.11 ne fonctionnent pas.

### Ouvrir un terminal

Toutes les commandes de ce guide se tapent dans un **terminal** :

- **Windows** : touche Windows, tapez `PowerShell`, puis Entrée.
- **Linux / macOS** : application « Terminal ».

### Vérifier les installations

Tapez ces commandes une par une. Chacune doit afficher un numéro de version :

```powershell
python --version      # attendu : Python 3.12.x, 3.13.x ou 3.14.x
git --version
docker --version
```

Si une commande répond « n'est pas reconnu », le logiciel n'est pas installé
ou n'est pas dans le PATH : réinstallez-le, puis **fermez et rouvrez** le
terminal.

> **Plusieurs versions de Python ?** Sous Windows, `py -0` les liste. Utilisez
> alors `py -3.14` (ou la version voulue) à la place de `python` à l'étape 4.

---

## 2. Récupérer le code

Choisissez un dossier de travail (par exemple `Documents\Projets`), puis :

```powershell
cd $HOME\Documents
git clone https://github.com/1998Jules/projet_horieon.git
cd projet_horieon
```

✅ **Vérification** : `dir` (Windows) ou `ls` (Linux) affiche notamment
`manage.py`, `requirements.txt`, et les dossiers `geoportail`, `agriculture`…

> **Toutes les commandes suivantes se tapent depuis ce dossier `projet_horieon`.**

---

## 3. Lancer la base de données

L'application stocke ses données dans **PostgreSQL** avec l'extension
géographique **PostGIS**. Le plus simple est de la lancer avec Docker.

1. Démarrez **Docker Desktop** (l'icône de la baleine doit être stable, pas en
   train de clignoter).
2. Tapez (sur **une seule ligne**) :

```powershell
docker run -d --name horieon-postgis -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=Ecommune -p 127.0.0.1:5440:5432 -v horieon-pgdata:/var/lib/postgresql/data --restart unless-stopped postgis/postgis:16-3.5
```

Ce que fait cette commande :

| Élément | Signification |
|---|---|
| `--name horieon-postgis` | Nom du conteneur, pour le retrouver |
| `POSTGRES_PASSWORD=1234` | Mot de passe de l'utilisateur `postgres` (**changez-le** si l'ordinateur est partagé ou exposé sur un réseau) |
| `POSTGRES_DB=Ecommune` | Crée directement la base `Ecommune` |
| `-p 127.0.0.1:5440:5432` | La base est accessible sur le **port 5440** de votre ordinateur, uniquement en local. On évite le port 5432, souvent déjà pris par un PostgreSQL installé |
| `-v horieon-pgdata:…` | Les données sont conservées même si le conteneur est supprimé |
| `--restart unless-stopped` | La base redémarre toute seule avec Docker |

✅ **Vérification** :

```powershell
docker exec horieon-postgis psql -U postgres -d Ecommune -c "select postgis_version();"
```

doit afficher une ligne commençant par `3.5`.

<details>
<summary><strong>Alternative sans Docker</strong> (PostgreSQL installé sur Windows)</summary>

1. Installez PostgreSQL depuis https://www.postgresql.org/download/windows/.
2. Lancez **Application Stack Builder** (menu Démarrer › PostgreSQL), puis
   choisissez *Spatial Extensions › PostGIS*.
3. Créez la base : `psql -U postgres -c "CREATE DATABASE \"Ecommune\";"`.
4. Dans `.env` (étape 5), mettez `DB_PORT=5432` et votre mot de passe
   `postgres`.

</details>

---

## 4. Préparer Python

### 4.1 Créer un environnement virtuel

Un **environnement virtuel** (`.venv`) est un dossier qui contient les
bibliothèques du projet, sans rien mélanger avec le reste de l'ordinateur.

```powershell
python -m venv .venv
.venv\Scripts\activate
```

✅ **Vérification** : le début de la ligne du terminal affiche `(.venv)`.

> **PowerShell refuse d'activer** (« l'exécution de scripts est désactivée ») ?
> Tapez une fois `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, répondez
> `O`, puis relancez `.venv\Scripts\activate`.

### 4.2 Installer les bibliothèques

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Cela prend quelques minutes (Django, pandas, rasterio, Earth Engine…).

### 4.3 Installer GDAL (Windows uniquement)

Django a besoin de **GDAL** et **GEOS**, deux bibliothèques de calcul
géographique. Sous Windows, on les installe avec une « roue » précompilée :

1. Allez sur https://github.com/cgohlke/geospatial-wheels/releases (dernière
   version).
2. Dans la liste des fichiers (*Assets*), repérez celui qui commence par
   `gdal-` et qui correspond à **votre version de Python** :
   `cp312` = Python 3.12, `cp313` = 3.13, `cp314` = 3.14, et se termine par
   `win_amd64.whl`.
   Exemple : `gdal-3.13.3-cp314-cp314-win_amd64.whl`.
3. Installez-le directement depuis son lien :

```powershell
pip install https://github.com/cgohlke/geospatial-wheels/releases/download/v2026.8.20/gdal-3.13.3-cp314-cp314-win_amd64.whl
```

(adaptez le lien au fichier choisi).

✅ **Vérification** :

```powershell
python -c "from osgeo import gdal; print(gdal.__version__)"
```

Le fichier `horison/settings.py` trouve ensuite tout seul `gdal.dll`,
`geos_c.dll` et les données PROJ dans le dossier `.venv`.

---

## 5. Configurer le fichier .env

Le fichier **`.env`** contient les réglages propres à votre ordinateur et
**les secrets** (mots de passe). Il n'est **jamais** envoyé sur GitHub.

```powershell
copy .env.exemple .env        # Linux/macOS : cp .env.exemple .env
```

Générez une clé secrète :

```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Puis ouvrez `.env` avec un éditeur (`notepad .env`) et remplissez :

```ini
SECRET_KEY=la-cle-generee-ci-dessus
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=Ecommune
DB_USER=postgres
DB_PASSWORD=1234
DB_HOST=127.0.0.1
DB_PORT=5440
```

| Variable | Rôle | Valeur par défaut si absente |
|---|---|---|
| `SECRET_KEY` | Clé de chiffrement des sessions. **Unique et secrète en production.** | clé de développement non sûre |
| `DEBUG` | `True` affiche les erreurs détaillées et sert les fichiers statiques. **`False` en production.** | `False` |
| `ALLOWED_HOSTS` | Noms de domaine autorisés, séparés par des virgules | `localhost,127.0.0.1` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | Connexion à PostgreSQL | `Ecommune` / `postgres` / `1234` / `localhost` / `5432` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` | Serveur d'envoi des e-mails | `smtp.gmail.com`, `587`, `True` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Compte et mot de passe d'envoi (voir [étape 9](#9-activer-les-e-mails-dalerte)) | vide (pas d'envoi) |
| `DEFAULT_FROM_EMAIL` | Expéditeur affiché | = `EMAIL_HOST_USER` |
| `ALERT_RECIPIENT_EMAIL` | Adresse de contrôle qui reçoit les alertes | vide |

> Une variable d'environnement définie dans le terminal **est prioritaire** sur
> la valeur du fichier `.env`.

---

## 6. Créer la base, charger les données, créer un compte admin

```powershell
python manage.py migrate
```
Crée les tables de l'application. ✅ Se termine par une série de `OK`.

```powershell
python manage.py loaddata cartotheque/fixtures/initial_domaines.json
```
Charge les 14 domaines de la cartothèque. ✅ `Installed 14 object(s)`.

```powershell
python manage.py import_blitta2
```
Télécharge les données ouvertes (limites officielles, OpenStreetMap,
inventaire OMS) et **remplit les couches du géoportail**. Il faut une connexion
internet ; comptez une à deux minutes. ✅ Se termine par `Import terminé` et le
nombre d'objets par table.

> ⚠️ Cette commande **efface et remplace** le contenu des couches du
> géoportail. Ne la lancez pas sur une base qui contient les relevés de
> terrain d'origine.

```powershell
python manage.py createsuperuser
```
Crée votre compte administrateur : choisissez un identifiant, une adresse
e-mail et un mot de passe (rien ne s'affiche pendant la saisie du mot de
passe, c'est normal).

---

## 7. Lancer le serveur

```powershell
python manage.py runserver
```

✅ Le terminal affiche `Starting development server at http://127.0.0.1:8000/`.
**Laissez ce terminal ouvert** tant que vous utilisez l'application
(`Ctrl + C` pour l'arrêter).

Ouvrez votre navigateur :

| Page | Adresse |
|---|---|
| Géoportail | http://127.0.0.1:8000/geoportail/ |
| Module agriculture | http://127.0.0.1:8000/agriculture/ |
| Administration | http://127.0.0.1:8000/admin/ |
| API cartothèque | http://127.0.0.1:8000/api/cartotheque/ |

> **Le port 8000 est déjà utilisé ?** Lancez sur un autre port :
> `python manage.py runserver 127.0.0.1:8002`, puis utilisez
> `http://127.0.0.1:8002/...`.

---

## 8. Activer le module agriculture (Google Earth Engine)

Les calculs satellites (NDVI, sécheresse…) passent par **Google Earth
Engine**, gratuit pour un usage non commercial (recherche, ONG, collectivités).

1. Avec un compte Google, créez un projet sur https://console.cloud.google.com/
   (menu *Sélectionner un projet › Nouveau projet*).
2. Enregistrez ce projet pour Earth Engine sur
   https://code.earthengine.google.com/register : choisissez *usage non
   commercial* puis le projet créé.
3. Dans la console Cloud : *API et services › Bibliothèque*, puis activez
   **Google Earth Engine API**.
4. *IAM et administration › Comptes de service › Créer un compte de service*.
   Donnez-lui le rôle **Earth Engine Resource Writer** (ou *Viewer* pour la
   lecture seule) et **Service Usage Consumer**.
5. Ouvrez ce compte de service, onglet *Clés*, puis *Ajouter une clé › JSON*.
   Un fichier `.json` est téléchargé.
6. **Copiez ce fichier à la racine du projet** (à côté de `manage.py`) sous le
   nom attendu par le code :

   ```
   ee-koutoumbogajules-c99000ca569e.json
   ```

   Ce nom est codé en dur dans `agriculture/gee_utils.py` (constante
   `SERVICE_ACCOUNT_KEY_FILE`). Le fichier est déjà exclu de Git par le
   `.gitignore`. Le serveur doit être lancé **depuis la racine du projet**,
   car le chemin est relatif.

> ⚠️ Ce fichier donne accès à votre compte Google Cloud : **ne le partagez
> jamais** et ne le commitez pas.

---

## 9. Activer les e-mails d'alerte

Exemple avec Gmail :

1. Activez la **validation en deux étapes** sur le compte Google d'envoi.
2. Créez un **mot de passe d'application** sur
   https://myaccount.google.com/apppasswords (nom : « E-commune »). Google
   affiche 16 caractères.
3. Complétez `.env` :

```ini
EMAIL_HOST_USER=adresse.envoi@gmail.com
EMAIL_HOST_PASSWORD=les16caracteres
DEFAULT_FROM_EMAIL=adresse.envoi@gmail.com
ALERT_RECIPIENT_EMAIL=adresse.de.controle@exemple.com
```

4. Redémarrez le serveur.

✅ **Test** : `python manage.py evaluate_field_alerts --dry-run` calcule les
alertes sans rien enregistrer ni envoyer.

> Pour tester sans vrai envoi, ajoutez
> `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` dans `.env` :
> les e-mails s'affichent alors dans le terminal.

---

## 10. Automatiser les alertes quotidiennes

La commande qui fait tout (collecte des indicateurs, score, alertes, e-mails) :

```powershell
python manage.py evaluate_field_alerts                 # tous les champs
python manage.py evaluate_field_alerts --champ-id 5    # un seul champ
python manage.py evaluate_field_alerts --dry-run       # simulation
python manage.py evaluate_field_alerts --no-collect    # sans réinterroger les satellites
python manage.py evaluate_field_alerts --no-email      # sans envoyer d'e-mail
```

**Windows** : `install_alerts_task.ps1` crée une tâche planifiée qui lance
`run_alerts.bat` chaque jour à 6 h. ⚠️ Ces deux fichiers contiennent des
chemins propres à l'ordinateur de l'auteur (`D:\Horison\...`) : **adaptez
d'abord** `$BatchPath` dans `install_alerts_task.ps1`, ainsi que les lignes
`cd /d`, `call ...\activate.bat` et le chemin du journal dans `run_alerts.bat`.
Lancez ensuite PowerShell **en administrateur** :

```powershell
.\install_alerts_task.ps1                 # tous les jours à 06:00
.\install_alerts_task.ps1 -Time "08:30"   # autre heure
.\install_alerts_task.ps1 -Interval 6     # toutes les 6 heures
.\install_alerts_task.ps1 -Test           # lancer immédiatement
.\install_alerts_task.ps1 -Uninstall      # supprimer la tâche
```

**Linux** : ajoutez une ligne dans `crontab -e` :

```cron
0 6 * * * cd /chemin/vers/projet_horieon && .venv/bin/python manage.py evaluate_field_alerts >> alerts.log 2>&1
```

---

## 11. Relancer le projet les jours suivants

```powershell
cd $HOME\Documents\projet_horieon
.venv\Scripts\activate
python manage.py runserver
```

Docker Desktop doit être démarré (la base redémarre toute seule grâce à
`--restart unless-stopped`). Si ce n'est pas le cas :
`docker start horieon-postgis`.

Après avoir récupéré des modifications (`git pull`), pensez à :

```powershell
pip install -r requirements.txt
python manage.py migrate
```

---

## 12. Installation sous Linux

Testé sur Debian/Ubuntu :

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev gdal-bin libgdal-dev git docker.io
sudo usermod -aG docker $USER      # puis se déconnecter / reconnecter

git clone https://github.com/1998Jules/projet_horieon.git && cd projet_horieon
docker run -d --name horieon-postgis -e POSTGRES_PASSWORD=1234 -e POSTGRES_DB=Ecommune \
  -p 127.0.0.1:5440:5432 -v horieon-pgdata:/var/lib/postgresql/data --restart unless-stopped postgis/postgis:16-3.5

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.exemple .env && nano .env
python manage.py migrate
python manage.py loaddata cartotheque/fixtures/initial_domaines.json
python manage.py import_blitta2
python manage.py createsuperuser
python manage.py runserver
```

Sous Linux, **pas besoin de la roue GDAL** : Django utilise la bibliothèque
système installée par `apt`.

### Mise en production (aperçu)

Le script `build.sh` (installation, `collectstatic`, `migrate`) est prévu pour
un hébergeur comme Render. En production :

- `DEBUG=False`, une vraie `SECRET_KEY`, `ALLOWED_HOSTS=mon-domaine.tg` ;
- servir l'application avec **gunicorn** :
  `gunicorn horison.wsgi:application --bind 0.0.0.0:8000` ;
- servir `staticfiles/` et `media/` par le serveur web (Nginx…) ;
- une base PostGIS gérée, avec des sauvegardes (`pg_dump`).

---

## 13. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Page not found (404)` sur `http://127.0.0.1:8000/` | Pas de page d'accueil | Aller sur `/geoportail/` |
| `Error: That port is already in use` | Un autre programme utilise le port 8000 | `python manage.py runserver 127.0.0.1:8002` |
| `connection refused` / `could not connect to server` | La base ne tourne pas | Démarrer Docker Desktop, puis `docker start horieon-postgis` |
| `password authentication failed for user` | Mauvais mot de passe ou mauvais port dans `.env` | Vérifier `DB_PASSWORD` et `DB_PORT` (5440 pour le conteneur) |
| `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9` au démarrage | Échec de connexion à un PostgreSQL configuré en français : le message d'erreur accentué fait planter `psycopg2` | C'est en réalité l'erreur ci-dessus : vérifier `DB_*` dans `.env` |
| `Could not find the GDAL library` / `OSError: [WinError 126]` | Roue GDAL absente ou pour une autre version de Python | Refaire l'[étape 4.3](#43-installer-gdal-windows-uniquement) avec le bon `cpXXX` |
| `Django requires Python 3.12 or later` | Python trop ancien | Installer Python 3.12+ et recréer le `.venv` |
| `Invalid requirement: 'D\x00j\x00a…'` | Ancien `requirements.txt` encodé en UTF-16 | Récupérer la version actuelle du dépôt (`git pull`) |
| `relation "bl2" does not exist` (erreur 500 sur les couches) | Tables du géoportail absentes | `python manage.py import_blitta2` |
| Erreur 500 sur `/agriculture/api/regions/`, `/prefectures/` ou `/communes/` | Tables `region`, `couche_prefecture_utm`, `communes_togo_utm` absentes (importées à la main par l'auteur) | Voir [4-AMELIORER.md](4-AMELIORER.md#3-limites-connues) |
| Fond de carte remplacé par des cases « Access blocked » | Ancienne version des fichiers JavaScript (tuiles OSM sans Referer) | Récupérer la version actuelle et vider le cache du navigateur (`Ctrl + Maj + R`) |
| La carte est vide mais sans erreur | Couches non activées | Icône orange en haut à droite, puis choisir un thème |
| `ERREUR: Le fichier clé 'ee-…json' est introuvable` | Clé Earth Engine absente | [Étape 8](#8-activer-le-module-agriculture-google-earth-engine) ; lancer le serveur depuis la racine du projet |
| `SMTPAuthenticationError` | Mot de passe Gmail normal au lieu d'un mot de passe d'application | [Étape 9](#9-activer-les-e-mails-dalerte) |
| `.venv\Scripts\activate` refusé | Politique d'exécution PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

@echo off
REM ============================================================
REM  Surveillance agricole préventive — Tâche planifiée Windows
REM ============================================================
REM  Ce batch est appelé automatiquement par le Planificateur de
REM  tâches Windows. Il lance la commande Django qui :
REM    1. Collecte les indicateurs (Earth Engine, CHIRPS-GEFS)
REM    2. Calcule le score de risque 0-100
REM    3. Crée des alertes si changement de niveau
REM    4. Envoie les emails en attente
REM
REM  Les logs sont écrits dans alerts.log (rotation manuelle).
REM ============================================================

REM Se place dans le dossier du projet (celui qui contient ce fichier),
REM quel que soit l'endroit où le projet est installé.
cd /d "%~dp0"

REM ============================================================
REM  IMPORTANT : Forcer l'encodage UTF-8 pour Python.
REM
REM  Sans ça, quand le batch redirige la sortie vers alerts.log,
REM  Python utilise l'encodage Windows par défaut (cp1252) qui ne
REM  supporte pas les caractères Unicode (✓, ⚠, ❌, 🟢, 🟡, 🟠, 🔴)
REM  utilisés dans settings.py et dans les commandes Django.
REM  → UnicodeEncodeError qui fait planter le batch.
REM ============================================================
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=0

REM Active le venv Python : .venv du projet par défaut, ou le dossier indiqué
REM dans la variable d'environnement HORIEON_VENV (ex. D:\Horison\hori).
if "%HORIEON_VENV%"=="" set "HORIEON_VENV=%~dp0.venv"
if not exist "%HORIEON_VENV%\Scripts\activate.bat" (
    echo [ERREUR] venv introuvable : %HORIEON_VENV% >> "%~dp0alerts.log"
    exit /b 1
)
call "%HORIEON_VENV%\Scripts\activate.bat"

REM Lance la commande Django
python manage.py evaluate_field_alerts >> "%~dp0alerts.log" 2>&1

REM Code de retour pour le Planificateur de tâches
exit /b %ERRORLEVEL%

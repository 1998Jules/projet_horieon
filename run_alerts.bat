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

cd /d D:\Horison\horison

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

REM Active le venv Python (adapte le chemin si nécessaire)
call D:\Horison\hori\Scripts\activate.bat

REM Lance la commande Django
python manage.py evaluate_field_alerts >> D:\Horison\horison\alerts.log 2>&1

REM Code de retour pour le Planificateur de tâches
exit /b %ERRORLEVEL%

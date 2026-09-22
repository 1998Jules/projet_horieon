@echo off
REM ============================================================
REM  run_alerts.bat — Surveillance agricole preventive (Windows)
REM ============================================================
REM  Version amelioree :
REM  - Chemins configurables via variables d'environnement ou .env
REM  - Verification de la connexion DB avant execution
REM  - Rotation automatique des logs (>30 jours)
REM  - Email admin si plantage
REM  - Encodage UTF-8 force (pour les emojis 🟢🟡🟠🔴)
REM
REM  Usage :
REM    run_alerts.bat                       ^> Toutes les etapes
REM    run_alerts.bat --champ-id 5           ^> Un seul champ
REM    run_alerts.bat --dry-run             ^> Simulation
REM    run_alerts.bat --no-collect          ^> Skip collecte
REM    run_alerts.bat --no-email            ^> Sans emails
REM    run_alerts.bat --limit-email 50      ^> Max 50 emails
REM
REM  Configuration (par ordre de priorite) :
REM    1. Variables d'environnement PROJECT_DIR, VENV_DIR, ADMIN_EMAIL
REM    2. Fichier .env a la racine du projet
REM    3. Valeurs par defaut ci-dessous
REM ============================================================

setlocal enabledelayedexpansion

REM ============================================================
REM  CONFIGURATION PAR DEFAUT
REM  (modifiables via variables d'environnement ou .env)
REM ============================================================
if "%PROJECT_DIR%"==""  set "PROJECT_DIR=D:\Horison\horison"
if "%VENV_DIR%"==""    set "VENV_DIR=D:\Horison\hori"
if "%LOG_DIR%"==""     set "LOG_DIR=%PROJECT_DIR%\logs"
if "%ADMIN_EMAIL%"=="" set "ADMIN_EMAIL=koutoumbogajules@gmail.com"

REM Date du jour pour le nom du fichier de log (YYYYMMDD)
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value 2^>nul') do set "ldt=%%a"
if defined ldt (
    set "DATE_STAMP=!ldt:~0,8!"
) else (
    set "DATE_STAMP=%date:~6,4%%date:~3,2%%date:~0,2%"
)
set "LOG_FILE=%LOG_DIR%\alerts_!DATE_STAMP!.log"

REM ============================================================
REM  ENCODAGE UTF-8 OBLIGATOIRE pour Python sur Windows
REM  (sinon les emojis font planter Python avec UnicodeEncodeError)
REM ============================================================
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=0

REM ============================================================
REM  CREER LE REPERTOIRE DE LOGS
REM ============================================================
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

REM ============================================================
REM  FONCTIONS DE LOG
REM ============================================================
set "TIMESTAMP=%date% %time%"
set "TIMESTAMP=%TIMESTAMP: =%"

echo [%TIMESTAMP%] ============================================ >> "%LOG_FILE%"
echo [%TIMESTAMP%] Demarrage surveillance agricole preventive >> "%LOG_FILE%"
echo [%TIMESTAMP%] Projet : %PROJECT_DIR% >> "%LOG_FILE%"
echo [%TIMESTAMP%] Venv   : %VENV_DIR% >> "%LOG_FILE%"
echo [%TIMESTAMP%] ============================================ >> "%LOG_FILE%"

REM ============================================================
REM  ETAPE 0 : VERIFICATIONS PRE-EXECUTION
REM ============================================================
if not exist "%PROJECT_DIR%\manage.py" (
    echo [%TIMESTAMP%] [ERROR] manage.py introuvable dans %PROJECT_DIR% >> "%LOG_FILE%"
    echo ERREUR : manage.py introuvable dans %PROJECT_DIR%
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [%TIMESTAMP%] [ERROR] venv introuvable : %VENV_DIR% >> "%LOG_FILE%"
    echo ERREUR : venv introuvable : %VENV_DIR%
    exit /b 1
)

REM ============================================================
REM  ETAPE 1 : ACTIVATION DU VIRTUALENV
REM ============================================================
echo [%TIMESTAMP%] Activation du virtualenv... >> "%LOG_FILE%"
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [%TIMESTAMP%] [ERROR] Echec activation venv >> "%LOG_FILE%"
    exit /b 1
)

REM ============================================================
REM  ETAPE 2 : VERIFICATION CONNEXION DB
REM ============================================================
echo [%TIMESTAMP%] Verification connexion DB... >> "%LOG_FILE%"
cd /d "%PROJECT_DIR%"
python manage.py check --database default >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%TIMESTAMP%] [ERROR] Echec check Django - BDD inaccessible >> "%LOG_FILE%"
    exit /b 1
)
echo [%TIMESTAMP%] Connexion DB OK >> "%LOG_FILE%"

REM ============================================================
REM  ETAPE 3 : EXECUTION DE LA COMMANDE DJANGO
REM ============================================================
echo [%TIMESTAMP%] Lancement : evaluate_field_alerts %* >> "%LOG_FILE%"
echo [%TIMESTAMP%] Debut execution : voir sortie ci-dessous >> "%LOG_FILE%"

python manage.py evaluate_field_alerts %* >> "%LOG_FILE%" 2>&1
set "CMD_EXIT=%ERRORLEVEL%"

if %CMD_EXIT% neq 0 (
    echo [%TIMESTAMP%] [ERROR] Echec evaluate_field_alerts ^(code %CMD_EXIT%^) >> "%LOG_FILE%"
    REM Envoyer email admin
    python manage.py shell -c "from django.core.mail import send_mail; send_mail(subject='[ALERTE PRECOSSE] Echec script run_alerts.bat', message='Echec code %CMD_EXIT%. Voir log : %LOG_FILE%', from_email=None, recipient_list=['%ADMIN_EMAIL%'], fail_silently=True)" 2>nul
    exit /b %CMD_EXIT%
)

echo [%TIMESTAMP%] Script termine avec succes >> "%LOG_FILE%"
echo [%TIMESTAMP%] ============================================ >> "%LOG_FILE%"

REM ============================================================
REM  ETAPE 4 : ROTATION DES LOGS (>30 jours)
REM ============================================================
forfiles /p "%LOG_DIR%" /m "alerts_*.log" /d -30 /c "cmd /c del @file" 2>nul

exit /b 0

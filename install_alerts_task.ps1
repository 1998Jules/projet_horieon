# ============================================================
#  install_alerts_task.ps1 — Task Scheduler Windows (amélioré)
# ============================================================
#  Crée une tâche planifiée qui exécute run_alerts.bat
#
#  Améliorations vs version originale :
#  - Chemins configurables via paramètres -ProjectDir / -VenvDir
#  - Vérification que run_alerts.bat existe
#  - Validation du fichier .env si présent
#
#  Usage :
#     .\install_alerts_task.ps1                            # quotidien à 06:00
#     .\install_alerts_task.ps1 -Time "08:30"             # quotidien à 08:30
#     .\install_alerts_task.ps1 -Interval 6               # toutes les 6 heures
#     .\install_alerts_task.ps1 -Uninstall                # supprimer la tâche
#     .\install_alerts_task.ps1 -Test                     # tester immédiatement
#     .\install_alerts_task.ps1 -ProjectDir "D:\Horison\horison" -BatchPath "D:\Horison\horison\run_alerts.bat"
#
#  Doit être exécuté en tant qu'administrateur.
# ============================================================

param(
    [string]$Time = "06:00",
    [int]$Interval = 0,
    [string]$ProjectDir = "D:\Horison\horison",
    [string]$BatchPath = "D:\Horison\horison\run_alerts.bat",
    [switch]$Uninstall = $false,
    [switch]$Test = $false
)

$ErrorActionPreference = "Stop"

# --- Configuration ---
$TaskName = "AlertesAgricoles_Auto"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Installation de la tache planifiee - Alertes Agricoles   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Nom de la tache : $TaskName"
Write-Host "Projet          : $ProjectDir"
Write-Host "Batch execute   : $BatchPath"

# --- Mode désinstallation ---
if ($Uninstall) {
    Write-Host "`n[1/2] Suppression de la tache existante..." -ForegroundColor Yellow
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "    [OK] Tache '$TaskName' supprimee." -ForegroundColor Green
    } catch {
        Write-Host "    [INFO] La tache n'existait pas ou deja supprimee." -ForegroundColor Gray
    }
    Write-Host "[2/2] Desinstallation terminee." -ForegroundColor Green
    exit 0
}

# --- Vérifications préalables ---
Write-Host "`n[1/4] Verification des prerequis..." -ForegroundColor Yellow

if (-not (Test-Path $BatchPath)) {
    Write-Host "    [ERREUR] Le fichier batch est introuvable : $BatchPath" -ForegroundColor Red
    Write-Host "    Creez d'abord run_alerts.bat puis relancez ce script." -ForegroundColor Red
    exit 1
}
Write-Host "    [OK] Batch trouve." -ForegroundColor Green

# Vérifier qu'on est admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "    [ERREUR] Ce script doit etre execute en tant qu'administrateur." -ForegroundColor Red
    Write-Host "    Clic droit sur PowerShell -> 'Executer en tant qu'administrateur'." -ForegroundColor Red
    exit 1
}
Write-Host "    [OK] Droits administrateur." -ForegroundColor Green

# Vérifier manage.py
$managePy = Join-Path $ProjectDir "manage.py"
if (-not (Test-Path $managePy)) {
    Write-Host "    [ERREUR] manage.py introuvable dans $ProjectDir" -ForegroundColor Red
    exit 1
}
Write-Host "    [OK] manage.py trouve." -ForegroundColor Green

# Vérifier .env si présent
$envFile = Join-Path $ProjectDir ".env"
if (Test-Path $envFile) {
    Write-Host "    [OK] Fichier .env detecte." -ForegroundColor Green
} else {
    Write-Host "    [INFO] Pas de fichier .env (valeurs par defaut utilisees)." -ForegroundColor Gray
}

# Supprimer une tâche existante
Write-Host "`n[2/4] Suppression de l'ancienne tache..." -ForegroundColor Yellow
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
    Write-Host "    [OK] Ancienne tache supprimee." -ForegroundColor Green
} catch {
    Write-Host "    [INFO] Aucune ancienne tache a supprimer." -ForegroundColor Gray
}

# --- Mode test ---
if ($Test) {
    Write-Host "`n[TEST] Execution immediate du batch..." -ForegroundColor Magenta
    & $BatchPath
    Write-Host "`n[OK] Test termine. Verifiez les logs dans $ProjectDir\logs\" -ForegroundColor Green
    exit 0
}

# --- Création de la tâche ---
Write-Host "`n[3/4] Creation de la tache planifiee..." -ForegroundColor Yellow

$Action = New-ScheduledTaskAction -Execute $BatchPath -WorkingDirectory $ProjectDir

if ($Interval -gt 0) {
    $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours $Interval)
    Write-Host "    Mode intervalle : toutes les $Interval heure(s)" -ForegroundColor Gray
} else {
    $triggerTime = [DateTime]::Parse($Time)
    $Trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
    Write-Host "    Mode quotidien : tous les jours a $Time" -ForegroundColor Gray
}

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Surveillance agricole preventive - collecte + scoring + alertes + emails" `
        -Force | Out-Null
    Write-Host "    [OK] Tache creee avec succes." -ForegroundColor Green
} catch {
    Write-Host "    [ERREUR] Echec de la creation : $_" -ForegroundColor Red
    exit 1
}

# --- Récap ---
Write-Host "`n[4/4] Recapitulatif..." -ForegroundColor Yellow
$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = $task | Get-ScheduledTaskInfo

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Tache planifiee creee avec succes !                     " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Nom           : $($task.TaskName)"
Write-Host "Etat          : $($task.State)"
if ($Interval -gt 0) {
    Write-Host "Intervalle    : toutes les $Interval heure(s)"
} else {
    Write-Host "Frequence     : Quotidienne a $Time"
}
Write-Host "Prochaine exec : $($taskInfo.NextRunTime)"
Write-Host "Derniere exec : $($taskInfo.LastRunTime)"
Write-Host "Log           : $ProjectDir\logs\alerts_YYYYMMDD.log"
Write-Host ""
Write-Host "Commandes utiles :" -ForegroundColor Cyan
Write-Host "  - Tester maintenant    : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  - Voir le statut      : Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host "  - Supprimer la tache  : .\install_alerts_task.ps1 -Uninstall"
Write-Host "============================================================" -ForegroundColor Green

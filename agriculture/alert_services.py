"""Moteur de détection d'alertes agricoles — version multi-indicateurs.

WORKFLOW
--------
1. Le collecteur (indicator_collector.py) a peuplé FieldIndicatorSnapshot
   avec tous les indicateurs (NDVI, EVI, NDWI, MSAVI, SPI_30, SPI_90,
   SPI_FORECAST, RAINFALL_24H, RAINFALL_72H, VCI, TCI, VHI, NCWSI).
2. Le moteur de scoring (risk_engine.py) calcule un score 0-100 et un niveau
   de risque (🟢🟡🟠🔴) en croisant les indicateurs.
3. CE MODULE décide s'il faut créer une alerte :
   - on compare le niveau actuel au niveau précédent (RiskAssessment)
   - on ne crée une alerte que si le niveau change (aggravation ou amélioration)
   - on génère un message contextuel selon le type d'alerte détecté
   - on crée un FarmerAlert + un AlertDelivery (EMAIL) si l'utilisateur a activé
   - on persiste le RiskAssessment pour tracer l'évolution

PROTECTION ANTI-DOUBLON
-----------------------
Un email n'est envoyé que lorsque le niveau de risque CHANGE :
- 1ère détection (pas de RiskAssessment précédent) → email
- aggravation (🟡 → 🟠, 🟠 → 🔴) → email
- amélioration (🟠 → 🟡, 🟡 → 🟢) → email de résolution
- niveau identique → PAS d'email (le cooldown inhérent au niveau change)
- disparition (🟠 → 🟢) → email de fin d'alerte
- réapparition (🟢 → 🟡 après disparition) → email
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import AlertDelivery, Champ, FarmerAlert, RiskAssessment
from .risk_engine import RiskResult, assess_champ_risk, persist_risk_assessment

logger = logging.getLogger(__name__)


# ============================================================
# TEMPLATES DE MESSAGES PAR TYPE D'ALERTE
# ============================================================
ALERT_TEMPLATES: dict[str, dict[str, str]] = {
    "STRESS_VEGETATIF": {
        "title": "🌿 Stress végétatif détecté — {champ_nom}",
        "message": (
            "Les indicateurs de vigueur de la végétation montrent une dégradation "
            "significative sur le champ {champ_nom} (culture : {culture}).\n\n"
            "Indicateurs contributeurs :\n{indicators_summary}\n\n"
            "Score de risque : {score}/100 — Niveau : {level_emoji} {level_label}"
        ),
        "recommendation": (
            "1. Inspecter le champ pour identifier la cause (stress hydrique, "
            "ravageurs, maladie, carence nutritionnelle).\n"
            "2. Vérifier l'humidité du sol à différentes profondeurs.\n"
            "3. Si stress hydrique confirmé, planifier une irrigation.\n"
            "4. En cas de ravageurs/maladie, consulter un technicien agricole."
        ),
    },
    "STRESS_HYDRIQUE": {
        "title": "💧 Risque de stress hydrique — {champ_nom}",
        "message": (
            "Les indicateurs hydriques et végétatifs montrent une dégradation "
            "des conditions d'eau sur le champ {champ_nom} (culture : {culture}).\n\n"
            "Indicateurs contributeurs :\n{indicators_summary}\n\n"
            "Score de risque : {score}/100 — Niveau : {level_emoji} {level_label}"
        ),
        "recommendation": (
            "1. Surveiller régulièrement l'état de la culture.\n"
            "2. Envisager les mesures de gestion de l'eau disponibles (irrigation, "
            "paillage, conservation de l'humidité du sol).\n"
            "3. Vérifier les prévisions météo pour adapter l'arrosage.\n"
            "4. Éviter les travaux du sol qui augmenteraient l'évaporation."
        ),
    },
    "SECHERESSE": {
        "title": "🏜️ Alerte sécheresse — {champ_nom}",
        "message": (
            "Une situation de sécheresse est détectée sur le champ {champ_nom} "
            "(culture : {culture}).\n\n"
            "Indicateurs pluviométriques :\n{indicators_summary}\n\n"
            "Score de risque : {score}/100 — Niveau : {level_emoji} {level_label}\n"
            "Prévision 15 jours : {forecast_summary}"
        ),
        "recommendation": (
            "1. Réduire les pertes d'eau (paillage, ombrage).\n"
            "2. Vérifier les plants et adapter les travaux agricoles aux conditions sèches.\n"
            "3. Si irrigation disponible, planifier un apport ciblé.\n"
            "4. Surveiller l'évolution via les prévisions à 15 jours."
        ),
    },
    "EXCES_PLUIE": {
        "title": "🌧️ Excès de précipitations — {champ_nom}",
        "message": (
            "Des précipitations importantes ont été observées sur le champ "
            "{champ_nom} (culture : {culture}).\n\n"
            "Cumuls observés :\n{indicators_summary}\n\n"
            "Score de risque : {score}/100 — Niveau : {level_emoji} {level_label}"
        ),
        "recommendation": (
            "1. Surveiller le drainage et l'érosion.\n"
            "2. Vérifier l'accès au champ avant les prochaines interventions.\n"
            "3. Inspecter les cultures pour détecter un jaunissement ou un asphyxie racinaire.\n"
            "4. Reporter les traitements phytosanitaires si sol saturé."
        ),
    },
    "GENERIC": {
        "title": "⚠️ Alerte agricole — {champ_nom}",
        "message": (
            "Une anomalie a été détectée sur le champ {champ_nom} "
            "(culture : {culture}).\n\n"
            "Indicateurs contributeurs :\n{indicators_summary}\n\n"
            "Score de risque : {score}/100 — Niveau : {level_emoji} {level_label}"
        ),
        "recommendation": "Inspecter le champ et consulter les indicateurs détaillés.",
    },
}

LEVEL_META = {
    "NORMAL":    {"emoji": "🟢", "label": "Normal"},
    "VIGILANCE": {"emoji": "🟡", "label": "Vigilance"},
    "ALERT":     {"emoji": "🟠", "label": "Alerte"},
    "CRITICAL":  {"emoji": "🔴", "label": "Critique"},
}


# ============================================================
# STRUCTURE DE RÉSULTAT
# ============================================================
@dataclass
class EvaluationResult:
    champ_id: int
    champ_nom: str = ""
    score: float = 0.0
    level: str = "NORMAL"
    previous_level: str | None = None
    level_changed: bool = False
    alerts_created: int = 0
    deliveries_created: int = 0
    alert_types: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    assessment_id: int | None = None


# ============================================================
# GÉNÉRATION DE MESSAGE
# ============================================================
def _format_indicators_summary(contributors: list[dict]) -> str:
    """Formate une liste lisible des indicateurs contributeurs."""
    lines: list[str] = []
    for c in contributors:
        indicator = c.get("indicator", "?")
        if indicator.startswith("_CROSS_"):
            note = c.get("note", "")
            contrib = c.get("contribution", 0)
            lines.append(f"  • Croisement : {note} (+{contrib:.0f} pts)")
            continue
        value = c.get("value")
        var = c.get("variation_pct")
        unit = c.get("unit", "")
        val_str = f"{value}{unit}" if value is not None else "n/a"
        var_str = f" (variation : {var:+.1f} %)" if var is not None else ""
        contrib = c.get("contribution", 0)
        lines.append(f"  • {indicator} = {val_str}{var_str} → +{contrib:.0f} pts")
    return "\n".join(lines) if lines else "  Aucun indicateur disponible"


def _format_forecast_summary(result: RiskResult) -> str:
    """Résumé de la prévision à 15 jours."""
    spi_fc = result.indicators.get("SPI_FORECAST")
    if spi_fc and spi_fc.value is not None:
        if spi_fc.value < -1.5:
            return f"SPI prévisionnel = {spi_fc.value:.2f} → sécheresse sévère prévue"
        if spi_fc.value < -1.0:
            return f"SPI prévisionnel = {spi_fc.value:.2f} → sécheresse modérée prévue"
        if spi_fc.value < -0.5:
            return f"SPI prévisionnel = {spi_fc.value:.2f} → conditions déficitaires"
        return f"SPI prévisionnel = {spi_fc.value:.2f} → conditions favorables"
    return "Données prévisionnelles indisponibles"


def _build_alert_message(alert_type: str, champ: Champ, result: RiskResult) -> dict[str, str]:
    """Construit le titre, message et recommandation pour une alerte."""
    template = ALERT_TEMPLATES.get(alert_type, ALERT_TEMPLATES["GENERIC"])
    level_meta = LEVEL_META.get(result.level, LEVEL_META["NORMAL"])
    context = {
        "champ_nom": champ.nom,
        "culture": champ.type_culture or "culture non précisée",
        "score": f"{result.score:.0f}",
        "level_emoji": level_meta["emoji"],
        "level_label": level_meta["label"],
        "indicators_summary": _format_indicators_summary(result.contributors),
        "forecast_summary": _format_forecast_summary(result),
    }
    try:
        title = template["title"].format(**context)
        message = template["message"].format(**context)
        recommendation = template["recommendation"]
    except (KeyError, ValueError) as exc:
        logger.error("Erreur template alerte %s: %s", alert_type, exc)
        title = template["title"]
        message = template["message"]
        recommendation = template["recommendation"]
    return {"title": title, "message": message, "recommendation": recommendation}


# ============================================================
# DÉCISION DE CRÉATION D'ALERTE
# ============================================================
def _should_create_alert(
    previous_level: str | None,
    current_level: str,
) -> tuple[bool, str]:
    """Décide s'il faut créer une alerte et pourquoi.

    Renvoie (créer, raison). Les règles :
    - Pas d'évaluation précédente + niveau > NORMAL → créer (première détection)
    - Niveau inchangé → ne pas créer (anti-doublon)
    - Niveau aggravé (NORMAL→VIGILANCE→ALERT→CRITICAL) → créer (aggravation)
    - Niveau amélioré → créer (amélioration / résolution)
    """
    level_order = ["NORMAL", "VIGILANCE", "ALERT", "CRITICAL"]
    if previous_level is None:
        if current_level != "NORMAL":
            return True, "Première détection d'une anomalie"
        return False, "Première évaluation, niveau normal"
    if previous_level == current_level:
        return False, "Niveau inchangé"
    prev_idx = level_order.index(previous_level) if previous_level in level_order else 0
    curr_idx = level_order.index(current_level) if current_level in level_order else 0
    if curr_idx > prev_idx:
        return True, f"Aggravation : {previous_level} → {current_level}"
    return True, f"Amélioration : {previous_level} → {current_level}"


# ============================================================
# FONCTION PRINCIPALE D'ÉVALUATION
# ============================================================
@transaction.atomic
def evaluate_champ(champ: Champ, *, dry_run: bool = False) -> EvaluationResult:
    """Évalue le risque d'un champ et crée une alerte si le niveau change.

    1. Calcule le score via risk_engine.assess_champ_risk()
    2. Compare au niveau précédent (RiskAssessment le plus récent)
    3. Si changement → crée FarmerAlert + AlertDelivery (EMAIL)
    4. Persiste le nouveau RiskAssessment
    """
    result = EvaluationResult(champ_id=champ.id, champ_nom=champ.nom)
    farmer = champ.owner
    if farmer is None or not farmer.is_active:
        result.errors.append("Aucun agriculteur actif associé au champ")
        return result

    # 1. Calculer le risque.
    try:
        risk = assess_champ_risk(champ)
    except Exception as exc:
        logger.exception("Erreur calcul risque champ %s", champ.id)
        result.errors.append(f"Erreur scoring : {exc}")
        return result

    result.score = risk.score
    result.level = risk.level
    result.alert_types = risk.detected_alert_types

    # 2. Récupérer le niveau précédent.
    prev_level = _get_previous_level(champ)
    result.previous_level = prev_level

    # 3. Décider s'il faut créer une alerte.
    should_create, reason = _should_create_alert(prev_level, risk.level)
    result.level_changed = should_create

    if not should_create:
        logger.info(
            "Champ %s : score %.1f, niveau %s (inchangé) — pas d'alerte",
            champ.id, risk.score, risk.level,
        )
        if not dry_run:
            assessment = persist_risk_assessment(champ, risk)
            result.assessment_id = assessment.id
        return result

    logger.info(
        "Champ %s : score %.1f, niveau %s (précédent : %s) — %s",
        champ.id, risk.score, risk.level, prev_level, reason,
    )

    # 4. Choisir le type d'alerte principal.
    if risk.detected_alert_types:
        alert_type = risk.detected_alert_types[0]  # priorité : vegetation > humidity > drought > rainfall
    elif risk.level == "CRITICAL":
        alert_type = "GENERIC"
    else:
        alert_type = "GENERIC"

    # 5. Construire le message.
    msg = _build_alert_message(alert_type, champ, risk)

    # 6. Créer le FarmerAlert.
    indicator_for_alert = (
        risk.contributors[0]["indicator"] if risk.contributors else "NDVI"
    )
    observed_value = (
        risk.indicators.get(indicator_for_alert).value
        if risk.indicators.get(indicator_for_alert)
        else risk.score
    )

    alert = FarmerAlert(
        farmer=farmer,
        champ=champ,
        rule=None,  # plus basé sur AlertRule, mais on garde la FK pour rétro-compat
        indicator=indicator_for_alert,
        observed_value=observed_value or risk.score,
        severity=_level_to_severity(risk.level),
        risk_level=risk.level,
        risk_score=risk.score,
        alert_type=alert_type,
        contributing_indicators=risk.contributors,
        title=msg["title"],
        message=msg["message"],
        recommendation=msg["recommendation"],
        observed_at=timezone.now(),
    )

    if dry_run:
        result.alerts_created = 1
        return result

    alert.save()
    result.alerts_created = 1

    # 7. Créer la livraison email si l'utilisateur a activé.
    profile = getattr(farmer, "profile", None)
    email_enabled = getattr(profile, "recevoir_alertes_email", True) if profile else True
    alerts_enabled = getattr(profile, "recevoir_alertes", True) if profile else True
    if alerts_enabled and email_enabled and farmer.email:
        AlertDelivery.objects.create(
            alert=alert,
            channel="EMAIL",
            destination=farmer.email,
        )
        result.deliveries_created = 1

    # 8. Persister le RiskAssessment et lier l'alerte.
    assessment = persist_risk_assessment(champ, risk)
    assessment.triggered_alerts.add(alert)
    result.assessment_id = assessment.id

    return result


def _level_to_severity(level: str) -> str:
    """Convertit un niveau de risque en sévérité (pour rétro-compat FarmerAlert.severity)."""
    return {
        "NORMAL": "INFO",
        "VIGILANCE": "LOW",
        "ALERT": "HIGH",
        "CRITICAL": "CRITICAL",
    }.get(level, "MEDIUM")


def _get_previous_level(champ: Champ) -> str | None:
    """Récupère le niveau du RiskAssessment le plus récent."""
    last = (
        RiskAssessment.objects.filter(champ=champ)
        .order_by("-assessed_at")
        .first()
    )
    return last.level if last else None


def evaluate_all_champs(*, champ_id: int | None = None, dry_run: bool = False) -> list[EvaluationResult]:
    """Évalue tous les champs (ou un seul si champ_id)."""
    qs = Champ.objects.select_related("owner", "owner__profile")
    if champ_id is not None:
        qs = qs.filter(pk=champ_id)
    return [evaluate_champ(champ, dry_run=dry_run) for champ in qs.iterator()]


# ============================================================
# RÉTRO-COMPATIBILITÉ — fonctions utilisées par l'ancien code
# ============================================================
def models_q_for_crop(crop: str):
    """Garde la fonction pour ne pas casser d'éventuels imports."""
    from django.db.models import Q
    return Q(crop_type="") | Q(crop_type__iexact=crop or "")

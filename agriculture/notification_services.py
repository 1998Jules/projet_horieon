"""Service de notification par email — version enrichie.

Construit des emails HTML riches avec :
- le niveau de risque (🟢🟡🟠🔴) et le score 0-100
- les indicateurs ayant contribué à l'alerte
- une recommandation contextuelle
- le contexte du champ (nom, culture, propriétaire)

La protection anti-doublon est gérée en amont par alert_services.py
(une alerte n'est créée que si le niveau de risque change), donc ce module
envoie simplement toutes les AlertDelivery en statut PENDING.
"""
from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import AlertDelivery

logger = logging.getLogger(__name__)


# ============================================================
# CONSTRUCTION DU CONTENU EMAIL
# ============================================================
def _format_contributors_html(contributors: list[dict]) -> str:
    """Génère un tableau HTML des indicateurs contributeurs."""
    if not contributors:
        return "<p><em>Aucun indicateur détaillé disponible.</em></p>"
    rows = []
    for c in contributors:
        indicator = c.get("indicator", "?")
        if indicator.startswith("_CROSS_"):
            note = c.get("note", "")
            contrib = c.get("contribution", 0)
            rows.append(
                f"<tr style='background:#fef9c3;'>"
                f"<td colspan='4'><strong>Croisement :</strong> {note} "
                f"<span style='color:#65a30d;'>(+{contrib:.0f} pts)</span></td></tr>"
            )
            continue
        value = c.get("value")
        var = c.get("variation_pct")
        unit = c.get("unit", "")
        contrib = c.get("contribution", 0)
        dimension = c.get("dimension", "")
        val_str = f"{value}{unit}" if value is not None else "—"
        var_str = f"{var:+.1f} %" if var is not None else "—"
        var_color = "#dc2626" if (var is not None and var < 0) else "#16a34a"
        rows.append(
            f"<tr>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{indicator}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{dimension}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;font-weight:bold;'>{val_str}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;color:{var_color};'>{var_str}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;text-align:right;'>+{contrib:.0f}</td>"
            f"</tr>"
        )
    header = (
        "<table style='border-collapse:collapse;width:100%;font-size:13px;'>"
        "<thead><tr style='background:#f3f4f6;text-align:left;'>"
        "<th style='padding:8px 12px;'>Indicateur</th>"
        "<th style='padding:8px 12px;'>Dimension</th>"
        "<th style='padding:8px 12px;'>Valeur</th>"
        "<th style='padding:8px 12px;'>Variation</th>"
        "<th style='padding:8px 12px;text-align:right;'>Contribution</th>"
        "</tr></thead><tbody>"
    )
    return header + "".join(rows) + "</tbody></table>"


def _level_badge_html(level: str, score: float) -> str:
    """Génère un badge HTML coloré pour le niveau de risque."""
    badges = {
        "NORMAL":    ("🟢", "#16a34a", "Normal"),
        "VIGILANCE": ("🟡", "#ca8a04", "Vigilance"),
        "ALERT":     ("🟠", "#ea580c", "Alerte"),
        "CRITICAL":  ("🔴", "#dc2626", "Critique"),
    }
    emoji, color, label = badges.get(level, ("⚪", "#6b7280", level))
    return (
        f"<div style='display:inline-block;padding:8px 16px;border-radius:8px;"
        f"background:{color};color:white;font-weight:bold;font-size:15px;'>"
        f"{emoji} {label} — Score : {score:.0f}/100</div>"
    )


def _format_contributor_line(c: dict) -> str:
    """Formate une ligne texte pour un indicateur contributeur.

    Renvoie par ex. : « • NDVI = 0.42 (variation : -14.5 %) → +18 pts »
    On utilise des guillemets simples partout pour éviter les conflits de
    backslash dans les f-strings (interdit avant Python 3.12).
    """
    indicator = c.get('indicator', '?')
    value = c.get('value', 'n/a')
    contribution = c.get('contribution', 0)
    line = f'  • {indicator} = {value}'
    var = c.get('variation_pct')
    if var is not None:
        line += f' (variation : {var:+.1f} %)'
    line += f' → +{contribution:.0f} pts'
    return line


def build_alert_email(delivery: AlertDelivery) -> tuple[str, str, str]:
    """Construit le sujet, le texte et le HTML de l'email d'alerte.

    Utilise les nouveaux champs risk_level, risk_score, alert_type et
    contributing_indicators du FarmerAlert. Si l'alerte est ancienne (ces
    champs sont vides), on bascule sur un format simplifié rétro-compatible.
    """
    alert = delivery.alert
    farmer_name = alert.farmer.get_full_name() or alert.farmer.username
    champ = alert.champ

    # --- Sujet ---
    subject = f"[{alert.get_risk_level_display() if alert.risk_level else alert.get_severity_display()}] {alert.title}"

    # --- Formatage des indicateurs contributeurs ---
    contributors = alert.contributing_indicators or []
    contributors_text = "\n".join(
        _format_contributor_line(c)
        for c in contributors
        if not c.get("indicator", "").startswith("_CROSS_")
    ) or "  Aucun indicateur détaillé disponible."

    # --- Texte brut ---
    text = (
        f"Bonjour {farmer_name},\n\n"
        f"{alert.message}\n\n"
        f"Recommandation :\n{alert.recommendation or 'Aucune recommandation supplémentaire.'}\n\n"
        f"--- Détails ---\n"
        f"Champ : {champ.nom}\n"
        f"Culture : {champ.type_culture or 'non précisée'}\n"
        f"Propriétaire : {champ.proprietaire or 'n/a'}\n"
        f"Type d'alerte : {alert.get_alert_type_display() if alert.alert_type else 'Générique'}\n"
        f"Niveau de risque : {alert.get_risk_level_display() if alert.risk_level else 'n/a'}\n"
        f"Score : {alert.risk_score:.0f}/100\n" if alert.risk_score else ""
        f"Indicateur principal : {alert.get_indicator_display()}\n"
        f"Valeur observée : {alert.observed_value}\n"
        f"Date d'observation : {alert.observed_at:%d/%m/%Y %H:%M}\n\n"
        f"Indicateurs contributeurs :\n{contributors_text}\n\n"
        f"Vous recevez ce message parce que vous avez activé les alertes agricoles."
    )

    # --- HTML ---
    badge = _level_badge_html(alert.risk_level, alert.risk_score) if alert.risk_level else ""
    contributors_html = _format_contributors_html(contributors)
    alert_type_display = alert.get_alert_type_display() if alert.alert_type else "Alerte"

    html = f"""
    <html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1f2937; max-width: 640px; margin: 0 auto;">
      <div style="background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); padding: 24px; border-radius: 12px 12px 0 0;">
        <h2 style="margin: 0 0 12px 0; color: #166534;">{alert.title}</h2>
        <p style="margin: 0 0 16px 0; font-size: 15px;">Bonjour {farmer_name},</p>
        <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.6;">{alert.message}</p>
        {f'<div style="margin: 16px 0;">{badge}</div>' if badge else ''}
      </div>

      <div style="padding: 24px; background: white; border: 1px solid #e5e7eb; border-top: none;">
        <h3 style="color: #166534; margin: 0 0 12px 0;">📋 Recommandation</h3>
        <p style="white-space: pre-line; line-height: 1.6; margin: 0 0 24px 0;">{alert.recommendation or 'Aucune recommandation supplémentaire.'}</p>

        <h3 style="color: #166534; margin: 0 0 12px 0;">📊 Indicateurs contributeurs</h3>
        {contributors_html}

        <h3 style="color: #166534; margin: 24px 0 12px 0;">🗺️ Contexte</h3>
        <table style="font-size: 13px; width: 100%;">
          <tr><td style="padding: 4px 0; color: #6b7280; width: 140px;">Champ</td><td style="font-weight: 500;">{champ.nom}</td></tr>
          <tr><td style="padding: 4px 0; color: #6b7280;">Culture</td><td>{champ.type_culture or 'non précisée'}</td></tr>
          <tr><td style="padding: 4px 0; color: #6b7280;">Propriétaire</td><td>{champ.proprietaire or 'n/a'}</td></tr>
          <tr><td style="padding: 4px 0; color: #6b7280;">Type d'alerte</td><td>{alert_type_display}</td></tr>
          <tr><td style="padding: 4px 0; color: #6b7280;">Score de risque</td><td><strong>{alert.risk_score:.0f}/100</strong></td></tr>
          <tr><td style="padding: 4px 0; color: #6b7280;">Date d'observation</td><td>{alert.observed_at:%d/%m/%Y %H:%M}</td></tr>
        </table>
      </div>

      <div style="padding: 16px 24px; background: #f9fafb; border-radius: 0 0 12px 12px; font-size: 12px; color: #6b7280;">
        Vous recevez cet email parce que vous avez activé les alertes agricoles.
        Pour modifier vos préférences, connectez-vous à votre espace.
      </div>
    </body></html>
    """
    return subject, text, html


# ============================================================
# ENVOI EFFECTIF
# ============================================================
def send_email_delivery(delivery: AlertDelivery) -> bool:
    """Envoie une livraison email unique via SMTP.

    Met à jour le statut (SENT/FAILED), le nombre de tentatives et le message
    d'erreur éventuel. Renvoie True si l'envoi a réussi.
    """
    if delivery.channel != "EMAIL":
        raise ValueError("Cette fonction ne traite que les livraisons EMAIL.")

    delivery.attempts += 1
    delivery.save(update_fields=["attempts", "updated_at"])

    subject, text, html = build_alert_email(delivery)
    sender = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
    if not sender:
        delivery.status = "FAILED"
        delivery.error_message = "DEFAULT_FROM_EMAIL ou EMAIL_HOST_USER n'est pas configuré."
        delivery.save(update_fields=["status", "error_message", "updated_at"])
        logger.error("Envoi email impossible : expéditeur non configuré")
        return False

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=sender,
            to=[delivery.destination],
        )
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
    except Exception as exc:
        delivery.status = "FAILED"
        delivery.error_message = str(exc)[:2000]
        delivery.save(update_fields=["status", "error_message", "updated_at"])
        logger.error("Échec envoi email alerte %s : %s", delivery.alert_id, exc)
        return False

    delivery.status = "SENT"
    delivery.sent_at = timezone.now()
    delivery.error_message = ""
    delivery.save(update_fields=["status", "sent_at", "error_message", "updated_at"])
    logger.info("Email envoyé à %s pour alerte %s", delivery.destination, delivery.alert_id)
    return True


def send_pending_email_deliveries(*, limit: int = 100) -> dict[str, int]:
    """Envoie tous les emails en attente (statut PENDING).

    Renvoie un compteur {sent, failed, skipped}.
    """
    counters = {"sent": 0, "failed": 0, "skipped": 0}
    deliveries = (
        AlertDelivery.objects
        .select_related("alert", "alert__farmer", "alert__champ")
        .filter(channel="EMAIL", status="PENDING")
        .order_by("created_at")[:limit]
    )
    for delivery in deliveries:
        if not delivery.destination:
            delivery.status = "SKIPPED"
            delivery.error_message = "Destination e-mail absente."
            delivery.save(update_fields=["status", "error_message", "updated_at"])
            counters["skipped"] += 1
        elif send_email_delivery(delivery):
            counters["sent"] += 1
        else:
            counters["failed"] += 1
    return counters

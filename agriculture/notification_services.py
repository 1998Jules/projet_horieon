from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import AlertDelivery


def build_alert_email(delivery: AlertDelivery) -> tuple[str, str, str]:
    alert = delivery.alert
    subject = f"[{alert.get_severity_display()}] {alert.title}"
    text = (
        f"Bonjour {alert.farmer.get_full_name() or alert.farmer.username},\n\n"
        f"{alert.message}\n\n"
        f"Recommandation :\n{alert.recommendation or 'Aucune recommandation supplémentaire.'}\n\n"
        f"Champ : {alert.champ.nom}\n"
        f"Indicateur : {alert.get_indicator_display()}\n"
        f"Valeur observée : {alert.observed_value}\n"
        f"Date : {alert.observed_at:%d/%m/%Y %H:%M}\n\n"
        "Vous recevez ce message parce que vous avez activé les alertes agricoles."
    )
    html = f"""
    <html><body>
      <h2>{alert.title}</h2>
      <p>Bonjour {alert.farmer.get_full_name() or alert.farmer.username},</p>
      <p>{alert.message}</p>
      <h3>Recommandation</h3>
      <p>{alert.recommendation or 'Aucune recommandation supplémentaire.'}</p>
      <hr>
      <p><strong>Champ :</strong> {alert.champ.nom}<br>
      <strong>Indicateur :</strong> {alert.get_indicator_display()}<br>
      <strong>Valeur observée :</strong> {alert.observed_value}<br>
      <strong>Date :</strong> {alert.observed_at:%d/%m/%Y %H:%M}</p>
    </body></html>
    """
    return subject, text, html


def send_email_delivery(delivery: AlertDelivery) -> bool:
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
        return False

    delivery.status = "SENT"
    delivery.sent_at = timezone.now()
    delivery.error_message = ""
    delivery.save(update_fields=["status", "sent_at", "error_message", "updated_at"])
    return True


def send_pending_email_deliveries(*, limit: int = 100) -> dict[str, int]:
    counters = {"sent": 0, "failed": 0, "skipped": 0}
    deliveries = AlertDelivery.objects.select_related(
        "alert", "alert__farmer", "alert__champ"
    ).filter(channel="EMAIL", status="PENDING").order_by("created_at")[:limit]
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

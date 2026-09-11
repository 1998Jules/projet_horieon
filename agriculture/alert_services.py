from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from .models import AlertDelivery, AlertRule, Champ, FarmerAlert, FieldIndicatorSnapshot


@dataclass
class EvaluationResult:
    champ_id: int
    alerts_created: int = 0
    deliveries_created: int = 0
    rules_matched: int = 0


def _matches(rule: AlertRule, value: float, previous_value: float | None = None) -> bool:
    if rule.operator == "LT":
        return value < rule.threshold
    if rule.operator == "LTE":
        return value <= rule.threshold
    if rule.operator == "GT":
        return value > rule.threshold
    if rule.operator == "GTE":
        return value >= rule.threshold
    if rule.operator == "EQ":
        return value == rule.threshold
    if rule.operator == "CHANGE_PCT":
        if previous_value in (None, 0):
            return False
        change_pct = ((value - previous_value) / abs(previous_value)) * 100
        return abs(change_pct) >= rule.threshold
    return False


def _context(snapshot: FieldIndicatorSnapshot, previous_value: float | None) -> dict:
    champ = snapshot.champ
    change_pct = None
    if previous_value not in (None, 0):
        change_pct = ((snapshot.value - previous_value) / abs(previous_value)) * 100
    return {
        "champ": champ.nom,
        "champ_nom": champ.nom,
        "culture": champ.type_culture or "culture non précisée",
        "indicateur": snapshot.get_indicator_display(),
        "indicator": snapshot.indicator,
        "valeur": f"{snapshot.value:.2f}",
        "value": snapshot.value,
        "unite": snapshot.unit,
        "source": snapshot.source,
        "date_observation": snapshot.observed_at.strftime("%d/%m/%Y"),
        "ancienne_valeur": "n/a" if previous_value is None else f"{previous_value:.2f}",
        "variation_pct": "n/a" if change_pct is None else f"{change_pct:.1f}%",
    }


def _render(template: str, context: dict) -> str:
    try:
        return template.format(**context)
    except (KeyError, IndexError, ValueError):
        # Une règle mal configurée ne doit pas bloquer tout le traitement.
        return template


def _latest_snapshots(champ: Champ) -> Iterable[tuple[FieldIndicatorSnapshot, float | None]]:
    snapshots = list(
        FieldIndicatorSnapshot.objects.filter(champ=champ).order_by("indicator", "-observed_at")
    )
    seen = set()
    latest = []
    for snapshot in snapshots:
        if snapshot.indicator in seen:
            continue
        seen.add(snapshot.indicator)
        previous = (
            FieldIndicatorSnapshot.objects.filter(
                champ=champ,
                indicator=snapshot.indicator,
                observed_at__lt=snapshot.observed_at,
            )
            .order_by("-observed_at")
            .values_list("value", flat=True)
            .first()
        )
        latest.append((snapshot, previous))
    return latest


def _within_cooldown(champ: Champ, rule: AlertRule, observed_at) -> bool:
    since = timezone.now() - timedelta(hours=rule.cooldown_hours)
    return FarmerAlert.objects.filter(
        champ=champ,
        rule=rule,
        created_at__gte=since,
        status__in=("OPEN", "ACKNOWLEDGED"),
    ).exists()


@transaction.atomic
def evaluate_champ(champ: Champ, *, dry_run: bool = False) -> EvaluationResult:
    result = EvaluationResult(champ_id=champ.pk)
    farmer = champ.owner
    if farmer is None or not farmer.is_active:
        return result

    rules = AlertRule.objects.filter(is_active=True).filter(
        models_q_for_crop(champ.type_culture)
    )
    for snapshot, previous_value in _latest_snapshots(champ):
        for rule in rules.filter(indicator=snapshot.indicator):
            if not _matches(rule, snapshot.value, previous_value):
                continue
            result.rules_matched += 1
            if _within_cooldown(champ, rule, snapshot.observed_at):
                continue

            context = _context(snapshot, previous_value)
            alert = FarmerAlert(
                farmer=farmer,
                champ=champ,
                rule=rule,
                indicator=snapshot.indicator,
                observed_value=snapshot.value,
                severity=rule.severity,
                title=_render(rule.title_template, context),
                message=_render(rule.message_template, context),
                recommendation=_render(rule.recommendation_template, context),
                observed_at=snapshot.observed_at,
            )
            if dry_run:
                result.alerts_created += 1
                continue

            alert.save()
            result.alerts_created += 1
            profile = getattr(farmer, "profile", None)
            email_enabled = getattr(profile, "recevoir_alertes_email", True)
            if profile and profile.recevoir_alertes and email_enabled and farmer.email:
                AlertDelivery.objects.create(
                    alert=alert,
                    channel="EMAIL",
                    destination=farmer.email,
                )
                result.deliveries_created += 1

    return result


def models_q_for_crop(crop: str):
    from django.db.models import Q
    return Q(crop_type="") | Q(crop_type__iexact=crop or "")


def evaluate_all_champs(*, champ_id: int | None = None, dry_run: bool = False) -> list[EvaluationResult]:
    queryset = Champ.objects.select_related("owner", "owner__profile")
    if champ_id is not None:
        queryset = queryset.filter(pk=champ_id)
    return [evaluate_champ(champ, dry_run=dry_run) for champ in queryset.iterator()]

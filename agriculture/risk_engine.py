"""Moteur de scoring de risque agricole — croisement multi-indicateurs.

PRINCIPES
---------
1. On ne déclenche pas d'alerte sur un seul indicateur : on croise plusieurs
   dimensions (végétation, humidité, sécheresse, précipitations, prévision).
2. Le score global est une somme pondérée de 5 sous-scores (0-100 chacun).
3. Les pondérations sont documentées dans WEIGHTS ci-dessous et peuvent être
   ajustées sans modifier la logique de croisement.
4. On distingue les variations (évolution par rapport à l'observation
   précédente) des valeurs absolues, car une baisse de 15 % du NDVI est
   souvent plus informative qu'une valeur absolue.

SCORES PAR DIMENSION (0-100, plus haut = plus risqué)
-----------------------------------------------------
- VÉGÉTATION   : NDVI, EVI, MSAVI (baisse + valeur absolue basse)
- HUMIDITÉ     : NDWI (valeur basse) + corroboration par EVI/MSAVI en baisse
- SÉCHERESSE   : SPI_30 (récente) + SPI_90 (persistante) + SPI_FORECAST
- PRÉCIPITATIONS : RAINFALL_24H + RAINFALL_72H (excès ou déficit)
- PRÉVISION    : SPI_FORECAST + pluie prévue 15j (Open-Meteo si dispo)

NIVEAUX DE RISQUE
-----------------
- 0-25   🟢 NORMAL     : situation saine, aucune alerte
- 26-50  🟡 VIGILANCE  : à surveiller, alerte d'information
- 51-75  🟠 ALERTE     : action recommandée
- 76-100 🔴 CRITIQUE   : action urgente requise
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import (
    AlertRule,
    Champ,
    FarmerAlert,
    FieldIndicatorSnapshot,
    RiskAssessment,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION DES POIDS — MODIFIER ICI POUR AJUSTER LE SYSTÈME
# ============================================================
# Poids de chaque dimension dans le score global (somme = 1.0).
WEIGHTS = {
    "vegetation": 0.30,   # NDVI + EVI + MSAVI — vigueur de la plante
    "humidity": 0.20,     # NDWI — état hydrique
    "drought": 0.25,      # SPI 30 + SPI 90 — déficit pluviométrique
    "rainfall": 0.15,     # Pluie 24h + 72h — excès ou déficit immédiat
    "forecast": 0.10,     # SPI forecast + tendance — vision prospective
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, "La somme des poids doit faire 1.0"

# Seuils des niveaux de risque (appliqués au score global 0-100).
LEVEL_THRESHOLDS = {
    "NORMAL":    (0, 25),
    "VIGILANCE": (26, 50),
    "ALERT":     (51, 75),
    "CRITICAL":  (76, 100),
}

# Seuils par indicateur (valeurs absolues) — ajustables.
THRESHOLDS = {
    # Indices spectraux (0-1) : en dessous de ces valeurs = stress.
    "NDVI_LOW": 0.30,      # < 0.30 = végétation clairsemée ou stressée
    "NDVI_VERY_LOW": 0.20,  # < 0.20 = sévère
    "EVI_LOW": 0.25,
    "NDWI_LOW": 0.10,       # NDWI < 0.10 = stress hydrique
    "MSAVI_LOW": 0.25,
    # Variations (%) : au-dessus de ces valeurs = dégradation significative.
    "VARIATION_DROP_MODERATE": 10.0,   # -10 % = vigilance
    "VARIATION_DROP_SEVERE": 20.0,    # -20 % = alerte
    # SPI (sans unité, ~loi normale) :
    "SPI_MILD": -0.5,       # -0.5 à -1.0 = sécheresse légère
    "SPI_MODERATE": -1.0,   # -1.0 à -1.5 = modérée
    "SPI_SEVERE": -1.5,     # < -1.5 = sévère
    # Précipitations (mm) :
    "RAIN_LOW_24H": 1.0,    # < 1 mm/24h = sec
    "RAIN_LOW_72H": 5.0,    # < 5 mm/72h = sec prolongé
    "RAIN_HIGH_24H": 50.0,  # > 50 mm/24h = risque inondation
    "RAIN_HIGH_72H": 100.0, # > 100 mm/72h = risque élevé
    "RAIN_CRITICAL_24H": 100.0,  # > 100 mm/24h = critique
}


# ============================================================
# STRUCTURES DE DONNÉES
# ============================================================
@dataclass
class IndicatorValue:
    """Valeur d'un indicateur avec son contexte (variation, référence)."""
    indicator: str
    value: float | None
    previous_value: float | None = None
    reference_value: float | None = None
    unit: str = ""
    observed_at: datetime | None = None

    @property
    def variation_pct(self) -> float | None:
        """Variation en % par rapport à la valeur précédente (négatif = baisse)."""
        if self.previous_value in (None, 0) or self.value is None:
            return None
        return ((self.value - self.previous_value) / abs(self.previous_value)) * 100

    @property
    def is_drop(self) -> bool:
        """True si la valeur a baissé significativement (≥ 10 %)."""
        var = self.variation_pct
        return var is not None and var <= -THRESHOLDS["VARIATION_DROP_MODERATE"]

    @property
    def is_severe_drop(self) -> bool:
        """True si la baisse est sévère (≥ 20 %)."""
        var = self.variation_pct
        return var is not None and var <= -THRESHOLDS["VARIATION_DROP_SEVERE"]


@dataclass
class DimensionScore:
    """Score d'une dimension (0-100) avec les contributeurs."""
    dimension: str
    score: float
    weight: float
    contributors: list[dict] = field(default_factory=list)


@dataclass
class RiskResult:
    """Résultat complet de l'évaluation du risque d'un champ."""
    champ_id: int
    score: float                     # 0-100
    level: str                       # NORMAL | VIGILANCE | ALERT | CRITICAL
    sub_scores: dict[str, float]     # par dimension
    indicators: dict[str, IndicatorValue]
    contributors: list[dict]         # indicateurs ayant contribué au score
    detected_alert_types: list[str] # STRESS_VEGETATIF, STRESS_HYDRIQUE, ...

    def as_dict(self) -> dict:
        return {
            "champ_id": self.champ_id,
            "score": round(self.score, 1),
            "level": self.level,
            "sub_scores": {k: round(v, 1) for k, v in self.sub_scores.items()},
            "indicators": {
                k: {
                    "value": v.value,
                    "previous_value": v.previous_value,
                    "variation_pct": round(v.variation_pct, 1) if v.variation_pct is not None else None,
                    "reference_value": v.reference_value,
                    "unit": v.unit,
                }
                for k, v in self.indicators.items()
            },
            "contributors": self.contributors,
            "detected_alert_types": self.detected_alert_types,
        }


# ============================================================
# LECTURE DES SNAPSHOTS DEPUIS LA BASE
# ============================================================
def load_champ_indicators(champ: Champ) -> dict[str, IndicatorValue]:
    """Charge les derniers snapshots de chaque indicateur pour un champ.

    Pour chaque indicateur, on récupère la valeur la plus récente et la
    précédente (pour calculer la variation). Renvoie un dict
    {'NDVI': IndicatorValue(...), 'SPI_30': IndicatorValue(...), ...}.
    """
    snapshots = list(
        FieldIndicatorSnapshot.objects.filter(champ=champ)
        .order_by("indicator", "-observed_at")
        .select_related("champ")
    )
    indicators: dict[str, IndicatorValue] = {}
    seen: set[str] = set()
    # snapshots est trié par indicator puis -observed_at, donc le 1er rencontré
    # pour un indicator donné est le plus récent ; le suivant est le précédent.
    for snap in snapshots:
        if snap.indicator in seen:
            # On ne garde que le plus récent + son précédent.
            if indicators[snap.indicator].previous_value is None:
                indicators[snap.indicator].previous_value = snap.value
            continue
        seen.add(snap.indicator)
        indicators[snap.indicator] = IndicatorValue(
            indicator=snap.indicator,
            value=snap.value,
            previous_value=None,  # sera rempli à la prochaine itération du même indicator
            reference_value=snap.reference_value,
            unit=snap.unit,
            observed_at=snap.observed_at,
        )
    return indicators


# ============================================================
# SOUS-SCORES PAR DIMENSION
# ============================================================
def _score_vegetation(indicators: dict[str, IndicatorValue]) -> DimensionScore:
    """Score végétation basé sur NDVI, EVI, MSAVI.

    On croise :
    - valeur absolue basse (stress structurel)
    - variation à la baisse (dégradation récente)

    Plusieurs baisses simultanées → score plus élevé (croisement).
    """
    contributors: list[dict] = []
    score = 0.0
    drop_count = 0

    for name in ("NDVI", "EVI", "MSAVI"):
        ind = indicators.get(name)
        if not ind or ind.value is None:
            continue
        # Score basé sur la valeur absolue (0-1 → 0-100).
        # NDVI = 0.5 → 0 points ; NDVI = 0.2 → ~60 points ; NDVI = 0.0 → 100 points.
        value_score = max(0.0, (0.5 - ind.value) / 0.5 * 100) if ind.value < 0.5 else 0.0
        # Bonus si la valeur est très basse.
        if ind.value < THRESHOLDS["NDVI_VERY_LOW"]:
            value_score = max(value_score, 70.0)
        # Pénalité si variation à la baisse.
        if ind.is_drop:
            drop_count += 1
            var = abs(ind.variation_pct or 0)
            value_score += min(40.0, var * 2)  # -10 % → +20, -20 % → +40
        if ind.is_severe_drop:
            value_score = min(100.0, value_score + 15.0)
        score = max(score, value_score * 0.6)  # contribution individuelle
        contributors.append({
            "indicator": name,
            "value": round(ind.value, 3),
            "variation_pct": round(ind.variation_pct, 1) if ind.variation_pct is not None else None,
            "contribution": round(value_score, 1),
            "is_drop": ind.is_drop,
        })

    # Croisement : plusieurs indices en baisse → score amplifié.
    if drop_count >= 3:
        score = min(100.0, score + 25.0)  # dégradation généralisée
        contributors.append({"indicator": "_CROSS_3_drops", "contribution": 25.0, "note": "3 indices en baisse simultanée"})
    elif drop_count == 2:
        score = min(100.0, score + 10.0)
        contributors.append({"indicator": "_CROSS_2_drops", "contribution": 10.0, "note": "2 indices en baisse"})

    return DimensionScore(
        dimension="vegetation",
        score=round(min(100.0, score), 1),
        weight=WEIGHTS["vegetation"],
        contributors=contributors,
    )


def _score_humidity(indicators: dict[str, IndicatorValue]) -> DimensionScore:
    """Score humidité basé sur NDWI + corroboration EVI/MSAVI.

    NDWI faible + NDVI en baisse → stress hydrique probable.
    """
    contributors: list[dict] = []
    score = 0.0

    ndwi = indicators.get("NDWI")
    if ndwi and ndwi.value is not None:
        # NDWI < 0 = stress hydrique net ; NDWI > 0.3 = bonne hydratation.
        if ndwi.value < 0:
            score = 70.0 + min(30.0, abs(ndwi.value) * 100)
        elif ndwi.value < THRESHOLDS["NDWI_LOW"]:
            score = 40.0 + (THRESHOLDS["NDWI_LOW"] - ndwi.value) / THRESHOLDS["NDWI_LOW"] * 30.0
        else:
            score = max(0.0, 20.0 - ndwi.value * 50.0)
        contributors.append({
            "indicator": "NDWI",
            "value": round(ndwi.value, 3),
            "contribution": round(score, 1),
        })

    # Corroboration : si NDVI et EVI sont aussi en baisse, le stress hydrique
    # est plus probable → on amplifie le score.
    corroboration_drops = []
    for name in ("NDVI", "EVI", "MSAVI"):
        ind = indicators.get(name)
        if ind and ind.is_drop:
            corroboration_drops.append(name)
    if corroboration_drops and score > 0:
        bonus = min(25.0, len(corroboration_drops) * 10.0)
        score = min(100.0, score + bonus)
        contributors.append({
            "indicator": "_CROSS_NDWI_drops",
            "contribution": round(bonus, 1),
            "note": f"Corroboration par baisses : {', '.join(corroboration_drops)}",
        })

    return DimensionScore(
        dimension="humidity",
        score=round(min(100.0, score), 1),
        weight=WEIGHTS["humidity"],
        contributors=contributors,
    )


def _score_drought(indicators: dict[str, IndicatorValue]) -> DimensionScore:
    """Score sécheresse basé sur SPI 30j, SPI 90j, SPI forecast.

    - SPI_30 : sécheresse récente (1 mois)
    - SPI_90 : sécheresse persistante (3 mois)
    - SPI_FORECAST : vision prospective 15j

    On distingue :
    - sécheresse récente seule (SPI_30 < seuil, SPI_90 OK) → score modéré
    - sécheresse persistante (SPI_90 < seuil) → score élevé
    - sécheresse aggravée (SPI_30 < SPI_90 < 0) → score critique
    """
    contributors: list[dict] = []
    score = 0.0

    spi_30 = indicators.get("SPI_30") or indicators.get("SPI_1")
    spi_90 = indicators.get("SPI_90") or indicators.get("SPI_3")
    spi_fc = indicators.get("SPI_FORECAST")

    def _spi_to_score(spi: float | None) -> float:
        if spi is None:
            return 0.0
        # SPI = 0 → 0 pts ; SPI = -1 → ~50 pts ; SPI = -2 → ~90 pts ; SPI = -3 → 100 pts.
        if spi >= 0:
            return 0.0
        return min(100.0, abs(spi) * 50.0)

    score_30 = _spi_to_score(spi_30.value if spi_30 else None)
    score_90 = _spi_to_score(spi_90.value if spi_90 else None)

    # On pondère : SPI_90 (persistant) a plus de poids que SPI_30 (récent).
    score = max(score_30 * 0.7, score_90 * 1.0)

    if spi_30 and spi_30.value is not None:
        contributors.append({
            "indicator": "SPI_30",
            "value": round(spi_30.value, 2),
            "contribution": round(score_30, 1),
            "classification": _classify_spi(spi_30.value),
        })
    if spi_90 and spi_90.value is not None:
        contributors.append({
            "indicator": "SPI_90",
            "value": round(spi_90.value, 2),
            "contribution": round(score_90, 1),
            "classification": _classify_spi(spi_90.value),
        })

    # Détection aggravation : SPI_30 < SPI_90 < 0 (la sécheresse s'aggrave).
    if (spi_30 and spi_90 and spi_30.value is not None and spi_90.value is not None
            and spi_30.value < spi_90.value < 0):
        score = min(100.0, score + 15.0)
        contributors.append({
            "indicator": "_CROSS_aggravation",
            "contribution": 15.0,
            "note": "Sécheresse s'aggrave (SPI_30 < SPI_90 < 0)",
        })

    # Prévision défavorable amplifie le score.
    if spi_fc and spi_fc.value is not None and spi_fc.value < THRESHOLDS["SPI_MILD"]:
        fc_score = _spi_to_score(spi_fc.value)
        score = min(100.0, score + fc_score * 0.3)
        contributors.append({
            "indicator": "SPI_FORECAST",
            "value": round(spi_fc.value, 2),
            "contribution": round(fc_score * 0.3, 1),
            "note": "Prévision 15j défavorable",
        })

    return DimensionScore(
        dimension="drought",
        score=round(min(100.0, score), 1),
        weight=WEIGHTS["drought"],
        contributors=contributors,
    )


def _score_rainfall(indicators: dict[str, IndicatorValue]) -> DimensionScore:
    """Score précipitations basé sur RAINFALL_24H et RAINFALL_72H.

    Détecte deux situations opposées :
    - Excès : > 50 mm/24h ou > 100 mm/72h → risque inondation
    - Déficit : < 1 mm/24h ET < 5 mm/72h → sol sec
    """
    contributors: list[dict] = []
    score = 0.0

    r24 = indicators.get("RAINFALL_24H") or indicators.get("RAINFALL")
    r72 = indicators.get("RAINFALL_72H") or indicators.get("RAINFALL")

    v24 = r24.value if r24 and r24.value is not None else None
    v72 = r72.value if r72 and r72.value is not None else None

    if v24 is not None:
        if v24 >= THRESHOLDS["RAIN_CRITICAL_24H"]:
            score = max(score, 95.0)
        elif v24 >= THRESHOLDS["RAIN_HIGH_24H"]:
            score = max(score, 70.0)
        elif v24 >= 25.0:
            score = max(score, 35.0)
        contributors.append({
            "indicator": "RAINFALL_24H",
            "value": round(v24, 1),
            "unit": "mm",
            "contribution": round(score, 1),
        })

    if v72 is not None:
        if v72 >= THRESHOLDS["RAIN_HIGH_72H"]:
            score = max(score, 85.0)
        elif v72 >= 50.0:
            score = max(score, 50.0)
        contributors.append({
            "indicator": "RAINFALL_72H",
            "value": round(v72, 1),
            "unit": "mm",
            "contribution": 0.0,  # déjà compté via 24h
        })

    # Déficit : pas de pluie récente → contribution à la sécheresse.
    if v24 is not None and v72 is not None:
        if v24 < THRESHOLDS["RAIN_LOW_24H"] and v72 < THRESHOLDS["RAIN_LOW_72H"]:
            deficit_score = 40.0
            score = max(score, deficit_score)
            contributors.append({
                "indicator": "_CROSS_deficit",
                "contribution": round(deficit_score, 1),
                "note": "Déficit pluviométrique 24h + 72h",
            })

    return DimensionScore(
        dimension="rainfall",
        score=round(min(100.0, score), 1),
        weight=WEIGHTS["rainfall"],
        contributors=contributors,
    )


def _score_forecast(indicators: dict[str, IndicatorValue]) -> DimensionScore:
    """Score prévision basé sur SPI_FORECAST et tendance.

    Vision prospective : on anticipe l'aggravation ou l'amélioration.
    """
    contributors: list[dict] = []
    score = 0.0

    spi_fc = indicators.get("SPI_FORECAST")
    if spi_fc and spi_fc.value is not None:
        if spi_fc.value < THRESHOLDS["SPI_SEVERE"]:
            score = 80.0
        elif spi_fc.value < THRESHOLDS["SPI_MODERATE"]:
            score = 55.0
        elif spi_fc.value < THRESHOLDS["SPI_MILD"]:
            score = 30.0
        contributors.append({
            "indicator": "SPI_FORECAST",
            "value": round(spi_fc.value, 2),
            "contribution": round(score, 1),
            "classification": _classify_spi(spi_fc.value),
        })

    return DimensionScore(
        dimension="forecast",
        score=round(min(100.0, score), 1),
        weight=WEIGHTS["forecast"],
        contributors=contributors,
    )


def _classify_spi(spi: float) -> str:
    """Classification standard du SPI (McKee et al., 1993)."""
    if spi >= -0.5:
        return "normal"
    if spi >= -1.0:
        return "secheresse_legere"
    if spi >= -1.5:
        return "secheresse_moderee"
    if spi >= -2.0:
        return "secheresse_severe"
    return "secheresse_extreme"


# ============================================================
# FONCTION PRINCIPALE
# ============================================================
def _level_from_score(score: float) -> str:
    """Convertit un score 0-100 en niveau de risque."""
    for level, (low, high) in LEVEL_THRESHOLDS.items():
        if low <= score <= high:
            return level
    return "CRITICAL" if score > 100 else "NORMAL"


def _detect_alert_types(
    vegetation: DimensionScore,
    humidity: DimensionScore,
    drought: DimensionScore,
    rainfall: DimensionScore,
) -> list[str]:
    """Détecte les types d'alerte à partir des sous-scores.

    Logique de croisement :
    - STRESS_VEGETATIF : végétation > 50 ET au moins 2 indices en baisse
    - STRESS_HYDRIQUE : humidité > 40 ET végétation en baisse
    - SECHERESSE : sécheresse > 50 (SPI_30 ou SPI_90 < -1)
    - EXCES_PLUIE : pluie > 60 (≥ 50 mm/24h ou ≥ 100 mm/72h)
    """
    types: list[str] = []

    # Stress végétatif
    veg_drops = [c for c in vegetation.contributors if c.get("is_drop")]
    if vegetation.score >= 50 and len(veg_drops) >= 2:
        types.append("STRESS_VEGETATIF")
    elif vegetation.score >= 75:
        types.append("STRESS_VEGETATIF")

    # Stress hydrique
    if humidity.score >= 40 and vegetation.score >= 30:
        types.append("STRESS_HYDRIQUE")

    # Sécheresse
    if drought.score >= 50:
        types.append("SECHERESSE")

    # Excès de pluie
    if rainfall.score >= 60:
        types.append("EXCES_PLUIE")

    return types


def assess_champ_risk(champ: Champ) -> RiskResult:
    """Évalue le risque global d'un champ en croisant tous les indicateurs.

    1. Charge les derniers snapshots depuis FieldIndicatorSnapshot
    2. Calcule 5 sous-scores (végétation, humidité, sécheresse, pluie, prévision)
    3. Combine en un score global pondéré 0-100
    4. Détermine le niveau (🟢🟡🟠🔴) et les types d'alerte détectés
    """
    indicators = load_champ_indicators(champ)

    vegetation = _score_vegetation(indicators)
    humidity = _score_humidity(indicators)
    drought = _score_drought(indicators)
    rainfall = _score_rainfall(indicators)
    forecast = _score_forecast(indicators)

    # Score global = somme pondérée des sous-scores.
    score = (
        vegetation.score * vegetation.weight
        + humidity.score * humidity.weight
        + drought.score * drought.weight
        + rainfall.score * rainfall.weight
        + forecast.score * forecast.weight
    )
    score = round(min(100.0, max(0.0, score)), 1)
    level = _level_from_score(score)
    alert_types = _detect_alert_types(vegetation, humidity, drought, rainfall)

    # Fusionner tous les contributeurs.
    all_contributors: list[dict] = []
    for dim in (vegetation, humidity, drought, rainfall, forecast):
        for c in dim.contributors:
            all_contributors.append({"dimension": dim.dimension, **c})

    return RiskResult(
        champ_id=champ.id,
        score=score,
        level=level,
        sub_scores={
            "vegetation": vegetation.score,
            "humidity": humidity.score,
            "drought": drought.score,
            "rainfall": rainfall.score,
            "forecast": forecast.score,
        },
        indicators=indicators,
        contributors=all_contributors,
        detected_alert_types=alert_types,
    )


def persist_risk_assessment(champ: Champ, result: RiskResult) -> RiskAssessment:
    """Persiste le résultat dans RiskAssessment pour tracer l'évolution."""
    from django.utils import timezone
    assessment = RiskAssessment.objects.create(
        champ=champ,
        assessed_at=timezone.now(),
        score=result.score,
        level=result.level,
        sub_scores=result.sub_scores,
        indicators_snapshot={
            k: {
                "value": v.value,
                "previous_value": v.previous_value,
                "variation_pct": round(v.variation_pct, 1) if v.variation_pct is not None else None,
                "reference_value": v.reference_value,
                "unit": v.unit,
                "observed_at": v.observed_at.isoformat() if v.observed_at else None,
            }
            for k, v in result.indicators.items()
        },
    )
    return assessment


def get_previous_risk_level(champ: Champ) -> str | None:
    """Récupère le niveau de risque précédent pour détecter aggravation/amélioration."""
    last = (
        RiskAssessment.objects.filter(champ=champ)
        .order_by("-assessed_at")
        .exclude(level="")  # sécurité
        .first()
    )
    return last.level if last else None

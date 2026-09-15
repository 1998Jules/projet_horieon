"""Collecteur d'indicateurs agricoles.

Ce module est le pont entre les fonctions de calcul existantes (gee_utils.py
pour les indices spectraux Sentinel-2, chirps_gefs.py pour les indices
pluviométriques CHIRPS/CHIRPS-GEFS) et le modèle FieldIndicatorSnapshot.

Il ne calcule rien lui-même : il orchestre les appels aux fonctions existantes
puis persiste les résultats en base pour que le moteur d'alertes puisse les
consommer sans réinterroger Earth Engine / CHIRPS-GEFS à chaque exécution.

Toutes les fonctions sont protégées contre les erreurs : si un indice échoue,
les autres sont quand même persistés. On renvoie un rapport détaillé.
"""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import Champ, FieldIndicatorSnapshot

logger = logging.getLogger(__name__)

# Fenêtres temporelles par défaut pour l'historique des indices spectraux.
# On prend les 30 derniers jours glissants pour avoir une valeur récente.
DEFAULT_SPECTRAL_WINDOW_DAYS = 30
# Nombre d'années d'historique pour le SPI (climatologie de référence).
DEFAULT_SPI_YEARS_HISTORY = 10


def _champ_to_geojson(champ: Champ) -> dict | None:
    """Convertit la géométrie d'un champ en dict GeoJSON WGS84.

    Retourne None si la géométrie est absente ou invalide. Cette fonction est
    volontairement défensive car c'est la première cause d'erreur Earth Engine.
    """
    try:
        if champ.geom is None:
            logger.error("Champ %s : géométrie NULL", champ.id)
            return None
        geom_wgs84 = champ.geom.transform(4326, clone=True)
        geom_wgs84 = geom_wgs84.buffer(0)  # répare les géométries invalides
        return json.loads(geom_wgs84.geojson)
    except Exception as exc:
        logger.error("Champ %s : erreur transformation géométrie : %s", champ.id, exc)
        return None


def _store_snapshot(
    champ: Champ,
    indicator: str,
    value: float,
    observed_at: datetime,
    *,
    unit: str = "",
    source: str = "",
    reference_value: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Persiste ou met à jour un FieldIndicatorSnapshot.

    Utilise update_or_create sur (champ, observed_at, indicator) grâce à la
    contrainte unique. Renvoie True si l'écriture a réussi.
    """
    if value is None:
        return False
    try:
        # On tronque la date à la journée pour éviter les doublons liés à l'heure.
        observed_at_day = observed_at.replace(hour=0, minute=0, second=0, microsecond=0)
        FieldIndicatorSnapshot.objects.update_or_create(
            champ=champ,
            observed_at=observed_at_day,
            indicator=indicator,
            defaults={
                "value": float(value),
                "unit": unit,
                "source": source,
                "reference_value": reference_value,
                "metadata": metadata or {},
            },
        )
        return True
    except Exception as exc:
        logger.error(
            "Erreur persistance snapshot %s pour champ %s: %s",
            indicator, champ.id, exc,
        )
        return False


def _collect_spectral_indices(champ: Champ, geojson_dict: dict, observed_at: datetime) -> dict[str, float]:
    """Récupère les derniers NDVI / EVI / NDWI / MSAVI via gee_utils.

    get_field_indices_history renvoie un dict {indice: [{date, value}, ...]}.
    On prend la dernière valeur de chaque série.
    """
    from .gee_utils import get_field_indices_history

    start = (observed_at - timedelta(days=DEFAULT_SPECTRAL_WINDOW_DAYS)).strftime("%Y-%m-%d")

    try:
        result = get_field_indices_history(geojson_dict, start, ["ndvi", "evi", "ndwi", "msavi"])
    except Exception as exc:
        logger.error("Erreur collecte indices spectraux champ %s: %s", champ.id, exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())
        return {}

    if not result or not isinstance(result, dict):
        logger.warning("Champ %s : get_field_indices_history a renvoyé un résultat vide", champ.id)
        return {}

    values: dict[str, float] = {}
    for idx_key, idx_name in [("ndvi", "NDVI"), ("evi", "EVI"), ("ndwi", "NDWI"), ("msavi", "MSAVI")]:
        series = result.get(idx_key, [])
        if series:
            last_entry = series[-1]
            val = last_entry.get("value")
            if val is not None:
                values[idx_name] = val
    return values


def _collect_drought_indices(champ: Champ, geojson_dict: dict, observed_at: datetime) -> dict[str, float]:
    """Récupère VHI (et optionnellement VCI/TCI/NCWSI) via gee_utils (MODIS)."""
    from .gee_utils import get_drought_index_timeseries

    current_year = observed_at.year
    results: dict[str, float] = {}

    try:
        vhi_series = get_drought_index_timeseries(
            geojson_dict, years=[current_year], index_type="vhi"
        )
        if vhi_series:
            last = vhi_series[-1]
            results["VHI"] = last.get("value")
    except Exception as exc:
        logger.error("Erreur VHI champ %s: %s", champ.id, exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())

    return results


def _collect_climate_indices(champ: Champ, geojson_dict: dict, observed_at: datetime) -> dict[str, dict]:
    """Récupère SPI 30j, SPI 90j, SPI forecast, pluie 24h/72h.

    Renvoie un dict {'SPI_30': {'value': -1.2, 'metadata': {...}}, ...}.
    """
    from .chirps_gefs import get_forecast_spi
    from .gee_utils import compute_observed_spi_windows, get_realtime_precipitation

    results: dict[str, dict] = {}

    # --- SPI observés 30 et 90 jours ---
    try:
        spi_obs = compute_observed_spi_windows(
            geojson_dict, years_history=DEFAULT_SPI_YEARS_HISTORY
        )
        if isinstance(spi_obs, dict):
            if "30" in spi_obs:
                results["SPI_30"] = {
                    "value": spi_obs["30"].get("spi"),
                    "metadata": spi_obs["30"],
                }
            if "90" in spi_obs:
                results["SPI_90"] = {
                    "value": spi_obs["90"].get("spi"),
                    "metadata": spi_obs["90"],
                }
    except Exception as exc:
        logger.error("Erreur SPI observé champ %s: %s", champ.id, exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())

    # --- SPI prévisionnel 15 jours ---
    try:
        spi_forecast = get_forecast_spi(
            champ, forecast_days=15, years_history=DEFAULT_SPI_YEARS_HISTORY
        )
        if isinstance(spi_forecast, dict) and "spi" in spi_forecast:
            results["SPI_FORECAST"] = {
                "value": spi_forecast.get("spi"),
                "metadata": spi_forecast,
            }
    except Exception as exc:
        logger.error("Erreur SPI prévisionnel champ %s: %s", champ.id, exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())

    # --- Précipitations temps réel 24h / 72h (GPM IMERG) ---
    try:
        realtime = get_realtime_precipitation(geojson_dict, hours=72)
        if isinstance(realtime, dict):
            results["RAINFALL_24H"] = {
                "value": realtime.get("total_24h_mm"),
                "unit": "mm",
                "metadata": {"source": realtime.get("source", "GPM_IMERG")},
            }
            results["RAINFALL_72H"] = {
                "value": realtime.get("total_mm"),
                "unit": "mm",
                "metadata": {"source": realtime.get("source", "GPM_IMERG")},
            }
    except Exception as exc:
        logger.error("Erreur précipitations temps réel champ %s: %s", champ.id, exc)
        logger.debug("Traceback:\n%s", traceback.format_exc())
        # Fallback : CHIRPS-GEFS prévision quotidienne (si GPM indisponible).
        try:
            from .views import get_chirps_gefs_now
            chirps_now = get_chirps_gefs_now(champ)
            results["RAINFALL_24H"] = {
                "value": chirps_now.get("total_24h_mm"),
                "unit": "mm",
                "metadata": {"source": chirps_now.get("source", "CHIRPS3-GEFS")},
            }
            results["RAINFALL_72H"] = {
                "value": chirps_now.get("total_mm"),
                "unit": "mm",
                "metadata": {"source": chirps_now.get("source", "CHIRPS3-GEFS")},
            }
        except Exception as exc2:
            logger.error("Erreur fallback CHIRPS-GEFS champ %s: %s", champ.id, exc2)

    return results


def collect_champ_indicators(champ: Champ, *, observed_at: datetime | None = None) -> dict[str, Any]:
    """Collecte et persiste TOUS les indicateurs d'un champ en une passe.

    Orchestration :
      1. Indices spectraux (NDVI, EVI, NDWI, MSAVI) — Sentinel-2 via Earth Engine
      2. Indices sécheresse (VHI) — MODIS via Earth Engine
      3. Indices climatiques (SPI_30, SPI_90, SPI_FORECAST, RAINFALL_24H, RAINFALL_72H)
         — CHIRPS / CHIRPS-GEFS / GPM IMERG

    Chaque indicateur collecté est persisté dans FieldIndicatorSnapshot via
    update_or_create (idempotent). Les erreurs d'un indicateur n'empêchent pas
    les autres d'être collectés.

    Renvoie un rapport dict avec les valeurs collectées et les compteurs.
    """
    if observed_at is None:
        observed_at = timezone.now()
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=dt_timezone.utc)

    report: dict[str, Any] = {
        "champ_id": champ.id,
        "champ_nom": champ.nom,
        "observed_at": observed_at.isoformat(),
        "collected": {},
        "errors": [],
        "count_persisted": 0,
    }

    # --- 0. Vérifier la géométrie (cause #1 d'erreur Earth Engine) ---
    geojson_dict = _champ_to_geojson(champ)
    if geojson_dict is None:
        report["errors"].append("Géométrie invalide ou absente — impossible d'interroger Earth Engine")
        logger.error("Champ %s : géométrie invalide, collecte abandonnée", champ.id)
        return report

    logger.info(
        "Champ %s : géométrie OK (type=%s, coords_len=%d), début collecte",
        champ.id, geojson_dict.get("type"), len(str(geojson_dict.get("coordinates", ""))),
    )

    # --- 1. Indices spectraux ---
    try:
        spectral = _collect_spectral_indices(champ, geojson_dict, observed_at)
        for indicator, value in spectral.items():
            if value is None:
                continue
            ok = _store_snapshot(
                champ, indicator, value, observed_at,
                unit="", source="Sentinel-2 (COPERNICUS/S2_SR_HARMONIZED)",
            )
            if ok:
                report["collected"][indicator] = value
                report["count_persisted"] += 1
            else:
                report["errors"].append(f"Échec persistance {indicator}")
    except Exception as exc:
        msg = f"Indices spectraux : {exc}"
        report["errors"].append(msg)
        logger.exception("Champ %s : erreur fatale collecte spectrale", champ.id)

    # --- 2. Indices sécheresse (VHI) ---
    try:
        drought = _collect_drought_indices(champ, geojson_dict, observed_at)
        for indicator, value in drought.items():
            if value is None:
                continue
            ok = _store_snapshot(
                champ, indicator, value, observed_at,
                unit="", source="MODIS (MOD13A2 + MOD11A2)",
                reference_value=50.0,  # seuil neutre 0-100
            )
            if ok:
                report["collected"][indicator] = value
                report["count_persisted"] += 1
            else:
                report["errors"].append(f"Échec persistance {indicator}")
    except Exception as exc:
        msg = f"Indices sécheresse : {exc}"
        report["errors"].append(msg)
        logger.exception("Champ %s : erreur fatale collecte sécheresse", champ.id)

    # --- 3. Indices climatiques (SPI + pluie) ---
    try:
        climate = _collect_climate_indices(champ, geojson_dict, observed_at)
        for indicator, payload in climate.items():
            value = payload.get("value")
            if value is None:
                continue
            ok = _store_snapshot(
                champ, indicator, value, observed_at,
                unit=payload.get("unit", ""),
                source=payload.get("metadata", {}).get("source", ""),
                metadata=payload.get("metadata", {}),
            )
            if ok:
                report["collected"][indicator] = value
                report["count_persisted"] += 1
            else:
                report["errors"].append(f"Échec persistance {indicator}")
    except Exception as exc:
        msg = f"Indices climatiques : {exc}"
        report["errors"].append(msg)
        logger.exception("Champ %s : erreur fatale collecte climatique", champ.id)

    logger.info(
        "Collecte indicateurs champ %s : %d persistés, %d erreurs",
        champ.id, report["count_persisted"], len(report["errors"]),
    )
    return report


def collect_all_champs(*, champ_id: int | None = None) -> list[dict[str, Any]]:
    """Collecte les indicateurs pour tous les champs (ou un seul si champ_id)."""
    qs = Champ.objects.all()
    if champ_id is not None:
        qs = qs.filter(pk=champ_id)
    return [collect_champ_indicators(champ) for champ in qs.iterator()]

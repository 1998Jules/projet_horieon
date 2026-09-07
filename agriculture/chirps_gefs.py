"""Accès à la prévision quotidienne CHIRPS3-GEFS sans stockage permanent."""

import json
import logging
import os
import tempfile
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

CHIRPS_GEFS_DAILY_ROOT = (
    "https://data.chc.ucsb.edu/products/CHIRPS-GEFS/v3/daily/global"
)
CHIRPS_GEFS_15DAY_ROOT = (
    "https://data.chc.ucsb.edu/products/CHIRPS-GEFS/v3/15_day/global/data"
)


def _candidate_urls(run_date, target_date):
    """Retourne l'URL officielle du raster pour une date de prévision."""
    directory = f"{run_date:%Y}/{run_date:%m}/{run_date:%d}"
    filename = f"c3g_{target_date:%Y.%m.%d}.tif"
    return f"{CHIRPS_GEFS_DAILY_ROOT}/{directory}/{filename}"


def _candidate_15day_urls(run_date):
    filename = f"c3g_{run_date:%Y.%m.%d}.tif"
    return f"{CHIRPS_GEFS_15DAY_ROOT}/{run_date:%Y}/{filename}"


def _find_available_15day_url(run_date=None):
    first_run = run_date or date.today()
    for offset in range(0, 8):
        candidate_run = first_run - timedelta(days=offset)
        url = _candidate_15day_urls(candidate_run)
        try:
            response = requests.head(url, timeout=20, allow_redirects=True)
            if response.ok:
                return url, candidate_run
        except requests.RequestException as exc:
            logger.warning("HEAD CHIRPS-GEFS 15j échoué pour %s: %s", url, exc)
    return None, None


def _find_available_url(target_date, run_date=None):
    """Trouve le run récent qui contient la date cible, sans télécharger le TIFF."""
    first_run = run_date or date.today()
    for offset in range(0, 8):
        candidate_run = first_run - timedelta(days=offset)
        url = _candidate_urls(candidate_run, target_date)
        try:
            response = requests.head(url, timeout=20, allow_redirects=True)
            if response.ok:
                return url, candidate_run
        except requests.RequestException as exc:
            logger.warning("HEAD CHIRPS-GEFS échoué pour %s: %s", url, exc)
    return None, None


def _download_temporary(url):
    """Télécharge un TIFF dans un fichier temporaire et renvoie son chemin."""
    response = requests.get(url, stream=True, timeout=(20, 180))
    response.raise_for_status()
    temporary_file = tempfile.NamedTemporaryFile(
        prefix="chirps_gefs_", suffix=".tif", delete=False
    )
    try:
        with temporary_file as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)
        return Path(temporary_file.name)
    except Exception:
        temporary_file.close()
        try:
            os.unlink(temporary_file.name)
        except OSError:
            pass
        raise


def _mean_over_geometry(tif_path, geometry):
    """Calcule la moyenne raster sur une géométrie GeoJSON WGS84."""
    try:
        import rasterio
        from rasterio.mask import mask
    except ImportError as exc:
        raise RuntimeError(
            "La dépendance rasterio est requise pour l'API CHIRPS-GEFS."
        ) from exc

    with rasterio.open(tif_path) as source:
        clipped, _ = mask(source, [geometry], crop=True, filled=False)
        values = clipped[0].compressed()
        if values.size == 0:
            return None
        return round(float(values.mean()), 2)


def _mean_over_remote_geometry(url, geometry):
    """Lit uniquement la fenêtre du GeoTIFF distant couvrant le champ.

    CHIRPS-GEFS est servi par HTTP avec support des requêtes Range. GDAL via
    ``/vsicurl/`` ne télécharge donc normalement que les blocs nécessaires,
    au lieu des 60--70 Mo du raster global.
    """
    try:
        import rasterio
        from rasterio.mask import mask
    except ImportError as exc:
        raise RuntimeError(
            "La dépendance rasterio est requise pour l'API CHIRPS-GEFS."
        ) from exc

    remote_path = f"/vsicurl/{url}"
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_TIMEOUT="30",
    ):
        with rasterio.open(remote_path) as source:
            clipped, _ = mask(source, [geometry], crop=True, filled=False)
            values = clipped[0].compressed()
            if values.size == 0:
                return None
            return round(float(values.mean()), 2)


def get_15day_total_forecast(champ, run_date=None):
    """Extrait le cumul global prévu à 15 jours avec un seul raster distant."""
    geometry = json.loads(champ.geom.transform(4326, clone=True).geojson)
    url, source_run = _find_available_15day_url(run_date=run_date)
    if not url:
        raise RuntimeError("Aucun raster CHIRPS3-GEFS 15 jours disponible")
    value = _mean_over_remote_geometry(url, geometry)
    return {
        "source": "CHIRPS3-GEFS",
        "forecast_days": 15,
        "run_date": source_run.isoformat(),
        "total_precipitation_mm": value,
        "daily": [],
        "optimized": True,
    }


def get_field_forecast(champ, forecast_days=5, run_date=None):
    """Extrait la pluie CHIRPS3-GEFS prévue sur un champ.

    Les GeoTIFF sont téléchargés un par un dans /tmp puis supprimés dans le
    bloc finally. Aucun raster n'est conservé par l'application.
    """
    if not 1 <= forecast_days <= 15:
        raise ValueError("forecast_days doit être compris entre 1 et 15")

    geometry = json.loads(champ.geom.transform(4326, clone=True).geojson)
    base_date = run_date or date.today()
    def process_day(day_offset):
        target_date = base_date + timedelta(days=day_offset)
        url, source_run = _find_available_url(target_date, run_date=base_date)
        if not url:
            return {
                "date": target_date.isoformat(),
                "precipitation_mm": None,
                "available": False,
            }

        try:
            # Chemin rapide : lecture HTTP Range de la seule fenêtre du champ.
            value = _mean_over_remote_geometry(url, geometry)
        except Exception as remote_error:
            # Repli compatible avec les serveurs/GDAL sans lecture Range.
            logger.warning(
                "Lecture distante impossible pour %s, repli téléchargement: %s",
                target_date,
                remote_error,
            )
            temporary_path = None
            try:
                temporary_path = _download_temporary(url)
                value = _mean_over_geometry(temporary_path, geometry)
            finally:
                if temporary_path:
                    try:
                        temporary_path.unlink(missing_ok=True)
                    except OSError:
                        logger.warning("Impossible de supprimer %s", temporary_path)

        return {
            "date": target_date.isoformat(),
            "precipitation_mm": value,
            "available": value is not None,
            "source_run": source_run.isoformat(),
        }

    # Les jours sont indépendants : traiter en parallèle réduit fortement le
    # temps d'attente pour les prévisions de 5 à 15 jours.
    with ThreadPoolExecutor(max_workers=min(forecast_days, 5)) as executor:
        futures = [executor.submit(process_day, offset) for offset in range(forecast_days)]
        daily = [future.result() for future in futures]

    available_values = [
        item["precipitation_mm"] for item in daily
        if item["precipitation_mm"] is not None
    ]
    return {
        "source": "CHIRPS3-GEFS",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_date": base_date.isoformat(),
        "forecast_days": forecast_days,
        "total_precipitation_mm": round(sum(available_values), 2),
        "daily": daily,
    }


def get_forecast_spi(champ, forecast_days=15, years_history=10, run_date=None):
    """Calcule un SPI prévisionnel sur une fenêtre de 15 jours.

    Le cumul CHIRPS3-GEFS prévu est comparé aux cumuls CHIRPS historiques
    sur la même fenêtre calendaire pour les années précédentes. La
    transformation Gamma puis normale suit le principe du SPI.
    """
    if forecast_days != 15:
        raise ValueError("Le SPI prévisionnel utilise une fenêtre de 15 jours")
    if not 5 <= years_history <= 40:
        raise ValueError("years_history doit être compris entre 5 et 40")

    # Optimisation majeure : le produit 15_day fournit directement le cumul
    # des 15 jours dans un seul raster, inutile de lire 15 TIFF quotidiens.
    forecast = get_15day_total_forecast(champ, run_date=run_date)
    forecast_total = forecast["total_precipitation_mm"]
    if forecast_total is None:
        raise RuntimeError("Cumul CHIRPS3-GEFS indisponible sur la géométrie du champ")

    try:
        import ee
        from .gee_utils import initialize_ee, geojson_to_ee_geometry
        initialize_ee()
        geometry = json.loads(champ.geom.transform(4326, clone=True).geojson)
        geom = geojson_to_ee_geometry(geometry)
        chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        reference = date.fromisoformat(forecast["run_date"])
        historical = []

        for year_offset in range(1, years_history + 1):
            end_date = ee.Date(reference.isoformat()).advance(-year_offset, "year")
            start_date = end_date.advance(-15, "day")
            images = chirps.filterDate(start_date, end_date).filterBounds(geom)
            total_image = ee.Image(ee.Algorithms.If(
                images.size().gt(0),
                images.sum(),
                ee.Image.constant(0).rename("precipitation")
            ))
            stats = total_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=5566,
                maxPixels=1e9,
                bestEffort=True,
            )
            historical.append(stats.get("precipitation"))

        values = ee.List(historical).getInfo()
        historical_values = [float(value) for value in values if value is not None]
    except Exception as exc:
        logger.exception("Erreur historique CHIRPS pour le SPI prévisionnel")
        raise RuntimeError(f"Impossible de calculer l'historique CHIRPS : {exc}") from exc

    if len(historical_values) < 5:
        raise RuntimeError("Pas assez de valeurs historiques CHIRPS pour calculer le SPI")

    try:
        from scipy.stats import gamma, norm
    except ImportError as exc:
        raise RuntimeError("La dépendance scipy est requise pour calculer le SPI") from exc

    positive_values = [value for value in historical_values if value > 0]
    zero_probability = (len(historical_values) - len(positive_values)) / len(historical_values)
    if len(positive_values) < 3:
        raise RuntimeError("Pas assez de précipitations positives pour ajuster la loi Gamma")

    shape, _, scale = gamma.fit(positive_values, floc=0)
    cumulative_probability = gamma.cdf(max(float(forecast_total), 0), shape, loc=0, scale=scale)
    cumulative_probability = zero_probability + (1 - zero_probability) * cumulative_probability
    cumulative_probability = min(max(cumulative_probability, 1e-6), 1 - 1e-6)
    spi = round(float(norm.ppf(cumulative_probability)), 2)

    if spi <= -2:
        risk = "secheresse_extreme"
    elif spi <= -1.5:
        risk = "secheresse_severe"
    elif spi <= -1:
        risk = "secheresse_moderee"
    elif spi >= 2:
        risk = "tres_humide"
    elif spi >= 1.5:
        risk = "humide"
    else:
        risk = "normal"

    return {
        "source_observation": "CHIRPS",
        "source_forecast": "CHIRPS3-GEFS",
        "spi_scale_days": 15,
        "forecast": forecast,
        "historical_years": len(historical_values),
        "historical_mean_mm": round(sum(historical_values) / len(historical_values), 2),
        "historical_min_mm": round(min(historical_values), 2),
        "historical_max_mm": round(max(historical_values), 2),
        "forecast_total_mm": round(float(forecast_total), 2),
        "spi": spi,
        "risk": risk,
    }


def summarize_forecast_alert(forecast, spi_data):
    """Produit l'alerte finale en tenant compte de toute la fenêtre prévue."""
    values = [
        item["precipitation_mm"] for item in forecast.get("daily", [])
        if item.get("precipitation_mm") is not None
    ]
    spi = spi_data.get("spi")
    dry_streak = 0
    max_dry_streak = 0
    for value in values:
        if value < 1:
            dry_streak += 1
            max_dry_streak = max(max_dry_streak, dry_streak)
        else:
            dry_streak = 0

    max_3day = max(
        (sum(values[index:index + 3]) for index in range(max(0, len(values) - 2))),
        default=0,
    )
    if len(values) >= 6:
        midpoint = len(values) // 2
        first_half = sum(values[:midpoint]) / midpoint
        second_half = sum(values[midpoint:]) / (len(values) - midpoint)
        if second_half > first_half * 1.25:
            trend = "pluie_en_augmentation"
        elif second_half < first_half * 0.75:
            trend = "pluie_en_diminution"
        else:
            trend = "pluie_stable"
    else:
        trend = "donnees_insuffisantes"

    if max_3day >= 100:
        flood_alert = "inondation_elevee"
    elif max_3day >= 60:
        flood_alert = "inondation_moderee"
    else:
        flood_alert = "normal"

    if spi is not None and spi <= -2:
        drought_alert = "secheresse_extreme"
    elif spi is not None and spi <= -1.5:
        drought_alert = "secheresse_severe"
    elif spi is not None and (spi <= -1 or max_dry_streak >= 7):
        drought_alert = "secheresse_moderee"
    else:
        drought_alert = "normal"

    severity = {
        "normal": 0,
        "secheresse_moderee": 2,
        "inondation_moderee": 2,
        "secheresse_severe": 3,
        "inondation_elevee": 3,
        "secheresse_extreme": 4,
    }
    final_alert = drought_alert if severity[drought_alert] >= severity[flood_alert] else flood_alert
    return {
        "niveau": final_alert,
        "type": "secheresse" if final_alert.startswith("secheresse") else (
            "inondation" if final_alert.startswith("inondation") else "normal"
        ),
        "source": "evolution_prevision_15_jours",
        "tendance": trend,
        "total_15j_mm": round(sum(values), 2),
        "max_3j_mm": round(max_3day, 2),
        "max_jours_secs_consecutifs": max_dry_streak,
        "spi": spi,
        "alerte_secheresse": drought_alert,
        "alerte_inondation": flood_alert,
    }

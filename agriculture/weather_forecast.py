# agriculture/weather_forecast.py
"""
Prévision météo réelle (7-16 jours) pour projeter le risque de sécheresse
ou d'inondation À VENIR sur une parcelle, à partir des coordonnées du champ.

Utilise Open-Meteo (https://open-meteo.com), gratuit, sans clé API,
avec une bonne couverture pour l'Afrique de l'Ouest (modèles ECMWF/GFS).

Ceci complète (et ne remplace pas) :
- compute_climate_risk (gee_utils.py) : risque basé sur la pluie DÉJÀ TOMBÉE
  (CHIRPS, comparaison à la climatologie) -> "ce qui s'est passé"
- get_realtime_precipitation (gee_utils.py) : pluie quasi temps réel (GPM IMERG)
  -> "ce qui se passe maintenant"
- Ce module : "ce qui va se passer" dans les prochains jours
"""
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Seuils par défaut (mm). Peuvent être affinés plus tard par type de sol/culture.
FLOOD_3D_THRESHOLD_MODERATE = 60    # mm cumulés sur 3 jours glissants
FLOOD_3D_THRESHOLD_HIGH = 100
FLOOD_3D_THRESHOLD_CRITICAL = 150

DRY_SPELL_MODERATE_DAYS = 7          # jours consécutifs < 1mm prévus
DRY_SPELL_HIGH_DAYS = 10
DRY_SPELL_CRITICAL_DAYS = 14


def fetch_forecast(lat, lon, forecast_days=16):
    """
    Interroge Open-Meteo pour la prévision journalière de précipitations et
    température sur `forecast_days` jours (max 16) à partir des coordonnées
    du champ (son centroïde).
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": forecast_days,
            "timezone": "auto",
        }
        response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])
        pmax = daily.get("precipitation_probability_max", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])

        days = []
        for i, d in enumerate(dates):
            days.append({
                "date": d,
                "precipitation_mm": precip[i] if i < len(precip) else None,
                "precipitation_probability": pmax[i] if i < len(pmax) else None,
                "t_max": tmax[i] if i < len(tmax) else None,
                "t_min": tmin[i] if i < len(tmin) else None,
            })
        return days

    except Exception as e:
        logger.error(f"Erreur fetch_forecast (Open-Meteo): {e}")
        raise e


def _max_dry_streak(days, threshold_mm=1.0):
    """Plus longue série de jours consécutifs avec pluie prévue < threshold_mm."""
    streak = 0
    best = 0
    for d in days:
        p = d.get("precipitation_mm")
        if p is not None and p < threshold_mm:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def _max_3day_rolling_sum(days):
    """Plus fort cumul de pluie prévu sur une fenêtre glissante de 3 jours."""
    vals = [d.get("precipitation_mm") or 0 for d in days]
    best = 0
    best_start = None
    for i in range(len(vals) - 2):
        window_sum = sum(vals[i:i + 3])
        if window_sum > best:
            best = window_sum
            best_start = days[i]["date"]
    return round(best, 1), best_start


def _classify_flood_forecast(max_3d_sum):
    if max_3d_sum >= FLOOD_3D_THRESHOLD_CRITICAL:
        return "inondation_critique"
    if max_3d_sum >= FLOOD_3D_THRESHOLD_HIGH:
        return "inondation_elevee"
    if max_3d_sum >= FLOOD_3D_THRESHOLD_MODERATE:
        return "inondation_moderee"
    return "normal"


def _classify_drought_forecast(dry_streak_days):
    if dry_streak_days >= DRY_SPELL_CRITICAL_DAYS:
        return "secheresse_severe"
    if dry_streak_days >= DRY_SPELL_HIGH_DAYS:
        return "secheresse_moderee"
    if dry_streak_days >= DRY_SPELL_MODERATE_DAYS:
        return "secheresse_legere"
    return "normal"


def compute_forecast_risk(lat, lon, forecast_days=14):
    """
    Calcule le risque PRÉVISIONNEL (à venir) de sécheresse et d'inondation
    pour une parcelle, à partir de la prévision météo réelle sur `forecast_days`.
    Contrairement à compute_climate_risk (rétrospectif), ceci répond à la
    question "que va-t-il se passer si les conditions prévues se confirment".
    """
    days = fetch_forecast(lat, lon, forecast_days=forecast_days)

    if not days:
        return {
            "forecast_days": forecast_days,
            "flood_forecast": {"level": "inconnu"},
            "drought_forecast": {"level": "inconnu"},
            "daily": [],
        }

    total_precip = round(sum(d.get("precipitation_mm") or 0 for d in days), 1)
    dry_streak = _max_dry_streak(days)
    max_3d_sum, max_3d_start = _max_3day_rolling_sum(days)

    flood_level = _classify_flood_forecast(max_3d_sum)
    drought_level = _classify_drought_forecast(dry_streak)

    return {
        "forecast_days": forecast_days,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "total_precipitation_mm": total_precip,
        "flood_forecast": {
            "level": flood_level,
            "max_3day_cumulative_mm": max_3d_sum,
            "risk_window_start": max_3d_start,
        },
        "drought_forecast": {
            "level": drought_level,
            "max_consecutive_dry_days": dry_streak,
        },
        "daily": days,
    }
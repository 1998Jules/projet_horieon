

# agriculture/gee_utils.py
import ee
import pandas as pd
from datetime import datetime  # <-- IMPORT AJOUTÉ
import os
from django.conf import settings
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)

# Chemin vers le fichier clé du compte de service : variable GEE_SERVICE_ACCOUNT_KEY
# (.env), sinon le fichier historique à la racine du projet. Le chemin est absolu :
# il ne dépend plus du dossier depuis lequel le serveur est lancé.
SERVICE_ACCOUNT_KEY_FILE = os.environ.get('GEE_SERVICE_ACCOUNT_KEY') or os.path.join(
    settings.BASE_DIR, 'ee-koutoumbogajules-c99000ca569e.json')
# Projet Google Cloud enregistré pour Earth Engine (facultatif : sinon celui de la clé)
GEE_PROJECT = os.environ.get('GEE_PROJECT') or None


def initialize_ee():
    """Initialise Earth Engine avec le compte de service"""
    try:
        if os.path.exists(SERVICE_ACCOUNT_KEY_FILE):
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_KEY_FILE,
                scopes=["https://www.googleapis.com/auth/earthengine"]
            )
            ee.Initialize(credentials, project=GEE_PROJECT)
            print("Earth Engine initialisé avec succès via Service Account.")
        else:
            print(f"ERREUR: Le fichier clé '{SERVICE_ACCOUNT_KEY_FILE}' est introuvable.")
            raise FileNotFoundError("Fichier de clé Google Earth Engine manquant")
    except Exception as e:
        print(f"Erreur critique lors de l'initialisation de Google Earth Engine: {e}")
        raise e
 
def geojson_to_ee_geometry(geojson_geometry):
    """
    Convertit proprement un GeoJSON en géométrie Earth Engine
    Gère les cas Polygon et MultiPolygon
    """
    try:
        geom_type = geojson_geometry["type"]
        
        if geom_type == "Polygon":
            # S'assurer que les coordonnées sont au bon format [longitude, latitude]
            coordinates = geojson_geometry["coordinates"]
            return ee.Geometry.Polygon(coordinates)
            
        elif geom_type == "MultiPolygon":
            # Pour MultiPolygon, on prend le premier polygone (le plus grand généralement)
            # Ou on peut fusionner tous les polygones
            coordinates = geojson_geometry["coordinates"]
            
            # Option 1: Prendre le premier polygone (plus simple)
            if len(coordinates) > 0:
                return ee.Geometry.Polygon(coordinates[0])
            
            # Option 2: Fusionner tous les polygones (plus précis mais plus complexe)
            # polygons = [ee.Geometry.Polygon(coords) for coords in coordinates]
            # return ee.Geometry.MultiPolygon(polygons)
            
        elif geom_type == "Point":
            return ee.Geometry.Point(geojson_geometry["coordinates"])
            
        else:
            # Autres types
            return ee.Geometry(geojson_geometry)
            
    except Exception as e:
        logger.error(f"Erreur conversion GeoJSON -> EE: {e}")
        raise e
def geojson_to_ee_geometry(geojson_geometry):
    """
    Convertit GeoJSON en EE Geometry en gérant le nettoyage des coordonnées 3D (x,y,z) -> 2D (x,y).
    """
    try:
        if not isinstance(geojson_geometry, dict):
            raise ValueError("L'entrée n'est pas un dictionnaire")
 
        geom_type = geojson_geometry.get("type")
        coords = geojson_geometry.get("coordinates")
 
        if not geom_type or not coords:
            raise ValueError("GeoJSON invalide")
 
        # FONCTION DE NETTOYAGE : Supprimer la 3ème dimension (Z) si elle existe
        def strip_z(coordinates, g_type):
            if g_type == 'Point':
                # Point: [x, y, z] -> [x, y]
                return [coordinates[0], coordinates[1]]
            
            elif g_type == 'LineString':
                # LineString: [[x, y, z], ...] -> [[x, y], ...]
                # On retourne directement la liste de points nettoyés
                return [[p[0], p[1]] for p in coordinates]
            
            elif g_type == 'Polygon':
                # Polygon: [ [ [x,y,z], ... ], ... ] -> [ [ [x,y], ... ], ... ]
                cleaned_rings = []
                for ring in coordinates:
                    # On nettoie chaque anneau (ring) individuellement
                    cleaned_ring = [[p[0], p[1]] for p in ring]
                    cleaned_rings.append(cleaned_ring)
                return cleaned_rings
            
            elif g_type == 'MultiPolygon':
                # MultiPolygon: Appel récursif pour chaque polygone
                return [strip_z(poly, 'Polygon') for poly in coordinates]
            
            return coordinates
 
        # Appliquer le nettoyage
        clean_coords = strip_z(coords, geom_type)
 
        # Créer l'objet GeoJSON propre (2D)
        clean_geom = {
            "type": geom_type,
            "coordinates": clean_coords
        }
 
        # Créer la géométrie Earth Engine
        geom = ee.Geometry(clean_geom)
        
        return geom
 
    except Exception as e:
        logger.error(f"Erreur conversion GeoJSON -> EE: {e}")
        raise e
def get_monthly_ndvi_series(geojson_geometry, years):
    """
    Calcule la série temporelle NDVI mensuelle pour une zone sur plusieurs années.
    """
    try:
        # Initialiser Earth Engine
        initialize_ee()
        
        # Convertir le GeoJSON en géométrie Earth Engine
        geom = geojson_to_ee_geometry(geojson_geometry)
        
        results = []
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        
        for year in years:
            for month in range(1, 13):
                try:
                    start_date = ee.Date.fromYMD(year, month, 1)
                    end_date = start_date.advance(1, 'month')
                    
                    # Filtrer la collection
                    month_col = collection \
                        .filterDate(start_date, end_date) \
                        .filterBounds(geom) \
                        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
                    
                    # Vérifier s'il y a des images
                    count = month_col.size().getInfo()
                    
                    if count > 0:
                        # Calculer NDVI
                        ndvi_image = month_col.median().normalizedDifference(['B8', 'B4']).rename('NDVI')
                        
                        # Calculer la moyenne sur la zone
                        stats = ndvi_image.reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=geom,
                            scale=100,  # Échelle plus grande pour éviter les timeouts
                            maxPixels=1e9,
                            bestEffort=True
                        )
                        
                        ndvi_value = stats.get('NDVI').getInfo()
                        
                        # Arrondir la valeur
                        if ndvi_value is not None:
                            ndvi_value = round(ndvi_value, 3)
                        else:
                            ndvi_value = 0
                    else:
                        ndvi_value = 0
                    
                    results.append({
                        'year': year,
                        'month': month,
                        'month_name': datetime(year, month, 1).strftime('%b'),  # <-- datetime utilisé ici
                        'ndvi': ndvi_value
                    })
                    
                except Exception as e:
                    logger.error(f"Erreur pour {year}-{month}: {e}")
                    results.append({
                        'year': year,
                        'month': month,
                        'month_name': datetime(year, month, 1).strftime('%b'),  # <-- datetime utilisé ici
                        'ndvi': 0
                    })
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur dans get_monthly_ndvi_series: {e}")
        raise e
# agriculture/gee_utils.py
 
# agriculture/gee_utils.py
 
def get_clipped_ndvi_map(geojson_geometry, year):
    """
    Génère une URL de tuiles (XYZ) NDVI découpée (clipped) pour une zone et une année spécifiques.
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
        
        start_date = ee.Date.fromYMD(int(year), 1, 1)
        end_date = start_date.advance(1, 'year')
        
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterDate(start_date, end_date) \
            .filterBounds(geom) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
        
        # Vérifier s'il y a des images
        count = collection.size().getInfo()
        if count == 0:
             logger.warning(f"Aucune image Sentinel-2 trouvée pour {year}.")
             return None
 
        # Calculer NDVI
        ndvi_image = collection.median().normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Clipper l'image sur la géométrie
        ndvi_clipped = ndvi_image.clip(geom)
        
        vis_params = {
            'min': 0,
            'max': 1,
            'palette': ['a50026', 'd73027', 'f46d43', 'fdae61', 'fee08b', 'd9ef8b', 'a6d96a', '66bd63', '1a9850', '006837']
        }
        
        # 1. Récupérer l'objet MapID
        map_id_dict = ndvi_clipped.getMapId(vis_params)
        
        # 2. CORRECTION ICI : Accéder à l'URL via 'tile_fetcher'
        # L'URL formatée pour Leaflet (avec {z}, {x}, {y}) se trouve ici :
        url = map_id_dict['tile_fetcher'].url_format
        
        return url
        
    except Exception as e:
        logger.error(f"Erreur génération carte clipée: {e}")
        return None
    
# agriculture/gee_utils.py
 
# ... (imports existants) ...
 
def get_ndvi_download_url(geojson_geometry, year):
    """
    Génère une URL de téléchargement pour l'image NDVI clipée (format GeoTIFF).
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
        
        start_date = ee.Date.fromYMD(int(year), 1, 1)
        end_date = start_date.advance(1, 'year')
        
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterDate(start_date, end_date) \
            .filterBounds(geom) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
        
        count = collection.size().getInfo()
        if count == 0:
            return None
 
        ndvi_image = collection.median().normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Clipper l'image
        ndvi_clipped = ndvi_image.clip(geom)
        
        # Générer l'URL de téléchargement
        # scale=100 signifie une résolution de 100m par pixel. 
        # Vous pouvez réduire à 10 ou 20 pour plus de précision, mais le fichier sera plus lourd.
        url = ndvi_clipped.getDownloadURL({
            'scale': 100, 
            'region': geom,
            'format': 'GEO_TIFF',
            'name': f'NDVI_{year}' # Nom du fichier téléchargé
        })
        
        return url
        
    except Exception as e:
        logger.error(f"Erreur génération URL téléchargement: {e}")
        return None
 
 
# agriculture/gee_utils.py
 
# ... (code existant) ...
 
def get_8_day_ndvi_series(geojson_geometry, year):
    """
    Calcule la série temporelle NDVI avec une moyenne sur 8 jours
    en utilisant les données Landsat 8/9 Surface Reflectance.
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
        
        results = []
        
        # Utiliser Landsat 9 (plus récent) avec une fallback sur Landsat 8
        collection = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2") \
            .merge(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2"))
        
        start_date = ee.Date.fromYMD(year, 1, 1)
        end_date = start_date.advance(1, 'year')
        
        # Filtrer la collection pour l'année et la zone
        year_col = collection \
            .filterDate(start_date, end_date) \
            .filterBounds(geom) \
            .filter(ee.Filter.lt('CLOUD_COVER', 50)) # Filtrage des nuages
        
        # Boucler sur l'année par intervalles de 8 jours
        current_date = start_date
        i = 0
        while current_date < end_date:
            period_start = current_date
            period_end = current_date.advance(8, 'day')
            
            # Filtrer les images pour la période de 8 jours
            period_col = year_col.filterDate(period_start, period_end)
            
            # Vérifier s'il y a des images
            count = period_col.size().getInfo()
            
            if count > 0:
                # Calculer la médiane des images de la période pour réduire les nuages
                composite = period_col.median()
                
                # Calculer NDVI. Les bandes pour Landsat sont SR_B5 (NIR) et SR_B4 (Red).
                ndvi_image = composite.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
                
                # Calculer la moyenne sur la zone
                stats = ndvi_image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geom,
                    scale=30,  # Résolution native de Landsat
                    maxPixels=1e9,
                    bestEffort=True
                )
                
                ndvi_value = stats.get('NDVI').getInfo()
                
                if ndvi_value is not None:
                    ndvi_value = round(ndvi_value, 3)
                else:
                    ndvi_value = 0
            else:
                ndvi_value = 0
            
            # Ajouter le résultat
            results.append({
                'date': period_start.format('YYYY-MM-dd').getInfo(), # Date de début de la période
                'ndvi': ndvi_value
            })
            
            # Passer à la période suivante
            current_date = period_end
            i += 1
            if i > 50: # Sécurité pour éviter une boucle infinie
                break
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur dans get_8_day_ndvi_series: {e}")
        raise e
 
def get_8_day_ndvi_map(geojson_geometry, start_date_str):
    """
    Génère une URL de tuiles (XYZ) NDVI pour une période de 8 jours spécifique.
    start_date_str doit être au format 'YYYY-MM-dd'.
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
        
        start_date = ee.Date(start_date_str)
        end_date = start_date.advance(8, 'day')
        
        collection = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2") \
            .merge(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")) \
            .filterDate(start_date, end_date) \
            .filterBounds(geom) \
            .filter(ee.Filter.lt('CLOUD_COVER', 50))
        
        count = collection.size().getInfo()
        if count == 0:
            logger.warning(f"Aucune image Landsat trouvée pour la période du {start_date_str}.")
            return None
 
        # Calculer NDVI
        composite = collection.median()
        ndvi_image = composite.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
        
        # Clipper l'image sur la géométrie
        ndvi_clipped = ndvi_image.clip(geom)
        
        vis_params = {
            'min': 0,
            'max': 1,
            'palette': ['a50026', 'd73027', 'f46d43', 'fdae61', 'fee08b', 'd9ef8b', 'a6d96a', '66bd63', '1a9850', '006837']
        }
        
        map_id_dict = ndvi_clipped.getMapId(vis_params)
        url = map_id_dict['tile_fetcher'].url_format
        
        return url
        
    except Exception as e:
        logger.error(f"Erreur génération carte NDVI 8 jours: {e}")
        return None
 
# agriculture/gee_utils.py
 
# agriculture/gee_utils.py
# agriculture/gee_utils.py
 
# ... (Vos imports existants) ...
 
def mask_s2_clouds(image):
    """Masque les nuages Sentinel-2 avec la classification SCL."""
    # QA60 peut être absent ou trop restrictif selon la période de données.
    # SCL est fourni par COPERNICUS/S2_SR_HARMONIZED et permet d'exclure
    # explicitement ombres, nuages, cirrus et neige/glace.
    scl = image.select('SCL')
    mask = (
        scl.neq(3)    # ombre de nuage
        .And(scl.neq(8))    # nuage moyen
        .And(scl.neq(9))    # nuage fort
        .And(scl.neq(10))   # cirrus
        .And(scl.neq(11))   # neige/glace
    )
    return image.updateMask(mask)
 
def calculate_index(image, index_type):
    """
    Calcule l'indice demandé (NDVI, EVI, NDWI, MSAVI).
    """
    if index_type == 'ndvi':
        return image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    elif index_type == 'evi':
        # EVI = 2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)
        return image.expression(
            '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
            {
                'NIR': image.select('B8'),
                'RED': image.select('B4'),
                'BLUE': image.select('B2')
            }
        ).rename('NDVI')
    elif index_type == 'ndwi':
        # NDWI (Gao) = (GREEN - NIR) / (GREEN + NIR)
        return image.normalizedDifference(['B8', 'B11']).rename('NDVI')
    elif index_type == 'msavi':
        # MSAVI2 simplifié : (2*NIR+1 - sqrt((2*NIR+1)^2 - 8*(NIR-RED))) / 2
        msavi = image.expression(
            '(2 * NIR + 1 - ((2 * NIR + 1) ** 2 - 8 * (NIR - RED)) ** 0.5) / 2',
            {
                'NIR': image.select('B8'),
                'RED': image.select('B4')
            }
        ).rename('NDVI')
        return msavi
    else:
        # Défaut NDVI
        return image.normalizedDifference(['B8', 'B4']).rename('NDVI')
 
def get_field_ndvi_history(geojson_geometry, start_date_str, end_date_str=None, index_type='ndvi'):
    """
    Récupère l'historique image par image, MOYENNÉ PAR JOUR.
    Supporte plusieurs types d'indices (NDVI, EVI, NDWI, MSAVI).
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
        
        # Définir la plage de dates
        start_date = ee.Date(start_date_str)
        if end_date_str:
            end_date = ee.Date(end_date_str)
        else:
            end_date = ee.Date(datetime.now()) 
 
        # Collection Sentinel-2
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterBounds(geom) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
        collection_count = collection.size().getInfo()
        logger.info(
            "NDVI champ: %s images Sentinel-2 entre %s et %s",
            collection_count,
            start_date_str,
            end_date_str or datetime.now().strftime('%Y-%m-%d')
        )
 
        # --- ÉTAPE 1 : RÉCUPÉRER LES DATES UNIQUES ---
        try:
            raw_date_list = collection.aggregate_array('system:time_start').getInfo()
            unique_dates_list = []
            for d in raw_date_list:
                if not d: continue
                try:
                    if isinstance(d, int):
                        dt = datetime.fromtimestamp(d / 1000)
                        date_str = dt.strftime('%Y-%m-%d')
                    else:
                        date_str = str(d)[:10]
                    unique_dates_list.append(date_str)
                except Exception as e:
                    logger.warning(f"Erreur conversion d'une date: {d}")
                    continue
            unique_dates = sorted(list(set(unique_dates_list)), reverse=True)
        except Exception as e:
            logger.error(f"Erreur récupération dates: {e}")
            unique_dates = []
 
        unique_dates = unique_dates[:30] # Limite à 30 jours
        logger.info("NDVI champ: %s dates distinctes à traiter", len(unique_dates))
        
        # Palettes de couleurs pour chaque indice
        vis_params_map = {
            'ndvi': {'min': 0, 'max': 1, 'palette': ['a50026', 'd73027', 'f46d43', 'fdae61', 'fee08b', 'd9ef8b', 'a6d96a', '66bd63', '1a9850', '006837']},
            'evi': {'min': 0, 'max': 2.5, 'palette': ['#000044', '#004433', '#008822', '#00aa44', '#00cc00', '#66ff00', '#ccff00', '#ffe611', '#ffffbe']},
            'ndwi': {'min': -1, 'max': 1, 'palette': ['#a50026', 'd73027', 'f46d43', '#fdae61', '#fee08b', 'd9ef8b', '#a6d96a', '#66bd63', '1a9850', '#006837']},
            'msavi': {'min': 0, 'max': 1, 'palette': ['a50026', 'd73027', 'f46d43', 'fdae61', 'fee08b', 'd9ef8b', 'a6d96a', '#66bd63', '1a9850', '006837']} # Identique à NDVI pour le vert
        }
        
        results = []
        
        # Palette par défaut (au cas où)
        current_vis_params = vis_params_map.get(index_type, vis_params_map['ndvi'])
 
        # --- ÉTAPE 2 : BOUCLE SUR CHAQUE JOUR UNIQUE ---
        for date_str in unique_dates:
            try:
                # Définir la fenêtre temporelle pour ce jour précis
                day_start = ee.Date(date_str)
                day_end = day_start.advance(1, 'day')
                
                # Filtrer la collection pour ne garder que les images de CE jour
                daily_col = collection.filterDate(day_start, day_end)
                
                # --- ÉTAPE 3 : APPLIQUER LE MASQUE DE NUAGES ---
                daily_col_masked = daily_col.map(mask_s2_clouds)
                
                # Vérifier s'il y a des images
                if daily_col_masked.size().getInfo() == 0:
                    continue
 
                # --- ÉTAPE 4 : CALCULER L'INDICE SPÉCIFIQUE ---
                index_image = calculate_index(daily_col_masked.median(), index_type)
 
                # Clipper sur la géométrie
                ndvi_image = index_image.clip(geom) # Note: on garde le nom 'NDVI' pour simplifier, mais la valeur est celle de l'indice choisi
                
                # Statistique moyenne sur le champ
                stats = ndvi_image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geom,
                    scale=10,
                    maxPixels=1e9
                )
                mean_ndvi = stats.get('NDVI').getInfo()
                
                if mean_ndvi is None:
                    continue
 
                # --- ÉTAPE 5 : GÉNÉRER L'URL DE LA CARTE (OPTIONNEL) ---
                # Une erreur de tuilage ne doit pas supprimer la valeur NDVI
                # déjà calculée pour cette date.
                tile_url = None
                try:
                    current_vis_params = vis_params_map.get(
                        index_type, vis_params_map['ndvi']
                    )
                    map_id_dict = ndvi_image.getMapId(current_vis_params)
                    tile_url = map_id_dict['tile_fetcher'].url_format
                except Exception as map_error:
                    logger.warning(
                        "URL tuile NDVI indisponible pour %s: %s",
                        date_str,
                        map_error
                    )

                results.append({
                    'date': date_str,
                    'ndvi': round(float(mean_ndvi), 3), # On garde le nom 'ndvi' pour le frontend (valeur générique de l'indice)
                    'map_url': tile_url
                })
                
            except Exception as e:
                logger.warning(f"Erreur traitement jour {date_str}: {e}")
                continue
 
        results.sort(key=lambda x: x['date'])
        logger.info("NDVI champ: %s résultats produits", len(results))
        return results

    except Exception as e:
        logger.error(f"Erreur get_field_ndvi_history: {e}")
        raise e
 
# agriculture/gee_utils.py
# agriculture/gee_utils.py
# ... (gardez tout le code précédent inchangé jusqu'à calculate_index) ...
 
def get_field_indices_history(geojson_geometry, start_date_str, indices):
    """
    Calcule l'historique pour plusieurs indices (NDVI, EVI, NDWI, MSAVI) en une seule passe.
    Retourne un dict { "ndvi": [{date, value}], "evi": [...], ... }
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
        
        start_date = ee.Date(start_date_str)
        end_date = ee.Date(datetime.now())
        
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterBounds(geom) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
        
        # Obtenir les dates uniques (triées, récentes en premier)
        raw_dates = collection.aggregate_array('system:time_start').getInfo()
        unique_dates = sorted(set(
            datetime.fromtimestamp(d/1000).strftime('%Y-%m-%d')
            for d in raw_dates if d
        ), reverse=True)[:30]  # limite à 30 dates
        
        # Préparer le dictionnaire de résultats
        result = {idx: [] for idx in indices}
        
        for date_str in unique_dates:
            day_start = ee.Date(date_str)
            day_end = day_start.advance(1, 'day')
            daily_col = collection.filterDate(day_start, day_end)
            daily_col_masked = daily_col.map(mask_s2_clouds)
            
            if daily_col_masked.size().getInfo() == 0:
                continue
            
            median_image = daily_col_masked.median()
            
            # Calculer chaque indice sur l'image médiane
            for idx in indices:
                try:
                    index_img = None
                    if idx == 'ndvi':
                        index_img = median_image.normalizedDifference(['B8', 'B4']).rename('INDEX')
                    elif idx == 'evi':
                        # EVI = 2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)
                        nir = median_image.select('B8')
                        red = median_image.select('B4')
                        blue = median_image.select('B2')
                        index_img = nir.expression(
                            '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
                            {
                                'NIR': nir,
                                'RED': red,
                                'BLUE': blue
                            }
                        ).rename('INDEX')
                    elif idx == 'ndwi':
                        # NDWI (Gao) = (GREEN - NIR) / (GREEN + NIR)
                        index_img = median_image.normalizedDifference(['B8', 'B11']).rename('INDEX')
                    elif idx == 'msavi':
                        # MSAVI2 : (2*NIR+1 - sqrt((2*NIR+1)^2 - 8*(NIR-RED))) / 2
                        nir = median_image.select('B8')
                        red = median_image.select('B4')
                        two_nir_plus_one = nir.multiply(2).add(1)
                        sqrt_term = two_nir_plus_one.pow(2).subtract(
                            nir.subtract(red).multiply(8)
                        ).sqrt()
                        index_img = two_nir_plus_one.subtract(sqrt_term).divide(2).rename('INDEX')
                    else:
                        continue
                    
                    if index_img is None:
                        continue
                    
                    # Clipper et réduire
                    clipped = index_img.clip(geom)
                    stats = clipped.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geom,
                        scale=10,
                        maxPixels=1e9
                    )
                    value = stats.get('INDEX').getInfo()
                    if value is not None:
                        result[idx].append({
                            'date': date_str,
                            'value': round(float(value), 3)
                        })
                except Exception as e:
                    logger.warning(f"Erreur pour l'indice {idx} à la date {date_str}: {e}")
                    continue
        
        # Trier chaque série par date croissante
        for idx in indices:
            result[idx].sort(key=lambda x: x['date'])
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur get_field_indices_history: {e}")
        raise e
 
 
# agriculture/gee_utils.py
# ==================== DONNÉES CLIMATIQUES (CHIRPS + ERA5-Land) ====================
# Ajouté pour l'onglet "Temps" : précipitations journalières (CHIRPS) et
# température journalière (ERA5-Land), superposables aux séries d'indices spectraux.
 
def get_chirps_precipitation_series(geojson_geometry, start_date_str, end_date_str=None):
    """
    Récupère la série temporelle journalière des précipitations (mm/jour)
    à partir de CHIRPS Daily (résolution ~5.5 km) sur la zone du champ.
    Une seule requête serveur (map + getInfo) pour éviter des centaines
    d'appels séquentiels à Earth Engine.
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
 
        start_date = ee.Date(start_date_str)
        end_date = ee.Date(end_date_str) if end_date_str else ee.Date(datetime.now().strftime('%Y-%m-%d'))
 
        collection = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
            .filterDate(start_date, end_date) \
            .filterBounds(geom)
 
        def reduce_image(img):
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=5566,  # résolution native CHIRPS
                maxPixels=1e9,
                bestEffort=True
            )
            return ee.Feature(None, {
                'date': img.date().format('YYYY-MM-dd'),
                'precipitation': stats.get('precipitation')
            })
 
        features = collection.map(reduce_image).getInfo().get('features', [])
 
        results = []
        for f in features:
            props = f['properties']
            val = props.get('precipitation')
            results.append({
                'date': props.get('date'),
                'precipitation': round(float(val), 2) if val is not None else 0
            })
 
        results.sort(key=lambda x: x['date'])
        return results
 
    except Exception as e:
        logger.error(f"Erreur get_chirps_precipitation_series: {e}")
        raise e
 
 
def get_era5_temperature_series(geojson_geometry, start_date_str, end_date_str=None):
    """
    Récupère la série temporelle journalière de température (°C) — min, max, moyenne —
    à partir de ERA5-Land Daily Aggregated (résolution ~11 km).
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
 
        start_date = ee.Date(start_date_str)
        end_date = ee.Date(end_date_str) if end_date_str else ee.Date(datetime.now().strftime('%Y-%m-%d'))
 
        collection = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
            .filterDate(start_date, end_date) \
            .filterBounds(geom) \
            .select(['temperature_2m_max', 'temperature_2m_min', 'temperature_2m'])
 
        def reduce_image(img):
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=11132,  # résolution native ERA5-Land
                maxPixels=1e9,
                bestEffort=True
            )
            return ee.Feature(None, {
                'date': img.date().format('YYYY-MM-dd'),
                't_max': stats.get('temperature_2m_max'),
                't_min': stats.get('temperature_2m_min'),
                't_mean': stats.get('temperature_2m'),
            })
 
        features = collection.map(reduce_image).getInfo().get('features', [])
 
        def k_to_c(v):
            return round(float(v) - 273.15, 1) if v is not None else None
 
        results = []
        for f in features:
            props = f['properties']
            results.append({
                'date': props.get('date'),
                't_max': k_to_c(props.get('t_max')),
                't_min': k_to_c(props.get('t_min')),
                't_mean': k_to_c(props.get('t_mean')),
            })
 
        results.sort(key=lambda x: x['date'])
        return results
 
    except Exception as e:
        logger.error(f"Erreur get_era5_temperature_series: {e}")
        raise e
 
 
# ==================== DÉTECTION AUTOMATIQUE SÉCHERESSE / INONDATION ====================
# Indice PNP (Percent of Normal Precipitation) : standard agrométéorologique utilisé
# notamment par FEWS NET pour le suivi de la sécheresse en Afrique. Calculé à partir de
# CHIRPS en comparant le cumul de pluie récent à la climatologie historique (même fenêtre
# calendaire, sur N années précédentes), sur la géométrie du champ ou de la zone.
 
def compute_climate_risk(geojson_geometry, reference_date_str=None, years_history=10):
    """
    Calcule un indicateur de risque sécheresse (PNP 30j/90j) et inondation
    (anomalie de pluie sur 5j) à partir de CHIRPS, pour une géométrie donnée.
 
    Toutes les statistiques (actuelles + historiques) sont regroupées dans un seul
    ee.Dictionary().getInfo() pour limiter les allers-retours client/serveur.
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
 
        ref_date = ee.Date(reference_date_str) if reference_date_str else ee.Date(datetime.now().strftime('%Y-%m-%d'))
        chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
 
        def cumulative_precip(end_date, days):
            start = end_date.advance(-days, 'day')
            filtered = chirps.filterDate(start, end_date).filterBounds(geom)
            # CHIRPS Daily a un délai de publication : pour les fenêtres récentes
            # (ex. les 5 derniers jours), il se peut qu'aucune image ne soit encore
            # disponible. Dans ce cas, ImageCollection.sum() sur une collection vide
            # renvoie une image SANS AUCUNE BANDE, ce qui fait échouer
            # stats.get('precipitation') côté serveur EE ("Dictionary does not
            # contain key"). On force donc une bande 'precipitation' à 0 par défaut
            # pour garantir que la clé existe toujours dans le dictionnaire renvoyé.
            total_img = ee.Image(ee.Algorithms.If(
                filtered.size().gt(0),
                filtered.sum(),
                ee.Image.constant(0).rename('precipitation').clip(geom)
            ))
            stats = total_img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=5566,
                maxPixels=1e9,
                bestEffort=True
            )
            return stats.get('precipitation')
 
        # Cumuls actuels
        current = {
            'c30': cumulative_precip(ref_date, 30),
            'c90': cumulative_precip(ref_date, 90),
            'c5': cumulative_precip(ref_date, 5),
        }
 
        # Climatologie : mêmes fenêtres calendaires, N années précédentes
        hist_30, hist_90, hist_5 = [], [], []
        for y in range(1, years_history + 1):
            past_end = ref_date.advance(-y, 'year')
            hist_30.append(cumulative_precip(past_end, 30))
            hist_90.append(cumulative_precip(past_end, 90))
            hist_5.append(cumulative_precip(past_end, 5))
 
        payload = ee.Dictionary({
            'current': current,
            'hist_30': hist_30,
            'hist_90': hist_90,
            'hist_5': hist_5,
        }).getInfo()
 
        def _pnp(current_val, hist_list):
            valid = [h for h in hist_list if h is not None]
            if not valid or current_val is None:
                return None, None
            mean_hist = sum(valid) / len(valid)
            if mean_hist == 0:
                return None, round(mean_hist, 1)
            return round((current_val / mean_hist) * 100, 1), round(mean_hist, 1)
 
        def _classify_drought(pnp_val):
            if pnp_val is None:
                return 'inconnu'
            if pnp_val < 50:
                return 'secheresse_severe'
            if pnp_val < 75:
                return 'secheresse_moderee'
            if pnp_val < 90:
                return 'secheresse_legere'
            if pnp_val <= 110:
                return 'normal'
            return 'excedentaire'
 
        pnp_30, mean_30 = _pnp(payload['current']['c30'], payload['hist_30'])
        pnp_90, mean_90 = _pnp(payload['current']['c90'], payload['hist_90'])
 
        # Inondation : anomalie standardisée du cumul 5 jours (z-score)
        hist_5_valid = [h for h in payload['hist_5'] if h is not None]
        flood_level = 'inconnu'
        mean_5 = None
        if payload['current']['c5'] is not None and len(hist_5_valid) >= 3:
            mean_5 = sum(hist_5_valid) / len(hist_5_valid)
            variance_5 = sum((x - mean_5) ** 2 for x in hist_5_valid) / len(hist_5_valid)
            std_5 = variance_5 ** 0.5
            flood_level = 'normal'
            if std_5 > 0:
                z_5 = (payload['current']['c5'] - mean_5) / std_5
                if z_5 >= 2.5:
                    flood_level = 'inondation_critique'
                elif z_5 >= 1.5:
                    flood_level = 'inondation_elevee'
                elif z_5 >= 1.0:
                    flood_level = 'inondation_moderee'
 
        return {
            'reference_date': reference_date_str or datetime.now().strftime('%Y-%m-%d'),
            'years_history': years_history,
            'drought_30d': {
                'pnp': pnp_30,
                'classification': _classify_drought(pnp_30),
                'current_mm': round(payload['current']['c30'], 1) if payload['current']['c30'] is not None else None,
                'historical_avg_mm': mean_30
            },
            'drought_90d': {
                'pnp': pnp_90,
                'classification': _classify_drought(pnp_90),
                'current_mm': round(payload['current']['c90'], 1) if payload['current']['c90'] is not None else None,
                'historical_avg_mm': mean_90
            },
            'flood_risk': {
                'level': flood_level,
                'current_5d_mm': round(payload['current']['c5'], 1) if payload['current']['c5'] is not None else None,
                'historical_avg_5d_mm': round(mean_5, 1) if mean_5 is not None else None
            }
        }
 
    except Exception as e:
        logger.error(f"Erreur compute_climate_risk: {e}")
        raise e


def compute_observed_spi_windows(geojson_geometry, reference_date_str=None, years_history=10):
    """Calcule les SPI observés sur 30 et 90 jours avec CHIRPS.

    Les cumuls actuels sont comparés aux mêmes fenêtres calendaires des années
    précédentes, puis transformés par ajustement Gamma vers la loi normale.
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)
        ref_date = ee.Date(reference_date_str or datetime.now().strftime('%Y-%m-%d'))
        chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
        windows = (30, 90)
        requests = {}

        for days in windows:
            current_images = chirps.filterDate(
                ref_date.advance(-days, 'day'), ref_date
            ).filterBounds(geom)
            current_image = ee.Image(ee.Algorithms.If(
                current_images.size().gt(0),
                current_images.sum(),
                ee.Image.constant(0).rename('precipitation')
            ))
            requests[f'current_{days}'] = current_image.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=geom, scale=5566,
                maxPixels=1e9, bestEffort=True
            ).get('precipitation')

            for year_offset in range(1, years_history + 1):
                end_date = ref_date.advance(-year_offset, 'year')
                images = chirps.filterDate(
                    end_date.advance(-days, 'day'), end_date
                ).filterBounds(geom)
                image = ee.Image(ee.Algorithms.If(
                    images.size().gt(0),
                    images.sum(),
                    ee.Image.constant(0).rename('precipitation')
                ))
                requests[f'hist_{days}_{year_offset}'] = image.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=geom, scale=5566,
                    maxPixels=1e9, bestEffort=True
                ).get('precipitation')

        payload = ee.Dictionary(requests).getInfo()
        from scipy.stats import gamma, norm

        output = {}
        for days in windows:
            current = payload.get(f'current_{days}')
            historical = [
                payload.get(f'hist_{days}_{year_offset}')
                for year_offset in range(1, years_history + 1)
            ]
            historical = [float(value) for value in historical if value is not None]
            if current is None or len(historical) < 5:
                output[str(days)] = {
                    'spi': None, 'current_mm': current,
                    'historical_mean_mm': None, 'alert': 'inconnu'
                }
                continue

            positive = [value for value in historical if value > 0]
            if len(positive) < 3:
                spi = None
            else:
                shape, _, scale = gamma.fit(positive, floc=0)
                zero_probability = (len(historical) - len(positive)) / len(historical)
                probability = gamma.cdf(max(float(current), 0), shape, loc=0, scale=scale)
                probability = zero_probability + (1 - zero_probability) * probability
                spi = round(float(norm.ppf(min(max(probability, 1e-6), 1 - 1e-6))), 2)

            if spi is None:
                alert = 'inconnu'
            elif spi <= -2:
                alert = 'secheresse_extreme'
            elif spi <= -1.5:
                alert = 'secheresse_severe'
            elif spi <= -1:
                alert = 'secheresse_moderee'
            elif spi >= 2:
                alert = 'tres_humide'
            elif spi >= 1.5:
                alert = 'humide'
            else:
                alert = 'normal'

            output[str(days)] = {
                'spi': spi,
                'current_mm': round(float(current), 2),
                'historical_mean_mm': round(sum(historical) / len(historical), 2),
                'historical_years': len(historical),
                'alert': alert,
            }
        return output
    except Exception as exc:
        logger.exception('Erreur calcul SPI observé 30/90 jours')
        raise exc

# ==================== PLUIE QUASI TEMPS RÉEL (GPM IMERG) ====================
# CHIRPS a un délai de publication de 2 à 3 jours : inutilisable pour détecter
# une inondation "en cours". GPM IMERG (NASA) publie des données demi-horaires
# avec une latence de quelques heures, ce qui permet un suivi beaucoup plus
# proche du temps réel pour la pluie récente (dernières 24-72h).

def get_realtime_precipitation(geojson_geometry, hours=72):
    """
    Récupère le cumul de pluie quasi temps réel (GPM IMERG, demi-horaire)
    sur la zone, sur les dernières `hours` heures. Retourne le cumul total
    et le cumul des 24 dernières heures, utiles pour une alerte inondation
    immédiate.
    """
    try:
        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)

        now = ee.Date(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        start = now.advance(-hours, 'hour')

        collection = ee.ImageCollection('NASA/GPM_L3/IMERG_V07') \
            .filterDate(start, now) \
            .filterBounds(geom) \
            .select('precipitation')  # mm/h

        def reduce_image(img):
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=11132,
                maxPixels=1e9,
                bestEffort=True
            )
            return ee.Feature(None, {
                'time': img.date().format('YYYY-MM-dd HH:mm'),
                'rate_mm_h': stats.get('precipitation')
            })

        features = collection.map(reduce_image).getInfo().get('features', [])

        slices = []
        for f in features:
            props = f['properties']
            rate = props.get('rate_mm_h')
            if rate is None:
                continue
            slices.append({
                'time': props.get('time'),
                'mm_30min': round(float(rate) * 0.5, 2)
            })

        slices.sort(key=lambda x: x['time'])
        total_mm = round(sum(s['mm_30min'] for s in slices), 1)

        last_24h_cutoff = datetime.utcnow().timestamp() - 24 * 3600
        total_24h = 0.0
        for s in slices:
            try:
                t = datetime.strptime(s['time'], '%Y-%m-%d %H:%M').timestamp()
                if t >= last_24h_cutoff:
                    total_24h += s['mm_30min']
            except Exception:
                continue
        total_24h = round(total_24h, 1)

        return {
            'window_hours': hours,
            'total_mm': total_mm,
            'total_24h_mm': total_24h,
            'nb_observations': len(slices),
            'last_observation': slices[-1]['time'] if slices else None,
            'series': slices,
        }

    except Exception as e:
        logger.error(f"Erreur get_realtime_precipitation: {e}")
        raise e


def classify_realtime_flood(total_24h_mm, total_72h_mm=None):
    """
    Classification simple du risque d'inondation immédiat. Seuils courants
    en Afrique de l'Ouest (50mm/24h, 100mm/72h) — à ajuster selon la zone.
    """
    if total_24h_mm is None:
        return 'inconnu'
    if total_24h_mm >= 100 or (total_72h_mm is not None and total_72h_mm >= 150):
        return 'inondation_critique'
    if total_24h_mm >= 50 or (total_72h_mm is not None and total_72h_mm >= 100):
        return 'inondation_elevee'
    if total_24h_mm >= 25:
        return 'inondation_moderee'
    return 'normal'


# ==================== INDICES DE SÉCHERESSE HISTORIQUE (VCI / TCI / VHI / NCWSI) ====================
# Version 2 — optimisée (cache mémoire + batch getInfo unique).
#
# Sources satellite :
#   - MOD13A2 (16-day NDVI, 1 km)  : bande 'NDVI', scale factor 0.0001
#   - MOD11A2 (8-day LST, 1 km)    : bande 'LST_Day_1km', scale factor 0.02 (K → °C)
#
# Indices implémentés (tous normalisés 0-100, plus haut = meilleure condition végétale) :
#   - VCI    : Vegetation Condition Index = (NDVI - NDVImin) / (NDVImax - NDVImin) * 100
#   - TCI    : Temperature Condition Index = (LSTmax - LST) / (LSTmax - LSTmin) * 100
#   - VHI    : Vegetation Health Index = 0.5 * VCI + 0.5 * TCI
#   - NCWSI  : Normalized Condition Water Stress Index = normalize(NDVI / LST) * 100
#
# Période de référence (min/max) : 2010 → année courante.

import time
import json as _json
import hashlib as _hashlib

DROUGHT_START_YEAR = 2010

_DROUGHT_VIS_PARAMS = {
    'min': 0,
    'max': 100,
    'palette': [
        '#a50026', '#d73027', '#f46d43', '#fdae61', '#fee08b',
        '#d9ef8b', '#a6d96a', '#66bd63', '#1a9850', '#006837'
    ]
}

# --- Cache mémoire (TTL 1h) : évite de recalculer les mêmes indices si l'utilisateur
#     recharge la même zone/années dans l'heure. Énorme gain de performance.
_DROUGHT_CACHE = {}
_DROUGHT_CACHE_TTL = 3600  # 1 heure


def _drought_cache_key(geojson_geometry, years, index_type, kind):
    """Construit une clé de cache stable à partir des paramètres."""
    try:
        geom_str = _json.dumps(geojson_geometry, sort_keys=True)
    except Exception:
        geom_str = str(geojson_geometry)
    years_str = ','.join(str(int(y)) for y in sorted(set(int(y) for y in years)))
    key_str = f"{kind}|{index_type}|{years_str}|{_hashlib.md5(geom_str.encode()).hexdigest()}"
    return key_str


def _drought_cache_get(key):
    if key in _DROUGHT_CACHE:
        ts, val = _DROUGHT_CACHE[key]
        if time.time() - ts < _DROUGHT_CACHE_TTL:
            return val
        del _DROUGHT_CACHE[key]
    return None


def _drought_cache_set(key, value):
    # Limite simple pour éviter une croissance infinie en mémoire
    if len(_DROUGHT_CACHE) > 200:
        # Supprime les 50 plus anciennes entrées
        sorted_keys = sorted(_DROUGHT_CACHE.keys(), key=lambda k: _DROUGHT_CACHE[k][0])
        for k in sorted_keys[:50]:
            del _DROUGHT_CACHE[k]
    _DROUGHT_CACHE[key] = (time.time(), value)


def _load_modis_ndvi_collection(geom, start_year, end_year):
    """Charge MOD13A2 NDVI à l'échelle réelle [0, 1] sur la période donnée."""
    start_date = ee.Date.fromYMD(start_year, 1, 1)
    end_date = ee.Date.fromYMD(end_year, 12, 31)
    return (
        ee.ImageCollection("MODIS/061/MOD13A2")
        .filterDate(start_date, end_date)
        .filterBounds(geom)
        .select('NDVI')
        .map(lambda img: img.multiply(0.0001)
             .copyProperties(img, ['system:time_start', 'system:time_end']))
    )


def _load_modis_lst_collection(geom, start_year, end_year):
    """Charge MOD11A2 LST (jour) en °C sur la période donnée."""
    start_date = ee.Date.fromYMD(start_year, 1, 1)
    end_date = ee.Date.fromYMD(end_year, 12, 31)
    return (
        ee.ImageCollection("MODIS/061/MOD11A2")
        .filterDate(start_date, end_date)
        .filterBounds(geom)
        .select('LST_Day_1km')
        .map(lambda img: img.multiply(0.02).subtract(273.15)
             .copyProperties(img, ['system:time_start', 'system:time_end']))
    )


def _build_drought_image(ndvi_month, lst_month, ndvi_min, ndvi_max,
                         lst_min, lst_max, ncws_min, ncws_max, index_type):
    """Construit l'image mensuelle pour l'indice demandé. Toutes les entrées sont des ee.Image."""
    if index_type == 'vci':
        return ndvi_month.expression(
            '(Ia - Imin) / (Imax - Imin) * 100',
            {'Ia': ndvi_month, 'Imin': ndvi_min, 'Imax': ndvi_max}
        ).rename('INDEX')
    if index_type == 'tci':
        return lst_month.expression(
            '(Imax - Ia) / (Imax - Imin) * 100',
            {'Ia': lst_month, 'Imin': lst_min, 'Imax': lst_max}
        ).rename('INDEX')
    if index_type == 'vhi':
        vci = ndvi_month.expression(
            '(Ia - Imin) / (Imax - Imin) * 100',
            {'Ia': ndvi_month, 'Imin': ndvi_min, 'Imax': ndvi_max}
        )
        tci = lst_month.expression(
            '(Imax - Ia) / (Imax - Imin) * 100',
            {'Ia': lst_month, 'Imin': lst_min, 'Imax': lst_max}
        )
        return vci.multiply(0.5).add(tci.multiply(0.5)).rename('INDEX')
    if index_type == 'ncwsi':
        ncws = ndvi_month.divide(lst_month)
        return ncws.expression(
            '(Ia - Imin) / (Imax - Imin) * 100',
            {'Ia': ncws, 'Imin': ncws_min, 'Imax': ncws_max}
        ).rename('INDEX')
    # Défaut : VCI
    return ndvi_month.expression(
        '(Ia - Imin) / (Imax - Imin) * 100',
        {'Ia': ndvi_month, 'Imin': ndvi_min, 'Imax': ndvi_max}
    ).rename('INDEX')


def _compute_ncws_min_max(geom, ndvi_col, lst_col, ref_start, ref_end):
    """
    Calcule min/max de NCWS = NDVI / LST sur la période de référence.
    Approche approximée : on prend le min/max des composites mensuels NDVI/LST.
    """
    # Composite mensuel moyen sur toute la période de référence
    ndvi_mean = ndvi_col.mean()
    lst_mean = lst_col.mean()
    # NCWS de référence = NDVI moyen / LST moyen
    ncws_ref = ndvi_mean.divide(lst_mean)
    # Pour le min/max on prend les bornes approximées (suffisant pour normaliser)
    ncws_min = ncws_ref.multiply(0.5)
    ncws_max = ncws_ref.multiply(2.0)
    return ncws_min, ncws_max


def get_drought_index_timeseries(geojson_geometry, years, index_type='vhi'):
    """
    Calcule la série mensuelle d'un indice de sécheresse (VCI/TCI/VHI/NCWSI) sur une zone,
    pour les années sélectionnées. La période de référence (min/max) s'étend de
    DROUGHT_START_YEAR (2010) à la dernière année sélectionnée.

    OPTIMISATIONS v2 :
      - 1 seul appel getInfo() au lieu de 12×N (gain ~10× sur le temps de réponse).
      - Cache mémoire Python (TTL 1h) pour les requêtes répétées.
    """
    try:
        # Vérification du cache en premier
        years_int = sorted(set(int(y) for y in years))
        if not years_int:
            return []

        cache_key = _drought_cache_key(geojson_geometry, years_int, index_type, 'ts')
        cached = _drought_cache_get(cache_key)
        if cached is not None:
            logger.info(f"[CACHE HIT] drought timeseries {index_type} years={years_int}")
            return cached

        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)

        ref_end = max(years_int)
        ref_start = DROUGHT_START_YEAR

        # Collections de référence (pour min/max)
        ndvi_col = _load_modis_ndvi_collection(geom, ref_start, ref_end)
        lst_col = _load_modis_lst_collection(geom, ref_start, ref_end)

        ndvi_min = ndvi_col.min()
        ndvi_max = ndvi_col.max()
        lst_min = lst_col.min()
        lst_max = lst_col.max()

        ncws_min, ncws_max = (None, None)
        if index_type == 'ncwsi':
            ncws_min, ncws_max = _compute_ncws_min_max(geom, ndvi_col, lst_col, ref_start, ref_end)

        band_name = 'INDEX'

        # --- Construction d'une FeatureCollection (côté serveur) ---
        # Chaque feature contient year, month, et la valeur moyenne de l'indice.
        # Cela permet un SEUL getInfo() pour récupérer TOUTES les valeurs mensuelles.
        def _build_monthly_feature(year_month):
            year, month = year_month
            start = ee.Date.fromYMD(year, month, 1)
            end = start.advance(1, 'month')

            ndvi_month = ndvi_col.filterDate(start, end).mean()
            lst_month = lst_col.filterDate(start, end).mean()

            img = _build_drought_image(
                ndvi_month, lst_month,
                ndvi_min, ndvi_max, lst_min, lst_max,
                ncws_min, ncws_max, index_type
            ).clip(geom)

            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=1000,  # MODIS natif ~1 km
                maxPixels=1e9,
                bestEffort=True
            )
            return ee.Feature(None, {
                'year': year,
                'month': month,
                'value': stats.get(band_name)
            })

        # Liste des (year, month) à calculer — UNIQUEMENT les années sélectionnées
        year_months = [(y, m) for y in years_int for m in range(1, 13)]

        # Construire la FeatureCollection côté serveur
        features_list = [_build_monthly_feature(ym) for ym in year_months]
        fc = ee.FeatureCollection(features_list)

        # UN SEUL appel getInfo() pour récupérer toutes les valeurs
        features_info = fc.getInfo()

        # Parser côté Python
        results = []
        for f in features_info.get('features', []):
            props = f.get('properties', {})
            val = props.get('value')
            year = props.get('year')
            month = props.get('month')
            if val is None:
                val = 0
            else:
                val = round(float(val), 2)
            try:
                month_name = datetime(year, month, 1).strftime('%b')
            except Exception:
                month_name = str(month)
            results.append({
                'year': year,
                'month': month,
                'month_name': month_name,
                'value': val
            })

        # Trier par year puis month
        results.sort(key=lambda r: (r['year'], r['month']))

        # Mettre en cache
        _drought_cache_set(cache_key, results)
        logger.info(f"[CACHE SET] drought timeseries {index_type} years={years_int} ({len(results)} points)")

        return results

    except Exception as e:
        logger.error(f"Erreur get_drought_index_timeseries: {e}")
        raise e


def get_drought_index_map_url(geojson_geometry, year, index_type='vhi'):
    """
    Génère une URL de tuiles XYZ pour la carte d'un indice de sécheresse, sur une année donnée
    (moyenne annuelle). Utilise un cache mémoire pour les requêtes répétées.
    """
    try:
        year = int(year)
        cache_key = _drought_cache_key(geojson_geometry, [year], index_type, 'map')
        cached = _drought_cache_get(cache_key)
        if cached is not None:
            return cached

        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)

        ndvi_col = _load_modis_ndvi_collection(geom, DROUGHT_START_YEAR, max(year, DROUGHT_START_YEAR))
        lst_col = _load_modis_lst_collection(geom, DROUGHT_START_YEAR, max(year, DROUGHT_START_YEAR))

        ndvi_min = ndvi_col.min()
        ndvi_max = ndvi_col.max()
        lst_min = lst_col.min()
        lst_max = lst_col.max()
        ncws_min, ncws_max = (None, None)
        if index_type == 'ncwsi':
            ncws_min, ncws_max = _compute_ncws_min_max(geom, ndvi_col, lst_col, DROUGHT_START_YEAR, year)

        start = ee.Date.fromYMD(year, 1, 1)
        end = start.advance(1, 'year')
        ndvi_year = ndvi_col.filterDate(start, end).mean()
        lst_year = lst_col.filterDate(start, end).mean()

        yearly_img = _build_drought_image(
            ndvi_year, lst_year,
            ndvi_min, ndvi_max, lst_min, lst_max,
            ncws_min, ncws_max, index_type
        ).clip(geom)

        map_id_dict = yearly_img.getMapId(_DROUGHT_VIS_PARAMS)
        url = map_id_dict['tile_fetcher'].url_format
        _drought_cache_set(cache_key, url)
        return url

    except Exception as e:
        logger.error(f"Erreur génération carte drought: {e}")
        return None


def get_drought_index_download_url(geojson_geometry, year, index_type='vhi'):
    """
    Génère une URL de téléchargement GeoTIFF pour la carte annuelle d'un indice de sécheresse.
    Utilise un cache mémoire pour les requêtes répétées.
    """
    try:
        year = int(year)
        cache_key = _drought_cache_key(geojson_geometry, [year], index_type, 'dl')
        cached = _drought_cache_get(cache_key)
        if cached is not None:
            return cached

        initialize_ee()
        geom = geojson_to_ee_geometry(geojson_geometry)

        ndvi_col = _load_modis_ndvi_collection(geom, DROUGHT_START_YEAR, max(year, DROUGHT_START_YEAR))
        lst_col = _load_modis_lst_collection(geom, DROUGHT_START_YEAR, max(year, DROUGHT_START_YEAR))

        ndvi_min = ndvi_col.min()
        ndvi_max = ndvi_col.max()
        lst_min = lst_col.min()
        lst_max = lst_col.max()
        ncws_min, ncws_max = (None, None)
        if index_type == 'ncwsi':
            ncws_min, ncws_max = _compute_ncws_min_max(geom, ndvi_col, lst_col, DROUGHT_START_YEAR, year)

        start = ee.Date.fromYMD(year, 1, 1)
        end = start.advance(1, 'year')
        ndvi_year = ndvi_col.filterDate(start, end).mean()
        lst_year = lst_col.filterDate(start, end).mean()

        yearly_img = _build_drought_image(
            ndvi_year, lst_year,
            ndvi_min, ndvi_max, lst_min, lst_max,
            ncws_min, ncws_max, index_type
        ).clip(geom)

        url = yearly_img.getDownloadURL({
            'scale': 1000,
            'region': geom,
            'format': 'GEO_TIFF',
            'name': f'{index_type.upper()}_{year}'
        })
        _drought_cache_set(cache_key, url)
        return url

    except Exception as e:
        logger.error(f"Erreur génération URL téléchargement drought: {e}")
        return None


def clear_drought_cache():
    """Vide le cache mémoire des indices de sécheresse (utile en cas de mise à jour des données)."""
    global _DROUGHT_CACHE
    _DROUGHT_CACHE.clear()
    logger.info("Cache drought vidé.")

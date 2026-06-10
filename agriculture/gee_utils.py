# agriculture/gee_utils.py
import ee
import pandas as pd
from datetime import datetime  # <-- IMPORT AJOUTÉ
import os
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)

# Chemin vers votre fichier clé


def initialize_ee():
    """Initialise Earth Engine avec le compte de service"""
    try:
        if os.path.exists(SERVICE_ACCOUNT_KEY_FILE):
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_KEY_FILE,
                scopes=["https://www.googleapis.com/auth/earthengine"]
            )
            ee.Initialize(credentials)
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
    """Masque les nuages et les cirrus d'une image Sentinel-2 en utilisant la bande QA60."""
    # (Votre code existant pour mask_s2_clouds ici...)
    qa = image.select('QA60')
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
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

                # --- ÉTAPE 5 : GÉNÉRER L'URL DE LA CARTE ---
                # Utiliser la palette de l'indice sélectionné
                current_vis_params = vis_params_map[index_type]
                
                map_id_dict = ndvi_image.getMapId(current_vis_params)
                tile_url = map_id_dict['tile_fetcher'].url_format
                
                results.append({
                    'date': date_str,
                    'ndvi': round(float(mean_ndvi), 3), # On garde le nom 'ndvi' pour le frontend (valeur générique de l'indice)
                    'map_url': tile_url
                })
                
            except Exception as e:
                logger.warning(f"Erreur traitement jour {date_str}: {e}")
                continue

        results.sort(key=lambda x: x['date'])
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
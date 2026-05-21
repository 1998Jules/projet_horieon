# agriculture/views.py
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import CropCalendar # Ajoutez cet import

import logging
from datetime import datetime  # <-- IMPORT AJOUTÉ ICI AUSSI
from .models import Prefecture, Region, Commune
from .gee_utils import get_monthly_ndvi_series, get_clipped_ndvi_map, get_ndvi_download_url,   get_field_ndvi_history  
from django.contrib.gis.geos import GEOSException
import json
from django.contrib.gis.geos import GEOSGeometry
logger = logging.getLogger(__name__)

# --- Pages HTML ---
def index(request):
    return render(request, 'agriculture/index.html')

# --- Vues GeoJSON ---
def region_geojson(request):
    qs = Region.objects.all()
    data = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('id', 'region')  # <--- AJOUTEZ 'id' ici
    )
    return HttpResponse(data, content_type='application/json')

def prefecture_geojson(request):
    qs = Prefecture.objects.all()
    data = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('id', 'prefecture')  # <--- AJOUTEZ 'id' ici
    )
    return HttpResponse(data, content_type='application/json')

def commune_geojson(request):
    qs = Commune.objects.all()
    data = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('id', 'commune', 'prefecture')  # <--- AJOUTEZ 'id' ici
    )
    return HttpResponse(data, content_type='application/json')
# --- Vues Google Earth Engine ---
@csrf_exempt
@require_http_methods(["GET"])
def ndvi_tiles(request):
    """Endpoint pour récupérer les URLs des tuiles NDVI par année."""
    try:
        data = {
            "2020": "https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/e80515e7935e428995eed8d9639bb7b0-f68e9452f721b60623c2fb0a67cfffa0/tiles/{z}/{x}/{y}",
            "2021": "https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/f29d971275e57f5d9ad695288672cf43-bceee7cdbbab5ebc9fdc26f2f9c05727/tiles/{z}/{x}/{y}",
            "2022": "https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/fe5ed7a8af1492554b15a7f6424c46df-d158c990443df253c1032fc7eca01fc1/tiles/{z}/{x}/{y}",
            "2023": "https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/a50bbbabe1020ff731b745da2c16a91d-e0a57815954ea12b36cc83b57ac97e0c/tiles/{z}/{x}/{y}",
            "2024": "https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/9c2051f2574302c4c54b0e60395dd160-db702ea520ed9daf3cf36e28af4c45fe/tiles/{z}/{x}/{y}",
            "2025": "https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/4fe19eda2271f2ebb6570778a3366808-1c500463cf001a57b36a65a177cbe135/tiles/{z}/{x}/{y}",
            "2026": "https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/88d49145525d5c81fbfa7f7c1c9f1c0c-af755efbe6ca0831aa1457a0cf0c6bf1/tiles/{z}/{x}/{y}",

        }
        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Erreur ndvi_tiles: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ndvi_timeseries(request):
    """
    Endpoint pour récupérer les séries temporelles NDVI
    """
    logger.info("--- NOUVELLE REQUÊTE NDVI TIMESERIES ---")
    
    try:
        # 1. Lecture du JSON
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON: {e}")
            return JsonResponse({
                "success": False, 
                "error": "Format JSON invalide"
            }, status=400)
        
        zone_type = data.get('zone_type')
        zone_id = data.get('zone_id')
        years = data.get('years', [])
        
        logger.info(f"Type: {zone_type}, ID: {zone_id}, Années: {years}")
        
        if not zone_type or not zone_id or not years:
            return JsonResponse({
                "success": False, 
                "error": "Paramètres manquants (zone_type, zone_id, years)"
            }, status=400)
        
        # 2. Récupération de l'objet géographique
        try:
            if zone_type == 'region':
                geo_model = Region.objects.get(id=zone_id)
            elif zone_type == 'prefecture':
                geo_model = Prefecture.objects.get(id=zone_id)
            elif zone_type == 'commune':
                geo_model = Commune.objects.get(id=zone_id)
            else:
                return JsonResponse({
                    "success": False, 
                    "error": f"Type de zone inconnu: {zone_type}"
                }, status=400)
                
            logger.info(f"Objet trouvé: {geo_model}")
            
        except Region.DoesNotExist:
            return JsonResponse({"success": False, "error": "Région introuvable"}, status=404)
        except Prefecture.DoesNotExist:
            return JsonResponse({"success": False, "error": "Préfecture introuvable"}, status=404)
        except Commune.DoesNotExist:
            return JsonResponse({"success": False, "error": "Commune introuvable"}, status=404)
        except Exception as e:
            logger.error(f"Erreur base de données: {e}")
            return JsonResponse({"success": False, "error": "Erreur d'accès à la base"}, status=500)
        
        # 3. Transformation de la géométrie
        try:
            # Transformer en WGS84 (EPSG:4326)
            geom_wgs84 = geo_model.geom.transform(4326, clone=True)
            
            # Nettoyer la géométrie (buffer 0)
            geom_wgs84 = geom_wgs84.buffer(0)
            
            # Convertir en GeoJSON
            geojson_str = geom_wgs84.geojson
            geojson = json.loads(geojson_str)
            
            # Simplifier la géométrie pour GEE (optionnel)
            # Si la géométrie est trop complexe, on peut la simplifier
            if hasattr(geom_wgs84, 'num_coords') and geom_wgs84.num_coords > 1000:  # Si plus de 1000 points
                simplified = geom_wgs84.simplify(tolerance=0.001, preserve_topology=True)
                geojson = json.loads(simplified.geojson)
            
            logger.info(f"Type de géométrie: {geojson['type']}")
            
        except Exception as e:
            logger.error(f"Erreur transformation géométrie: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                "success": False, 
                "error": f"Erreur de traitement de la géométrie: {str(e)}"
            }, status=500)
        
        # 4. Appel à Earth Engine
                # 4. Appel à Earth Engine
        try:
            logger.info("Appel à get_monthly_ndvi_series...")
            
            # A. Récupérer les données de la courbe (Timeseries) - C'est prioritaire
            timeseries_data = get_monthly_ndvi_series(geojson, years)
            
            # B. Essayer de générer l'image clipée (Map) - C'est "optionnel"
            # On isole ceci dans un try/except séparé pour éviter de planter tout si ça échoue
            clipped_map_url = None
            map_year = years[-1] if years else 2024
            
            try:
                clipped_map_url = get_clipped_ndvi_map(geojson, map_year)
            except Exception as map_error:
                logger.warning(f"Impossible de générer la carte clipée (GEE Error): {map_error}")
            
            download_url = None 
            try:
                download_url = get_ndvi_download_url(geojson, map_year)
            except Exception as dl_error:
                logger.warning(f"Erreur génération téléchargement: {dl_error}")
            
                # On continue, clipped_map_url reste None
            
            logger.info(f"Données GEE reçues: {len(timeseries_data)} points")
            
            return JsonResponse({
                "success": True,
                "data": timeseries_data,
                "map_url": clipped_map_url, # Sera None si erreur
                "map_year": map_year,
                "download_url": download_url 
            })
            
        except Exception as e:
            logger.error(f"Erreur GEE critique (Timeseries): {e}")
            import traceback
            traceback.print_exc()
            
            return JsonResponse({
                "success": False,
                "error": f"Erreur de calcul Google Earth Engine: {str(e)}"
            }, status=500)
            logger.error(f"Erreur GEE: {e}")
            import traceback
            traceback.print_exc()
            
            # En cas d'erreur GEE, renvoyer des données mock pour le développement
            # À supprimer en production
            
            
    except Exception as e:
        logger.error(f"Erreur globale: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
    

# agriculture/views.py
from .models import Champ, Region, Prefecture, Commune # Ajoutez Champ
from django.core.serializers import serialize
from .gee_utils import get_field_ndvi_history # Importez la nouvelle fonction

# --- Vue pour lister les GeoJSON des champs (pour la carte) ---
def champs_geojson(request):
    qs = Champ.objects.all()
    data = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('id', 'nom', 'type_culture', 'proprietaire')
    )
    return HttpResponse(data, content_type='application/json')

# --- Vue API pour créer un champ (Simplifiée pour l'exemple) ---
@csrf_exempt
def create_champ(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Charger les données JSON
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
    
    # Validation des champs
    nom = data.get('nom')
    date_semi = data.get('date_semi')
    geom_data = data.get('geom')
    
    if not nom:
        return JsonResponse({'success': False, 'error': 'Nom requis'}, status=400)
    if not date_semi:
        return JsonResponse({'success': False, 'error': 'Date de semis requise'}, status=400)
    if not geom_data:
        return JsonResponse({'success': False, 'error': 'Géométrie requise'}, status=400)
    
    # Convertir la géométrie
    try:
        from django.contrib.gis.geos import GEOSGeometry
        # Si le geom_data est un Feature ou FeatureCollection, extraire la geometry
        if geom_data.get('type') == 'Feature':
            geom_data = geom_data['geometry']
        elif geom_data.get('type') == 'FeatureCollection' and geom_data.get('features'):
            geom_data = geom_data['features'][0]['geometry']
        
        geojson_str = json.dumps(geom_data)
        geom = GEOSGeometry(geojson_str)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Géométrie invalide: {str(e)}'}, status=400)
    
    # Création du champ
    try:
        champ = Champ.objects.create(
            nom=nom,
            proprietaire=data.get('proprietaire', ''),
            type_culture=data.get('type_culture', ''),
            date_semi=date_semi,
            geom=geom
        )
        return JsonResponse({'success': True, 'id': champ.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erreur base: {str(e)}'}, status=500)
# --- Nouvelle Vue NDVI pour un Champ Spécifique ---
@csrf_exempt
# agriculture/views.py
# ... (Vos imports existants) ...

# --- Nouvelle Vue NDVI pour un Champ Spécifique ---
@csrf_exempt
def field_ndvi_timeseries(request):
    """
    Endpoint spécifique pour un Champ (ID).
    Retourne l'historique image par image.
    Accepte un paramètre 'index_type' (ndvi, evi, ndwi, msavi).
    Gère le cas où la date de semis est vide.
    """
    logger.info("--- REQUÊTE NDVI CHAMP ---")
    try:
        data = json.loads(request.body)
        champ_id = data.get('champ_id')
        
        # --- NOUVEAU : RÉCUPÉRATION DU TYPE D'INDICE ---
        index_type = data.get('index_type', 'ndvi') # Par défaut NDVI

        if not champ_id:
            return JsonResponse({'success': False, 'error': 'ID champ manquant'}, status=400)

        try:
            champ = Champ.objects.get(id=champ_id)
        except Champ.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Champ introuvable'}, status=404)

        # --- GESTION DE LA DATE DE SEMIS VIDE ---
        if champ.date_semi:
            start_date = champ.date_semi.strftime('%Y-%m-%d')
            logger.info(f"Champ {champ_id} - Date de semis trouvée : {start_date} - Indice: {index_type}")
        else:
            from datetime import timedelta # Assurez l'import est en haut
            one_year_ago = datetime.now() - timedelta(days=365)
            start_date = one_year_ago.strftime('%Y-%m-%d')
            logger.warning(f"Champ {champ_id} - Date de semis vide. Utilisation date par défaut (1 an avant aujourd'hui) : {start_date}")
        
        # Transformation géométrie
        geom_wgs84 = champ.geom.transform(4326, clone=True)
        geom_wgs84 = geom_wgs84.buffer(0)
        geojson_str = geom_wgs84.geojson
        geojson = json.loads(geojson_str)

        # Appel GEE avec le paramètre index_type
        timeseries_data = get_field_ndvi_history(geojson, start_date, index_type=index_type)
        
        return JsonResponse({
            "success": True,
            "data": timeseries_data,
            "index_type": index_type # Renvoyer le type pour que le frontend sache quelle palette utiliser
        })

    except Exception as e:
        logger.error(f"Erreur field_ndvi: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    


    # agriculture/views.py

from .gee_utils import get_field_indices_history  # à créer plus bas

@csrf_exempt
def field_indices_comparison(request):
    """
    Endpoint pour comparer plusieurs indices spectraux pour un champ.
    Body JSON : { "champ_id": 1, "indices": ["ndvi", "evi", "ndwi"] }
    Retourne : { "success": True, "data": { "ndvi": [...], "evi": [...] } }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
    
    champ_id = data.get('champ_id')
    indices = data.get('indices', [])
    
    if not champ_id:
        return JsonResponse({'success': False, 'error': 'ID champ manquant'}, status=400)
    
    if not indices:
        return JsonResponse({'success': False, 'error': 'Aucun indice demandé'}, status=400)
    
    try:
        champ = Champ.objects.get(id=champ_id)
    except Champ.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Champ introuvable'}, status=404)
    
    # Gestion de la date de semis
    from datetime import timedelta
    if champ.date_semi:
        start_date = champ.date_semi.strftime('%Y-%m-%d')
    else:
        one_year_ago = datetime.now() - timedelta(days=365)
        start_date = one_year_ago.strftime('%Y-%m-%d')
    
    # Transformation géométrie
    geom_wgs84 = champ.geom.transform(4326, clone=True)
    geom_wgs84 = geom_wgs84.buffer(0)
    geojson = json.loads(geom_wgs84.geojson)
    
    # Appel à la nouvelle fonction utilitaire
    result = get_field_indices_history(geojson, start_date, indices)
    
    return JsonResponse({
        "success": True,
        "data": result
    })



# ... imports existants ...
from django.views.decorators.http import require_http_methods

# ... Vos autres vues ...

# MISE À JOUR : Inclure variety et duration_days
@csrf_exempt
@require_http_methods(["GET"])
def get_crop_calendar(request):
    try:
        items = CropCalendar.objects.all().order_by('name', 'variety')
        data = list(items.values(
            'id', 'name', 'variety', 'crop_type', 'duration_days', # Ajoutés
            'sowing_start', 'sowing_end',
            'weeding_start', 'weeding_end',
            'harvest_start', 'harvest_end',
            'other_activities'
        ))
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# MISE À JOUR : Ajout/Create
@csrf_exempt
@require_http_methods(["POST"])
def add_crop_calendar(request):
    try:
        data = json.loads(request.body)
        item = CropCalendar.objects.create(
            name=data['name'],
            variety=data.get('variety', ''), # Nouveau
            crop_type=data['crop_type'],
            duration_days=data.get('duration_days', 90), # Nouveau
            sowing_start=data['sowing_start'],
            sowing_end=data['sowing_end'],
            weeding_start=data['weeding_start'],
            weeding_end=data['weeding_end'],
            harvest_start=data['harvest_start'],
            harvest_end=data['harvest_end'],
            other_activities=data.get('other_activities', '')
        )
        return JsonResponse({'success': True, 'id': item.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# MISE À JOUR : Update
@csrf_exempt
@require_http_methods(["POST"])
def update_crop_calendar(request, pk):
    try:
        data = json.loads(request.body)
        item = CropCalendar.objects.get(pk=pk)
        item.name = data.get('name', item.name)
        item.variety = data.get('variety', item.variety) # Nouveau
        item.crop_type = data.get('crop_type', item.crop_type)
        item.duration_days = data.get('duration_days', item.duration_days) # Nouveau
        # ... autres champs ...
        item.sowing_start = data.get('sowing_start', item.sowing_start)
        item.sowing_end = data.get('sowing_end', item.sowing_end)
        item.weeding_start = data.get('weeding_start', item.weeding_start)
        item.weeding_end = data.get('weeding_end', item.weeding_end)
        item.harvest_start = data.get('harvest_start', item.harvest_start)
        item.harvest_end = data.get('harvest_end', item.harvest_end)
        item.other_activities = data.get('other_activities', item.other_activities)
        item.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# NOUVELLE VUE : Simulation
@csrf_exempt
@require_http_methods(["POST"])
def simulate_growth(request):
    """
    Simule la croissance basée sur le calendrier sélectionné et le jour actuel.
    """
    try:
        data = json.loads(request.body)
        calendar_id = data.get('calendar_id')
        current_day = int(data.get('day', 0))

        if not calendar_id:
            return JsonResponse({'success': False, 'error': 'ID Calendrier manquant'}, status=400)

        item = CropCalendar.objects.get(id=calendar_id)
        duration = item.duration_days if item.duration_days else 90
        
        # Calcul du pourcentage de progression
        progress = min(100, (current_day / duration) * 100)
        
        # Définition des étapes phénologiques (simplifiées)
        stage = ""
        actions = []
        icon = "🌱"

        if progress < 10:
            stage = "Germination / Levée"
            icon = "🌱"
            actions = [
                "Surveiller l'humidité du sol",
                "Protéger contre les oiseaux et rongeurs",
                "Vérifier la levée uniforme"
            ]
        elif progress < 30:
            stage = "Croissance Végétative (Début)"
            icon = "🌿"
            actions = [
                "Effectuer le premier désherbage",
                "Apporter une fertilisation de fond (si non fait)",
                "Surveiller les maladies de jeunes plants"
            ]
        elif progress < 60:
            stage = "Croissance Végétative (Pleine phase)"
            icon = "🪴"
            actions = [
                "Deuxième désherbage (sarclage)",
                "Application d'engrais (couverture)",
                "Lutte contre les ravageurs (chenilles, etc.)"
            ]
        elif progress < 80:
            stage = "Floraison / Fructification"
            icon = "🌸"
            actions = [
                "Régulation de l'eau (stress hydrique à éviter)",
                "Surveillance des maladies fongiques (mildiou, rouille)",
                "Apport de potasse si nécessaire"
            ]
        elif progress < 100:
            stage = "Maturation"
            icon = "🌾"
            actions = [
                "Arrêt progressif de l'irrigation",
                "Préparation du matériel de récolte",
                "Surveillance des prédateurs de grains/fruits"
            ]
        else:
            stage = "Récolte"
            icon = " baskets" # Emoji cueillette
            actions = [
                "Récolter au moment optimal",
                "Séchage et tri de la récolte",
                "Stockage dans des conditions appropriées"
            ]

        return JsonResponse({
            'success': True,
            'data': {
                'crop_name': f"{item.name} ({item.variety})",
                'current_day': current_day,
                'total_days': duration,
                'progress': round(progress, 1),
                'stage': stage,
                'icon': icon,
                'actions': actions
            }
        })

    except CropCalendar.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Culture introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def delete_crop_calendar(request, pk):
    """Supprime une entrée du calendrier"""
    try:
        # On cherche l'élément par sa clé primaire (pk)
        item = CropCalendar.objects.get(pk=pk)
        item.delete()
        return JsonResponse({'success': True})
    except CropCalendar.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Culture introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
from django.shortcuts import render
import json
from django.http import JsonResponse
from django.core.serializers import serialize



from django.http import JsonResponse
from django.core.serializers import serialize

def index(request):
    return render(request, 'index.html')

from django.http import HttpResponse, JsonResponse
from django.core.serializers import serialize
from .models import  Cantons, Commune,routes,lycee,college,jardin,pea,marche,bornefontaine,chateau,hopitale,terrain,coperative,magazinbl2



def cantons_geojson(request):
    qs = Cantons.objects.all()
    geojson = serialize('geojson', qs, geometry_field='geom', fields=('canton','code_canto','prefecture','code_prefe','region','code_regio'))
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')





def commune_geojson(request):
    qs = Commune.objects.all()
    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('commune','code_commu','region','code_regio','prefecture','code_prefe')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')


def route_geojson(request):
    qs = routes.objects.all()
    geojson = serialize('geojson', qs, geometry_field='geom', fields=('route_clas','route_type','route_clas','route_reco','route_nom'))
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')

def lycee_geojson(request):
    qs = lycee.objects.all()
    geojson = serialize(
        'geojson', qs, geometry_field='geom',
        fields=('canton_nom','nom_locali','etablissem','ouverture','etabliss_1','terrain','inspection')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')


def college_geojson(request):
    qs = college.objects.all()
    geojson = serialize(
        'geojson', qs, geometry_field='geom',
        fields=('canton_nom','nom_locali','etablissem','ouverture','etabliss_1','terrain','inspection')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')


def jardin_geojson(request):
    qs = jardin.objects.all()
    geojson = serialize(
        'geojson', qs, geometry_field='geom',
        fields=('canton_nom','nom_locali','etablissem','ouverture','etabliss_1','terrain','inspection')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')


def pea_geojson(request):
    qs = pea.objects.exclude(geom__isnull=True)
    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','forage_nom','forage_typ','batiment_n')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')
from django.core.serializers import serialize
from django.http import JsonResponse, HttpResponse
import json
from .models import marche


def marche_geojson(request):
    qs =marche.objects.exclude(geom__isnull=True)
    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','marche_nom','jour')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')



def borne_geojson(request):
    qs =bornefontaine.objects.exclude(geom__isnull=True)
    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','borne_font')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')


def chateau_geojson(request):
    qs = chateau.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','chateau_no','organisme')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')




def terrain_geojson(request):
    qs =terrain.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','terrain','terrain_sp')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')



def hopital_geojson(request):
    qs = hopitale.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','nom_fs','ouverture','secteur','services_p')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')



def cooperative_geojson(request):
    qs = coperative.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','cooperativ','cooperat_1')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')




def magazin_geojson(request):
    qs = magazinbl2.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','etab_nom','ouverture','organisme')
    )
    return HttpResponse(geojson, content_type='application/json; charset=utf-8')

# pour construrure l'api 



# geoportail/views.py
import json
from django.http import JsonResponse
from django.contrib.gis.db.models.functions import AsGeoJSON
from .models import (
    Cantons, Commune, routes, marche, jardin, college, lycee, pea,
    bornefontaine, chateau, hopitale, terrain, coperative, magazinbl2
)

def get_all_layers(request):
    """Retourne toutes les couches SIG en GeoJSON"""

    layers = {}

    # ------------------ Cantons ------------------
    cantons_qs = Cantons.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['cantons'] = {
        "name": "Cantons",
        "visible": True,
        "opacity": 0.6,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(c.geom_json),
                    "properties": {
                        "gid": c.gid,
                        "canton": c.canton,
                        "prefecture": c.prefecture,
                        "region": c.region,
                        "code_canto": c.code_canto
                    }
                } for c in cantons_qs
            ]
        }
    }

    # ------------------ Communes ------------------
    communes_qs = Commune.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['communes'] = {
        "name": "Communes",
        "visible": True,
        "opacity": 0.5,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(c.geom_json),
                    "properties": {
                        "commune": c.commune,
                        "prefecture": c.prefecture,
                        "region": c.region,
                        "code_commu": c.code_commu
                    }
                } for c in communes_qs
            ]
        }
    }

    # ------------------ Routes ------------------
    routes_qs = routes.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['routes'] = {
        "name": "Routes",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(r.geom_json),
                    "properties": {
                        "id": r.id,
                        "route_nom": r.route_nom,
                        "route_type": r.route_type
                    }
                } for r in routes_qs
            ]
        }
    }

    # ------------------ Marchés ------------------
    marches_qs = marche.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['marches'] = {
        "name": "Marchés",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(m.geom_json),
                    "properties": {
                        "marche_nom": m.marche_nom,
                        "canton": m.canton_nom,
                        "jour": m.jour
                    }
                } for m in marches_qs
            ]
        }
    }

    # ------------------ Jardins ------------------
    jardins_qs = jardin.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['jardins'] = {
        "name": "Jardins",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(j.geom_json),
                    "properties": {
                        "nom_locali": j.nom_locali,
                        "etablissem": j.etablissem,
                        "canton": j.canton_nom
                    }
                } for j in jardins_qs
            ]
        }
    }

    # ------------------ Collèges ------------------
    colleges_qs = college.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['colleges'] = {
        "name": "Collèges",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(c.geom_json),
                    "properties": {
                        "nom_locali": c.nom_locali,
                        "etablissem": c.etablissem,
                        "canton": c.canton_nom
                    }
                } for c in colleges_qs
            ]
        }
    }

    # ------------------ Lycées ------------------
    lycees_qs = lycee.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['lycees'] = {
        "name": "Lycées",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(l.geom_json),
                    "properties": {
                        "nom_locali": l.nom_locali,
                        "etablissem": l.etablissem,
                        "canton": l.canton_nom
                    }
                } for l in lycees_qs
            ]
        }
    }

    # ------------------ Puits / Forages (PEA) ------------------
    peas_qs = pea.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['peas'] = {
        "name": "Forages PEA",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(p.geom_json),
                    "properties": {
                        "forage_nom": p.forage_nom,
                        "forage_typ": p.forage_typ,
                        "canton": p.canton_nom
                    }
                } for p in peas_qs
            ]
        }
    }

    # ------------------ Borne fontaines ------------------
    bornes_qs = bornefontaine.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['bornefontaines'] = {
        "name": "Bornes fontaines",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(b.geom_json),
                    "properties": {
                        "borne_font": b.borne_font,
                        "canton": b.canton_nom
                    }
                } for b in bornes_qs
            ]
        }
    }

    # ------------------ Châteaux ------------------
    chateaux_qs = chateau.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['chateaux'] = {
        "name": "Châteaux",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(c.geom_json),
                    "properties": {
                        "nom_locali": c.nom_locali,
                        "chateau_no": c.chateau_no,
                        "canton": c.canton_nom
                    }
                } for c in chateaux_qs
            ]
        }
    }

    # ------------------ Hôpitaux ------------------
    hopitaux_qs = hopitale.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['hopitaux'] = {
        "name": "Hôpitaux",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(h.geom_json),
                    "properties": {
                        "nom_fs": h.nom_fs,
                        "nom_locali": h.nom_locali,
                        "canton": h.canton_nom
                    }
                } for h in hopitaux_qs
            ]
        }
    }

    # ------------------ Terrains / stades ------------------
    terrains_qs = terrain.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['terrains'] = {
        "name": "Terrains / Stades",
        "visible": True,
        "opacity": 0.7,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(t.geom_json),
                    "properties": {
                        "terrain": t.terrain,
                        "terrain_sp": t.terrain_sp,
                        "canton": t.canton_nom
                    }
                } for t in terrains_qs
            ]
        }
    }

    # ------------------ Coopératives ------------------
   
    # ------------------ Magasins ------------------
    magasins_qs = magazinbl2.objects.all().annotate(geom_json=AsGeoJSON('geom'))
    layers['magasins'] = {
        "name": "Magasins / Intrants",
        "visible": True,
        "opacity": 1,
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(m.geom_json),
                    "properties": {
                        "etab_nom": m.etab_nom,
                        "canton": m.canton_nom
                    }
                } for m in magasins_qs
            ]
        }
    }

    return JsonResponse({"success": True, "layers": layers})





# ============================================================
# RECHERCHE MULTI-COUCHES
# ============================================================
from django.db.models import Q

def search_entities(request):
    """
    Recherche multi-couches.
    GET /api/search/?q=marché&layer=marches
    """
    query = request.GET.get('q', '').strip()
    layer_filter = request.GET.get('layer', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'count': 0, 'query': query})
    
    # Configuration adaptée à VOS modèles et VOS champs
    SEARCHABLE_LAYERS = {
        'cantons': {
            'model': Cantons,
            'search_fields': ['canton', 'prefecture', 'region'],
            'display_field': 'canton',
            'sub_fields': ['prefecture', 'region'],
            'layer_name': 'Cantons',
            'id_field': 'gid',
        },
        'communes': {
            'model': Commune,
            'search_fields': ['commune', 'prefecture', 'region'],
            'display_field': 'commune',
            'sub_fields': ['prefecture', 'region'],
            'layer_name': 'Communes',
            'id_field': 'gid',
        },
        'routes': {
            'model': routes,
            'search_fields': ['route_nom', 'route_type', 'route_clas'],
            'display_field': 'route_nom',
            'sub_fields': ['route_type', 'route_clas'],
            'layer_name': 'Routes',
            'id_field': 'id',
        },
        'marches': {
            'model': marche,
            'search_fields': ['marche_nom', 'canton_nom', 'jour'],
            'display_field': 'marche_nom',
            'sub_fields': ['canton_nom', 'jour'],
            'layer_name': 'Marchés',
            'id_field': 'id',
        },
        'jardins': {
            'model': jardin,
            'search_fields': ['nom_locali', 'etablissem', 'canton_nom'],
            'display_field': 'nom_locali',
            'sub_fields': ['etablissem', 'canton_nom'],
            'layer_name': 'Jardins',
            'id_field': 'id',
        },
        'colleges': {
            'model': college,
            'search_fields': ['nom_locali', 'etablissem', 'canton_nom'],
            'display_field': 'nom_locali',
            'sub_fields': ['etablissem', 'canton_nom'],
            'layer_name': 'Collèges',
            'id_field': 'id',
        },
        'lycees': {
            'model': lycee,
            'search_fields': ['nom_locali', 'etablissem', 'canton_nom'],
            'display_field': 'nom_locali',
            'sub_fields': ['etablissem', 'canton_nom'],
            'layer_name': 'Lycées',
            'id_field': 'id',
        },
        'peas': {
            'model': pea,
            'search_fields': ['forage_nom', 'forage_typ', 'canton_nom', 'nom_locali'],
            'display_field': 'forage_nom',
            'sub_fields': ['forage_typ', 'canton_nom'],
            'layer_name': 'Forages PEA',
            'id_field': 'id',
        },
        'bornefontaines': {
            'model': bornefontaine,
            'search_fields': ['borne_font', 'canton_nom'],
            'display_field': 'borne_font',
            'sub_fields': ['canton_nom'],
            'layer_name': 'Bornes fontaines',
            'id_field': 'id',
        },
        'chateaux': {
            'model': chateau,
            'search_fields': ['chateau_no', 'nom_locali', 'canton_nom', 'organisme'],
            'display_field': 'chateau_no',
            'sub_fields': ['organisme', 'canton_nom'],
            'layer_name': 'Châteaux',
            'id_field': 'id',
        },
        'hopitaux': {
            'model': hopitale,
            'search_fields': ['nom_fs', 'nom_locali', 'canton_nom'],
            'display_field': 'nom_fs',
            'sub_fields': ['nom_locali', 'canton_nom'],
            'layer_name': 'Hôpitaux',
            'id_field': 'id',
        },
        'terrains': {
            'model': terrain,
            'search_fields': ['terrain', 'terrain_sp', 'canton_nom', 'nom_locali'],
            'display_field': 'terrain',
            'sub_fields': ['terrain_sp', 'canton_nom'],
            'layer_name': 'Terrains / Stades',
            'id_field': 'id',
        },
        'magasins': {
            'model': magazinbl2,
            'search_fields': ['etab_nom', 'canton_nom'],
            'display_field': 'etab_nom',
            'sub_fields': ['canton_nom'],
            'layer_name': 'Magasins / Intrants',
            'id_field': 'id',
        },
    }
    
    results = []
    layers_to_search = [layer_filter] if layer_filter else SEARCHABLE_LAYERS.keys()
    
    for layer_key in layers_to_search:
        if layer_key not in SEARCHABLE_LAYERS:
            continue
        
        config = SEARCHABLE_LAYERS[layer_key]
        Model = config['model']
        
        try:
            # Construire la requête Q
            q_objects = Q()
            for field in config['search_fields']:
                q_objects |= Q(**{f'{field}__icontains': query})
            
            # Exclure les géométries nulles
            qs = Model.objects.filter(q_objects).filter(geom__isnull=False)[:15]
            
            # Annoter avec le GeoJSON
            qs = qs.annotate(geom_json=AsGeoJSON('geom'))
            
            for obj in qs:
                # Construire les propriétés
                properties = {}
                for field in config['search_fields']:
                    val = getattr(obj, field, None)
                    if val is not None:
                        properties[field] = str(val)
                
                # Construire le sublabel
                sublabel_parts = []
                for sf in config['sub_fields']:
                    val = getattr(obj, sf, None)
                    if val:
                        sublabel_parts.append(str(val))
                
                # Récupérer l'ID
                obj_id = getattr(obj, config['id_field'], None) or obj.pk
                
                # Récupérer la géométrie
                geom_json = getattr(obj, 'geom_json', None)
                try:
                    geometry = json.loads(geom_json) if geom_json else None
                except (json.JSONDecodeError, TypeError):
                    geometry = None
                
                if geometry is None:
                    continue
                
                results.append({
                    'id': obj_id,
                    'layer_id': layer_key,
                    'layer_name': config['layer_name'],
                    'label': str(getattr(obj, config['display_field'], '') or config['layer_name']),
                    'sublabel': ' • '.join(sublabel_parts) if sublabel_parts else '',
                    'properties': properties,
                    'geometry': geometry,
                })
        except Exception as e:
            import traceback
            print(f"⚠️ Erreur recherche {layer_key}: {e}")
            traceback.print_exc()
            continue
    
    # Trier par pertinence : ordre alphabétique du label
    results.sort(key=lambda r: r['label'].lower())
    
    return JsonResponse({
        'success': True,
        'results': results,
        'count': len(results),
        'query': query,
    })
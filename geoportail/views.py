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
    geojson = serialize('geojson', qs, geometry_field='geom', fields=('canton','code_canton','prefecture','code_prefe','region','code_regio'))
    return HttpResponse(geojson, content_type='application/json')





def commune_geojson(request):
    qs = Commune.objects.all()
    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('commune','code_commu','region','code_regio','prefecture','code_prefe')
    )
    return HttpResponse(geojson, content_type='application/json')


def route_geojson(request):
    qs = routes.objects.all()
    geojson = serialize('geojson', qs, geometry_field='geom', fields=('route_clas','route_type','route_clas','route_reco','route_nom'))
    return HttpResponse(geojson, content_type='application/json')

def lycee_geojson(request):
    qs = lycee.objects.all()
    geojson = serialize(
        'geojson', qs, geometry_field='geom',
        fields=('canton_nom','nom_locali','etablissem','ouverture','etabliss_1','type_terrain','inspection')
    )
    return HttpResponse(geojson, content_type='application/json')


def college_geojson(request):
    qs = college.objects.all()
    geojson = serialize(
        'geojson', qs, geometry_field='geom',
        fields=('canton_nom','nom_locali','etablissem','ouverture','etabliss_1','type_terrain','inspection')
    )
    return HttpResponse(geojson, content_type='application/json')


def jardin_geojson(request):
    qs = jardin.objects.all()
    geojson = serialize(
        'geojson', qs, geometry_field='geom',
        fields=('canton_nom','nom_locali','etablissem','ouverture','etabliss_1','type_terrain','inspection')
    )
    return HttpResponse(geojson, content_type='application/json')


def pea_geojson(request):
    qs = pea.objects.exclude(geom__isnull=True)
    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','forage_nom','forage_typ','batiment_n')
    )
    return HttpResponse(geojson, content_type='application/json')
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
        fields=('canton_nom','nom_locali','marche_nom,','jour')
    )
    return HttpResponse(geojson, content_type='application/json')



def borne_geojson(request):
    qs =bornefontaine.objects.exclude(geom__isnull=True)
    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','borne_font')
    )
    return HttpResponse(geojson, content_type='application/json')


def chateau_geojson(request):
    qs = chateau.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','chateau_no','organisme')
    )
    return HttpResponse(geojson, content_type='application/json')




def terrain_geojson(request):
    qs =terrain.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','terrain','terrain_sp')
    )
    return HttpResponse(geojson, content_type='application/json')



def hopital_geojson(request):
    qs = hopitale.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','nom_fs','ouverture','secteur','services_p')
    )
    return HttpResponse(geojson, content_type='application/json')



def cooperative_geojson(request):
    qs = coperative.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','nom_locali','cooperativ','cooperat_1')
    )
    return HttpResponse(geojson, content_type='application/json')




def magazin_geojson(request):
    qs = magazinbl2.objects.exclude(geom__isnull=True)

    geojson = serialize(
        'geojson',
        qs,
        geometry_field='geom',
        fields=('canton_nom','etab_nom','ouverture','organisme')
    )
    return HttpResponse(geojson, content_type='application/json')

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

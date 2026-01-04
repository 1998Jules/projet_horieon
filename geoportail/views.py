from django.shortcuts import render

from django.http import JsonResponse
from django.core.serializers import serialize
from .models import QuartierAneho
def index(request):
    return render(request, 'index.html')

#vue pour la couche quartiers

from django.http import JsonResponse
from django.core.serializers import serialize
from .models import QuartierAneho

def quartiers_geojson(request):
    # Exclure les géométries NULL pour éviter GDALException
    qs = QuartierAneho.objects.exclude(geom__isnull=True)
    geojson = serialize(
        "geojson",
        qs,
        geometry_field="geom",
        fields=("quartiers",)
    )
    return JsonResponse(geojson, safe=False)

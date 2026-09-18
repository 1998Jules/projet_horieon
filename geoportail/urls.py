from django.contrib import admin
from django.urls import path
from .views import get_all_layers,search_entities
from . import views

urlpatterns = [
    path('', views.index, name='index'),
  
    path('geojson/cantons/', views.cantons_geojson, name='cantons_geojson'),
    path('geojson/commune/', views.commune_geojson, name='commune_geojson'),
    path('geojson/routes/', views.route_geojson, name='route_geojson'),
    path('geojson/lycee/', views.lycee_geojson, name='lycee_geojson'),
    path('geojson/college/', views.college_geojson, name='college_geojson'),
    path('geojson/jardin/', views.jardin_geojson, name='jardin_geojson'),
    path('geojson/Point_eau/', views.pea_geojson, name='pea_geojson'),
    path('geojson/Marches/', views.marche_geojson, name='marche_geojson'),
    path('geojson/bornefontaine/', views.borne_geojson, name='borne_geojson'),
    path('geojson/chateau/', views.chateau_geojson, name='chateau_geojson'),
    path('geojson/hopitale/', views.hopital_geojson, name='hopital_geojson'),
    path('geojson/terrain/', views.terrain_geojson, name='terrain_geojson'),
    path('geojson/cooperative/', views.cooperative_geojson, name='cooperative_geojson'),
    path('geojson/magasin/', views.magazin_geojson, name='magazin_geojson'),
    path('api/layers/', views.get_all_layers, name='get_all_layers'),
    path('api/search/', views.search_entities, name='search_entities'),
   
   
    
]
# geoportail/urls.py


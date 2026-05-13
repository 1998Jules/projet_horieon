from django.urls import path
from . import views

urlpatterns = [
    # Page d'accueil standard (Optionnel)
    path('', views.index, name='index'),
    
    # --- API POUR L'APPLICATION REACT ---
    
    # API pour les tuiles NDVI (appelée par React dans useEffect)
    path('api/ndvi-tiles/', views.ndvi_tiles, name='ndvi_tiles'),
    
    # API pour les régions (appelée par React dans useEffect)
    path('api/regions/', views.region_geojson, name='region_geojson'),
    
    # Si vous voulez ajouter les préfectures/communes plus tard dans React :
    path('api/prefectures/', views.prefecture_geojson, name='prefecture_geojson'),
    path('api/communes/', views.commune_geojson, name='commune_geojson'),

    # API pour les séries temporelles (si vous l'activez dans React)
    path('api/ndvi-timeseries/', views.ndvi_timeseries, name='ndvi_timeseries'),
    path('api/champs/', views.ndvi_timeseries, name='ndvi_timeseries'),

    # 1. Récupérer la liste de tous les champs (pour afficher sur la carte)
    path('api/champs/geojson/', views.champs_geojson, name='champs_geojson'),
    
    # 2. Créer un nouveau champ (Formulaire de dessin)
    path('api/champs/create/', views.create_champ, name='create_champ'),
    
    # 3. Récupérer l'historique NDVI d'un champ spécifique (Graphique & Carte)
    path('api/field-ndvi/', views.field_ndvi_timeseries, name='field_ndvi_timeseries'),
    path('api/field-indices-comparison/', views.field_indices_comparison, name='field_indices_comparison'),

    
]
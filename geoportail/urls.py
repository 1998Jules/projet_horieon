from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('quartiers/', views.quartiers_geojson, name='quartiers_geojson')
]

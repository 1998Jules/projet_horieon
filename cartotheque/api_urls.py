"""
API URLs de l'application cartotheque
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'domaines', views.DomaineCarteViewSet, basename='domaine-carte')
router.register(r'cartes', views.CarteTheematiqueViewSet, basename='carte-theematique')

urlpatterns = [
    path('', include(router.urls)),
    
]
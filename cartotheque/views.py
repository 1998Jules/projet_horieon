from django.shortcuts import render

# Create your views here.
"""
Vues API pour la Cartothèque
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend

from .models import DomaineCarte, CarteTheematique
from .serializers import (
    DomaineCarteSerializer,
    CarteTheematiqueListSerializer,
    CarteTheematiqueDetailSerializer,
    CarteTheematiqueCreateSerializer,
)


class DomaineCarteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour les domaines thématiques (lecture seule).
    GET /api/cartotheque/domaines/
    GET /api/cartotheque/domaines/{id}/
    """
    queryset = DomaineCarte.objects.filter(actif=True)
    serializer_class = DomaineCarteSerializer
    search_fields = ['nom', 'description']
    ordering_fields = ['ordre', 'nom']


class CarteTheematiqueViewSet(viewsets.ModelViewSet):
    """
    API CRUD pour les cartes thématiques.
    GET    /api/cartotheque/cartes/           - Liste des cartes publiées
    POST   /api/cartotheque/cartes/           - Créer une nouvelle carte
    GET    /api/cartotheque/cartes/{id}/      - Détail d'une carte
    PUT    /api/cartotheque/cartes/{id}/      - Mettre à jour une carte
    DELETE /api/cartotheque/cartes/{id}/      - Supprimer une carte
    GET    /api/cartotheque/cartes/stats/     - Statistiques de la cartothèque
    """
    queryset = CarteTheematique.objects.select_related('domaine').all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titre', 'description', 'mots_cles', 'auteur']
    ordering_fields = ['date_creation', 'titre', 'date_modification']
    ordering = ['-date_creation']

    def get_serializer_class(self):
        if self.action == 'list':
            return CarteTheematiqueListSerializer
        if self.action == 'retrieve':
            return CarteTheematiqueDetailSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return CarteTheematiqueCreateSerializer
        return CarteTheematiqueDetailSerializer

    def get_queryset(self):
        """
        Filtrer les résultats :
        - Par défaut, retourner uniquement les cartes publiées
        - Si le paramètre 'statut' est fourni, filtrer par statut
        - Si le paramètre 'domaine' est fourni, filtrer par domaine
        """
        queryset = super().get_queryset()

        # Filtre par statut (défaut: publie)
        statut = self.request.query_params.get('statut', 'publie')
        if statut != 'tous':
            queryset = queryset.filter(statut=statut)

        # Filtre par domaine
        domaine_id = self.request.query_params.get('domaine')
        if domaine_id:
            queryset = queryset.filter(domaine_id=domaine_id)

        # Filtre par domaine slug
        domaine_slug = self.request.query_params.get('domaine_slug')
        if domaine_slug:
            queryset = queryset.filter(domaine__slug=domaine_slug)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Statistiques de la cartothèque"""
        total_cartes = CarteTheematique.objects.count()
        cartes_publiees = CarteTheematique.objects.filter(statut='publie').count()
        cartes_brouillon = CarteTheematique.objects.filter(statut='brouillon').count()

        domaines_stats = []
        for domaine in DomaineCarte.objects.filter(actif=True):
            count = domaine.cartes.filter(statut='publie').count()
            domaines_stats.append({
                'id': domaine.id,
                'nom': domaine.nom,
                'slug': domaine.slug,
                'couleur': domaine.couleur,
                'icone': domaine.icone,
                'nombre_cartes': count
            })

        return Response({
            'success': True,
            'data': {
                'total_cartes': total_cartes,
                'cartes_publiees': cartes_publiees,
                'cartes_brouillon': cartes_brouillon,
                'domaines': domaines_stats
            }
        })

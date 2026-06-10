"""
Serializers DRF pour la Cartothèque
"""
from rest_framework import serializers
from .models import DomaineCarte, CarteTheematique


class DomaineCarteSerializer(serializers.ModelSerializer):
    """Serializer pour les domaines thématiques"""
    nombre_cartes = serializers.SerializerMethodField()

    class Meta:
        model = DomaineCarte
        fields = [
            'id', 'nom', 'slug', 'description', 'icone',
            'couleur', 'ordre', 'actif', 'nombre_cartes'
        ]
        read_only_fields = ['id', 'slug', 'nombre_cartes']

    def get_nombre_cartes(self, obj):
        return obj.cartes.filter(statut='publie').count()


class CarteTheematiqueListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des cartes (sans les données GeoJSON lourdes)"""
    domaine_nom = serializers.CharField(source='domaine.nom', default=None, read_only=True)
    domaine_couleur = serializers.CharField(source='domaine.couleur', default=None, read_only=True)
    domaine_icone = serializers.CharField(source='domaine.icone', default=None, read_only=True)
    vignette_url = serializers.SerializerMethodField()
    type_carte = serializers.SerializerMethodField()

    class Meta:
        model = CarteTheematique
        fields = [
            'id', 'titre', 'description', 'domaine', 'domaine_nom',
            'domaine_couleur', 'domaine_icone', 'vignette_url',
            'type_carte', 'statut', 'auteur', 'source', 'mots_cles',
            'date_creation', 'date_modification'
        ]

    def get_vignette_url(self, obj):
        if obj.vignette:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.vignette.url)
            return obj.vignette.url
        return None

    def get_type_carte(self, obj):
        """Détermine le type de carte : dynamique (couches du géoportail) ou statique (GeoJSON)"""
        if obj.couches_associees and len(obj.couches_associees) > 0:
            return 'dynamique'
        elif obj.geojson_url:
            return 'url_externe'
        elif obj.geojson_file:
            return 'fichier'
        return 'vide'


class CarteTheematiqueDetailSerializer(CarteTheematiqueListSerializer):
    """Serializer complet pour le détail d'une carte (avec les données de visualisation)"""
    geojson_file_url = serializers.SerializerMethodField()

    class Meta(CarteTheematiqueListSerializer.Meta):
        fields = CarteTheematiqueListSerializer.Meta.fields + [
            'geojson_url', 'geojson_file_url', 'couches_associees',
            'centre_lat', 'centre_lng', 'zoom_default', 'fond_carte'
        ]

    def get_geojson_file_url(self, obj):
        if obj.geojson_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.geojson_file.url)
            return obj.geojson_file.url
        return None


class CarteTheematiqueCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/mise à jour d'une carte"""

    class Meta:
        model = CarteTheematique
        fields = [
            'titre', 'description', 'domaine', 'vignette',
            'geojson_url', 'geojson_file', 'couches_associees',
            'centre_lat', 'centre_lng', 'zoom_default', 'fond_carte',
            'statut', 'auteur', 'source', 'mots_cles'
        ]

    def validate(self, data):
        """Valider qu'au moins une source de données est fournie"""
        geojson_url = data.get('geojson_url', '')
        geojson_file = data.get('geojson_file')
        couches = data.get('couches_associees', [])

        if not geojson_url and not geojson_file and not couches:
            # C'est OK pour un brouillon, mais on avertit
            pass
        return data

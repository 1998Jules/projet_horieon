from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class DomaineCarte(models.Model):
    """Domaine thématique pour classer les cartes"""
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom du domaine")
    slug = models.SlugField(max_length=120, unique=True, blank=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Description")
    icone = models.CharField(max_length=50, default='Map', verbose_name="Icône Lucide")
    couleur = models.CharField(max_length=7, default='#22c55e', verbose_name="Couleur hex")
    ordre = models.IntegerField(default=0, verbose_name="Ordre d'affichage")
    actif = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Domaine de carte"
        verbose_name_plural = "Domaines de cartes"
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    @property
    def nombre_cartes(self):
        return self.cartes.filter(statut='publie').count()


class CarteTheematique(models.Model):
    """Carte thématique publiée dans la cartothèque"""

    TYPE_FOND_CARTE = [
        ('osm', 'OpenStreetMap'),
        ('satellite', 'Satellite ESRI'),
        ('dark', 'CartoDB Dark'),
    ]

    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('publie', 'Publié'),
        ('archive', 'Archivé'),
    ]

    titre = models.CharField(max_length=250, verbose_name="Titre de la carte")
    description = models.TextField(blank=True, verbose_name="Description")
    domaine = models.ForeignKey(
        DomaineCarte, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cartes', verbose_name="Domaine thématique"
    )
    vignette = models.ImageField(
        upload_to='cartotheque/vignettes/', blank=True, null=True, verbose_name="Vignette"
    )
    geojson_url = models.URLField(max_length=500, blank=True, verbose_name="URL GeoJSON externe")
    geojson_file = models.FileField(
        upload_to='cartotheque/geojson/', blank=True, null=True, verbose_name="Fichier GeoJSON"
    )
    couches_associees = models.JSONField(default=list, blank=True, verbose_name="Couches associées")
    centre_lat = models.FloatField(default=8.32, verbose_name="Latitude du centre")
    centre_lng = models.FloatField(default=0.9797, verbose_name="Longitude du centre")
    zoom_default = models.IntegerField(default=12, verbose_name="Zoom par défaut")
    fond_carte = models.CharField(max_length=20, choices=TYPE_FOND_CARTE, default='osm', verbose_name="Fond de carte")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon', verbose_name="Statut")
    auteur = models.CharField(max_length=200, blank=True, verbose_name="Auteur")
    source = models.CharField(max_length=300, blank=True, verbose_name="Source des données")
    mots_cles = models.CharField(max_length=500, blank=True, verbose_name="Mots-clés")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        verbose_name = "Carte thématique"
        verbose_name_plural = "Cartes thématiques"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.titre} ({self.get_statut_display()})"

    @property
    def type_donnees(self):
        if self.couches_associees:
            return 'dynamique'
        elif self.geojson_url:
            return 'url_externe'
        elif self.geojson_file:
            return 'fichier'
        return 'vide'

    @property
    def liste_mots_cles(self):
        if not self.mots_cles:
            return []
        return [k.strip() for k in self.mots_cles.split(',') if k.strip()]
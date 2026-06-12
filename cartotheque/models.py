from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class DomaineCarte(models.Model):
    """Domaine thematique pour classer les cartes"""
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom du domaine")
    slug = models.SlugField(max_length=120, unique=True, blank=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Description")
    icone = models.CharField(max_length=50, default='Map', verbose_name="Icone Lucide")
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
    """Carte thematique publiee dans la cartotheque"""

    TYPE_FOND_CARTE = [
        ('osm', 'OpenStreetMap'),
        ('satellite', 'Satellite ESRI'),
        ('dark', 'CartoDB Dark'),
    ]

    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('publie', 'Publie'),
        ('archive', 'Archive'),
    ]

    FORMAT_IMPRESSION_CHOICES = [
        ('A0', 'A0 (841 x 1189 mm)'),
        ('A1', 'A1 (594 x 841 mm)'),
        ('A2', 'A2 (420 x 594 mm)'),
        ('A3', 'A3 (297 x 420 mm)'),
        ('A4', 'A4 (210 x 297 mm)'),
        ('personnalise', 'Personnalise'),
    ]

    titre = models.CharField(max_length=250, verbose_name="Titre de la carte")
    description = models.TextField(blank=True, verbose_name="Description")
    domaine = models.ForeignKey(
        DomaineCarte, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cartes', verbose_name="Domaine thematique"
    )
    vignette = models.ImageField(
        upload_to='cartotheque/vignettes/', blank=True, null=True, verbose_name="Vignette"
    )
    # Image principale de la carte (pour la visualisation agrandie)
    image = models.ImageField(
        upload_to='cartotheque/images/', blank=True, null=True, verbose_name="Image de la carte"
    )
    geojson_url = models.URLField(max_length=500, blank=True, verbose_name="URL GeoJSON externe")
    geojson_file = models.FileField(
        upload_to='cartotheque/geojson/', blank=True, null=True, verbose_name="Fichier GeoJSON"
    )
    couches_associees = models.JSONField(default=list, blank=True, verbose_name="Couches associees")
    centre_lat = models.FloatField(default=8.32, verbose_name="Latitude du centre")
    centre_lng = models.FloatField(default=0.9797, verbose_name="Longitude du centre")
    zoom_default = models.IntegerField(default=12, verbose_name="Zoom par defaut")
    fond_carte = models.CharField(max_length=20, choices=TYPE_FOND_CARTE, default='osm', verbose_name="Fond de carte")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon', verbose_name="Statut")
    auteur = models.CharField(max_length=200, blank=True, verbose_name="Auteur")
    source = models.CharField(max_length=300, blank=True, verbose_name="Source des donnees")
    mots_cles = models.CharField(max_length=500, blank=True, verbose_name="Mots-cles")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de creation")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    # Nouveaux champs pour le modele CNTIG
    echelle = models.CharField(
        max_length=50, blank=True, verbose_name="Echelle",
        help_text="Ex: 1:50000, 1:25000, 1:100000"
    )
    format_impression = models.CharField(
        max_length=20, choices=FORMAT_IMPRESSION_CHOICES, blank=True,
        verbose_name="Format d'impression"
    )
    date_edition = models.DateField(
        null=True, blank=True, verbose_name="Date d'edition",
        help_text="Date de publication/edition de la carte"
    )
    realisateur = models.CharField(
        max_length=200, blank=True, verbose_name="Realisateur",
        help_text="Personne ou organisme qui a realise la carte"
    )
    is_payant = models.BooleanField(
        default=False, verbose_name="Payant",
        help_text="Indique si la carte est payante"
    )
    prix = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Prix (F CFA)",
        help_text="Prix en Francs CFA si la carte est payante"
    )

    class Meta:
        verbose_name = "Carte thematique"
        verbose_name_plural = "Cartes thematiques"
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

    @property
    def prix_formate(self):
        """Retourne le prix formate en F CFA"""
        if self.prix:
            return f"{int(self.prix):,} F CFA".replace(',', ' ')
        return "Gratuit"

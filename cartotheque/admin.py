from django.contrib import admin
from .models import DomaineCarte, CarteTheematique


@admin.register(DomaineCarte)
class DomaineCarteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'icone', 'couleur', 'ordre', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'description')
    prepopulated_fields = {'slug': ('nom',)}
    ordering = ('ordre',)


@admin.register(CarteTheematique)
class CarteTheematiqueAdmin(admin.ModelAdmin):
    list_display = (
        'titre', 'domaine', 'statut', 'is_payant', 'prix',
        'echelle', 'format_impression', 'date_creation', 'date_modification', 'auteur'
    )
    list_filter = ('statut', 'domaine', 'is_payant', 'format_impression')
    search_fields = ('titre', 'description', 'realisateur')
    list_editable = ('statut',)
    date_hierarchy = 'date_creation'
    ordering = ('-date_creation',)
    readonly_fields = ('date_creation', 'date_modification')

    fieldsets = (
        ('Informations generales', {
            'fields': ('titre', 'description', 'domaine', 'statut')
        }),
        ('Images', {
            'fields': ('vignette', 'image')
        }),
        ('Sources de donnees', {
            'fields': ('geojson_url', 'geojson_file', 'couches_associees'),
            'classes': ('collapse',)
        }),
        ('Configuration de la carte', {
            'fields': ('centre_lat', 'centre_lng', 'zoom_default', 'fond_carte'),
            'classes': ('collapse',)
        }),
        ('Metadonnees', {
            'fields': ('auteur', 'source', 'mots_cles', 'realisateur')
        }),
        ('Caracteristiques produit', {
            'fields': ('echelle', 'format_impression', 'date_edition')
        }),
        ('Tarification', {
            'fields': ('is_payant', 'prix')
        }),
    )

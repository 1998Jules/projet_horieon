from django.contrib import admin

# Register your models here.
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
    list_display = ('titre', 'domaine', 'statut', 'date_creation', 'date_modification', 'auteur')
    list_filter = ('statut', 'domaine')
    search_fields = ('titre', 'description')
    list_editable = ('statut',)
    date_hierarchy = 'date_creation'
    ordering = ('-date_creation',)
    readonly_fields = ('date_creation', 'date_modification')
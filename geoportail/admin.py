from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.utils.html import format_html
from .models import marche
from django.utils.html import format_html

@admin.register(marche)
class MarcheAdmin(admin.ModelAdmin):
    list_display = ('marche_nom', 'canton_nom', 'jour', 'photo_preview')

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="100" />', obj.photo.url)
        return "-"
    photo_preview.short_description = "Photo"
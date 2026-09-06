from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "secteur_activite", "whatsapp", "recevoir_alertes")
    list_filter = ("recevoir_alertes", "secteur_activite")
    search_fields = ("user__username", "user__email", "whatsapp", "secteur_activite")

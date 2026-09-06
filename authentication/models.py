from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    secteur_activite = models.CharField(max_length=150, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    recevoir_alertes = models.BooleanField(default=True)

    def __str__(self):
        return f"Profil de {self.user.username}"

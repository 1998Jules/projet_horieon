from django.db import models

from django.contrib.gis.db import models

class QuartierAneho(models.Model):
    quartiers = models.CharField(max_length=100)
    geom = models.MultiPolygonField(srid=4326)  # MULTIPOLYGON compatible

    class Meta:
        db_table = "qartier_aneho"  # Nom exact de la table dans PostGIS
        managed = False             # Django ne touche pas à la table

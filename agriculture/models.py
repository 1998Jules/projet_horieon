from django.db import models

# Create your models here.
from django.db import models
from django.contrib.gis.db import models
from django.contrib.gis.db import models as gis_models

class Prefecture(models.Model):
    id = models.IntegerField(primary_key=True)
    prefecture = models.CharField(max_length=100)
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        db_table = "couche_prefecture_utm"
        managed = False


class Region(models.Model):
    id = models.IntegerField(primary_key=True)
    region = models.CharField(max_length=100)
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        db_table = "region"
        managed = False
        
class Commune(models.Model):
    id = models.IntegerField(primary_key=True)
    commune = models.CharField(max_length=100)
    prefecture=models.CharField(max_length=100)
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        db_table = "communes_togo_utm"
        managed = False

# agriculture/models.py
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import User

# agriculture/models.py
from django.contrib.gis.db import models as gis_models
from django.db import models  # pour les champs standards (CharField, DateField, etc.)
from django.db import models
from django.contrib.gis.db import models as gis_models

class Champ(models.Model):
    nom = models.CharField(max_length=200)
    proprietaire = models.CharField(max_length=200)
    type_culture = models.CharField(max_length=100)
    date_semi = models.DateField()

    geom = gis_models.GeometryField(srid=4326)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agriculture_champ"
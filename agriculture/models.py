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



# agriculture/models.py
# ... (vos imports existants) ...

# ... autres imports...

class CropCalendar(models.Model):
    CROP_TYPES = [
        ('CEREAL', 'Céréale'),
        ('LEGUME', 'Légume'),
        ('TUBERCULE', 'Tubercule'),
        ('LEGUMINEUSE', 'Légumineuse'),
    ]

    name = models.CharField(max_length=100, verbose_name="Nom de la culture")
    variety = models.CharField(max_length=100, blank=True, null=True, verbose_name="Variété") # NOUVEAU
    crop_type = models.CharField(max_length=20, choices=CROP_TYPES, verbose_name="Type")
    duration_days = models.IntegerField(default=90, verbose_name="Durée cycle (jours)") # NOUVEAU
    
    # Périodes (stockées en mois : 1=Janvier, 12=Décembre)
    sowing_start = models.IntegerField(verbose_name="Début Semi (Mois)")
    sowing_end = models.IntegerField(verbose_name="Fin Semi (Mois)")
    
    weeding_start = models.IntegerField(verbose_name="Début Sarclage (Mois)")
    weeding_end = models.IntegerField(verbose_name="Fin Sarclage (Mois)")
    
    harvest_start = models.IntegerField(verbose_name="Début Récolte (Mois)")
    harvest_end = models.IntegerField(verbose_name="Fin Récolte (Mois)")
    
    other_activities = models.TextField(blank=True, null=True, verbose_name="Autres activités")

    class Meta:
        db_table = "agriculture_crop_calendar"
        verbose_name = "Calendrier Cultural"
        verbose_name_plural = "Calendriers Culturaux"

    def __str__(self):
        return f"{self.name} - {self.variety}" if self.variety else self.name
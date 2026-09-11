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
    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='champs_agriculture',
    )

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




class FieldIndicatorSnapshot(models.Model):
    """Valeurs observées pour un champ à une date donnée."""

    INDEX_CHOICES = [
        ("SPI_1", "SPI 1 mois"),
        ("SPI_3", "SPI 3 mois"),
        ("SPI_6", "SPI 6 mois"),
        ("SPI_FORECAST", "SPI prévisionnel"),
        ("NDVI", "NDVI"),
        ("EVI", "EVI"),
        ("NDWI", "NDWI"),
        ("VCI", "VCI"),
        ("TCI", "TCI"),
        ("VHI", "VHI"),
        ("NCWSI", "NCWSI"),
        ("RAINFALL", "Précipitations"),
        ("TEMPERATURE", "Température"),
    ]

    champ = models.ForeignKey(Champ, on_delete=models.CASCADE, related_name="indicator_snapshots")
    observed_at = models.DateTimeField(db_index=True)
    indicator = models.CharField(max_length=30, choices=INDEX_CHOICES, db_index=True)
    value = models.FloatField()
    reference_value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["champ", "observed_at", "indicator"],
                name="unique_field_indicator_observation",
            )
        ]
        indexes = [models.Index(fields=["champ", "indicator", "-observed_at"])]

    def __str__(self):
        return f"{self.champ.nom} — {self.indicator} = {self.value}"


class AlertRule(models.Model):
    """Seuil configurable utilisé pour transformer un indicateur en alerte."""

    OPERATORS = [(op, op) for op in ("LT", "LTE", "GT", "GTE", "EQ", "CHANGE_PCT")]
    SEVERITIES = [(level, level.title()) for level in ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")]

    name = models.CharField(max_length=150)
    indicator = models.CharField(max_length=30, choices=FieldIndicatorSnapshot.INDEX_CHOICES)
    operator = models.CharField(max_length=15, choices=OPERATORS)
    threshold = models.FloatField()
    severity = models.CharField(max_length=10, choices=SEVERITIES, default="MEDIUM")
    title_template = models.CharField(max_length=255)
    message_template = models.TextField()
    recommendation_template = models.TextField(blank=True)
    crop_type = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    cooldown_hours = models.PositiveIntegerField(default=24)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["indicator", "severity", "name"]

    def __str__(self):
        return self.name


class FarmerAlert(models.Model):
    """Alerte personnalisée produite pour un agriculteur et un champ."""

    STATUSES = [(status, status.title()) for status in ("OPEN", "ACKNOWLEDGED", "RESOLVED", "EXPIRED")]

    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farmer_alerts")
    champ = models.ForeignKey(Champ, on_delete=models.CASCADE, related_name="farmer_alerts")
    rule = models.ForeignKey(AlertRule, null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts")
    indicator = models.CharField(max_length=30, choices=FieldIndicatorSnapshot.INDEX_CHOICES)
    observed_value = models.FloatField()
    severity = models.CharField(max_length=10, choices=AlertRule.SEVERITIES, default="MEDIUM")
    title = models.CharField(max_length=255)
    message = models.TextField()
    recommendation = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUSES, default="OPEN", db_index=True)
    observed_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["farmer", "status", "-created_at"])]

    def __str__(self):
        return f"{self.severity} — {self.title} ({self.farmer.username})"


class AlertDelivery(models.Model):
    """Journal de livraison, conçu pour supporter e-mail puis WhatsApp."""

    CHANNELS = [(channel, channel.title()) for channel in ("EMAIL", "WHATSAPP")]
    STATUSES = [(status, status.title()) for status in ("PENDING", "SENT", "FAILED", "SKIPPED")]

    alert = models.ForeignKey(FarmerAlert, on_delete=models.CASCADE, related_name="deliveries")
    channel = models.CharField(max_length=15, choices=CHANNELS)
    destination = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUSES, default="PENDING")
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "channel"],
                name="unique_alert_delivery_channel",
            )
        ]
        indexes = [models.Index(fields=["channel", "status", "created_at"])]

    def __str__(self):
        return f"{self.channel} — {self.status} — alerte {self.alert_id}"

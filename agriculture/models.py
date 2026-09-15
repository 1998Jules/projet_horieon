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
        # Indices spectraux (Sentinel-2 / MODIS)
        ("NDVI", "NDVI"),
        ("EVI", "EVI"),
        ("NDWI", "NDWI"),
        ("MSAVI", "MSAVI"),
        ("VCI", "VCI"),
        ("TCI", "TCI"),
        ("VHI", "VHI"),
        ("NCWSI", "NCWSI"),
        # Indices pluviométriques (CHIRPS / CHIRPS-GEFS)
        ("SPI_30", "SPI 30 jours"),
        ("SPI_90", "SPI 90 jours"),
        ("SPI_FORECAST", "SPI prévisionnel 15 jours"),
        ("RAINFALL_24H", "Précipitations 24 h"),
        ("RAINFALL_72H", "Précipitations 72 h"),
        # Rétro-compatibilité (alias historiques)
        ("SPI_1", "SPI 1 mois (alias)"),
        ("SPI_3", "SPI 3 mois (alias)"),
        ("SPI_6", "SPI 6 mois (alias)"),
        ("RAINFALL", "Précipitations (générique)"),
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

    # Niveaux de risque normalisés, partagés entre AlertRule, FarmerAlert et RiskAssessment.
    # 🟢 0-25 : Normal | 🟡 26-50 : Vigilance | 🟠 51-75 : Alerte | 🔴 76-100 : Critique
    RISK_LEVELS = [
        ("NORMAL", "🟢 Normal"),
        ("VIGILANCE", "🟡 Vigilance"),
        ("ALERT", "🟠 Alerte"),
        ("CRITICAL", "🔴 Critique"),
    ]

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

    # Type d'alerte détecté par le moteur de croisement d'indicateurs.
    ALERT_TYPES = [
        ("STRESS_VEGETATIF", "🌿 Stress végétatif"),
        ("STRESS_HYDRIQUE", "💧 Stress hydrique"),
        ("SECHERESSE", "🏜️ Sécheresse"),
        ("EXCES_PLUIE", "🌧️ Excès de précipitations"),
        ("GENERIC", "Alerte générique"),
    ]

    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farmer_alerts")
    champ = models.ForeignKey(Champ, on_delete=models.CASCADE, related_name="farmer_alerts")
    rule = models.ForeignKey(AlertRule, null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts")
    indicator = models.CharField(max_length=30, choices=FieldIndicatorSnapshot.INDEX_CHOICES)
    observed_value = models.FloatField()
    severity = models.CharField(max_length=10, choices=AlertRule.SEVERITIES, default="MEDIUM")
    # Niveau de risque normalisé (🟢🟡🟠🔴) — utilisé pour détecter aggravation/amélioration.
    risk_level = models.CharField(max_length=15, choices=AlertRule.RISK_LEVELS, default="VIGILANCE")
    # Score de risque global au moment de la détection (0-100).
    risk_score = models.FloatField(default=0.0)
    # Type d'alerte (stress végétatif, hydrique, sécheresse, excès pluie).
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES, default="GENERIC")
    # Indicateurs ayant contribué à l'alerte (JSON : [{"indicator": "NDVI", "value": 0.32, "contribution": 18}]).
    contributing_indicators = models.JSONField(default=list, blank=True)
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
        indexes = [
            models.Index(fields=["farmer", "status", "-created_at"]),
            models.Index(fields=["champ", "alert_type", "-created_at"]),
            models.Index(fields=["farmer", "risk_level", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.severity} — {self.title} ({self.farmer.username})"


class RiskAssessment(models.Model):
    """Score de risque global calculé pour un champ à un instant donné.

    Ce modèle trace l'évolution du score dans le temps et permet au moteur
    d'alertes de détecter les changements de niveau ( aggravation / amélioration ).
    """

    RISK_LEVELS = AlertRule.RISK_LEVELS

    champ = models.ForeignKey(Champ, on_delete=models.CASCADE, related_name="risk_assessments")
    assessed_at = models.DateTimeField(db_index=True)
    score = models.FloatField(help_text="Score global 0-100")
    level = models.CharField(max_length=15, choices=RISK_LEVELS, default="NORMAL")
    # Sous-scores par catégorie (0-100 chacun), pour traçabilité.
    sub_scores = models.JSONField(
        default=dict,
        help_text="{'vegetation': 35, 'humidity': 28, 'drought': 45, 'rainfall': 10, 'forecast': 60}",
    )
    # Indicateurs utilisés (snapshot complet au format JSON).
    indicators_snapshot = models.JSONField(default=dict)
    # Alertes éventuellement créées à partir de cette évaluation (M2M pour flexibilité).
    triggered_alerts = models.ManyToManyField(
        "FarmerAlert", blank=True, related_name="risk_assessments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assessed_at"]
        indexes = [
            models.Index(fields=["champ", "-assessed_at"]),
            models.Index(fields=["level", "-assessed_at"]),
        ]

    def __str__(self):
        return f"{self.champ.nom} — {self.level} ({self.score:.0f}/100) @ {self.assessed_at:%d/%m/%Y}"


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

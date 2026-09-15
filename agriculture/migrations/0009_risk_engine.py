"""Ajoute MSAVI/SPI_30/SPI_90/RAINFALL_24H/RAINFALL_72H aux choices, les champs
risk_level/risk_score/alert_type/contributing_indicators sur FarmerAlert, et le
modèle RiskAssessment pour tracer le score de risque dans le temps."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agriculture", "0008_default_alert_rules"),
    ]

    operations = [
        # 1. Modifier les choices de FieldIndicatorSnapshot.indicator pour inclure
        #    MSAVI, SPI_30, SPI_90, RAINFALL_24H, RAINFALL_72H.
        migrations.AlterField(
            model_name="fieldindicatorsnapshot",
            name="indicator",
            field=models.CharField(
                choices=[
                    ("NDVI", "NDVI"),
                    ("EVI", "EVI"),
                    ("NDWI", "NDWI"),
                    ("MSAVI", "MSAVI"),
                    ("VCI", "VCI"),
                    ("TCI", "TCI"),
                    ("VHI", "VHI"),
                    ("NCWSI", "NCWSI"),
                    ("SPI_30", "SPI 30 jours"),
                    ("SPI_90", "SPI 90 jours"),
                    ("SPI_FORECAST", "SPI prévisionnel 15 jours"),
                    ("RAINFALL_24H", "Précipitations 24 h"),
                    ("RAINFALL_72H", "Précipitations 72 h"),
                    ("SPI_1", "SPI 1 mois (alias)"),
                    ("SPI_3", "SPI 3 mois (alias)"),
                    ("SPI_6", "SPI 6 mois (alias)"),
                    ("RAINFALL", "Précipitations (générique)"),
                    ("TEMPERATURE", "Température"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),

        # 2. Modifier les choices de AlertRule.indicator (hérite des nouveaux indices).
        migrations.AlterField(
            model_name="alertrule",
            name="indicator",
            field=models.CharField(
                choices=[
                    ("NDVI", "NDVI"),
                    ("EVI", "EVI"),
                    ("NDWI", "NDWI"),
                    ("MSAVI", "MSAVI"),
                    ("VCI", "VCI"),
                    ("TCI", "TCI"),
                    ("VHI", "VHI"),
                    ("NCWSI", "NCWSI"),
                    ("SPI_30", "SPI 30 jours"),
                    ("SPI_90", "SPI 90 jours"),
                    ("SPI_FORECAST", "SPI prévisionnel 15 jours"),
                    ("RAINFALL_24H", "Précipitations 24 h"),
                    ("RAINFALL_72H", "Précipitations 72 h"),
                    ("SPI_1", "SPI 1 mois (alias)"),
                    ("SPI_3", "SPI 3 mois (alias)"),
                    ("SPI_6", "SPI 6 mois (alias)"),
                    ("RAINFALL", "Précipitations (générique)"),
                    ("TEMPERATURE", "Température"),
                ],
                max_length=30,
            ),
        ),

        # 3. Ajouter les nouveaux champs sur FarmerAlert.
        migrations.AddField(
            model_name="farmeralert",
            name="risk_level",
            field=models.CharField(
                choices=[
                    ("NORMAL", "🟢 Normal"),
                    ("VIGILANCE", "🟡 Vigilance"),
                    ("ALERT", "🟠 Alerte"),
                    ("CRITICAL", "🔴 Critique"),
                ],
                default="VIGILANCE",
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name="farmeralert",
            name="risk_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="farmeralert",
            name="alert_type",
            field=models.CharField(
                choices=[
                    ("STRESS_VEGETATIF", "🌿 Stress végétatif"),
                    ("STRESS_HYDRIQUE", "💧 Stress hydrique"),
                    ("SECHERESSE", "🏜️ Sécheresse"),
                    ("EXCES_PLUIE", "🌧️ Excès de précipitations"),
                    ("GENERIC", "Alerte générique"),
                ],
                default="GENERIC",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="farmeralert",
            name="contributing_indicators",
            field=models.JSONField(blank=True, default=list),
        ),

        # 4. Ajouter les nouveaux index sur FarmerAlert.
        migrations.AddIndex(
            model_name="farmeralert",
            index=models.Index(fields=["champ", "alert_type", "-created_at"], name="agri_farmeralert_champ_type_idx"),
        ),
        migrations.AddIndex(
            model_name="farmeralert",
            index=models.Index(fields=["farmer", "risk_level", "-created_at"], name="agri_farmeralert_risk_idx"),
        ),

        # 5. Créer le modèle RiskAssessment.
        migrations.CreateModel(
            name="RiskAssessment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assessed_at", models.DateTimeField(db_index=True)),
                ("score", models.FloatField(help_text="Score global 0-100")),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("NORMAL", "🟢 Normal"),
                            ("VIGILANCE", "🟡 Vigilance"),
                            ("ALERT", "🟠 Alerte"),
                            ("CRITICAL", "🔴 Critique"),
                        ],
                        default="NORMAL",
                        max_length=15,
                    ),
                ),
                (
                    "sub_scores",
                    models.JSONField(
                        default=dict,
                        help_text="{'vegetation': 35, 'humidity': 28, 'drought': 45, 'rainfall': 10, 'forecast': 60}",
                    ),
                ),
                ("indicators_snapshot", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "champ",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="risk_assessments",
                        to="agriculture.champ",
                    ),
                ),
                (
                    "triggered_alerts",
                    models.ManyToManyField(
                        blank=True,
                        related_name="risk_assessments",
                        to="agriculture.farmeralert",
                    ),
                ),
            ],
            options={
                "ordering": ["-assessed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="riskassessment",
            index=models.Index(fields=["champ", "-assessed_at"], name="agri_risk_champ_idx"),
        ),
        migrations.AddIndex(
            model_name="riskassessment",
            index=models.Index(fields=["level", "-assessed_at"], name="agri_risk_level_idx"),
        ),
    ]

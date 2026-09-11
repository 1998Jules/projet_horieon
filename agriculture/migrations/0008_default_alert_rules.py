from django.db import migrations


DEFAULT_RULES = [
    {
        "name": "Sécheresse SPI prévisionnel",
        "indicator": "SPI_FORECAST",
        "operator": "LTE",
        "threshold": -1.0,
        "severity": "HIGH",
        "title_template": "Alerte sécheresse — {champ_nom}",
        "message_template": "Le SPI prévisionnel du champ {champ_nom} est de {value}, ce qui indique un risque de sécheresse pour la culture {culture}.",
        "recommendation_template": "Vérifier l'humidité du sol, planifier une irrigation si possible et surveiller les signes de stress hydrique.",
        "cooldown_hours": 24,
    },
    {
        "name": "Sécheresse SPI observé",
        "indicator": "SPI_3",
        "operator": "LTE",
        "threshold": -1.0,
        "severity": "MEDIUM",
        "title_template": "Sécheresse observée — {champ_nom}",
        "message_template": "Le SPI à 3 mois du champ {champ_nom} est de {value}. Les précipitations récentes sont inférieures aux normales.",
        "recommendation_template": "Réduire les pertes d'eau, vérifier les plants et adapter les travaux agricoles aux conditions sèches.",
        "cooldown_hours": 72,
    },
    {
        "name": "Baisse de vigueur NDVI",
        "indicator": "NDVI",
        "operator": "CHANGE_PCT",
        "threshold": 15.0,
        "severity": "MEDIUM",
        "title_template": "Baisse de vigueur — {champ_nom}",
        "message_template": "Le NDVI du champ {champ_nom} a varié de {variation_pct} depuis la dernière observation et vaut maintenant {value}.",
        "recommendation_template": "Inspecter le champ à la recherche de stress hydrique, ravageurs ou maladie.",
        "cooldown_hours": 72,
    },
    {
        "name": "Stress végétatif VHI",
        "indicator": "VHI",
        "operator": "LTE",
        "threshold": 35.0,
        "severity": "HIGH",
        "title_template": "Stress végétatif — {champ_nom}",
        "message_template": "Le VHI du champ {champ_nom} est de {value}, sous le seuil de vigilance.",
        "recommendation_template": "Contrôler l'état des cultures et rechercher les causes possibles de stress thermique ou hydrique.",
        "cooldown_hours": 48,
    },
    {
        "name": "Excès de précipitations",
        "indicator": "RAINFALL",
        "operator": "GTE",
        "threshold": 50.0,
        "severity": "MEDIUM",
        "title_template": "Pluies importantes — {champ_nom}",
        "message_template": "Les précipitations observées sur {champ_nom} atteignent {value} {unite}.",
        "recommendation_template": "Surveiller le drainage, l'érosion et l'accès au champ avant les prochaines interventions.",
        "cooldown_hours": 24,
    },
]


def create_default_rules(apps, schema_editor):
    AlertRule = apps.get_model("agriculture", "AlertRule")
    for data in DEFAULT_RULES:
        values = {"crop_type": "", **data}
        AlertRule.objects.get_or_create(name=data["name"], defaults=values)


def remove_default_rules(apps, schema_editor):
    AlertRule = apps.get_model("agriculture", "AlertRule")
    AlertRule.objects.filter(name__in=[rule["name"] for rule in DEFAULT_RULES]).delete()


class Migration(migrations.Migration):
    dependencies = [("agriculture", "0007_alertrule_farmeralert_alertdelivery_and_more")]
    operations = [migrations.RunPython(create_default_rules, remove_default_rules)]

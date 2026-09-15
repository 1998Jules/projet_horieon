"""Commande de surveillance agricole préventive.

Workflow complet :
1. COLLECTE — Pour chaque champ, interroge Earth Engine / CHIRPS-GEFS et
   peuple FieldIndicatorSnapshot avec NDVI, EVI, NDWI, MSAVI, SPI_30, SPI_90,
   SPI_FORECAST, RAINFALL_24H, RAINFALL_72H, VCI, TCI, VHI, NCWSI.
2. SCORING — Calcule un score de risque 0-100 en croisant les indicateurs
   (voir risk_engine.py) et persiste un RiskAssessment par champ.
3. ALERTES — Si le niveau de risque a changé depuis la dernière évaluation
   (aggravation ou amélioration), crée un FarmerAlert avec un message
   contextuel (stress végétatif, hydrique, sécheresse, excès pluie).
4. NOTIFICATIONS — Envoie les AlertDelivery EMAIL en attente via SMTP.

Usage :
    python manage.py evaluate_field_alerts                    # tout
    python manage.py evaluate_field_alerts --champ-id 5       # un seul champ
    python manage.py evaluate_field_alerts --dry-run          # simulation
    python manage.py evaluate_field_alerts --no-collect       # skip collecte (si déjà fait)
    python manage.py evaluate_field_alerts --no-email         # skip envoi emails
"""
from django.core.management.base import BaseCommand, CommandError

from agriculture.alert_services import evaluate_all_champs
from agriculture.indicator_collector import collect_all_champs
from agriculture.notification_services import send_pending_email_deliveries


class Command(BaseCommand):
    help = (
        "Surveillance agricole préventive : collecte les indicateurs, "
        "calcule le score de risque, crée les alertes si changement de "
        "niveau, et envoie les emails en attente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--champ-id", type=int,
            help="Limiter l'analyse à un champ (par ID).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Calculer les alertes sans les enregistrer ni envoyer d'email.",
        )
        parser.add_argument(
            "--no-collect", action="store_true",
            help="Sauter l'étape de collecte (si les snapshots sont déjà à jour).",
        )
        parser.add_argument(
            "--no-email", action="store_true",
            help="Créer les alertes sans envoyer les emails en attente.",
        )
        parser.add_argument(
            "--limit-email", type=int, default=100,
            help="Nombre maximum d'emails à traiter (défaut : 100).",
        )

    def handle(self, *args, **options):
        if options["limit_email"] < 1:
            raise CommandError("--limit-email doit être supérieur à zéro.")

        champ_id = options.get("champ_id")
        dry_run = options["dry_run"]
        no_collect = options["no_collect"]
        no_email = options["no_email"]

        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(self.style.MIGRATE_HEADING("SURVEILLANCE AGRICOLE PRÉVENTIVE"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))

        # ---------- 1. COLLECTE ----------
        if no_collect:
            self.stdout.write(self.style.WARNING("⏭️  Étape collecte ignorée (--no-collect)"))
        else:
            self.stdout.write(self.style.MIGRATE_HEADING("\n📡 ÉTAPE 1/4 — Collecte des indicateurs"))
            try:
                collect_reports = collect_all_champs(champ_id=champ_id)
                total_persisted = sum(r.get("count_persisted", 0) for r in collect_reports)
                total_errors = sum(len(r.get("errors", [])) for r in collect_reports)
                self.stdout.write(
                    f"   ✓ {len(collect_reports)} champ(s) traité(s) — "
                    f"{total_persisted} snapshot(s) persisté(s), {total_errors} erreur(s)"
                )
                for r in collect_reports:
                    if r.get("errors"):
                        self.stdout.write(
                            f"     Champ {r.get('champ_nom', r.get('champ_id'))} : "
                            + ", ".join(r["errors"][:3])
                        )
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Erreur collecte : {exc}"))
                if options["verbosity"] > 1:
                    import traceback
                    traceback.print_exc()

        # ---------- 2 & 3. SCORING + ALERTES ----------
        self.stdout.write(self.style.MIGRATE_HEADING("\n🎯 ÉTAPE 2/4 — Scoring & détection d'alertes"))
        results = evaluate_all_champs(champ_id=champ_id, dry_run=dry_run)

        total_alerts = 0
        total_deliveries = 0
        for result in results:
            level_emoji = {
                "NORMAL": "🟢", "VIGILANCE": "🟡",
                "ALERT": "🟠", "CRITICAL": "🔴",
            }.get(result.level, "⚪")
            self.stdout.write(
                f"   {level_emoji} Champ {result.champ_id} ({result.champ_nom}) : "
                f"score={result.score:.0f}/100 niveau={result.level}"
            )
            if result.previous_level:
                self.stdout.write(
                    f"      précédent={result.previous_level} → "
                    f"{'CHANGEMENT' if result.level_changed else 'inchangé'}"
                )
            if result.alert_types:
                self.stdout.write(f"      types détectés : {', '.join(result.alert_types)}")
            if result.errors:
                self.stdout.write(self.style.ERROR(
                    f"      erreurs : {', '.join(result.errors[:2])}"
                ))
            if dry_run and result.alerts_created:
                self.stdout.write(self.style.WARNING(
                    f"      (dry-run) {result.alerts_created} alerte(s) aurait été créée(s)"
                ))
            total_alerts += result.alerts_created
            total_deliveries += result.deliveries_created

        self.stdout.write(
            self.style.SUCCESS(
                f"\n   Récap : {total_alerts} alerte(s) créée(s), "
                f"{total_deliveries} livraison(s) email programmée(s)"
            )
        )

        # ---------- 4. ENVOI EMAILS ----------
        if dry_run or no_email:
            self.stdout.write(self.style.WARNING(
                "\n⏭️  Étape envoi emails ignorée"
                + (" (dry-run)" if dry_run else " (--no-email)")
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("\n📧 ÉTAPE 4/4 — Envoi des emails en attente"))
        counters = send_pending_email_deliveries(limit=options["limit_email"])
        self.stdout.write(
            self.style.SUCCESS(
                f"   ✓ {counters['sent']} envoyé(s), "
                f"{counters['failed']} échec(s), "
                f"{counters['skipped']} ignoré(s)"
            )
        )

        self.stdout.write(self.style.MIGRATE_HEADING("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ Surveillance terminée."))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))

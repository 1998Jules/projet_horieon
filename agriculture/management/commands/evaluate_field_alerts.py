from django.core.management.base import BaseCommand, CommandError

from agriculture.alert_services import evaluate_all_champs
from agriculture.notification_services import send_pending_email_deliveries


class Command(BaseCommand):
    help = "Évalue les indicateurs des champs, crée les alertes et envoie les e-mails en attente."

    def add_arguments(self, parser):
        parser.add_argument("--champ-id", type=int, help="Limiter l'analyse à un champ.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculer les alertes sans les enregistrer ni envoyer d'e-mail.",
        )
        parser.add_argument(
            "--limit-email",
            type=int,
            default=100,
            help="Nombre maximum d'e-mails à traiter (défaut : 100).",
        )
        parser.add_argument(
            "--no-email",
            action="store_true",
            help="Créer les alertes sans envoyer les e-mails en attente.",
        )

    def handle(self, *args, **options):
        if options["limit_email"] < 1:
            raise CommandError("--limit-email doit être supérieur à zéro.")

        results = evaluate_all_champs(
            champ_id=options.get("champ_id"),
            dry_run=options["dry_run"],
        )
        for result in results:
            self.stdout.write(
                f"Champ {result.champ_id}: {result.rules_matched} règle(s), "
                f"{result.alerts_created} alerte(s), {result.deliveries_created} livraison(s)."
            )

        if options["dry_run"] or options["no_email"]:
            return

        counters = send_pending_email_deliveries(limit=options["limit_email"])
        self.stdout.write(
            self.style.SUCCESS(
                f"E-mails : {counters['sent']} envoyé(s), "
                f"{counters['failed']} échec(s), {counters['skipped']} ignoré(s)."
            )
        )

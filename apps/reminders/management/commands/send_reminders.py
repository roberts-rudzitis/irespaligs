"""Send the daily reminder emails. Scheduled once a day (07:00 Europe/Riga) on the host.

    python manage.py send_reminders
    python manage.py send_reminders --date 01.12.2026   # pretend it's another day (testing)
"""

from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.reminders.services import send_reminders


class Command(BaseCommand):
    help = "Send daily reminder emails to landlords."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="dd.mm.yyyy – run as if today were this date")

    def handle(self, *args, **options):
        today = datetime.strptime(options["date"], "%d.%m.%Y").date() if options["date"] else timezone.localdate()
        count = send_reminders(today)
        self.stdout.write(f"Sent {count} reminder email(s) for {today:%d.%m.%Y}.")

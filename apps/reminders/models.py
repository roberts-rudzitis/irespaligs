from django.conf import settings
from django.db import models


class ReminderLog(models.Model):
    """Remembers which reminders were already sent, so nobody gets the same one twice.

    `key` identifies what the reminder was about, e.g. "statement:42" or "month:2026-11".
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reminder_logs")
    kind = models.CharField(max_length=30)
    key = models.CharField(max_length=50)
    sent_at = models.DateTimeField(auto_now_add=True)

    owner_lookup = "user"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "kind", "key"], name="reminder_sent_once")]

from django.db import models


class OwnedQuerySet(models.QuerySet):
    """Every model holding a landlord's data uses this, so views can always do
    `Model.objects.for_owner(request.user)` and never see other landlords' rows.

    Each model sets `owner_lookup` to the path from the model to its User,
    e.g. "owner" for Property, "property__owner" for Lease.
    """

    def for_owner(self, user):
        return self.filter(**{self.model.owner_lookup: user})


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

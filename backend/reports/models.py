from django.db import models
from django.conf import settings


class VehicleReport(models.Model):
    vin                    = models.CharField(max_length=17, unique=True, db_index=True)
    raw_data               = models.JSONField()
    risk_score             = models.IntegerField()
    accident_count         = models.IntegerField(default=0)
    owner_count            = models.IntegerField(null=True, blank=True)
    has_salvage_title      = models.BooleanField(default=False)
    has_flood_damage       = models.BooleanField(default=False)
    open_recall_count      = models.IntegerField(default=0)
    last_reported_odometer = models.IntegerField(null=True, blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    updated_at             = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vin} — score: {self.risk_score}"


class ReportLookup(models.Model):
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report    = models.ForeignKey(VehicleReport, on_delete=models.CASCADE)
    looked_up = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-looked_up']


class OwnedVehicle(models.Model):
    user     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_vehicles',
    )
    vin      = models.CharField(max_length=17)
    nickname = models.CharField(max_length=100, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'vin')

    def __str__(self):
        return f"{self.user} — {self.vin}"

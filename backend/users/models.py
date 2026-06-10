import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    stripe_customer_id  = models.CharField(max_length=100, blank=True, null=True)
    subscription_status = models.CharField(max_length=30, default='inactive')
    subscription_id     = models.CharField(max_length=100, blank=True, null=True)
    lookup_credits      = models.IntegerField(default=0)

    @property
    def can_lookup(self):
        return (
            self.subscription_status == 'active'
            or self.lookup_credits > 0
            or (hasattr(self, 'dealer_profile') and self.dealer_profile.is_active)
        )

    def __str__(self):
        return self.username


class DealerProfile(models.Model):
    user            = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='dealer_profile'
    )
    business_name   = models.CharField(max_length=200)
    brand_color     = models.CharField(max_length=7, default='#185FA5')
    logo_url        = models.URLField(blank=True, null=True)
    stripe_sub_id   = models.CharField(max_length=100, blank=True, null=True)
    is_active       = models.BooleanField(default=False)
    monthly_lookups = models.IntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name


class PushToken(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_tokens')
    token      = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.token[:24]}..."


class APIKey(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    key        = models.CharField(max_length=64, unique=True, db_index=True)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used  = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_urlsafe(40)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} — {self.name}"

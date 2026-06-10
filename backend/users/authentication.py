from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        key = request.META.get('HTTP_X_API_KEY')
        if not key:
            return None
        try:
            api_key = APIKey.objects.select_related('user').get(key=key, is_active=True)
            api_key.last_used = timezone.now()
            api_key.save(update_fields=['last_used'])
            return (api_key.user, api_key)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid API key.')

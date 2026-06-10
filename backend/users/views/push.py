from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import PushToken


class RegisterPushTokenView(APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token required.'}, status=400)
        PushToken.objects.get_or_create(user=request.user, token=token)
        return Response({'success': True})

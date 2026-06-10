from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import APIKey


class APIKeyView(APIView):

    def get(self, request):
        keys = APIKey.objects.filter(user=request.user, is_active=True)
        return Response({'keys': [
            {'id': k.id, 'name': k.name, 'key': k.key,
             'created_at': k.created_at, 'last_used': k.last_used}
            for k in keys
        ]})

    def post(self, request):
        name = request.data.get('name', 'Default key')
        key  = APIKey.objects.create(user=request.user, name=name)
        return Response({'id': key.id, 'name': key.name, 'key': key.key})

    def delete(self, request, key_id):
        APIKey.objects.filter(user=request.user, id=key_id).update(is_active=False)
        return Response({'success': True})

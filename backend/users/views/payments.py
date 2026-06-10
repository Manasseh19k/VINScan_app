from rest_framework.views import APIView
from rest_framework.response import Response
from decouple import config
from users.services.stripe_service import (
    create_subscription_checkout,
    create_lookup_checkout,
    create_dealer_checkout,
    cancel_subscription,
)

BASE = config('FRONTEND_URL', default='https://your-app.railway.app')


class SubscriptionCheckoutView(APIView):
    def post(self, request):
        url = create_subscription_checkout(
            user=request.user,
            success_url=f'{BASE}/api/payments/success/?type=subscription',
            cancel_url=f'{BASE}/api/payments/cancel/',
        )
        return Response({'checkout_url': url})


class LookupCheckoutView(APIView):
    def post(self, request):
        url = create_lookup_checkout(
            user=request.user,
            success_url=f'{BASE}/api/payments/success/?type=lookup',
            cancel_url=f'{BASE}/api/payments/cancel/',
        )
        return Response({'checkout_url': url})


class DealerCheckoutView(APIView):
    def post(self, request):
        business_name = request.data.get('business_name', '')
        url = create_dealer_checkout(
            user=request.user,
            business_name=business_name,
            success_url=f'{BASE}/api/payments/success/?type=dealer',
            cancel_url=f'{BASE}/api/payments/cancel/',
        )
        return Response({'checkout_url': url})


class CancelSubscriptionView(APIView):
    def post(self, request):
        cancel_subscription(request.user)
        return Response({'message': 'Subscription will cancel at period end.'})


class BillingStatusView(APIView):
    def get(self, request):
        u = request.user
        is_dealer = hasattr(u, 'dealer_profile') and u.dealer_profile.is_active
        return Response({
            'subscription_status': u.subscription_status,
            'lookup_credits':       u.lookup_credits,
            'can_lookup':           u.can_lookup,
            'is_dealer':            is_dealer,
            'dealer_name':          u.dealer_profile.business_name if is_dealer else None,
        })

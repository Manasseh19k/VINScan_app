from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from reports.views import (
    VehicleReportView, UserReportHistoryView, ReportPDFView,
    BatchVINLookupView, DealerUsageView, OwnedVehicleView,
)
from users.views.payments import (
    SubscriptionCheckoutView, LookupCheckoutView,
    DealerCheckoutView, CancelSubscriptionView, BillingStatusView,
)
from users.views.webhooks import stripe_webhook
from users.views.push     import RegisterPushTokenView
from users.views.api_keys import APIKeyView
from users.views.auth import SignUpView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('api/auth/token/',         TokenObtainPairView.as_view()),
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),
    path('api/auth/register/',      SignUpView.as_view()),

    # Reports
    path('api/report/',             VehicleReportView.as_view()),
    path('api/report/<str:vin>/pdf/', ReportPDFView.as_view()),
    path('api/history/',            UserReportHistoryView.as_view()),

    # Owned vehicles (garage)
    path('api/vehicles/',           OwnedVehicleView.as_view()),
    path('api/vehicles/<str:vin>/', OwnedVehicleView.as_view()),

    # Dealer
    path('api/dealer/batch/',       BatchVINLookupView.as_view()),
    path('api/dealer/profile/',     DealerUsageView.as_view()),

    # Payments
    path('api/payments/subscribe/', SubscriptionCheckoutView.as_view()),
    path('api/payments/lookup/',    LookupCheckoutView.as_view()),
    path('api/payments/dealer/',    DealerCheckoutView.as_view()),
    path('api/payments/cancel/',    CancelSubscriptionView.as_view()),
    path('api/payments/billing/',   BillingStatusView.as_view()),

    # Stripe webhook
    path('api/webhooks/stripe/',    stripe_webhook),

    # Push notifications
    path('api/push/register/',      RegisterPushTokenView.as_view()),

    # B2B API keys
    path('api/keys/',               APIKeyView.as_view()),
    path('api/keys/<int:key_id>/',  APIKeyView.as_view()),

    # Health check
    path('api/health/', lambda r: JsonResponse({'status': 'ok'})),
]

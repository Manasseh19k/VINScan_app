import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decouple import config
from users.models import User, DealerProfile

WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig     = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    handlers = {
        'checkout.session.completed':    _handle_checkout_complete,
        'customer.subscription.updated': _handle_subscription_updated,
        'customer.subscription.deleted': _handle_subscription_deleted,
        'invoice.payment_failed':        _handle_payment_failed,
    }
    handler = handlers.get(event['type'])
    if handler:
        handler(event['data']['object'])
    return HttpResponse(status=200)


def _get_user_by_metadata(obj):
    user_id = obj.get('metadata', {}).get('user_id')
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def _get_user_by_customer(customer_id):
    try:
        return User.objects.get(stripe_customer_id=customer_id)
    except User.DoesNotExist:
        return None


def _handle_checkout_complete(session):
    user = _get_user_by_metadata(session)
    if not user:
        return
    payment_type = session.get('metadata', {}).get('type')

    if payment_type == 'subscription':
        user.subscription_status = 'active'
        user.subscription_id     = session.get('subscription')
        user.save(update_fields=['subscription_status', 'subscription_id'])

    elif payment_type == 'lookup':
        from django.db.models import F
        User.objects.filter(id=user.id).update(lookup_credits=F('lookup_credits') + 1)

    elif payment_type == 'dealer':
        business_name = session.get('metadata', {}).get('business_name', '')
        DealerProfile.objects.get_or_create(
            user=user,
            defaults={'business_name': business_name, 'is_active': True},
        )
        user.subscription_status = 'active'
        user.subscription_id     = session.get('subscription')
        user.save(update_fields=['subscription_status', 'subscription_id'])


def _handle_subscription_updated(subscription):
    user = _get_user_by_customer(subscription['customer'])
    if user:
        user.subscription_status = subscription['status']
        user.save(update_fields=['subscription_status'])


def _handle_subscription_deleted(subscription):
    user = _get_user_by_customer(subscription['customer'])
    if user:
        user.subscription_status = 'inactive'
        user.subscription_id     = None
        user.save(update_fields=['subscription_status', 'subscription_id'])


def _handle_payment_failed(invoice):
    user = _get_user_by_customer(invoice['customer'])
    if user:
        user.subscription_status = 'past_due'
        user.save(update_fields=['subscription_status'])

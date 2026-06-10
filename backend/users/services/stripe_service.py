import stripe
from decouple import config

stripe.api_key = config('STRIPE_SECRET_KEY', default='')

MONTHLY_PRICE_ID = config('STRIPE_MONTHLY_PRICE_ID', default='')
LOOKUP_PRICE_ID  = config('STRIPE_LOOKUP_PRICE_ID',  default='')
DEALER_PRICE_ID  = config('STRIPE_DEALER_PRICE_ID',  default='')


def get_or_create_customer(user) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.first_name} {user.last_name}".strip() or user.username,
        metadata={'user_id': str(user.id)},
    )
    user.stripe_customer_id = customer.id
    user.save(update_fields=['stripe_customer_id'])
    return customer.id


def create_subscription_checkout(user, success_url: str, cancel_url: str) -> str:
    customer_id = get_or_create_customer(user)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': MONTHLY_PRICE_ID, 'quantity': 1}],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'user_id': str(user.id), 'type': 'subscription'},
    )
    return session.url


def create_lookup_checkout(user, success_url: str, cancel_url: str) -> str:
    customer_id = get_or_create_customer(user)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': LOOKUP_PRICE_ID, 'quantity': 1}],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'user_id': str(user.id), 'type': 'lookup'},
    )
    return session.url


def create_dealer_checkout(user, business_name: str,
                            success_url: str, cancel_url: str) -> str:
    customer_id = get_or_create_customer(user)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': DEALER_PRICE_ID, 'quantity': 1}],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'user_id':       str(user.id),
            'type':          'dealer',
            'business_name': business_name,
        },
    )
    return session.url


def cancel_subscription(user) -> None:
    if user.subscription_id:
        stripe.Subscription.modify(user.subscription_id, cancel_at_period_end=True)
        user.subscription_status = 'canceled'
        user.save(update_fields=['subscription_status'])

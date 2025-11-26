from django.contrib.auth.models import User
import payment.types as payment_types
from core.models import PaymentGatewaySettings

uniq_id = 0

def get_uniq_id():
    global uniq_id
    r = uniq_id
    uniq_id += 1
    return r

def create_gateways_settings():
    for k, v in payment_types.GATEWAY_CHOICES:
        PaymentGatewaySettings.objects.create(
            type=k,
            commission_extra=0.5,
        )


def create_user():
    username = f'username{get_uniq_id()}'
    email = f'{username}@localhost'
    return User.objects.create_user(
        username=username,
        email=email,
    )
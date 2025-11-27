import json
from django.urls import reverse
from urllib.parse import urlparse, parse_qs

from django.contrib.auth.models import User
from django.test import Client, TestCase
import payment.types as payment_types
from core.models import PaymentGatewaySettings, Profile, get_profile, TopUpRequest
import sitebuilder.settings


uniq_id = 0

def get_uniq_id():
    global uniq_id
    r = uniq_id
    uniq_id += 1
    return r

class FakeUser:

    def __init__(self, p: Profile):

        self.user = p.user
        self.client = Client(HTTP_HOST='localhost:8000')


    def login_user(self):
        self.client.force_login(self.user)


def create_gateways_settings():
    for k, _ in payment_types.GATEWAY_CHOICES:
        for m, _ in TopUpRequest.METHOD_CHOICES:
            for c, _ in TopUpRequest.CURRENCY_CHOICES:
                PaymentGatewaySettings.objects.create(
                    type=k,
                    commission_extra=0.5,
                    method=m,
                    currency=c
                )


def create_profile():
    username = f'username{get_uniq_id()}'
    email = f'{username}@localhost'
    u = User.objects.create_user(
        username=username,
        email=email,
    )
    return get_profile(u)


def view_topup_create(p: Profile, currency: str, method: str):

    u = FakeUser(
        p=p,
    )
    u.login_user()

    print(f"User ID in session: {u.client.session.get('_auth_user_id')}")
    print(f"User is authenticated: {u.user.is_authenticated}")
    from django.conf import settings
    print(f"LOGIN_URL: {settings.LOGIN_URL}")


    data = {}
    data['currency'] = currency
    data['method'] = method
    data['disclaimer']  = 1

    url = reverse('topup_create', kwargs={})
    print(f"URL: {url}")
    response = u.client.post(url,
                    data=json.dumps(data),
                    content_type='application/json',
                )
    if response.status_code != 200:
        print(response)
        return None, f"Response.status_code <> 200: {response.status_code}"


    response_data = response.json()

    if response_data['status'] != True:
        return None, f"Status != True: {response_data.get('error', 'Unknown error')}"

    redirect_url = response_data.get('redirect', '')
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    topup_id = query_params.get('open', [None])[0]

    topup = TopUpRequest.objects.filter(id=topup_id, user=p.user).first()

    if not topup:
        return None, f"Can't find topup with id: {topup_id}"

    return topup, f"Success"

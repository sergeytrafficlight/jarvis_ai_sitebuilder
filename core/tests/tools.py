import json
from django.urls import reverse
from urllib.parse import urlparse, parse_qs

from django.contrib.auth.models import User
from django.test import Client, TestCase
import payment.types as payment_types
from core.models import PaymentGatewaySettings, Profile, get_profile, TopUpRequest, SiteProject, SubSiteProject
from core.tools import generate_uniq_subsite_dir_for_site
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


    data = {}
    data['currency'] = currency
    data['method'] = method
    data['disclaimer']  = 1

    url = reverse('topup_create', kwargs={})

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


def view_payment_receive_topup(p:Profile, topup: TopUpRequest, amount:float, status: str, txId: str):
    u = FakeUser(
        p=p,
    )
    u.login_user()

    data = {}
    data['uuid'] = str(topup.payment_gateway_transaction_id)
    data['amount'] = str(amount)
    data['currency']  = topup.payment_gateway_settings.currency
    data['status'] = status
    data['txId'] = str(txId)
    data['targetCurrency'] = topup.payment_gateway_settings.currency
    data['externalId'] = str(topup.id)
    data['customerId'] = str(topup.user.id)


    url = reverse('payment_receive_topup', kwargs={'gateway': topup.payment_gateway_settings.type, 'topup_request_id': topup.id})
    response = u.client.post(url,
                    data=json.dumps(data),
                    content_type='application/json',
                )

    return response.status_code == 200

def view_topup_request_status(p: Profile, topup: TopUpRequest):
    u = FakeUser(
        p=p,
    )
    u.login_user()
    url = reverse('topup_request_status', kwargs={'request_id': topup.id})
    response = u.client.get(url)
    if response.status_code != 200:
        return False, f"Response status code: {response.status_code} <> 200"

    return True, f"Success"


def create_site_sub_site(p: Profile):

    name = f"Site {get_uniq_id()}"
    site = SiteProject.objects.create(
        user=p.user,
        name=name,
        prompt='',
        ref_site_url=None,
    )

    full_path, uniq_dir = generate_uniq_subsite_dir_for_site(site)

    sub_site = SubSiteProject.objects.create(
        site=site,
        root_sub_site=None,
        dir=uniq_dir,
    )

    return sub_site




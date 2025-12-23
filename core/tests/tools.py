import json
import os
from django.urls import reverse
from django.db import connection
from urllib.parse import urlparse, parse_qs

from django.contrib.auth.models import User
from django.test import Client, TestCase
import payment.types as payment_types
from core.models import PaymentGatewaySettings, Profile, get_profile, TopUpRequest, SiteProject, SubSiteProject, AIModelsSettings
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


def create_site(p: Profile):
    site = SiteProject.objects.create(
        user=p.user,
        name=get_uniq_id(),
    )
    return site

def create_sub_site(site: SiteProject):
    full_path, uniq_dir = generate_uniq_subsite_dir_for_site(site)

    sub_site = SubSiteProject.objects.create(
        site=site,
        root_sub_site=None,
        dir=uniq_dir,
    )

    return sub_site

def create_ai_model_settings(engine: str, model: str = '', format: str = ''):

    return AIModelsSettings.objects.create(
        engine=engine,
        model=model,
        format=format,
    )


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


def compare_dicts(d1, d2):
    differences = []

    def compare(v1, v2, path="root"):
        # Разные типы
        if type(v1) != type(v2):
            differences.append(
                f"{path}: type mismatch ({type(v1).__name__} != {type(v2).__name__})"
            )
            return

        # Словари
        if isinstance(v1, dict):
            keys1 = set(v1.keys())
            keys2 = set(v2.keys())

            for key in keys1 - keys2:
                differences.append(f"{path}: key '{key}' missing in second dict")

            for key in keys2 - keys1:
                differences.append(f"{path}: extra key '{key}' in second dict")

            for key in keys1 & keys2:
                compare(v1[key], v2[key], f"{path}.{key}")

        # Списки / кортежи
        elif isinstance(v1, (list, tuple)):
            if len(v1) != len(v2):
                differences.append(
                    f"{path}: length mismatch ({len(v1)} != {len(v2)})"
                )
                return

            for i, (i1, i2) in enumerate(zip(v1, v2)):
                compare(i1, i2, f"{path}[{i}]")

        # Множества
        elif isinstance(v1, set):
            if v1 != v2:
                differences.append(
                    f"{path}: set mismatch ({v1} != {v2})"
                )

        # Остальные типы
        else:
            if v1 != v2:
                differences.append(
                    f"{path}: value mismatch ({v1} != {v2})"
                )

    compare(d1, d2)

    if differences:
        return False, "; ".join(differences)

    return True, "OK"


def restore_ai_settings():
    sql_path = os.path.join(os.path.dirname(__file__), '../../ai_settings.sql')
    with open(sql_path, 'r') as f:
        sql_statements = f.read()
    with connection.cursor() as cursor:
        for statement in sql_statements.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)



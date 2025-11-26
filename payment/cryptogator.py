import time
import hmac
import hashlib
import requests
import json
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth.models import User
from core.models import TopUpRequest, PaymentGatewaySettings
from django.urls import reverse
import payment.types as payment_types
from config import PAYMENT_GATEWAY_CRYPTOGATOR_API_KEY, PAYMENT_GATEWAY_CRYPTOGATOR_SECRET_KEY, PAYMENT_GATEWAY_CRYPTOGATOR_BASE_URL, SITE_URL

def convert_method(method: str):
    if method == TopUpRequest.METHOD_TRON:
        return 'Tron'
    elif method == TopUpRequest.METHOD_ETHEREUM:
        return 'Etherium'

    raise Exception(f"Unknown method: {method}")

def sign(timestamp, http_method, api_method, body):
    s = f"{timestamp}{http_method}{api_method}"
    s += "{"
    first = True
    for k in body:
        if not first:
            s += ', '
        s += f"\"{k}\": \"{str(body[k])}\""
        first = False
    s += "}"
    signature = hmac.new(
        PAYMENT_GATEWAY_CRYPTOGATOR_SECRET_KEY.encode('utf-8'),
        s.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature

def get_topup(user: User, method: str, currency: str):

    if not method in dict(TopUpRequest.METHOD_CHOICES):
        raise Exception(f"Unknown method: {method}")

    if not currency in dict(TopUpRequest.CURRENCY_CHOICES):
        raise Exception(f"Unknown currency: {currency}")

    topup = TopUpRequest.objects.create(
        status=TopUpRequest.STATUS_AWAITING,
        user=user,
        method=method,
        provider=TopUpRequest.PROVIDER_CRYPTOGATOR,
    )

    http_method = 'POST'
    http_function = '/v1/platforms/orders'
    callback_url = SITE_URL+reverse("payment_receive_topup", kwargs={
        "gateway": payment_types.GATEWAY_CRYPTOGATOR,
        "topup_request_id": topup.id
    })
    timestamp = int(time.time())
    data = {
        "externalId": f"{topup.id}",
        "blockchain": method,
        "currency": currency,
        "customerId": f"{user.id}",
        "callbackUrl": callback_url,
    }

    headers = {
        "X-Api-Key": PAYMENT_GATEWAY_CRYPTOGATOR_API_KEY,
        "X-Signature": sign(timestamp, http_method, http_function, data),
        "X-Timestamp": f"{timestamp}",
        "Content-Type": "application/json"
    }

    url = f"{PAYMENT_GATEWAY_CRYPTOGATOR_BASE_URL}{http_function}"
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"Repsonse code {response.status_code} ({payment_types.GATEWAY_CRYPTOGATOR}) {http_function}")
    #print(f"Status Code: {response.status_code}")
    #print(f"Response: {response.text}")

    try:
        settings = PaymentGatewaySettings.objects.get(type=payment_types.GATEWAY_CRYPTOGATOR)
        data = json.loads(response.text)
        status = data.get('status')
        expired_at = data.get('expiredAt')

        expired_at = datetime.strptime(expired_at, "%Y-%m-%d %H:%M:%S")
        expired_at = timezone.make_aware(expired_at)
        comission_rate = Decimal(settings.commission_extra)

        if status != 'NEW':
            raise Exception(f"{payment_types.GATEWAY_CRYPTOGATOR} invalid status {status}")


        topup.status = TopUpRequest.STATUS_AWAITING
        topup.wallet_to_pay_address = data.get('address')
        topup.expired_at = expired_at
        topup.amount_min_for_order = data.get('minAmount')
        topup.payment_gateway_transaction_id = data.get('uuid')
        topup.comission = comission_rate
        topup.save()


    except ValueError as e:
        raise Exception(f"{payment_types.GATEWAY_CRYPTOGATOR} JSON error {str(e)}")

    return topup

def webhook(post_data: str, topup_request_id: str):

    try:
        uuid = post_data.get('uuid')
        amount = post_data.get('amount')
        amount = float(amount)

        currency = post_data.get("currency")
        status = post_data.get('status')
        trx_id = post_data.get('trxId')
        target_currency = post_data.get('targetCurrency')
        external_id = post_data.get('externalId')
        customer_id = post_data.get('customerId')
    except Exception as e:
        raise Exception(f"{payment_types.GATEWAY_CRYPTOGATOR} wehook parsing error: {str(e)}")

    if topup_request_id != external_id:
        raise Exception(f"error 0x01")

    user = User.objects.filter(
        id=customer_id
    ).first()

    if not user:
        raise Exception(f"error 0x02")

    if not status == 'DONE':
        raise Exception(f"error 0x03")


    topup = TopUpRequest.objects.filter(
        user=user,
        status=TopUpRequest.STATUS_AWAITING,
        provider=payment_types.GATEWAY_CRYPTOGATOR,
        currency=currency,
        payment_gateway_transaction_id=uuid,
    ).first()

    if not topup:
        raise Exception(f"error 0x04")

    


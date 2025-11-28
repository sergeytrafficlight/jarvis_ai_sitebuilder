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
from config import PAYMENT_GATEWAY_CRYPTOGATOR_API_KEY, PAYMENT_GATEWAY_CRYPTOGATOR_SECRET_KEY, \
    PAYMENT_GATEWAY_CRYPTOGATOR_BASE_URL_ADAPTER, PAYMENT_GATEWAY_CRYPTOGATOR_BASE_URL_PARTNER, SITE_URL, DEBUG
import core.funds_balance as funds_balance

from core.log import *
logger.setLevel(logging.DEBUG)

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

def get_topup(user: User, pgs: PaymentGatewaySettings):


    topup = TopUpRequest.objects.create(
        status=TopUpRequest.STATUS_AWAITING,
        user=user,
        payment_gateway_settings=pgs,
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
        "blockchain": pgs.method,
        "currency": pgs.currency,
        "customerId": f"{user.id}",
        "callbackUrl": callback_url,
    }

    headers = {
        "X-Api-Key": PAYMENT_GATEWAY_CRYPTOGATOR_API_KEY,
        "X-Signature": sign(timestamp, http_method, http_function, data),
        "X-Timestamp": f"{timestamp}",
        "Content-Type": "application/json"
    }

    url = f"{PAYMENT_GATEWAY_CRYPTOGATOR_BASE_URL_ADAPTER}{http_function}"
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        logger.error(f"response status: {response.status_code} | {response.text}")
        raise Exception(f"Repsonse code {response.status_code} ({payment_types.GATEWAY_CRYPTOGATOR}) {http_function}")
    #print(f"Status Code: {response.status_code}")
    #print(f"Response: {response.text}")

    try:

        data = json.loads(response.text)
        status = data.get('status')
        expired_at = data.get('expiredAt')

        expired_at = datetime.strptime(expired_at, "%Y-%m-%d %H:%M:%S")
        expired_at = timezone.make_aware(expired_at)


        if status != 'NEW':
            logger.error(f"wrong status: {status}")
            raise Exception(f"{payment_types.GATEWAY_CRYPTOGATOR} invalid status {status}")


        topup.status = TopUpRequest.STATUS_AWAITING
        topup.wallet_to_pay_address = data.get('address')
        topup.expired_at = expired_at
        topup.amount_min_for_order = data.get('minAmount')
        topup.payment_gateway_transaction_id = data.get('uuid')
        topup.save()


    except ValueError as e:
        logger.error(f"Can't parse json {str(e)}")
        raise Exception(f"{payment_types.GATEWAY_CRYPTOGATOR} JSON error {str(e)}")

    return topup

def _commit_topup(topup_request: TopUpRequest, amount: Decimal, blockchain_trx_id: str):
    topup_transaction = funds_balance.topup(
        user=topup_request.user,
        amount=amount,
        description=f'trx id: {blockchain_trx_id}, topup request id: {topup_request.id}'
    )

    topup_request.amount = amount
    topup_request.status = TopUpRequest.STATUS_DONE
    topup_request.blockchain_trx_id = blockchain_trx_id
    topup_request.topup_transaction = topup_transaction

    topup_request.save()


def webhook(post_data: str, topup_request_id: str):

    logger.debug(f"webhook topup id: {topup_request_id} post data: {str(post_data)}", payment_gateway=payment_types.GATEWAY_CRYPTOGATOR)

    try:
        uuid = post_data.get('uuid')
        amount = post_data.get('amount')
        amount = Decimal(amount)

        currency = post_data.get("currency")
        status = post_data.get('status')
        trx_id = post_data.get('txId')
        target_currency = post_data.get('targetCurrency')
        external_id = post_data.get('externalId')
        customer_id = post_data.get('customerId')
    except Exception as e:
        raise Exception(f"{payment_types.GATEWAY_CRYPTOGATOR} wehook parsing error: {str(e)}")

    if str(topup_request_id) != str(external_id):
        logger.error(f"webhook topup id: {topup_request_id} post data: {str(post_data)} "+
                     f"topup_request_id ({topup_request_id}) != external_id ({external_id})",
                     payment_gateway=payment_types.GATEWAY_CRYPTOGATOR,
                     payment_error='0x01',
                     )
        raise Exception(f"error 0x01")

    user = User.objects.filter(
        id=customer_id
    ).first()

    if not user:
        logger.error(f"webhook topup id: {topup_request_id} post data: {str(post_data)}"+
                     f"can't find user: {customer_id}",
                     payment_gateway=payment_types.GATEWAY_CRYPTOGATOR,
                     payment_error='0x02',
                     )

        raise Exception(f"error 0x02")

    if not status == 'DONE':
        logger.error(f"webhook topup id: {topup_request_id} post data: {str(post_data)}"+
                     f"wrong status {status}",
                     payment_gateway=payment_types.GATEWAY_CRYPTOGATOR,
                     payment_error='0x03',
                     )

        raise Exception(f"error 0x03")

    if currency != target_currency:
        logger.error(f"webhook topup id: {topup_request_id} post data: {str(post_data)}"+
                     f"currency missmatch currency {currency} != target_currency {target_currency}",
                     payment_gateway=payment_types.GATEWAY_CRYPTOGATOR,
                     payment_error='0x04',
                     )

        raise Exception(f"error 0x04")


    topup_request = TopUpRequest.objects.filter(
        user=user,
        status=TopUpRequest.STATUS_AWAITING,
        payment_gateway_settings__type=payment_types.GATEWAY_CRYPTOGATOR,
        payment_gateway_settings__currency=currency,
        payment_gateway_transaction_id=uuid,
        topup_transaction__isnull=True,
        id=topup_request_id,
    ).first()

    if not topup_request:
        if not currency != target_currency:
            logger.error(f"webhook topup id: {topup_request_id} post data: {str(post_data)}" +
                         f"can't find topuprequest",
                         payment_gateway=payment_types.GATEWAY_CRYPTOGATOR,
                         payment_error='0x05',
                         )

        raise Exception(f"error 0x05")
    _commit_topup(topup_request, amount, trx_id)

    return True

def recheck_topup_request(topup_request: TopUpRequest):

    date_from = (topup_request.created_at - timedelta(days=1)).strftime("%Y-%m-%d")
    date_to = (topup_request.created_at + timedelta(days=1)).strftime("%Y-%m-%d")

    http_method = 'GET'
    http_function = '/v2/platforms/unified-orders'
    timestamp = int(time.time())
    data = {
        "fromDate": f"{date_from}",
        "endDate": f"{date_to}",
    }

    print(data)

    headers = {
        "X-Api-Key": PAYMENT_GATEWAY_CRYPTOGATOR_API_KEY,
        "X-Signature": sign(timestamp, http_method, http_function, data),
        "X-Timestamp": f"{timestamp}",
        "Content-Type": "application/json"
    }

    url = f"{PAYMENT_GATEWAY_CRYPTOGATOR_BASE_URL_PARTNER}{http_function}"
    print(f"url: {url}")
    response = requests.get(url, headers=headers, params=data, json=data)
    if response.status_code != 200:
        logger.error(f"status code: {response.status_code} | {response.text}")
        raise Exception(f"Repsonse code {response.status_code} ({payment_types.GATEWAY_CRYPTOGATOR}) {http_function}")

    try:

        data = json.loads(response.text)
        print(data)

    except ValueError as e:
        logger.error(f"Can't parse json {str(e)}")
        raise Exception(f"{payment_types.GATEWAY_CRYPTOGATOR} JSON error {str(e)}")
















import uuid
import random
from django.test import TestCase
from core.tests.tools import create_profile, create_gateways_settings, view_topup_create
from payment.cryptogator import get_topup, webhook, recheck_topup_request
from core.models import TopUpRequest, PaymentGatewaySettings
import payment.types as payment_types

from core.log import *
logger.setLevel(logging.DEBUG)




#uuid.uuid4().hex
def _make_moc_post_data(topup_request, amount, status, blockchain_trx_id):

    r = {}
    r['uuid'] = topup_request.payment_gateway_transaction_id
    r['amount'] = amount
    r['currency'] = topup_request.payment_gateway_settings.currency
    r['status'] = status
    r['txId'] = blockchain_trx_id
    r['targetCurrency'] = topup_request.payment_gateway_settings.currency
    r['externalId'] = topup_request.id
    r['customerId'] = topup_request.user.id

    return r


class CryptogatorTest(TestCase):

    def setUp(self):
        create_gateways_settings()

    def test_topup_flow(self):

        p = create_profile()

        pgs_all = PaymentGatewaySettings.objects.filter(type=payment_types.GATEWAY_CRYPTOGATOR).all()
        for pgs in pgs_all:
            current_balance = p.get_balance()
            topup_request, msg = view_topup_create(p, pgs.currency, pgs.method)
            self.assertIsNotNone(topup_request, msg)

            topup_balance = random.randint(1, 10)
            post_data = _make_moc_post_data(topup_request, topup_balance, 'DONE', uuid.uuid4().hex)
            self.assertTrue(webhook(post_data, topup_request.id))

            new_balance = p.get_balance()

            self.assertAlmostEqual(float(current_balance + topup_balance), float(new_balance), 2)
            logger.info(f"prev balance: {current_balance} new balance {new_balance} topup {topup_balance}")

    def test_topup_internal_flow_recheck(self):

        p = create_profile()
        topup_request = get_topup(p.user, TopUpRequest.METHOD_TRON, TopUpRequest.CURRENCY_USDT)
        recheck_topup_request(topup_request)











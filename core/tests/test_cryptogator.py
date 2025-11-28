import uuid
import random
from django.test import TestCase
from core.tests.tools import create_profile, create_gateways_settings, view_topup_create, view_payment_receive_topup, view_topup_request_status
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

            result, msg = view_topup_request_status(p, topup_request)
            self.assertTrue(result, msg)

            topup_balance = random.randint(1, 10)

            view_payment_receive_topup(p, topup_request, topup_balance, 'DONE', uuid.uuid4().hex)

            new_balance = p.get_balance()

            self.assertAlmostEqual(float(current_balance + topup_balance), float(new_balance), 2)
            logger.info(f"prev balance: {current_balance} new balance {new_balance} topup {topup_balance}")

    def test_topup_internal_flow_recheck(self):

        p = create_profile()

        pgs = PaymentGatewaySettings.objects.filter(type=payment_types.GATEWAY_CRYPTOGATOR).first()
        topup_request, msg = view_topup_create(p, pgs.currency, pgs.method)
        self.assertIsNotNone(topup_request, msg)

        recheck_topup_request(topup_request)











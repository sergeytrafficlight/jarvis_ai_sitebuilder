from django.test import TestCase
from core.tests.tools import create_user, create_gateways_settings
from payment.cryptogator import get_topup
from core.models import TopUpRequest

class ToolsTests(TestCase):

    def setUp(self):
        create_gateways_settings()

    def test_topup_internal_flow(self):

        u = create_user()
        topup_request = get_topup(u, TopUpRequest.METHOD_TRON, TopUpRequest.CURRENCY_USDT)

        self.assertIsNotNone(topup_request)



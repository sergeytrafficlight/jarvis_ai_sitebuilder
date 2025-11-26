from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import TopUpRequest
from payment.cryptogator import get_topup
from sitebuilder.settings import DEBUG

class Command(BaseCommand):

    def handle(self, *args, **options):

        if not DEBUG:
            raise Exception(f"Debug is OFF")

        TopUpRequest.objects.all().delete()
        u = User.objects.first()
        topup = get_topup(user=u, method=TopUpRequest.METHOD_TRON, currency=TopUpRequest.CURRENCY_USDT)
        print(f"uuid: {topup.payment_gateway_transaction_id}")
        print(f"wallet_to_pay_address: {topup.wallet_to_pay_address}")
        print(f"expired_at: {topup.expired_at}")
        print(f"amount_min_for_order: {topup.amount_min_for_order}")
        print(f"comission: {topup.comission}")

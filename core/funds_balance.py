
from decimal import Decimal
from core.models import SiteProject, SubSiteProject, AICommunicationLog, Transaction
from django.contrib.auth.models import User
from django.db.models import Sum
from ai.ai import ai_answer

def charge(sub_site: SubSiteProject, ai_answer: ai_answer, description: str = None):

    Transaction.objects.create(
        user=sub_site.site.user,
        amount_client=ai_answer.price_for_client,
        amount_ai=ai_answer.price_for_ai,
        type=Transaction.TYPE_CHARGE,
        description=description,
        sub_site=sub_site,
    )

def topup(user: User, amount: Decimal, description: str = None):
    Transaction.objects.create(
        user=user,
        amount=amount,
        type=Transaction.TYPE_TOPUP,
    )

def balance(user: User = None, site: SiteProject = None, sub_site: SubSiteProject = None) -> Decimal:

    entities = 0
    entities += user is not None
    entities += site is not None
    entities += sub_site is not None

    if entities != 1:
        raise Exception(f"Expecting only one arg, got {entities}")

    if user:
        qs = Transaction.objects.filter(user=user)
    elif site:
        qs = Transaction.objects.filter(sub_site__site=site)
    elif sub_site:
        qs = Transaction.objects.filter(sub_site=sub_site)


    return qs.aggregate(
            total_amount=Sum('amount_client')
        )['total_amount'] or 0

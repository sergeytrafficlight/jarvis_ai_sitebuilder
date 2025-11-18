from core.models import AIModelsSettings
from decimal import Decimal

def _get_price_for_ai(ai_settings, prompt_tokens, completion_tokens):

    return (
        ai_settings.prompt_tokens_price_1m / 1000000 * prompt_tokens
        +
        ai_settings.completion_tokens_price_1m / 1000000 * completion_tokens
    )


def _get_price_for_client(ai_settings, prompt_tokens, completion_tokens):
    mutliplyer = Decimal(str(ai_settings.my_margin))
    return _get_price_for_ai(ai_settings, prompt_tokens, completion_tokens) * mutliplyer


class ai_answer:

    def __init__(self, ai_settings: AIModelsSettings, answer, prompt_tokens, completion_tokens):
        self.type = ai_settings.type
        self.model = ai_settings.model
        self.answer = answer
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.price_for_ai = _get_price_for_ai(ai_settings, prompt_tokens, completion_tokens)
        self.price_for_client = _get_price_for_client(ai_settings, prompt_tokens, completion_tokens)

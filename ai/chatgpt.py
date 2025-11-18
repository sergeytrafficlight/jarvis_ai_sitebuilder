
import requests
import httpx
from openai import OpenAI, APITimeoutError
from config import AI_PROXY, CHATGPT_API_KEY
from ai.ai_answer import ai_answer
from core.models import AIModelsSettings
from core.models import MODEL_CHATGPT_5_1
from core.models import TYPE_CHATGPT

HTTP_TIMEOUT = 60.0 * 20


def get_text2text_answer(prompt: str) -> str:
    model = MODEL_CHATGPT_5_1

    ai_settings = AIModelsSettings.objects.get(type=TYPE_CHATGPT, model=model)

    if len(AI_PROXY):
        http_client =  httpx.Client(
            proxy=AI_PROXY,
            timeout=httpx.Timeout(HTTP_TIMEOUT)
        )
    else:
        http_client = httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT))

    client = OpenAI(
        api_key=CHATGPT_API_KEY,
        http_client=http_client
    )

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    answer_txt = response.choices[0].message.content

    answer = ai_answer(
        ai_settings=ai_settings,
        answer=answer_txt,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
    )

    return answer



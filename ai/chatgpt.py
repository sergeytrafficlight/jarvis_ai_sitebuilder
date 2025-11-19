
import requests
import httpx
import base64
from openai import OpenAI, APITimeoutError
from config import AI_PROXY, CHATGPT_API_KEY
from ai.ai_answer import ai_answer
from core.models import AIModelsSettings
from core.models import MODEL_CHATGPT_5_1, MODEL_CHATGPT_IMG_1
from core.models import TYPE_CHATGPT

HTTP_TIMEOUT = 60.0 * 20


def get_text2text_answer(prompt: str, creative_enabled=False) -> str:
    model = MODEL_CHATGPT_5_1

    if creative_enabled:
        temperature = 1.8
        top_p = 1
    else:
        temperature = 0.0
        top_p = 1

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
        temperature=temperature,
        top_p = top_p,
    )

    answer_txt = response.choices[0].message.content

    answer = ai_answer(
        ai_settings=ai_settings,
        answer=answer_txt,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
    )

    return answer

def get_text2img_answer(
    prompt: str,
    input_image_path: str,
    creative_enabled=False,
):
    model = MODEL_CHATGPT_IMG_1

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

    if input_image_path:
        response = client.images.edit(
            model=model,
            image=open(input_image_path, "rb"),
            prompt=prompt,
        )
    else:
        response = client.images.edit(
            model=model,
            prompt=prompt,
        )


    # Достаём картинку
    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    #todo there is no tokens
    answer = ai_answer(
        ai_settings=ai_settings,
        answer=image_bytes,
        prompt_tokens=100,
        completion_tokens=100,
    )

    return answer


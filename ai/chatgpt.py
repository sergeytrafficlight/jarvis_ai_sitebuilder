
import requests
import httpx
import base64
from openai import OpenAI, APITimeoutError
from config import AI_PROXY, CHATGPT_API_KEY
from ai.ai_answer import ai_answer
from core.models import AIModelsSettings
from core.models import MODEL_CHATGPT_5_1, MODEL_CHATGPT_IMG_1, MODEL_CHATGPT_5
from core.models import TYPE_CHATGPT
import math
from PIL import Image
from io import BytesIO

from core.log import *
logger.setLevel(logging.DEBUG)


HTTP_TIMEOUT = 60.0 * 20


def get_text2text_answer(prompt: str, creative_enabled=False) -> str:
    model = MODEL_CHATGPT_5_1

    if creative_enabled:
        temperature = 1.8
        top_p = 1
    else:
        temperature = 0.0
        top_p = 1

    ai_settings = AIModelsSettings.objects.get(type=TYPE_CHATGPT, model=model, format=AIModelsSettings.FORMAT_TXT)

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

    ai_settings = AIModelsSettings.objects.get(type=TYPE_CHATGPT, model=model, format=AIModelsSettings.FORMAT_IMAGE)

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

    logger.debug(f"image: {input_image_path}")
    logger.debug(f"prompt: {prompt}")
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
        prompt_tokens=0,
        completion_tokens=6208, #max amount of tokens for image
    )

    return answer


def calculate_gpt5_image_tokens(image_source, fidelity: str = "high") -> int:
    """
    Полный и точный расчёт токенов для GPT Image 1 input image.
    image_source: путь к файлу (str) или bytes (in-memory)
    fidelity: 'low' | 'high'
    """

    BASE_TOKENS = 65
    TILE_TOKENS = 129

    # === Step 1: load image from path OR bytes ===
    if isinstance(image_source, str):
        # image_source is path
        img = Image.open(image_source)
    else:
        # image_source is bytes or bytearray or BytesIO-like
        if isinstance(image_source, (bytes, bytearray)):
            img = Image.open(BytesIO(image_source))
        else:
            # Assume it's already a file-like object
            img = Image.open(image_source)

    w, h = img.size

    # === Step 2: scale shortest side to 512 ===
    shortest = min(w, h)
    scale = 512 / shortest

    w = int(round(w * scale))
    h = int(round(h * scale))

    # === Step 3: count 512px tiles ===
    tiles_w = math.ceil(w / 512)
    tiles_h = math.ceil(h / 512)
    tiles = tiles_w * tiles_h

    # === Step 4: base price ===
    tokens = BASE_TOKENS + tiles * TILE_TOKENS

    # === Step 5: high-fidelity modifiers ===
    if fidelity == "high":
        # determine shape
        if abs(w - h) < 5:
            tokens += 4160
        else:
            tokens += 6240

    return tokens



def get_edit_image_conversation(prompt: str, input_image_path:str, last_answer_id:str):

    logger.debug(f"input image: {input_image_path}")

    model = MODEL_CHATGPT_5

    if input_image_path:
        prompt_input_tokens = calculate_gpt5_image_tokens(input_image_path)
    else:
        prompt_input_tokens = 0

    ai_settings = AIModelsSettings.objects.get(type=TYPE_CHATGPT, model=model, format=AIModelsSettings.FORMAT_IMAGE)

    if len(AI_PROXY):
        http_client = httpx.Client(
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
        with open(input_image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
    else:
        image_b64 = None

    input = [
        {
            'role': 'user',
            'content': [
                {'type': 'input_text', 'text': prompt},
            ]
        }
    ]
    if image_b64:
        input[0]['content'].append(
            {'type': 'input_image', "image_url": f"data:image/jpeg;base64,{image_b64}", }
        )

    if last_answer_id:
        response = client.responses.create(
            model=model,
            input=input,
            previous_response_id=last_answer_id,
            tools=[{"type": "image_generation"}],
        )
    else:
        response = client.responses.create(
            model=model,
            input=input,
            tools=[{"type": "image_generation"}],
        )

    image_generation_calls = [
        output
        for output in response.output
        if output.type == "image_generation_call"
    ]
    image_data = [output.result for output in image_generation_calls]

    comment = ''
    if not image_data:
        comment = response.output.content

    img_bytes = base64.b64decode(image_data[0])
    buf = BytesIO(img_bytes)
    tokens = calculate_gpt5_image_tokens(buf)

    answer = ai_answer(
        ai_settings=ai_settings,
        answer=img_bytes,
        comment=comment,
        prompt_tokens=prompt_input_tokens,
        completion_tokens=tokens,
        response_id=response.id,
    )

    return answer

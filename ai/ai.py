from core.models import SiteProject, MyTask, AICommunicationLog
import ai.chatgpt as chatgpt
from ai.ai_answer import ai_answer


def ai_log(task: MyTask, prompt: str):
    return AICommunicationLog.objects.create(
        task=task,
        prompt=prompt
    )

def ai_log_update(log: AICommunicationLog, answer: ai_answer):
    log.answer = answer.answer
    log.type = answer.type
    log.model = answer.model
    log.prompt_tokens = answer.prompt_tokens
    log.completion_tokens = answer.completion_tokens
    log.price_for_ai = answer.price_for_ai
    log.price_for_client = answer.price_for_client
    log.save()


def get_text2text_answer(prompt: str, creative_enabled=False, model: str = ''):
    return chatgpt.get_text2text_answer(prompt, creative_enabled)

def get_text2img_answer(prompt: str, input_image_path: str, creative_enabled=False):
    return chatgpt.get_text2img_answer(prompt, input_image_path, creative_enabled)

def get_edit_image_conversation(prompt: str, input_image:str):
    return chatgpt.get_edit_image_conversation(prompt, input_image)
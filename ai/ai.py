from core.models import SiteProject, MyTask, AICommunicationLog, AI_ENGINE_CHOICES, AI_ENGINE_CHATGPT
import ai.chatgpt as chatgpt
from ai.ai_answer import ai_answer

AI_TYPE_PROCESSOR_TXT_IMG_2_TXT = 'AI_TYPE_PROCESSOR_TXT_IMG_2_TXT'
AI_TYPE_PROCESSOR_TXT_2_IMG = 'AI_TYPE_PROCESSOR_TXT_2_IMG'
AI_TYPE_PROCESSOR_IMG_2_IMG_CONVERSATION = 'AI_TYPE_PROCESSOR_IMG_2_IMG_CONVERSATION'
AI_TYPE_EXPENSES = 'AI_TYPE_EXPENSES'


AI_TYPE_PROCESSORS = [
    AI_TYPE_PROCESSOR_TXT_IMG_2_TXT,
    AI_TYPE_PROCESSOR_TXT_2_IMG,
    AI_TYPE_PROCESSOR_IMG_2_IMG_CONVERSATION,
    AI_TYPE_EXPENSES,
]

AI_ENGINE_DEFAULT = AI_ENGINE_CHATGPT

class AIProcessorFactory:

    def __init__(self):
        self.processor = {}

    def register(self, processor_type: str, engine: str, func):
        assert processor_type in AI_TYPE_PROCESSORS

        if processor_type not in self.processor:
            self.processor[processor_type] = {}

        assert engine not in self.processor[processor_type]
        self.processor[processor_type][engine] = func

    def get(self, processor_type: str, engine: str):
        if processor_type not in self.processor:
            raise Exception(f"Can't find AI engine for type [{processor_type}]")
        if engine not in self.processor[processor_type]:
            raise Exception(f"Can't find AI engine [{engine}] for type [{processor_type}]")

        return self.processor[processor_type][engine]

    def call(self, processor_type: str, engine: str, *args, **kwargs):

        func = self.get(processor_type, engine)
        return func(*args, **kwargs)

    def get_default_config(self):
        r = {}
        for p in AI_TYPE_PROCESSORS:
            r[p] = AI_ENGINE_DEFAULT
        return r

AI_PROCESSOR_FACTORY = AIProcessorFactory()

def ai_processor_register(processor_type: str, engine: str, func):
    global AI_PROCESSOR_FACTORY
    return AI_PROCESSOR_FACTORY.register(processor_type, engine, func)

def ai_processor_get_default_config():
    global AI_PROCESSOR_FACTORY
    return AI_PROCESSOR_FACTORY.get_default_config()


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


def get_text_img2text_answer(prompt: str, img_path=None, creative_enabled=False, engine_cfg: str = ai_processor_get_default_config()):
    global AI_PROCESSOR_FACTORY
    return AI_PROCESSOR_FACTORY.call(AI_TYPE_PROCESSOR_TXT_IMG_2_TXT, engine_cfg[AI_TYPE_PROCESSOR_TXT_IMG_2_TXT], prompt, img_path, creative_enabled)


def get_text2img_answer(prompt: str, input_image_path: str, creative_enabled=False, engine_cfg: str = ai_processor_get_default_config()):
    global AI_PROCESSOR_FACTORY
    return AI_PROCESSOR_FACTORY.call(AI_TYPE_PROCESSOR_TXT_2_IMG, engine_cfg[AI_TYPE_PROCESSOR_TXT_2_IMG], prompt, input_image_path, creative_enabled)


def get_edit_image_conversation(prompt: str, input_image:str, last_answer_id: str, engine_cfg: str = ai_processor_get_default_config()):
    global AI_PROCESSOR_FACTORY
    return AI_PROCESSOR_FACTORY.call(AI_TYPE_PROCESSOR_IMG_2_IMG_CONVERSATION, engine_cfg[AI_TYPE_PROCESSOR_IMG_2_IMG_CONVERSATION], prompt, input_image, last_answer_id)

def get_expenses(start_date, end_date=None, engine_cfg: str = ai_processor_get_default_config()):

    global AI_PROCESSOR_FACTORY
    return AI_PROCESSOR_FACTORY.call(AI_TYPE_EXPENSES, engine_cfg[AI_TYPE_EXPENSES], start_date, end_date)

from core.models import SiteProject, MyTask, AICommunicationLog

MODEL_CHATGPT = "chatgpt"

MODEL_CHOICES = [
    MODEL_CHATGPT,
]

class ai_answer:

    def __init__(self):
        pass

def ai_log(task: MyTask, model:str, promt: str):
    return AICommunicationLog.objects.create(
        task=task,
        ai_model=model,
        promt=promt
    )

def ai_log_update(log: AICommunicationLog, answer:str):
    log.answer = answer
    log.save()


def get_text2text_answer(promt: str, model: str):
    pass


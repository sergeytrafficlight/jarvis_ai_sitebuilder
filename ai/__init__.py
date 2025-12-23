from ai.ai import (
    ai_processor_register,
    AI_TYPE_PROCESSOR_TXT_IMG_2_TXT,
    AI_TYPE_PROCESSOR_TXT_2_IMG,
    AI_TYPE_PROCESSOR_IMG_2_IMG_CONVERSATION,
    AI_TYPE_EXPENSES
)
from core.models import AI_ENGINE_CHATGPT
import ai.chatgpt as chatgpt

ai_processor_register(AI_TYPE_PROCESSOR_TXT_IMG_2_TXT, AI_ENGINE_CHATGPT, chatgpt.get_text_img2text_answer)
ai_processor_register(AI_TYPE_PROCESSOR_TXT_2_IMG, AI_ENGINE_CHATGPT, chatgpt.get_text2img_answer)
ai_processor_register(AI_TYPE_PROCESSOR_IMG_2_IMG_CONVERSATION, AI_ENGINE_CHATGPT, chatgpt.get_edit_image_conversation)
ai_processor_register(AI_TYPE_EXPENSES, AI_ENGINE_CHATGPT, chatgpt.get_expenses)


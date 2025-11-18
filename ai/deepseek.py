import requests
import httpx
from openai import OpenAI
from openai import APITimeoutError, APIConnectionError
from config import AI_PROXY, CHATGPT_API_KEY
from ai.ai_answer import ai_answer
from core.models import AIModelsSettings


import uuid
import os
from urllib.parse import urlparse
from django.contrib.auth.models import User
from config import DIR_USER_PREFIX, DIR_IMAGES_PREFIX, DIR_SITES_PREFIX
from sitebuilder.settings import USER_FILES_ROOT
import re
import json
from typing import Optional
from pathlib import Path
from typing import List, Dict, Union


def get_base_path_for_user(user):
    return f"users/{user.id}"

def get_image_path_for_user(user):
    return f"{get_base_path_for_user(user)}/{DIR_IMAGES_PREFIX}"

def get_sites_path_for_user(user):
    return f"{get_base_path_for_user(user)}/{DIR_SITES_PREFIX}"

def generate_uniq_site_dir_for_user(user):
    base_dir = get_sites_path_for_user(user)
    name = str(uuid.uuid4())
    path = os.path.join(base_dir, name)
    os.makedirs(path, exist_ok=False)
    return path


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc), ""
    except Exception as e:
        return False, str(e)


def extract_json_from_text(text: str) -> Optional[dict]:
    # Ищем начало блока ```json
    start_pos = text.find('```json\n')
    if start_pos == -1:
        start_pos = text.find('```json\r\n')  # Для Windows-переводов строк
        if start_pos == -1:
            return text

    start_pos += len('```json\n')

    # Ищем конец блока, игнорируя ``` внутри JSON
    end_pos = start_pos
    balance = 0  # Счетчик вложенности JSON-структур
    in_string = False  # Флаг нахождения внутри строки
    escape = False  # Флаг экранированного символа

    for i in range(start_pos, len(text)):
        char = text[i]

        if escape:
            escape = False
            continue

        if char == '\\':
            escape = True
            continue

        if char == '"':
            in_string = not in_string

        if not in_string:
            if char in '{[':
                balance += 1
            elif char in '}]':
                balance -= 1
                if balance < 0:
                    break

        # Проверяем конец блока только когда JSON структура закрыта
        if balance == 0 and text.startswith('```', i):
            end_pos = i
            break

    if end_pos <= start_pos:
        return None

    json_str = text[start_pos:end_pos].strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {str(e)}") from e



def process_file_operations(operations: Union[str, List[Dict]], base_dir:str) -> Dict:

    # Парсим входные данные
    if isinstance(operations, str):
        try:
            operations = json.loads(operations)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "processed": 0,
                'imgs': [],
                "errors": [{"error": f"Invalid JSON: {str(e)}"}],
                "comments": []
            }

    if not isinstance(operations, list):
        return {
            "success": False,
            "processed": 0,
            'imgs': [],
            "errors": [{"error": "Input data must be a list of operations"}],
            "comments": []
        }

    result = {
        "success": True,
        "processed": 0,
        'imgs': [],
        "errors": [],
        "comments": []
    }

    for op in operations:
        try:
            file_op = op.get("file_operation")
            file_path = base_dir + '/' + op.get("file_path")

            # Обработка комментариев
            if file_op == "comment":
                if "text" in op:
                    result["comments"].append(op["text"])
                continue

            # Валидация обязательных полей
            if not file_op:
                raise ValueError("Missing required field: file_operation")

            if file_op in ("delete", "replace") and not file_path:
                raise ValueError(f"Missing required field: file_path for {file_op} operation")

            # Полный путь к файлу
            full_path = Path(file_path).absolute()

            # Обработка операций
            print(f"{file_op} file: {file_path}")
            if file_op == "delete":
                if not full_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")

                if not full_path.is_file():
                    raise ValueError(f"Path is not a file: {file_path}")

                os.remove(full_path)
                result["processed"] += 1

            elif file_op == "replace" or file_op == "add" or file_op == 'create':
                if "text" not in op:
                    raise ValueError("Missing 'text' for replace operation")

                # Создаем директории, если их нет
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Записываем файл
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(op["text"])
                result["processed"] += 1
            elif file_op == 'prompt':
                if 'prompt' not in op:
                    raise ValueError("Missing 'prompt' for prompt")
                result['imgs'].append((file_path, op['prompt']))
            else:
                raise ValueError(f"Unknown operation: {file_op}")

        except Exception as e:
            result["success"] = False
            result["errors"].append({
                "operation": op,
                "error": str(e),
                "file_path": file_path
            })

    return result
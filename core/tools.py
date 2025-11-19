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
from core.log import *
logger.setLevel(logging.DEBUG)



def get_base_path_for_user(user):
    return f"users/{user.id}"

def get_image_path_for_user(user):
    return f"{get_base_path_for_user(user)}/{DIR_IMAGES_PREFIX}"

def get_sites_path_for_user(user):
    return f"{get_base_path_for_user(user)}/{DIR_SITES_PREFIX}"

def get_subsite_dir(subsite: 'SubSiteProject'):
    dir = get_sites_path_for_user(subsite.site.user)
    dir += f"/{subsite.site.id}/{subsite.dir}"
    return dir


def generate_uniq_subsite_dir_for_site(site: 'SiteProject'):
    base_dir = get_sites_path_for_user(site.user)
    base_dir += f"/{site.id}"
    uniq = str(uuid.uuid4())
    name = uniq
    path = os.path.join(base_dir, name)
    os.makedirs(path, exist_ok=False)
    return (path, uniq)




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


class ProcessFileResult:

    class File:

        TYPE_TEXT = "txt"
        TYPE_IMG = "img"

        OPERATION_CREATE_OR_MODIFY = "create_or_modify"

        OPERATIONS_DELETE = "delete"

        def __init__(self):
            self.path = None
            self.body = None
            self.prompt = None
            self.operation = None

        def type(self):
            if not self.path:
                return None

            ext = os.path.splitext(self.path)[1].lstrip(".").lower()
            if ext in ["png", 'jpg']:
                return self.TYPE_IMG
            elif ext in ["html", 'htm', 'css', 'js']:
                return self.TYPE_TEXT

            raise Exception(f"Unknown extension [{ext}] for file {self.path}")


        def info(self):
            return f"op: {self.operation} path: {self.path} type: {self.type()} len: {len(self.body)} prompt: {self.prompt}"

    def __init__(self):
        self.processed = 0
        self.errors = []
        self.files = []


    def process_file_operations(self, operations: Union[str, List[Dict]], base_dir:str) -> Dict:
        # Парсим входные данные
        if isinstance(operations, str):
            try:
                operations = json.loads(operations)
            except json.JSONDecodeError as e:
                self.errors.append(
                    f"Invalid JSON"
                )
                return False

        if not isinstance(operations, list):
            self.errors.append("Input data must be a list of operations")
            return False


        for op in operations:
            file_path = None


            try:
                f = self.File()
                f.path = op.get("file_path")
                f.prompt = op.get("prompt")
                f.body = op.get('text')


                file_op = op.get("file_operation")

                file_path = base_dir + '/' + f.path


                # Валидация обязательных полей
                if not file_op:
                    raise ValueError("Missing required field: file_operation")

                if file_op in ("delete", "replace", "create") and not file_path:
                    raise ValueError(f"Missing required field: file_path for {file_op} operation")

                # Полный путь к файлу
                full_path = Path(file_path).absolute()
                if file_op == "delete":
                    f.operation = self.File.OPERATIONS_DELETE
                    if not full_path.exists():
                        raise FileNotFoundError(f"File not found: {file_path}")

                    if not full_path.is_file():
                        raise ValueError(f"Path is not a file: {file_path}")

                    os.remove(full_path)
                    self.processed += 1

                elif file_op == "replace" or file_op == "add" or file_op == 'create':
                    if "text" not in op:
                        raise ValueError("Missing 'text' for replace operation")

                    # Создаем директории, если их нет
                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    # Записываем файл
                    with open(full_path, "w", encoding="utf-8") as file:
                        file.write(f.body)
                    f.operation = self.File.OPERATION_CREATE_OR_MODIFY
                    self.processed += 1

                else:
                    raise ValueError(f"Unknown operation: {file_op}")

                self.files.append(f)

            except Exception as e:
                self.errors.append(
                    f"operation: {op if op else ''}, file_path {file_path if file_path else ''}, error: {str(e)}"
                )

        return not len(self.errors)
from urllib.parse import urlparse
from django.contrib.auth.models import User
from config import DIR_USER_PREFIX, DIR_IMAGES_PREFIX

def get_image_path_for_user(User):
    return f"{DIR_USER_PREFIX}/{User.id}/{DIR_IMAGES_PREFIX}"


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc), ""
    except Exception as e:
        return False, str(e)

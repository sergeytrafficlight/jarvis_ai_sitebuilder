from urllib.parse import urlparse
from django.contrib.auth.models import User
from config import DIR_USER_PREFIX, DIR_IMAGES_PREFIX
from sitebuilder.settings import USER_FILES_ROOT



def get_base_path_for_user(user):
    return f"users/{user.id}"

def get_image_path_for_user(user):
    return f"{get_base_path_for_user(user)}/{DIR_IMAGES_PREFIX}"


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc), ""
    except Exception as e:
        return False, str(e)

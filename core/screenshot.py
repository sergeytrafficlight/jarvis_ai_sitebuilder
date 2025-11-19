import asyncio
from django.contrib.auth.models import User
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
from pathlib import Path
import time
from urllib.parse import urlparse
from django.utils.translation import gettext_lazy as _
from django.core.files import File
from core.models import GeneratedImage
from .tools import is_valid_http_url, get_image_path_for_user
from core.utils import make_session_cookie_for_user

from core.log import *
logger.setLevel(logging.DEBUG)


DEFAULT_TIMEOUT_MS = 30000

async def take_full_screenshot(url: str,
                               out_path: str,
                               timeout: int = DEFAULT_TIMEOUT_MS,
                               headless: bool = True,
                               wait_after_load: float = 0.5,
                               cookies=None,
                               headers=None
                               ):

    logger.debug(f"take screen: {url}")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            extra_http_headers=headers or {}
        )
        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
        except PWTimeoutError:
            await browser.close()
            return False, _("Timeout")
        except Exception as e:
            await browser.close()
            return False, str(e)

        # Небольшая пауза на финальную прорисовку динамики (можно увеличить)
        if wait_after_load:
            await page.wait_for_timeout(int(wait_after_load * 1000))

        # Скриншот всей страницы
        await page.screenshot(path=str(out_path), full_page=True)
        await browser.close()

        return True, ""

def generate_screenshort(u: User, url: str, auth_user: User = None):
    logger.debug(f"take url {url}")
    r, msg = is_valid_http_url(url)
    if not r:
        return r, msg

    filename = f"screenshot_{u.id}_{int(time.time() * 1000)}.png"

    dir = get_image_path_for_user(u)
    dir = Path(dir)
    dir.mkdir(parents=True, exist_ok=True)
    out_path = f"{dir}/{filename}"

    cookies = None
    session_to_cleanup = None
    if auth_user:
        host = urlparse(url).hostname or 'localhost'
        session_to_cleanup, cookie = make_session_cookie_for_user(auth_user, domain=host)
        cookies = [cookie]

    r, msg = asyncio.run(take_full_screenshot(url, str(out_path), cookies=cookies))

    if session_to_cleanup:
        try:
            session_to_cleanup.delete()
        except Exception:
            pass

    if not r:
        return r, msg

    with open(out_path, "rb") as f:
        img = GeneratedImage.objects.create(
            user=u,
            image=File(f, name=filename)
        )

    return True, img
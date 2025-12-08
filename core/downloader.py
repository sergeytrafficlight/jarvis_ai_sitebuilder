import os
import re
import threading
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from core.tools import is_valid_http_url
from core.log import *

logger.setLevel(logging.DEBUG)


def _clean_url(url):
    try:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    except:
        url = url.strip('?')
        return url[0]

def _get_domain(url):
    parsed = urlparse(url)
    return parsed.netloc

def _get_web_dir(url: str):
    parsed = urlparse(url)
    path = parsed.path
    directory = os.path.dirname(path)
    return urlunparse((parsed.scheme, parsed.netloc, directory, '', '', ''))


def _is_internal_link(link, my_domain):
    if not link.startswith(('http://', 'https://')):
        return True
    try:
        parsed = urlparse(link)
        return parsed.netloc == my_domain or parsed.netloc.endswith('.' + my_domain)
    except:
        return False

def _compose_full_link(link, current_path):
    return urljoin(current_path, link)


class Downloader:


    def __init__(self, url: str, download_dir: str, max_depth : int = 5, max_threads: int = 5):

        if not is_valid_http_url(url):
            raise Exception(f"Invalid url: {url}")

        self.url = url
        self.url_cleaned = _clean_url(url)
        self.my_domain = _get_domain(url)

        self.dir = download_dir
        self.max_depth = max_depth
        self.max_threads = max_threads

        self.visited_url = set()

        self.to_download_js_css = {}
        self.to_download_img = {}

    def extract_links(self, content):
        soup = BeautifulSoup(content, 'html.parser')

        links_html = []
        links_css_js = []
        links_imgs = []

        for a_tag in soup.find_all('a'):
            if not a_tag.get('href'):
                continue
            href = a_tag['href'].strip()
            if not len(href):
                continue
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            links_html.append(href)

        for form_tag in soup.find_all('form'):
            if not form_tag.get('action'):
                continue
            action = form_tag.get('action')
            if not len(action):
                continue
            if action.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            links_html.append(action)


        for img_tag in soup.find_all('img'):
            if not img_tag.get('src'):
                continue
            src = img_tag['src'].strip()
            if not len(src):
                continue
            links_imgs.append(src)

        for script_tag in soup.find_all('script'):
            if not script_tag.get('src'):
                continue
            src = script_tag['src'].strip()
            if not len(src):
                continue
            links_css_js.append(src)

        for css_tag in soup.find_all('link'):
            if not css_tag.get('href'):
                continue
            href = css_tag['href'].strip()
            if not len(href):
                continue

            links_css_js.append(href)


        return links_html, links_css_js, links_imgs


    def get_structure(self, url, current_depth):
        logger.debug(f"cycle url: {url}")
        clean_url = _clean_url(url)
        logger.debug(f"clean url: {clean_url}")
        if clean_url in self.visited_url:
            logger.debug(f"already visited {clean_url}")
            return None

        self.visited_url.add(clean_url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                page.goto(url, wait_until='networkidle')
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                content = page.content()
                logger.debug(f"done")
            except Exception as e:
                logger.error(f"Error loading {url}: {e}")
                return None
            finally:
                browser.close()

        logger.debug(f"downloaded {len(content)}")
        links_html, links_css_js, links_imgs = self.extract_links(content)



        for l in links_css_js:
            if not _is_internal_link(l, self.my_domain):
                continue
            clean = _clean_url(l)
            if clean in self.to_download_js_css:
                continue
            self.to_download_js_css[clean] = l

        for l in links_imgs:
            if not _is_internal_link(l, self.my_domain):
                continue
            clean = _clean_url(l)
            if clean in self.to_download_img:
                continue
            self.to_download_img[clean] = l

        for l in links_html:
            if not _is_internal_link(l, self.my_domain):
                continue

            new_link = _compose_full_link(l, clean_url)
            logger.debug(f"link {l} clean url {clean_url}, composed {new_link}")
            self.get_structure(new_link, current_depth + 1)





    def download(self):
        os.makedirs(self.dir, exist_ok=True)

        logger.debug(f"url {self.url} -> {self.dir}")
        logger.debug(f"clean url: {self.url_cleaned}")

        self.get_structure(self.url, 0)

        logger.debug(f"imgs: {len(self.to_download_img)}")
        logger.debug(f"js_css: {len(self.to_download_js_css)}")


def _get_target_name(base_web_dir: str, url: str) -> str:
    """
    Продвинутая версия с обработкой различных случаев

    Args:
        base_web_dir: Базовый URL директории
        url: Полный URL

    Returns:
        Относительный путь от base_web_dir к url
    """
    # Нормализуем URL: убираем фрагменты, параметры запроса
    base_parsed = urlparse(base_web_dir)
    url_parsed = urlparse(url)

    # Собираем нормализованные URL без query и fragment
    base_normalized = f"{base_parsed.scheme}://{base_parsed.netloc}{base_parsed.path}"
    url_normalized = f"{url_parsed.scheme}://{url_parsed.netloc}{url_parsed.path}"

    # Добавляем завершающий слеш к base_normalized если это не файл
    if '.' not in base_normalized.split('/')[-1] and not base_normalized.endswith('/'):
        base_normalized += '/'

    # Проверяем, является ли base_normalized префиксом url_normalized
    if url_normalized.startswith(base_normalized):
        # Вырезаем префикс
        relative_part = url_normalized[len(base_normalized):]
        # Преобразуем в путь
        if not relative_part:
            return '/'
        # Убеждаемся, что путь начинается со слеша
        return '/' + relative_part if not relative_part.startswith('/') else relative_part
    else:
        # Возвращаем полный путь из URL
        return url_parsed.path or '/'

class URL4Download:

    STATUS_NEW = 'NEW'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_DONE = 'DONE'

    def __init__(self, base_web_dir: str, url: str):
        self.url = _clean_url(url)
        self.base_web_dir = base_web_dir
        self.target_name = _get_target_name(self.base_web_dir, self.url)
        if self.target_name.endswith('/'):
            self.target_name += 'index.html'
        self.status = URL4Download.STATUS_NEW

    def __str__(self):
        return self.target_name

    def info(self):
        return f"bwd [{self.base_web_dir}] url [{self.url}] tn [{self.target_name}]"

class Downloader2:

    def __init__(self, url: str, download_dir: str, max_depth : int = 5, max_threads: int = 5):

        if not is_valid_http_url(url):
            raise Exception(f"Invalid url: {url}")

        self.url = url
        self.url_cleaned = _clean_url(url)
        self.my_domain = _get_domain(url)
        self.base_web_dir = _get_web_dir(url)

        self.dir = download_dir
        self.max_depth = max_depth
        self.max_threads = max_threads

        self.urls4download = set()
        self.urls4download_lock = threading.Lock()
        self.urls2download_new_urls_found = threading.Event()



    def get_url(self):
        while True:
            done_count = 0
            with self.urls4download_lock:
                for url in self.urls4download:
                    if url.status == URL4Download.STATUS_DONE:
                        done_count += 1
                    if url.status != URL4Download.STATUS_NEW:
                        continue
                    url.status = URL4Download.STATUS_PROCESSING
                    return url


                if done_count == len(self.urls4download):
                    return None

                self.urls4download_lock.release()
                self.urls2download_new_urls_found.wait(timeout=1)
                self.urls2download_new_urls_found.clear()
                self.urls4download_lock.acquire()
                continue

    def url_finished(self, url):
        with self.urls4download_lock:
            url.status = url.status = URL4Download.STATUS_DONE

    def download_thread(self):
        thread_id = threading.get_ident()

        while True:
            url = self.get_url()

            if url is None:
                print(f"tid: {thread_id} url is None")
                return None

            print(f"proceed tid: {thread_id} url {url.info()}")


            self.url_finished(url)


    def download(self):
        os.makedirs(self.dir, exist_ok=True)

        self.urls4download.add(URL4Download(self.base_web_dir, self.url))

        threads = []
        for i in range(self.max_threads):
            t = threading.Thread(target=self.download_thread)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()


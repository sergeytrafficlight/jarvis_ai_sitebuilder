import os
import re
import threading
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from core.models import TYPE_CHOICES
from core.tools import is_valid_http_url
from core.log import *

logger.setLevel(logging.DEBUG)


class SafePathResolver:

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).resolve()

    def safe_path(self, relative_path: str) -> Path:
        clean_path = os.path.normpath(relative_path)
        clean_path = clean_path.strip('/').lstrip('\\')
        if clean_path.startswith('..') or clean_path == '..':
            raise Exception(f'Path traversal attempt detected: {relative_path}')
        full_path = self.base_dir / clean_path
        try:
            if os.path.commonpath([self.base_dir, full_path]) != str(self.base_dir):
                raise Exception(f"Path escapes download directory: {relative_path}")
        except ValueError:
            raise Exception(f"Invalid path: {relative_path}")

        return full_path

    def ensure_safe_directory(self, relative_path: str) -> Path:
        safe_path = self.safe_path(relative_path)
        safe_path.mkdir(parents=True, exist_ok=True)
        return safe_path



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
    result = urlunparse((parsed.scheme, parsed.netloc, directory, '', '', ''))
    if not result.endswith('/'):
        result += '/'
    return result


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

class URL4Download:

    STATUS_NEW = 'NEW'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_DONE = 'DONE'

    STATUS_CHOICES = (
        (STATUS_NEW, STATUS_NEW),
        (STATUS_PROCESSING, STATUS_PROCESSING),
        (STATUS_DONE, STATUS_DONE),
    )

    TYPE_HTML = 'HTML'
    TYPE_CSS_JS = 'CSS_JS'
    TYPE_IMG = 'IMG'

    TYPE_CHOICES = (
        (TYPE_HTML, TYPE_HTML),
        (TYPE_CSS_JS, TYPE_CSS_JS),
        (TYPE_IMG, TYPE_IMG),
    )

    def __init__(self, downloader: 'Downloader2',  url: str, type: str):
        assert type in dict(URL4Download.TYPE_CHOICES), f"Wrong type [{type}] [{dict(URL4Download.TYPE_CHOICES)}]"
        self.type = type
        self.error = ''
        self.status = URL4Download.STATUS_NEW
        self.downloader = downloader

        self.url = _clean_url(url)

        self.full_url = self.get_full_url()

        self.target_name = _get_target_name(self.downloader.base_web_dir, self.url)

        if self.target_name.endswith('/'):
            self.target_name += 'index.html'



        self.target_path = self.get_target_path()

    def get_target_path(self):
        try:
            base_dir = os.path.normpath(self.downloader.dir)
            r = SafePathResolver(base_dir)
            return r.safe_path(self.target_name)
        except Exception as e:
            self.error = str(e)
            self.status = URL4Download.STATUS_DONE
            return None


        #print(f"URL: {str(url.info())}")
        if self.target_name.startswith('./'):
            url_path = self.target_name[2:]
        else:
            url_path = self.target_name

        #print(f"url path: {url_path}")

        url_path = url_path.strip('/')
        full_path = os.path.join(base_dir, url_path)
        full_path = os.path.normpath(full_path)
        return full_path

    def get_full_url(self):
        if urllib.parse.urlparse(self.url).scheme:
            return self.url
        full_url = urllib.parse.urljoin(self.downloader.base_web_dir, self.url)
        return full_url

    def __str__(self):
        return self.target_path

    def __hash__(self):
        return hash(self.target_path)

    def __eq__(self, other):
        if not isinstance(other, URL4Download):
            return False
        return self.target_path == other.target_path

    def info(self):
        return f"bwd [{self.downloader.base_web_dir}] url [{self.url}] tn [{self.target_name}] tp [{self.target_path}] f.url [{self.full_url}]"

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


def _extract_links(downloader: 'Downloader2', content: str):
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
        if not _is_internal_link(href, downloader.my_domain):
            continue

        url = URL4Download(downloader, href, URL4Download.TYPE_HTML)
        links_html.append(url)
        a_tag['href'] = url.target_name



    for form_tag in soup.find_all('form'):
        if not form_tag.get('action'):
            continue
        action = form_tag.get('action')
        if not len(action):
            continue
        if action.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        if not _is_internal_link(action, downloader.my_domain):
            continue


        url = URL4Download(downloader, action, URL4Download.TYPE_HTML)
        links_html.append(url)
        form_tag['action'] = url.target_name


    for img_tag in soup.find_all('img'):
        if not img_tag.get('src'):
            continue
        src = img_tag['src'].strip()
        if not len(src):
            continue
        if not _is_internal_link(src, downloader.my_domain):
            continue

        url = URL4Download(downloader, src, URL4Download.TYPE_IMG)
        links_imgs.append(url)
        img_tag['src'] = url.target_name


    for script_tag in soup.find_all('script'):
        if not script_tag.get('src'):
            continue
        src = script_tag['src'].strip()
        if not len(src):
            continue
        if not _is_internal_link(src, downloader.my_domain):
            continue

        url = URL4Download(downloader, src, URL4Download.TYPE_CSS_JS)
        links_css_js.append(url)
        script_tag['src'] = url.target_name


    for css_tag in soup.find_all('link'):
        if not css_tag.get('href'):
            continue
        href = css_tag['href'].strip()
        if not len(href):
            continue
        if not _is_internal_link(href, downloader.my_domain):
            continue

        url = URL4Download(downloader, href, URL4Download.TYPE_CSS_JS)
        links_css_js.append(url)
        css_tag['href'] = url.target_name


    return str(soup), links_html + links_css_js + links_imgs


class Downloader2:

    def __init__(self, url: str, download_dir: str, max_depth : int = 5, max_threads: int = 5, timeout_per_url: int = 10):

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

        self.timeout_per_url = timeout_per_url


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

    def url_finished(self, url: URL4Download, error: str = ''):
        with self.urls4download_lock:
            url.status = url.status = URL4Download.STATUS_DONE
            url.error = error

    def download_url_html(self, url):
        content = None
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                page.goto(url.full_url, wait_until='networkidle')
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                content = page.content()
            finally:
                browser.close()

        return content

    def download_url_common(self, url):
        """Загружает контент и определяет его тип"""
        response = requests.get(
            url.full_url,
            timeout=self.timeout_per_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        response.raise_for_status()

        # Определяем Content-Type
        content_type = response.headers.get('Content-Type', '').lower()

        # Если это изображение или другой бинарный тип
        if any(binary_type in content_type for binary_type in [
            'image/', 'font/', 'application/octet-stream',
            'application/pdf', 'video/', 'audio/'
        ]):
            return response.content  # bytes
        else:
            # Пробуем получить как текст с правильной кодировкой
            if response.encoding:
                return response.text
            else:
                # Если кодировка не определена, пробуем декодировать
                try:
                    return response.content.decode('utf-8')
                except UnicodeDecodeError:
                    # Если не получается, возвращаем как bytes
                    return response.content


    def download_thread(self):
        thread_id = threading.get_ident()

        while True:
            url = self.get_url()

            if url is None:
                logger.debug(f"tid: {thread_id} url is None")
                return None

            logger.debug(f"proceed tid: {thread_id} url {url.info()}")


            if url.type == URL4Download.TYPE_HTML:
                try:
                    content = self.download_url_html(url)
                    logger.debug(f"done")
                except Exception as e:
                    logger.error(f"Error loading {url}: {e}")
                    self.url_finished(url, f"Error loading {url}: {e}")
                    continue

                logger.debug(f"Content len {len(content)}")

                content, links = _extract_links(self, content)

                for link in links:
                    self.urls4download.add(link)

            elif url.type in [URL4Download.TYPE_CSS_JS, URL4Download.TYPE_IMG]:

                try:
                    content = self.download_url_common(url)
                except Exception as e:
                    logger.error(f"Error loading {url}: {e}")
                    self.url_finished(url, f"Error loading {url}: {e}")
                    continue



            else:
                raise Exception(f"Unknown url type: {url.type}: {url.info()}")


            try:
                logger.debug(f'save {len(content)} to {self.dir} | {url.target_name} -> {url.target_path}')
                directory = os.path.dirname(url.target_path)
                os.makedirs(directory, exist_ok=True)

                mode = 'wb' if isinstance(content, bytes) else 'w'
                encoding = None if isinstance(content, bytes) else 'utf-8'

                with open(url.target_path, mode, encoding=encoding) as f:
                    f.write(content)

            except Exception as e:
                logger.error(f"Error write {url.info()}: {e} to: {url.target_path}")
                self.url_finished(url, f"Error write {url.info()}: {e} to: {url.target_path}")
                continue

            self.url_finished(url)


    def download(self):
        os.makedirs(self.dir, exist_ok=True)

        self.urls4download.add(URL4Download(self, self.url, URL4Download.TYPE_HTML))

        threads = []
        for i in range(self.max_threads):
            t = threading.Thread(target=self.download_thread)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()


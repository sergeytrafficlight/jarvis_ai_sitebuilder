import os
import re
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from core.tools import is_valid_http_url
from core.log import *

logger.setLevel(logging.DEBUG)


def download_site2(start_url, max_depth: int, download_dir: str):
    """
    Упрощенная версия для скачивания сайта с относительными путями
    """

    visited = set()
    base_domain = urlparse(start_url).netloc

    def get_page_content(url):
        logger.debug(f"url: {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                page.goto(url, wait_until='networkidle')
                # Скролл для активации ленивой загрузки
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                content = page.content()
                logger.debug(f"done")
                return content
            except Exception as e:
                logger.error(f"Error loading {url}: {e}")
                return None
            finally:
                browser.close()

    def save_processed_page(url, html):
        """Сохраняет страницу с относительными путями"""
        parsed_url = urlparse(url)
        path = parsed_url.path

        logger.debug(f"parsed_url: {parsed_url} path: {path}")

        # Определяем путь к файлу
        if not path or path == "/":
            file_path = os.path.join(download_dir, "index.html")
        else:
            if path.startswith("/"):
                path = path[1:]
            if path.endswith("/"):
                path += "index.html"
            elif "." not in os.path.basename(path):
                path += "/index.html"
            file_path = os.path.join(download_dir, path)

        # Создаем директории
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Конвертируем URLs в относительные пути
        def make_relative(match):
            tag, attr, original_url = match.groups()
            full_url = urljoin(url, original_url)

            if urlparse(full_url).netloc == base_domain:
                # Вычисляем относительный путь
                current_dir = os.path.dirname(parsed_url.path) or "."
                target_path = urlparse(full_url).path or "index.html"

                # Простая логика для относительных путей
                if current_dir == ".":
                    relative_path = target_path.lstrip("/")
                else:
                    relative_path = os.path.relpath(target_path, current_dir)

                return f'{tag} {attr}="{relative_path}"'
            return match.group(0)

        # Регулярное выражение для поиска URL в тегах
        pattern = r'<(a|link|script|img|source)\s+[^>]*(href|src)=["\']([^"\']*)["\'][^>]*>'
        processed_html = re.sub(pattern, make_relative, html, flags=re.IGNORECASE)

        # Сохраняем файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(processed_html)

        print(f"✓ Saved: {file_path}")
        return processed_html

    def extract_links(html, base_url):
        """Извлекает ссылки из HTML"""
        links = []
        pattern = r'<a\s+[^>]*href=["\']([^"\']*)["\'][^>]*>'

        for match in re.finditer(pattern, html, re.IGNORECASE):
            href = match.group(1)
            if not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                full_url = urljoin(base_url, href)
                if urlparse(full_url).netloc == base_domain:
                    links.append(full_url)

        return links

    def crawl(url, depth=0):
        if depth > max_depth or url in visited:
            return

        logger.debug(f"[Depth {depth}] Processing: {url}")
        visited.add(url)



        html = get_page_content(url)
        if not html:
            return

        # Сохраняем и обрабатываем страницу
        processed_html = save_processed_page(url, html)

        # Рекурсивно обходим ссылки
        if depth < max_depth:
            links = extract_links(processed_html, url)
            for link in links:
                if link not in visited:
                    crawl(link, depth + 1)

    # Запускаем
    logger.debug(f"url: {start_url}  -> {download_dir}")
    os.makedirs(download_dir, exist_ok=True)
    crawl(start_url)
    logger.debug(f"Download completed! Total pages: {len(visited)}")



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

def _is_internal_link(link, my_domain):
    if not link.startswith(('http://', 'https://')):
        return True
    try:
        parsed = urlparse(link)
        return parsed.netloc == my_domain or parsed.netloc.endswith('.' + my_domain)
    except:
        return False

def _compose_full_link(link, current_path):
    if link.startswith(('http://', 'https://')):
        return link
    if link.startswith('./'):
        link = link[2:]
    elif link.startswith('/'):
        link = link[1:]
    if not len(link):
        return current_path
    if current_path.endswith('/'):
        path = current_path + link
    else:
        path = f"{current_path}/{link}"
    return path


class Downloader:


    def __init__(self, url: str, download_dir: str, max_depth : int = 5):

        if not is_valid_http_url(url):
            raise Exception(f"Invalid url: {url}")

        self.url = url
        self.url_cleaned = _clean_url(url)
        self.my_domain = _get_domain(url)

        self.dir = download_dir
        self.max_depth = max_depth

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



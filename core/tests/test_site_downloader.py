import http.server
import socketserver
import threading
import functools
import os
import shutil
from pathlib import Path
from django.test import TestCase
from core.tests.tools import create_profile, create_site_sub_site
from core.tools import get_subsite_dir, dir_copy, generate_uniq_subsite_dir_for_site
from core.downloader import Downloader, Downloader2, SafePathResolver
from core.site_analyzer import SiteAnalyzer

test_data_dir_site = 'test_data/test_site/'
test_data_dir_to_download = 'test_data/test_site_download/'

class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # тихий хэндлер
        pass

def _serve_dir(directory: str, port: int = 0):
    Handler = functools.partial(SilentHandler, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, f"http://127.0.0.1:{port}/"



class SiteDownloaderTest(TestCase):


    def test_site_downloader(self):

        httpd, base_url = _serve_dir(test_data_dir_site)

        try:
            
            if os.path.exists(test_data_dir_to_download):
                shutil.rmtree(test_data_dir_to_download)

            d = Downloader2(base_url, test_data_dir_to_download)
            d.download()

        finally:
            httpd.shutdown()

        for url in d.urls4download:
            print(f"URL: {url.info()}")

        s = SiteAnalyzer(test_data_dir_site)
        s = s.analyze()

        original_site = {}
        for k in s:
            relative = s[k]['relative']
            original_site[relative] = s[k]

        s = SiteAnalyzer(test_data_dir_to_download)
        s = s.analyze()

        downloaded_site = {}
        for k in s:
            relative = s[k]['relative']
            downloaded_site[relative] = s[k]

        print("==")
        print(original_site)
        print("==")
        print(downloaded_site)

        print(f":: {original_site == downloaded_site}")







import http.server
import socketserver
import threading
import functools
import os
import time
import shutil
from pathlib import Path
from django.test import TestCase
from core.tests.tools import create_profile, create_site_sub_site
from core.tools import get_subsite_dir, dir_copy, generate_uniq_subsite_dir_for_site
from core.downloader import Downloader, SafePathResolver
from core.site_analyzer import SiteAnalyzer
from core.tests.tools import compare_dicts
from core.scan_directory import compare_directories

test_data_dir_site = 'test_data/test_site/'
test_data_dir_to_download = 'test_data/test_site_download/'

class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # тихий хэндлер
        pass

    def log_error(self, format, *args):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except Exception:
            # глотаем ВСЁ
            pass

class SlowHandler(SilentHandler):
    chunk_size = 1024        # 1 KB
    delay_per_chunk = 0.2    # 200 ms между чанками

    def copyfile(self, source, outputfile):
        """
        Отдаём файл кусками с задержкой
        """
        while True:
            chunk = source.read(self.chunk_size)
            if not chunk:
                break
            outputfile.write(chunk)
            outputfile.flush()
            time.sleep(self.delay_per_chunk)



def _serve_dir(directory: str, port: int = 0):
    Handler = functools.partial(SilentHandler, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, f"http://127.0.0.1:{port}/"

def _serve_dir_slow(directory: str, port: int = 0):
    Handler = functools.partial(SlowHandler, directory=directory)
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

            d = Downloader(base_url, test_data_dir_to_download)
            d.download()

        finally:
            httpd.shutdown()


        r, msg = compare_directories(test_data_dir_site, test_data_dir_to_download, max_diff=0.01)
        self.assertTrue(r, msg)
        self.assertEqual(len(d.errors), 0)

    def test_site_downloader_max_size_reached(self):

        httpd, base_url = _serve_dir(test_data_dir_site)

        try:

            if os.path.exists(test_data_dir_to_download):
                shutil.rmtree(test_data_dir_to_download)

            d = Downloader(
                base_url,
                test_data_dir_to_download,
                max_size_to_download=100
            )
            d.download()

        finally:
            httpd.shutdown()

        s = SiteAnalyzer(test_data_dir_to_download)
        s = s.analyze()

        self.assertEqual(len(s), 1)
        self.assertNotEqual(len(d.errors), 0)


    def test_site_downloader_max_resources(self):

        httpd, base_url = _serve_dir(test_data_dir_site)

        try:

            if os.path.exists(test_data_dir_to_download):
                shutil.rmtree(test_data_dir_to_download)

            d = Downloader(
                base_url,
                test_data_dir_to_download,
                max_resources_to_download=1
            )
            d.download()

        finally:
            httpd.shutdown()

        s = SiteAnalyzer(test_data_dir_to_download)
        s = s.analyze()

        self.assertEqual(len(s), 1)
        self.assertNotEqual(len(d.errors), 0)

    def test_site_downloader_timeout(self):

        httpd, base_url = _serve_dir_slow(test_data_dir_site)

        try:

            if os.path.exists(test_data_dir_to_download):
                shutil.rmtree(test_data_dir_to_download)

            d = Downloader(
                base_url,
                test_data_dir_to_download,
                timeout_per_url=1
            )
            d.download()

        finally:
            httpd.shutdown()

        s = SiteAnalyzer(test_data_dir_to_download)
        s = s.analyze()

        self.assertEqual(len(s), 0)
        self.assertNotEqual(len(d.errors), 0)





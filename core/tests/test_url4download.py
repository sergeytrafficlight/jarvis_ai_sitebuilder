from django.test import TestCase
from core.downloader import URL4Download, Downloader2

class URL4DownloadTest(TestCase):

    def test_compose_url(self):

        d = Downloader2('https://ya.ru/124/', '')
        test_cases = [
            ('./123.html', 'https://ya.ru/124/123.html'),
        ]

        for t in test_cases:
            url = URL4Download(d, t[0], URL4Download.TYPE_HTML)
            self.assertEqual(url.full_url, t[1])

    def test_unique_url(self):

        d = Downloader2('https://ya.ru/123/', '')
        test_cases = [
            './123.html',
            './1234.html',
        ]

        s = set()


        for i in range(2):
            for t in test_cases:
                url = URL4Download(d, t, URL4Download.TYPE_HTML)
                s.add(url)

        self.assertEqual(len(test_cases), len(s))

    def test_target_path(self):

        download_dir = "test_dir/dir2"

        test_cases = [
            ('./123.html', download_dir + '/123.html'),
            ('./xx/1234.html', download_dir + '/xx/1234.html'),
        ]


        d = Downloader2('https://ya.ru/123/', download_dir)

        for t in test_cases:
            url = URL4Download(d, t[0], URL4Download.TYPE_HTML)
            self.assertEqual(t[1], d.get_target_path(url))






from django.test import TestCase
from core.downloader import URL4Download, Downloader, _extract_links

class URL4DownloadTest(TestCase):

    def test_compose_url(self):

        d = Downloader('https://ya.ru/124/', '')
        test_cases = [
            ('./123.html', 'https://ya.ru/124/123.html'),
        ]

        for t in test_cases:
            url = URL4Download(d, t[0], URL4Download.TYPE_HTML)
            self.assertEqual(url.full_url, t[1])

    def test_unique_url(self):

        d = Downloader('https://ya.ru/123/', '')
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


    def test_extract_links(self):
        content = '''
        <html>
        <body>
            <link rel="stylesheet" href="/static/tlight/css/main/homepage.main.css?1147" type="text/css" />
            <link rel="stylesheet" type="text/css" href="/static/tlight/css/main/forks/traffic_light/extra_homepage.main.css?1147">    
            <script src="/static/vendor/jquery-3.2.1.min.js?1147"></script>
            <a href="/?"><img class="logo" src="/static/tlight/images/logo/logo_TL_New_213x52.svg" alt="" /></a>
        </body>
        </html>        
        '''

        check_links = [
            './static/tlight/css/main/homepage.main.css',
            './static/tlight/css/main/forks/traffic_light/extra_homepage.main.css',
            './static/vendor/jquery-3.2.1.min.js',
            './index.html',
            './static/tlight/images/logo/logo_TL_New_213x52.svg'
        ]

        d = Downloader('http://localhost/test/', "./test")
        content, links = _extract_links(d, content)



        for l in links:
            self.assertTrue(l.target_name in check_links, f"Can't find [{l.target_name}] in {check_links}")
            check_links.remove(l.target_name)

        self.assertEqual(len(check_links), 0)






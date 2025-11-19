import os
import pathlib
from bs4 import BeautifulSoup


class SiteAnalyzer:

    def __init__(self, base_path: str):
        # нормализуем в абсолютный путь
        self.base_path = os.path.abspath(base_path)
        # теперь список словарей: {'full': ..., 'rel': ...}
        self.files = []
        self.structure = {}

    # -----------------------------
    #  Сканирование директории
    # -----------------------------
    def scan_files(self):
        self.files.clear()
        for root, _, files in os.walk(self.base_path):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, start=self.base_path)
                self.files.append({"full": full, "rel": rel})

    # -----------------------------
    #  Определение типа файла
    # -----------------------------
    @staticmethod
    def get_file_type(path: str):
        ext = pathlib.Path(path).suffix.lower()

        if ext in {".html", ".htm"}:
            return "html"
        if ext == ".css":
            return "css"
        if ext == ".js":
            return "js"
        if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
            return "image"
        return "other"

    # -----------------------------
    #  Анализ одного HTML-файла
    # -----------------------------
    def analyze_html(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
        except Exception:
            # HTML некорректный или не прочитан
            return {}

        links = [tag.get("href") for tag in soup.find_all("a") if tag.get("href")]
        scripts = [tag.get("src") for tag in soup.find_all("script") if tag.get("src")]
        css = [tag.get("href") for tag in soup.find_all("link", rel="stylesheet") if tag.get("href")]
        images = [tag.get("src") for tag in soup.find_all("img") if tag.get("src")]
        forms = soup.find_all("form")

        return {
            "links": links,
            "scripts": scripts,
            "css": css,
            "images": images,
            "has_forms": len(forms) > 0,
        }

    # -----------------------------
    #  Запуск полного анализа
    # -----------------------------
    def analyze(self):
        self.scan_files()

        self.structure = {}
        for item in self.files:
            full = item["full"]
            rel = item["rel"]
            ftype = self.get_file_type(full)

            self.structure[full] = {
                "relative": rel,
                "type": ftype,
                "html_info": None,
            }

            if ftype == "html":
                self.structure[full]["html_info"] = self.analyze_html(full)

        return self.structure

    # -----------------------------
    #  Получение результата
    # -----------------------------
    def get_structure(self, by: str = "full"):
        """
        by='full'     -> вернуть словарь, где ключи — полные пути (поведение по умолчанию).
        by='relative' -> вернуть словарь, где ключи — относительные пути, а внутри есть 'full'.
        """
        if by == "full":
            return self.structure

        if by == "relative":
            return {
                info["relative"]: {
                    "full": full,
                    "type": info["type"],
                    "html_info": info["html_info"],
                }
                for full, info in self.structure.items()
            }

        raise ValueError("by must be 'full' or 'relative'")


    def get_related_files(self, file_path):
        file_path = file_path.lower().strip()
        if file_path.startswith("./"):
            file_path = file_path[2:]

        result = []
        for file, info in self.structure.items():
            if not info['html_info']:
                continue
            #print(f"file: {file} -> {info['html_info']}")
            for block in ['scripts', 'css', 'images']:
                for rel in info['html_info'][block]:
                    if rel.startswith("./"):
                        rel = rel[2:].lower().strip()
                        if file_path == rel:
                            result.append(info['relative'])
        return result

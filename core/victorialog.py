# victorialogs_handler.py
import logging
import requests
import json
from datetime import datetime
from config import VICTORIA_LOGS_HOST, VICTORIA_LOGS_PORT, DEBUG


class VictoriaLogsHandler(logging.Handler):

    def __init__(self, host=VICTORIA_LOGS_HOST, port=VICTORIA_LOGS_PORT, app_name:str=""):
        super().__init__()
        self.url = f"http://{host}:{port}/insert/loki/api/v1/push"
        self.app_name = app_name

    def emit(self, record):
        log_entry = self.format_record(record)

        #print(f"Sending to VictoriaLogs: {json.dumps(log_entry, indent=2)}")

        try:
            response = requests.post(
                self.url,
                json=log_entry,
                headers={'Content-Type': 'application/json'},
                timeout=3
            )
            if response.status_code != 204:
                if DEBUG:
                    print(f"VictoriaLogs error: {response.status_code}")
        except Exception as e:
            if DEBUG:
                print(f"VictoriaLogs emit error: {e}")

    def format_record(self, record):
        stream_labels = {
            "app": self.app_name,
            "level": record.levelname,
            "logger": record.name,
            "module": record.module or "unknown"
        }

        # Добавляем дополнительные поля в labels
        standard_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process', 'message', 'extra_fields'
        }

        # Добавляем дополнительные поля в labels (только строковые значения)
        for attr_name in vars(record):
            if attr_name not in standard_attrs and not attr_name.startswith('_'):
                attr_value = getattr(record, attr_name)
                if attr_value is not None and isinstance(attr_value, (str, int, float, bool)):
                    stream_labels[attr_name] = str(attr_value)

        # Также добавляем поля из extra_fields
        if hasattr(record, 'extra_fields') and record.extra_fields:
            for key, value in record.extra_fields.items():
                if value is not None and isinstance(value, (str, int, float, bool)):
                    stream_labels[key] = str(value)

        # Создаем log line в JSON формате
        log_line = {
            "_msg": record.getMessage(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module or "unknown",
            "function": record.funcName or "unknown",
            "lineno": record.lineno,
            "filename": getattr(record, 'filename', 'unknown')
        }

        # Добавляем дополнительные поля в log line
        for attr_name in vars(record):
            if attr_name not in standard_attrs and not attr_name.startswith('_'):
                attr_value = getattr(record, attr_name)
                if attr_value is not None:
                    log_line[attr_name] = str(attr_value)

        if hasattr(record, 'extra_fields') and record.extra_fields:
            for key, value in record.extra_fields.items():
                if value is not None:
                    log_line[key] = str(value)

        # Loki формат
        log_data = {
            "streams": [
                {
                    "stream": stream_labels,
                    "values": [
                        [
                            str(int(datetime.now().timestamp() * 1000000000)),  # наносекунды
                            json.dumps(log_line)  # сообщение в JSON
                        ]
                    ]
                }
            ]
        }

        return log_data


class CustomLogger:

    def __init__(self, logger, handler):
        self.logger = logger
        self.handler =  handler

    def _makeLogRecord(self, msg, level, **kwargs):
        """Создает кастомную запись лога с дополнительными полями"""
        # Получаем информацию о caller'е
        import inspect
        frame = inspect.currentframe().f_back.f_back  # Два уровня назад
        frame_info = inspect.getframeinfo(frame)

        # Создаем запись лога
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn=frame_info.filename,
            lno=frame_info.lineno,
            msg=msg,
            args=(),
            exc_info=None
        )

        # Добавляем дополнительные поля
        for key, value in kwargs.items():
            setattr(record, key, value)

        return record

    def info(self, msg, **kwargs):
        record = self._makeLogRecord(msg, logging.INFO, **kwargs)
        self.logger.handle(record)

    def warning(self, msg, **kwargs):
        record = self._makeLogRecord(msg, logging.WARNING, **kwargs)
        self.logger.handle(record)

    def error(self, msg, **kwargs):
        record = self._makeLogRecord(msg, logging.ERROR, **kwargs)
        self.logger.handle(record)

    def debug(self, msg, **kwargs):
        record = self._makeLogRecord(msg, logging.DEBUG, **kwargs)
        self.logger.handle(record)

    # Прокси методы для стандартного использования
    def log(self, level, msg, *args, **kwargs):
        self.logger.log(level, msg, *args)

    def setLevel(self, level: str):
        self.handler.setLevel(level)


def setup_logging(app_name=f'Black&White(Release: {not DEBUG})'):
    """Настройка логирования с VictoriaLogs"""
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.INFO)

    # VictoriaLogs handler
    vl_handler = VictoriaLogsHandler(app_name=app_name)
    vl_handler.setLevel(logging.INFO)

    # Console handler для дублирования
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s -  %(message)s'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(vl_handler)
    logger.addHandler(console_handler)

    return CustomLogger(logger, vl_handler)

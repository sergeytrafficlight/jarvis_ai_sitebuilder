import logging
import traceback
from config import VICTORIA_LOGS_ENABLED
from core.victorialog import setup_logging


def add_kwargs_support_to_logger(logger: logging.Logger) -> logging.Logger:
    """
    Добавляет поддержку kwargs к существующему логгеру.
    Возвращает тот же объект логгера с модифицированными методами.
    """
    original_debug = logger.debug
    original_info = logger.info
    original_warning = logger.warning
    original_error = logger.error
    original_critical = logger.critical
    original_log = logger.log

    def make_wrapper(original_method):
        def wrapper(msg, *args, **kwargs):
            # Разделяем стандартные и пользовательские kwargs
            logging_kwargs = {}
            custom_kwargs = {}

            for key, value in kwargs.items():
                if key in ['exc_info', 'stack_info', 'stacklevel', 'extra']:
                    logging_kwargs[key] = value
                else:
                    custom_kwargs[key] = value

            # Форматируем сообщение с пользовательскими параметрами
            if custom_kwargs:
                extra_str = " ".join(f"{k}={v}" for k, v in custom_kwargs.items())
                msg = f"{msg} [{extra_str}]"

            # Вызываем оригинальный метод
            return original_method(msg, *args, **logging_kwargs)

        return wrapper

    # Заменяем методы логгера
    logger.debug = make_wrapper(original_debug)
    logger.info = make_wrapper(original_info)
    logger.warning = make_wrapper(original_warning)
    logger.error = make_wrapper(original_error)
    logger.critical = make_wrapper(original_critical)
    logger.log = make_wrapper(original_log)

    return logger


if not VICTORIA_LOGS_ENABLED:
    logger = logging.getLogger(__name__)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger = add_kwargs_support_to_logger(logger)
else:
    logger = setup_logging()

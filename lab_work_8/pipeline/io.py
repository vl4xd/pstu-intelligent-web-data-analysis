import logging
import sys
import json

def setup_logging():
    log = logging.getLogger("pipeline")
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    
    # Структурированные логи в JSON
    formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": %(message)s}')
    
    # Кастомный форматтер для вывода message как JSON, если это dict/строка JSON
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "time": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "module": record.module,
                "message": record.getMessage()
            }
            if hasattr(record, 'extra'):
                log_record.update(record.extra)
            return json.dumps(log_record)

    handler.setFormatter(JsonFormatter())
    log.addHandler(handler)
    return log
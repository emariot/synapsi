import logging
from functools import wraps
from datetime import datetime

# ============================
# Configuração global do logger
# ============================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logging.getLogger('yfinance').setLevel(logging.WARNING)
logging.getLogger('sqlitedict').setLevel(logging.WARNING)

# ============================
# Configuração do werkzeug
# ============================
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

class DashRequestFilter(logging.Filter):
    def filter(self, record):
        if 'GET /dash' in record.msg or 'POST /dash' in record.msg:
            return False
        return True

werkzeug_logger.addFilter(DashRequestFilter())

# ============================
# Decorador para logar callbacks
# ============================
callback_counter = {}

def log_callback(callback_name=None):
    def decorator(func):
        name = callback_name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            count = callback_counter.get(name, 0) + 1
            callback_counter[name] = count
            start_time = datetime.now()
            logger.info(f"[{start_time.strftime('%H:%M:%S')}][CALLBACK:{name}] ▶ Início (execução #{count})")

            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.info(f"[{end_time.strftime('%H:%M:%S')}][CALLBACK:{name}] ✅ Fim (duração: {duration:.2f}s)")
                return result
            except Exception as e:
                logger.error(f"[CALLBACK:{name}] ❌ Erro durante execução: {e}", exc_info=True)
                raise e  # Relevante para manter comportamento esperado no Dash

        return wrapper
    return decorator
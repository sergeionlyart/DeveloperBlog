"""
Конфигурация Gunicorn для оптимизации производительности и устранения проблем с сигналами

Этот файл содержит настройки для оптимизации стабильности, обработки сигналов
и предотвращения зависаний под нагрузкой.
"""

import multiprocessing
import os
import resource

# Основные настройки сервера
bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1  # Рекомендуемое количество
worker_class = "sync"  # Синхронные воркеры для максимальной стабильности
timeout = 120  # Увеличенный тайм-аут для предотвращения преждевременного убийства процессов
capture_output = True  # Перехватывать вывод для улучшенного логирования

# Предотвращение проблем с сигналами
ignore_winch = True  # Игнорировать сигнал WINCH полностью
forwarded_allow_ips = '*'  # Доверять всем заголовкам X-Forwarded-*
reuse_port = True  # Улучшает поведение при перезапуске
worker_tmp_dir = '/dev/shm'  # Использовать tmpfs для временных файлов, повышает производительность
disable_winch_logs = True  # Отключить логирование событий SIGWINCH
log_winch = False  # Дополнительный флаг отключения логирования SIGWINCH

# Основные оптимизации производительности
max_requests = 1000  # Перезапускать воркеры после обработки 1000 запросов
max_requests_jitter = 200  # Добавить случайность для предотвращения одновременного перезапуска
graceful_timeout = 30  # Время ожидания до принудительного завершения
keepalive = 5  # Сохранять соединение в течение 5 секунд после запроса

# Кастомный класс логгера для подавления WINCH сообщений
class CustomLogger:
    def setup(self, cfg):
        from gunicorn import glogging
        import logging
        
        self._logger = glogging.Logger(cfg)
        self._logger.setup(cfg)
        
        # Получаем оригинальный обработчик
        self.error_handlers = self._logger.error_handlers
        
        # Создаем фильтр для WINCH
        class WinchFilter(logging.Filter):
            def filter(self, record):
                return 'Handling signal: winch' not in record.getMessage()
                
        # Добавляем фильтр ко всем обработчикам логов
        for handler in self.error_handlers:
            handler.addFilter(WinchFilter())
    
    # Проксируем все методы к внутреннему логгеру
    def critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        if 'winch' not in msg.lower():
            self._logger.info(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        if 'winch' not in msg.lower():
            self._logger.debug(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)
    
    def log(self, lvl, msg, *args, **kwargs):
        if 'winch' not in msg.lower():
            self._logger.log(lvl, msg, *args, **kwargs)
    
    def access(self, resp, req, environ, request_time):
        self._logger.access(resp, req, environ, request_time)

# Логирование с улучшенной гибкостью
accesslog = "-"  # Выводить логи доступа в stdout
errorlog = "-"   # Выводить логи ошибок в stdout
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
logger_class = 'gunicorn_config.CustomLogger'

# Отладочные возможности
reload = True  # Перезагрузка при изменении файлов
spew = False  # Включать подробное логирование трассировки (в случае необходимости отладки установите True)

# Регулирование нагрузки для предотвращения перегрузки
worker_connections = 1000  # Максимальное количество соединений на воркер
limit_request_line = 4094  # Ограничение длины строки запроса для предотвращения атак
limit_request_fields = 100  # Ограничение количества заголовков для предотвращения атак
limit_request_field_size = 8190  # Ограничение размера заголовков

# Путь к приложению
wsgi_app = "main:app"

# Дополнительные функции для улучшения стабильности
def post_fork(server, worker):
    """Выполняется после создания рабочего процесса"""
    # Устанавливаем мягкий лимит для файловых дескрипторов
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
    except (ValueError, resource.error):
        pass

def worker_int(worker):
    """Обработчик получения сигнала SIGINT"""
    # Ничего не делаем для предотвращения зависаний из-за несинхронизированного логирования
    pass

def worker_abort(worker):
    """Обработчик аварийного прерывания"""
    # Ничего не делаем для предотвращения зависаний из-за несинхронизированного логирования
    pass
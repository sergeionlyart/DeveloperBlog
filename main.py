import os
import signal
import logging
import threading
from app import app

# Флаг для отслеживания состояния логирования
# Предотвращает рекурсивные вызовы при обработке сигналов
_logging_in_progress = threading.Lock()

# Настройка безопасного логирования для предотвращения реентрантных вызовов
def safe_log(level, message):
    """Логирование с блокировкой для предотвращения проблем с реентрантностью"""
    if _logging_in_progress.acquire(blocking=False):
        try:
            if level == 'debug':
                logging.debug(message)
            elif level == 'info':
                logging.info(message)
            elif level == 'warning':
                logging.warning(message)
            elif level == 'error':
                logging.error(message)
            elif level == 'critical':
                logging.critical(message)
        finally:
            _logging_in_progress.release()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Улучшенный обработчик сигналов для предотвращения зависаний
def handle_signal(signum, frame):
    """Усовершенствованный обработчик сигналов
    
    Важно: Используем safe_log чтобы избежать реентрантных вызовов и зависаний.
    Обрабатываем как WINCH, так и другие критические сигналы.
    """
    signal_names = {
        signal.SIGWINCH: "SIGWINCH (window change)",
        signal.SIGTERM: "SIGTERM (termination)",
        signal.SIGINT: "SIGINT (interrupt)",
        signal.SIGHUP: "SIGHUP (hangup)"
    }
    
    signal_name = signal_names.get(signum, f"Signal {signum}")
    
    # Используем безопасное логирование для предотвращения зависаний
    safe_log('info', f"Received {signal_name}, handling gracefully")
    
    # Для сигналов завершения (TERM, INT, HUP) делаем специальную обработку
    if signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        # Здесь можно выполнить операции очистки перед завершением
        pass

# Регистрируем обработчики сигналов
for sig in (signal.SIGWINCH, signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    try:
        signal.signal(sig, handle_signal)
        safe_log('info', f"Successfully registered handler for signal {sig}")
    except (AttributeError, ValueError) as e:
        safe_log('warning', f"Could not register handler for signal {sig}: {e}")

# Логируем информацию о запуске
safe_log('info', "Application initialization completed")

if __name__ == "__main__":
    safe_log('info', "Starting Flask development server")
    app.run(host="0.0.0.0", port=5000, debug=True)

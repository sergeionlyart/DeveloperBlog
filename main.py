import os
import signal
import logging
from app import app

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Настраиваем обработчик сигнала WINCH для предотвращения проблем
def handle_winch(signum, frame):
    """Пустой обработчик сигнала WINCH для предотвращения зависаний
    
    Важно: НЕ используем логирование здесь, чтобы избежать 
    реентрантных вызовов и зависаний
    """
    return

# Регистрируем обработчик, чтобы перехватывать сигналы до того, как их получит Gunicorn
try:
    signal.signal(signal.SIGWINCH, handle_winch)
    logging.info("Successfully registered WINCH signal handler")
except (AttributeError, ValueError) as e:
    logging.warning(f"Could not register WINCH signal handler: {e}")

if __name__ == "__main__":
    logging.info("Starting Flask development server")
    app.run(host="0.0.0.0", port=5000, debug=True)

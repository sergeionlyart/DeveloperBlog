// Упрощенный JavaScript для админ-панели с расширенным логированием
// Для отслеживания потенциальных проблем и зависаний

// Настройка расширенного логирования
const DEBUG = true;
const LOG_PREFIX = '[Admin Panel]';

// Функция для логирования с таймстампами
function log(message, type = 'info') {
  if (!DEBUG) return;
  
  const timestamp = new Date().toISOString();
  const prefix = `${LOG_PREFIX} [${timestamp}]`;
  
  switch(type) {
    case 'error':
      console.error(`${prefix} ERROR:`, message);
      break;
    case 'warn':
      console.warn(`${prefix} WARNING:`, message);
      break;
    case 'debug':
      console.debug(`${prefix} DEBUG:`, message);
      break;
    default:
      console.log(`${prefix} INFO:`, message);
  }
  
  // При ошибках сохраняем информацию в sessionStorage для диагностики
  if (type === 'error') {
    try {
      const errors = JSON.parse(sessionStorage.getItem('admin_errors') || '[]');
      errors.push({
        timestamp,
        message: typeof message === 'string' ? message : JSON.stringify(message),
        url: window.location.href
      });
      sessionStorage.setItem('admin_errors', JSON.stringify(errors.slice(-10))); // Храним последние 10 ошибок
    } catch (e) {
      console.error('Ошибка при сохранении лога ошибок:', e);
    }
  }
}

// Перехват и логирование всех неперехваченных ошибок
window.onerror = function(message, source, lineno, colno, error) {
  log(`Необработанная ошибка: ${message} (${source}:${lineno}:${colno})`, 'error');
  if (error && error.stack) {
    log(`Стек ошибки: ${error.stack}`, 'error');
  }
  return false; // Позволяем стандартному обработчику ошибок также выполниться
};

// Основная инициализация
document.addEventListener('DOMContentLoaded', function() {
  log("Административная панель загружена");
  
  try {
    // Базовая функция преобразования заголовка в слаг (URL)
    const titleInput = document.getElementById('title');
    const slugInput = document.getElementById('slug');
    
    if (titleInput && slugInput) {
      log("Найдены поля заголовка и slug, настраиваем автогенерацию");
      
      titleInput.addEventListener('input', function() {
        // Генерируем слаг только если поле пустое
        if (slugInput && !slugInput.value.trim()) {
          try {
            log("Генерируем slug из заголовка: " + titleInput.value);
            
            // Простая конвертация без сложной обработки
            let slug = titleInput.value
              .toLowerCase()
              .replace(/[^a-z0-9\s-]/g, '') // Удаляем спецсимволы
              .replace(/\s+/g, '-')         // Заменяем пробелы на дефисы
              .replace(/-+/g, '-');         // Убираем дублирующиеся дефисы
            
            slugInput.value = slug;
            log("Slug сгенерирован успешно: " + slug);
          } catch (e) {
            log("Ошибка при генерации слага: " + e.message, 'error');
          }
        }
      });
    } else {
      if (!titleInput) log("Элемент 'title' не найден на странице", 'warn');
      if (!slugInput) log("Элемент 'slug' не найден на странице", 'warn');
    }

    // Простое подтверждение удаления без сложной обработки DOM
    document.body.addEventListener('click', function(e) {
      if (e.target && e.target.classList.contains('delete-confirm')) {
        log("Запрос на подтверждение удаления элемента");
        if (!confirm('Вы уверены, что хотите удалить этот элемент? Это действие нельзя отменить.')) {
          log("Пользователь отменил удаление");
          e.preventDefault();
        } else {
          log("Пользователь подтвердил удаление");
        }
      }
    });
    
    // Отслеживаем отправку форм для логирования
    const forms = document.querySelectorAll('form');
    if (forms.length > 0) {
      forms.forEach((form, index) => {
        form.addEventListener('submit', function(e) {
          log(`Отправка формы #${index+1} на ${this.action || 'текущую страницу'}`);
        });
      });
    }
    
  } catch (error) {
    log("Ошибка при инициализации административной панели: " + error.message, 'error');
    if (error.stack) {
      log("Стек ошибки: " + error.stack, 'error');
    }
  }
});

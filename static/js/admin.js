// Оптимизированный JavaScript для админ-панели с расширенным логированием
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

// Определение текущей страницы
function detectCurrentPage() {
  const path = window.location.pathname;
  if (path.includes('/admin/article/new') || path.includes('/admin/article/edit/')) {
    return 'article_edit';
  } else if (path.includes('/admin/articles')) {
    return 'articles_list';
  } else if (path.includes('/admin/categories')) {
    return 'categories';
  } else if (path.includes('/admin/tags')) {
    return 'tags';
  } else if (path.includes('/admin')) {
    return 'dashboard';
  }
  return 'unknown';
}

// Инициализация страницы редактирования статьи
function initArticleEditorPage() {
  log("Инициализация страницы редактора статьи");
  
  // Базовая функция преобразования заголовка в слаг (URL)
  const titleInput = document.getElementById('title');
  const slugInput = document.getElementById('slug');
  
  if (titleInput && slugInput) {
    log("Найдены поля заголовка и slug, настраиваем автогенерацию");
    
    titleInput.addEventListener('input', function() {
      // Предотвращаем зависания при вводе длинного текста
      if (titleInput.value.length > 500) {
        log("Предупреждение: длина заголовка превышает 500 символов", 'warn');
      }
      
      // Генерируем слаг только если поле пустое
      if (slugInput && !slugInput.value.trim()) {
        try {
          log("Генерируем slug из заголовка");
          
          // Простая конвертация без сложной обработки
          let slug = titleInput.value
            .toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '') // Удаляем спецсимволы
            .replace(/\s+/g, '-')         // Заменяем пробелы на дефисы
            .replace(/-+/g, '-')          // Убираем дублирующиеся дефисы
            .replace(/^-+|-+$/g, '');     // Убираем начальные и конечные дефисы
          
          // Ограничиваем длину slug для предотвращения проблем
          if (slug.length > 100) {
            slug = slug.substring(0, 100);
            log("Slug был обрезан до 100 символов", 'warn');
          }
          
          slugInput.value = slug;
          log("Slug сгенерирован успешно");
        } catch (e) {
          log("Ошибка при генерации слага: " + e.message, 'error');
        }
      }
    });
    
    // Дополнительно следим за потреблением памяти формой
    const form = document.querySelector('form.article-form');
    if (form) {
      // Мониторинг размера контента
      const contentArea = document.getElementById('content');
      if (contentArea) {
        contentArea.addEventListener('input', function() {
          if (contentArea.value.length > 50000) {
            log("Предупреждение: размер контента превышает 50000 символов, возможны проблемы с производительностью", 'warn');
          }
        });
      }
      
      // Защита от случайной отправки недозаполненной формы
      form.addEventListener('submit', function(e) {
        const title = titleInput.value.trim();
        if (!title) {
          e.preventDefault();
          log("Попытка отправки формы без заголовка предотвращена", 'warn');
          alert('Пожалуйста, заполните заголовок статьи');
          return false;
        }
        log("Форма отправляется. Размер заголовка: " + title.length + " символов");
      });
    }
  } else {
    log("Страница редактора статьи не содержит ожидаемых полей формы", 'warn');
  }
}

// Инициализация страницы списка статей
function initArticlesListPage() {
  log("Инициализация страницы списка статей");
  
  // Ничего специфичного пока не требуется
  const articleTable = document.querySelector('.table');
  if (articleTable) {
    log("Таблица статей найдена");
    
    // Можно добавить сортировку, пагинацию или фильтры в будущем
  }
}

// Общая функциональность для всех страниц администратора
function initCommonAdminFeatures() {
  log("Инициализация общих функций администратора");
  
  // Отслеживание удаления элементов
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
  
  // Отслеживание отправки форм
  const forms = document.querySelectorAll('form');
  if (forms.length > 0) {
    log(`Найдено ${forms.length} форм на странице`);
    forms.forEach((form, index) => {
      form.addEventListener('submit', function(e) {
        log(`Отправка формы #${index+1} на ${this.action || 'текущую страницу'}`);
      });
    });
  }
  
  // Мониторинг ошибок сети
  window.addEventListener('online', function() {
    log("Соединение с интернетом восстановлено");
  });
  
  window.addEventListener('offline', function() {
    log("Соединение с интернетом потеряно", 'warn');
  });
  
  // Отслеживание состояния страницы
  window.addEventListener('beforeunload', function() {
    log("Пользователь покидает страницу");
  });
  
  // Отслеживание видимости страницы
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      log("Страница скрыта (пользователь переключился на другую вкладку)");
    } else {
      log("Страница снова видна");
    }
  });
}

// Основная инициализация
document.addEventListener('DOMContentLoaded', function() {
  const currentPage = detectCurrentPage();
  log(`Административная панель загружена (страница: ${currentPage})`);
  
  try {
    // Инициализация функций только на соответствующих страницах
    if (currentPage === 'article_edit') {
      initArticleEditorPage();
    } else if (currentPage === 'articles_list') {
      initArticlesListPage();
    } else {
      log(`Стандартная инициализация для страницы: ${currentPage}`);
    }
    
    // Общая инициализация для всех страниц админки
    initCommonAdminFeatures();
  } catch (error) {
    log(`Ошибка при инициализации страницы ${currentPage}: ${error.message}`, 'error');
    if (error.stack) {
      log(`Стек ошибки: ${error.stack}`, 'error');
    }
  }
});

// Упрощенный JavaScript для админ-панели без сложной обработки DOM
// Минимальный код для снижения риска ошибок и зависаний

document.addEventListener('DOMContentLoaded', function() {
  console.log("Admin JS loaded successfully");
  
  // Базовая функция преобразования заголовка в слаг (URL)
  const titleInput = document.getElementById('title');
  const slugInput = document.getElementById('slug');
  
  if (titleInput && slugInput) {
    titleInput.addEventListener('input', function() {
      // Генерируем слаг только если поле пустое
      if (slugInput && !slugInput.value.trim()) {
        try {
          // Простая конвертация без сложной обработки
          let slug = titleInput.value
            .toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '') // Удаляем спецсимволы
            .replace(/\s+/g, '-')         // Заменяем пробелы на дефисы
            .replace(/-+/g, '-');         // Убираем дублирующиеся дефисы
          
          slugInput.value = slug;
        } catch (e) {
          console.error("Ошибка при генерации слага:", e);
        }
      }
    });
  }

  // Простое подтверждение удаления без сложной обработки DOM
  document.body.addEventListener('click', function(e) {
    if (e.target && e.target.classList.contains('delete-confirm')) {
      if (!confirm('Вы уверены, что хотите удалить этот элемент? Это действие нельзя отменить.')) {
        e.preventDefault();
      }
    }
  });
});

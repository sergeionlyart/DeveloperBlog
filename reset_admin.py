from app import app, db, ADMIN_USERNAME, ADMIN_PASSWORD
from models import User
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.INFO)

def reset_admin_password():
    """Сбрасывает пароль администратора на значение по умолчанию."""
    try:
        with app.app_context():
            # Находим пользователя admin
            admin = User.query.filter_by(username=ADMIN_USERNAME).first()
            if not admin:
                logging.error(f"Пользователь {ADMIN_USERNAME} не найден")
                return False
                
            # Обновляем хеш пароля
            admin.password_hash = generate_password_hash(ADMIN_PASSWORD)
            db.session.commit()
            
            # Выводим новый хеш для отладки
            logging.info(f"Пароль администратора сброшен на значение по умолчанию")
            logging.info(f"Новый хеш пароля: {admin.password_hash}")
            
            return True
            
    except Exception as e:
        logging.error(f"Ошибка при сбросе пароля: {str(e)}")
        return False

if __name__ == "__main__":
    print("Сброс пароля администратора")
    print("--------------------------")
    
    if reset_admin_password():
        print(f"\nПароль администратора успешно сброшен!")
        print(f"Теперь вы можете войти с учетными данными:")
        print(f"Логин: {ADMIN_USERNAME}")
        print(f"Пароль: {ADMIN_PASSWORD}")
    else:
        print("\nНе удалось сбросить пароль администратора.")
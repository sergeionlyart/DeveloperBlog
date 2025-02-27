from app import app, db
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)

def migrate_database():
    """Применяет изменения схемы базы данных."""
    try:
        with app.app_context():
            # Создаем все таблицы по обновленным моделям
            db.create_all()
            logging.info("Database tables created/verified.")
            
            # Выполняем SQL-запросы для обновления существующих полей по очереди
            # 1. Изменение meta_description на TEXT если он существует как VARCHAR
            check_sql = text("""
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'article' 
                AND column_name = 'meta_description'
                AND data_type = 'character varying'
            """)
            
            result = db.session.execute(check_sql).fetchone()
            if result:
                logging.info("Changing meta_description column type to TEXT...")
                alter_sql = text("ALTER TABLE article ALTER COLUMN meta_description TYPE TEXT")
                db.session.execute(alter_sql)
                logging.info("meta_description column type changed.")
            
            # 2. Изменение meta_title на VARCHAR(200) если он существует и короче
            check_sql = text("""
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'article' 
                AND column_name = 'meta_title'
                AND character_maximum_length < 200
            """)
            
            result = db.session.execute(check_sql).fetchone()
            if result:
                logging.info("Changing meta_title column length to 200...")
                alter_sql = text("ALTER TABLE article ALTER COLUMN meta_title TYPE VARCHAR(200)")
                db.session.execute(alter_sql)
                logging.info("meta_title column length changed.")
            
            # 3. Изменение meta_keywords на VARCHAR(200) если он существует и короче
            check_sql = text("""
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'article' 
                AND column_name = 'meta_keywords'
                AND character_maximum_length < 200
            """)
            
            result = db.session.execute(check_sql).fetchone()
            if result:
                logging.info("Changing meta_keywords column length to 200...")
                alter_sql = text("ALTER TABLE article ALTER COLUMN meta_keywords TYPE VARCHAR(200)")
                db.session.execute(alter_sql)
                logging.info("meta_keywords column length changed.")
            
            # Фиксируем изменения
            db.session.commit()
            logging.info("All database schema changes applied successfully.")
            
    except Exception as e:
        logging.error(f"Error during database migration: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Database Migration")
    print("-----------------")
    
    success = migrate_database()
    
    if success:
        print("\nDatabase migration completed successfully!")
    else:
        print("\nDatabase migration failed. Check the error logs.")
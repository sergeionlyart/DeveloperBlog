from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.INFO)

def create_admin_user(username, email, password):
    """Create an admin user for the blog."""
    try:
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                logging.info(f"User with username '{username}' already exists.")
            if existing_user.email == email:
                logging.info(f"User with email '{email}' already exists.")
            return False
            
        # Create new user
        user = User(
            username=username, 
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True
        )
        
        db.session.add(user)
        db.session.commit()
        logging.info(f"Admin user '{username}' created successfully.")
        return True
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating admin user: {str(e)}")
        return False

if __name__ == "__main__":
    # Run with app context
    with app.app_context():
        # Default admin credentials - for testing only
        username = "admin"
        email = "admin@example.com"
        password = "adminpassword"
        
        # Ask for credentials
        print("Create Admin User")
        print("-----------------")
        print(f"Default: username='{username}', email='{email}', password='{password}'")
        print("Press Enter to use defaults or enter new values.")
        
        new_username = input("Username: ").strip()
        if new_username:
            username = new_username
            
        new_email = input("Email: ").strip()
        if new_email:
            email = new_email
            
        new_password = input("Password: ").strip()
        if new_password:
            password = new_password
        
        # Create the admin user
        if create_admin_user(username, email, password):
            print(f"\nAdmin user '{username}' created successfully!")
            print(f"You can now login at /login with these credentials.")
        else:
            print("\nFailed to create admin user.")
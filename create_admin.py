from app2 import app, db, Admin
from werkzeug.security import generate_password_hash

def create_admin():
    with app.app_context():
        # Check if admin already exists
        admin = Admin.query.filter_by(username='admin').first()
        if admin:
            print("Admin user already exists!")
            return

        # Create new admin user
        admin = Admin(
            username='admin',
            password=generate_password_hash('Admin@123'),
            email='admin@example.com'
        )
        
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: Admin@123")

if __name__ == '__main__':
    create_admin() 
from app import app, init_db, db
from sqlalchemy.exc import IntegrityError

if __name__ == '__main__':
    # Initialize the database
    with app.app_context():
        # Ensure database is created
        db.create_all()
        
        # Initialize database (create admin user, etc.) with error handling
        try:
            init_db()
        except IntegrityError:
            print("Admin user already exists. Skipping initialization.")
            db.session.rollback()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000) 
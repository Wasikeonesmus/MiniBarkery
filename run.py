from app import app, init_db, db

if __name__ == '__main__':
    # Initialize the database
    with app.app_context():
        # Ensure database is created
        db.create_all()
        
        # Initialize database (create admin user, etc.)
        init_db()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000) 
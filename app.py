from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Product, Supplier, Sale, SaleItem, Purchase, Expense, Recipe, ProductionBatch, StockHistory, Payment, Employee
from forms import LoginForm, ProductForm, SupplierForm, RecipeForm, ProductionBatchForm, ExpenseForm, PurchaseForm, PaymentForm, SaleForm, EmployeeForm, RegistrationForm
from datetime import datetime, timezone
import os
import csv
from io import StringIO
import json
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get the database URL from environment variable, with a fallback to SQLite
database_url = os.environ.get('DATABASE_URL', 'sqlite:///bakery.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create database tables
with app.app_context():
    try:
        db.create_all()
        # Create admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@bakery.com', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin user created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# ... rest of your existing code ...

if __name__ == '__main__':
    # For production, use a proper WSGI server like Gunicorn
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 
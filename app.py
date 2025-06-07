from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_file, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, migrate, csrf, login_manager
from forms import LoginForm, ProductForm, SupplierForm, RecipeForm, ProductionBatchForm, ExpenseForm, PurchaseForm, PaymentForm, SaleForm, EmployeeForm, RegistrationForm, StockHistoryForm, ImportForm
from datetime import datetime, timezone, timedelta
import os
import csv
from io import StringIO
import json
from urllib.parse import urlparse
import pathlib
import logging
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text, func
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_caching import Cache
import pandas as pd
from werkzeug.utils import secure_filename
from io import BytesIO
import secrets
from functools import wraps
from logging.handlers import RotatingFileHandler
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import uuid

# Logging Configuration
import logging
from logging.handlers import RotatingFileHandler
import os

# Ensure log directory exists
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logger = logging.getLogger('barkery_system')
logger.setLevel(logging.INFO)

# Create a file handler with a larger max file size and fewer backups
try:
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'), 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=3
    )
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
except PermissionError:
    print("Warning: Unable to create log file. Logging to console only.")

# Create Flask app
app = Flask(__name__)

# Configure app
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///barkery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Handle proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize extensions with app
db.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)
login_manager.init_app(app)

# Import models after db is initialized
from models import *
print("ProductionBatch imported:", ProductionBatch)

# Initialize cache
cache = Cache(app, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes
})

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

def init_db():
    """Initialize the database with default data."""
    try:
        # Drop all existing tables (use with caution in production)
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Check if admin user already exists
        existing_admin = User.query.filter_by(email='admin@example.com').first()
        
        if not existing_admin:
            # Create admin user if not exists
            admin_user = User(
                username='admin', 
                email='admin@example.com', 
                is_active=True
            )
            admin_user.set_password('adminpassword')  # Use a secure password
            db.session.add(admin_user)
        
        # Commit changes
        db.session.commit()
        
        logger.info("Database initialized successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing database: {str(e)}")
        raise

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                user.last_login = datetime.now(timezone.utc)
                db.session.commit()
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('dashboard')
                logger.info(f"User {user.username} logged in successfully")
                return redirect(next_page)
            logger.warning(f"Failed login attempt for username: {form.username.data}")
            flash('Invalid username or password', 'danger')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        logger.info(f"User logged out successfully")
        return redirect(url_for('login'))
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        flash('An error occurred during logout. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get total products
        total_products = Product.query.filter_by(is_active=True).count()
        # Get active products
        active_products = Product.query.filter_by(is_active=True).count()
        # Get today's sales
        today = datetime.now(timezone.utc).date()
        today_sales = Sale.query.filter(
            db.func.date(Sale.sale_date) == today
        ).all()
        today_revenue = sum(sale.total_amount for sale in today_sales)
        today_transactions = len(today_sales)
        # Get this month's sales
        first_day = today.replace(day=1)
        month_sales = Sale.query.filter(
            db.func.date(Sale.sale_date) >= first_day
        ).all()
        month_revenue = sum(sale.total_amount for sale in month_sales)
        month_transactions = len(month_sales)
        # Get recent sales
        recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
        # Get recent stock updates
        recent_stock_updates = StockHistory.query.order_by(StockHistory.created_at.desc()).limit(5).all()
        return render_template('dashboard.html',
            total_products=total_products,
            active_products=active_products,
            today_revenue=today_revenue,
            today_transactions=today_transactions,
            month_revenue=month_revenue,
            month_transactions=month_transactions,
            recent_sales=recent_sales,
            recent_stock_updates=recent_stock_updates)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('An error occurred loading the dashboard.', 'danger')
        return redirect(url_for('index'))

@app.route('/products')
@login_required
def product_list():
    products = Product.query.all()
    return render_template('product_list.html', products=products)

@app.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    form = ProductForm()
    # Populate supplier choices
    suppliers = Supplier.query.filter_by(is_active=True).all()
    form.supplier_id.choices = [(0, 'Select a supplier')] + [(s.id, s.name) for s in suppliers]
    
    if form.validate_on_submit():
        try:
            product = Product(
                name=form.name.data,
                description=form.description.data,
                price=form.price.data,
                category=form.category.data,
                unit=form.unit.data,
                stock_quantity=form.stock_quantity.data,
                minimum_stock_level=form.min_stock.data,
                supplier_id=form.supplier_id.data if form.supplier_id.data != 0 else None,
                is_active=form.is_active.data
            )
            db.session.add(product)
            db.session.commit()
            invalidate_dashboard_cache()
            flash('Product added successfully', 'success')
            return redirect(url_for('product_list'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error adding product: {str(e)}')
            flash(f'Error adding product: {str(e)}', 'danger')
    else:
        # Log specific form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                app.logger.error(f'Validation error in {field}: {error}')
                flash(f'{field}: {error}', 'danger')
    
    return render_template('product_form.html', form=form, title='New Product')

@app.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    # Populate supplier choices
    suppliers = Supplier.query.filter_by(is_active=True).all()
    form.supplier_id.choices = [(0, 'Select a supplier')] + [(s.id, s.name) for s in suppliers]
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.category = form.category.data
        product.supplier_id = form.supplier_id.data if form.supplier_id.data != 0 else None
        product.stock_quantity = form.stock_quantity.data
        product.minimum_stock_level = form.minimum_stock_level.data
        product.reorder_quantity = form.reorder_quantity.data
        product.is_active = form.is_active.data
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Product updated successfully')
        return redirect(url_for('product_list'))
    return render_template('product_form.html', form=form, title='Edit Product', product=product)

@app.route('/products/<int:id>')
@login_required
def product_detail(id):
    product = Product.query.get_or_404(id)
    stock_history = StockHistory.query.filter_by(product_id=id).order_by(StockHistory.created_at.desc()).limit(10).all()
    return render_template('product_detail.html', product=product, stock_history=stock_history)

@app.route('/products/<int:id>/delete', methods=['POST'])
@login_required
def product_delete(id):
    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Product deleted successfully')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product: ' + str(e), 'error')
    return redirect(url_for('product_list'))

@app.route('/pos')
@login_required
def pos():
    products = Product.query.filter_by(is_active=True).all()
    # Get recent sales for reference
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    return render_template('pos.html', products=products, recent_sales=recent_sales)

@app.route('/inventory')
@login_required
def inventory():
    products = Product.query.all()
    low_stock_products = [p for p in products if p.stock_quantity <= p.minimum_stock_level]
    return render_template('inventory.html', products=products, low_stock_products=low_stock_products)

@app.route('/inventory/add-stock', methods=['POST'])
@login_required
def add_stock():
    try:
        # Log all incoming form data for debugging
        logger.info(f"Add Stock Request - Form Data: {dict(request.form)}")
        
        # Get form data
        product_id = request.form.get('product_id')
        quantity = request.form.get('quantity')
        notes = request.form.get('notes', '')
        
        # Validate input
        if not product_id or not quantity:
            logger.error("Add Stock Error: Product ID or quantity missing")
            return jsonify({
                'success': False, 
                'message': 'Product ID and quantity are required'
            }), 400
        
        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except ValueError:
            logger.error(f"Add Stock Error: Invalid product ID or quantity. product_id: {product_id}, quantity: {quantity}")
            return jsonify({
                'success': False, 
                'message': 'Invalid product ID or quantity'
            }), 400
        
        # Find the product
        product = Product.query.get(product_id)
        if not product:
            logger.error(f"Add Stock Error: Product not found. ID: {product_id}")
            return jsonify({
                'success': False, 
                'message': 'Product not found'
            }), 404
        
        # Update stock quantity
        product.stock_quantity += quantity
        product.updated_at = datetime.now(timezone.utc)
        
        # Create stock history record
        stock_history = StockHistory(
            product_id=product.id,
            quantity=quantity,
            type='addition',
            notes=notes,
            user_id=current_user.id
        )
        
        # Add to session and commit
        try:
            db.session.add(stock_history)
            db.session.commit()
            
            # Invalidate dashboard cache
            invalidate_dashboard_cache()
            
            logger.info(f"Stock added successfully. Product: {product.name}, Quantity: {quantity}")
            
            return jsonify({
                'success': True, 
                'message': f'Added {quantity} units to {product.name}'
            }), 200
        
        except Exception as commit_error:
            db.session.rollback()
            logger.error(f"Database commit error: {str(commit_error)}")
            return jsonify({
                'success': False, 
                'message': 'Error saving stock addition to database'
            }), 500
    
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in add_stock: {str(e)}")
        
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred while adding stock'
        }), 500

@app.route('/inventory/adjust-stock/<int:product_id>', methods=['POST'])
@login_required
def adjust_stock(product_id):
    """Adjust stock quantity for a specific product."""
    try:
        # Get form data
        quantity = request.form.get('quantity')
        adjustment_type = request.form.get('adjustment_type')

        # Validate inputs
        if not quantity or not adjustment_type:
            return jsonify({
                'success': False, 
                'message': 'Missing required parameters.'
            }), 400

        try:
            quantity = int(quantity)
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Quantity must be a valid number.'
            }), 400

        # Validate quantity
        if quantity <= 0:
            return jsonify({
                'success': False, 
                'message': 'Quantity must be a positive number.'
            }), 400

        # Find the product
        product = Product.query.get_or_404(product_id)

        # Adjust stock based on type
        if adjustment_type == 'add':
            product.stock_quantity += quantity
        elif adjustment_type == 'remove':
            if product.stock_quantity < quantity:
                return jsonify({
                    'success': False, 
                    'message': f'Cannot remove more stock than available for {product.name}.'
                }), 400
            product.stock_quantity -= quantity
        else:
            return jsonify({
                'success': False, 
                'message': 'Invalid adjustment type.'
            }), 400

        # Log stock adjustment
        stock_adjustment = StockAdjustment(
            product_id=product.id,
            quantity=quantity,
            adjustment_type=adjustment_type,
            user_id=current_user.id
        )
        db.session.add(stock_adjustment)
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': f'Successfully {"added" if adjustment_type == "add" else "removed"} {quantity} units from {product.name} stock.'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating stock adjustment: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'An error occurred while adjusting stock. Please try again later.'
        }), 500

@app.route('/inventory/history/<int:product_id>')
@login_required
def stock_history(product_id):
    product = Product.query.get_or_404(product_id)
    history = StockHistory.query.filter_by(product_id=product_id).order_by(StockHistory.created_at.desc()).all()
    return render_template('stock_history.html', product=product, history=history)

@app.route('/inventory/export')
@login_required
def export_inventory():
    
    products = Product.query.all()
    
    # Create CSV data
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product', 'Category', 'Current Stock', 'Minimum Level', 'Status', 'Last Updated'])
    
    for product in products:
        writer.writerow([
            product.name,
            product.category,
            product.stock_quantity,
            product.minimum_stock_level,
            'Low Stock' if product.stock_quantity <= product.minimum_stock_level else 'In Stock',
            product.updated_at.strftime('%Y-%m-%d')
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=inventory.csv'}
    )

@app.route('/suppliers')
@login_required
def supplier_list():
    suppliers = Supplier.query.all()
    return render_template('supplier_list.html', suppliers=suppliers)

@app.route('/suppliers/new', methods=['GET', 'POST'])
@login_required
def new_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        try:
            supplier = Supplier(
                name=form.name.data,
                contact_person=form.contact_person.data,
                phone=form.phone.data,
                email=form.email.data,
                address=form.address.data
            )
            db.session.add(supplier)
            db.session.commit()
            flash('Supplier added successfully', 'success')
            return redirect(url_for('supplier_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding supplier: {str(e)}', 'danger')
    return render_template('supplier_form.html', form=form, title='New Supplier')

@app.route('/suppliers/<int:id>')
@login_required
def supplier_detail(id):
    supplier = Supplier.query.get_or_404(id)
    products = Product.query.filter_by(supplier_id=id).all()
    return render_template('supplier_detail.html', supplier=supplier, products=products)

@app.route('/suppliers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)
    if form.validate_on_submit():
        supplier.name = form.name.data
        supplier.contact_person = form.contact_person.data
        supplier.phone = form.phone.data
        supplier.email = form.email.data
        supplier.address = form.address.data
        supplier.is_active = form.is_active.data
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Supplier updated successfully')
        return redirect(url_for('supplier_list'))
    return render_template('supplier_form.html', form=form, title='Edit Supplier', supplier=supplier)

@app.route('/suppliers/<int:id>/delete', methods=['POST'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    invalidate_dashboard_cache()
    flash('Supplier deleted successfully')
    return redirect(url_for('supplier_list'))

@app.route('/financial')
@login_required
def financial():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('financial.html', expenses=expenses)

@app.route('/production')
@login_required
def production():
    try:
        recipes = Recipe.query.filter_by(is_active=True).all()
        recent_batches = ProductionBatch.query.order_by(ProductionBatch.start_time.desc()).limit(10).all()
        return render_template('production.html', recipes=recipes, recent_batches=recent_batches)
    except Exception as e:
        logger.error(f"Production route error: {str(e)}")
        flash('An error occurred loading the production page.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/expenses/new', methods=['GET', 'POST'])
@login_required
def new_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        expense = Expense(
            date=form.date.data,
            type=form.type.data,
            amount=form.amount.data,
            description=form.description.data
        )
        db.session.add(expense)
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Expense added successfully')
        return redirect(url_for('financial'))
    return render_template('expense_form.html', form=form, title='New Expense')

@app.route('/expenses/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    expense = Expense.query.get_or_404(id)
    form = ExpenseForm(obj=expense)
    if form.validate_on_submit():
        expense.date = form.date.data
        expense.type = form.type.data
        expense.amount = form.amount.data
        expense.description = form.description.data
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Expense updated successfully')
        return redirect(url_for('financial'))
    return render_template('expense_form.html', form=form, title='Edit Expense', expense=expense)

@app.route('/expenses/<int:id>/delete', methods=['POST'])
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    invalidate_dashboard_cache()
    flash('Expense deleted successfully')
    return redirect(url_for('financial'))

@app.route('/expenses')
@login_required
def expense_list():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    form = ExpenseForm()
    return render_template('expense_list.html', expenses=expenses, form=form)

@app.route('/sales/<int:id>/payment', methods=['GET', 'POST'])
@login_required
def process_payment(id):
    sale = Sale.query.get_or_404(id)
    form = PaymentForm()
    
    if form.validate_on_submit():
        payment = Payment(
            sale_id=sale.id,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            transaction_id=form.transaction_id.data if form.payment_method.data in ['mpesa', 'card'] else None,
            status='completed'
        )
        
        # Calculate total paid amount
        total_paid = sum(p.amount for p in sale.payments if p.status == 'completed') + form.amount.data
        
        # Update sale payment status
        if total_paid >= sale.total_amount:
            sale.payment_status = 'completed'
        elif total_paid > 0:
            sale.payment_status = 'partial'
        
        db.session.add(payment)
        db.session.commit()
        
        invalidate_dashboard_cache()
        
        flash('Payment processed successfully!', 'success')
        return redirect(url_for('sale_detail', id=sale.id))
    
    return render_template('payment_form.html', sale=sale, form=form)

@app.route('/sales/<int:id>/payments')
@login_required
def sale_payments(id):
    sale = Sale.query.get_or_404(id)
    return render_template('sale_payments.html', sale=sale)

@app.route('/payments/<int:id>/status', methods=['POST'])
@login_required
def update_payment_status(id):
    payment = Payment.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    
    payment.status = data['status']
    
    # Update sale payment status
    sale = payment.sale
    total_paid = sum(p.amount for p in sale.payments if p.status == 'completed')
    
    if total_paid >= sale.total_amount:
        sale.payment_status = 'completed'
    elif total_paid > 0:
        sale.payment_status = 'partial'
    else:
        sale.payment_status = 'pending'
    
    db.session.commit()
    invalidate_dashboard_cache()
    return jsonify({'success': True})

@app.route('/sales/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    form = SaleForm()
    
    # Populate product choices
    products = Product.query.filter_by(is_active=True).all()
    product_choices = [(p.id, f"{p.name} (KES {p.price:.2f})") for p in products]
    for item_form in form.items:
        item_form.product_id.choices = product_choices
    
    if form.validate_on_submit():
        # Create new sale
        sale = Sale(
            customer_name=form.customer_name.data or None,
            total_amount=0  # Will be calculated from items
        )
        db.session.add(sale)
        
        # Process sale items
        total_amount = 0
        for item_form in form.items:
            product = Product.query.get(item_form.product_id.data)
            if not product:
                flash('Invalid product selected', 'error')
                return redirect(url_for('new_sale'))
            
            # Check stock availability
            if product.stock_quantity < item_form.quantity.data:
                flash(f'Insufficient stock for {product.name}. Available: {product.stock_quantity}', 'error')
                return redirect(url_for('new_sale'))
            
            # Create sale item
            sale_item = SaleItem(
                sale=sale,
                product=product,
                quantity=item_form.quantity.data,
                unit_price=item_form.unit_price.data,
                total_price=item_form.quantity.data * item_form.unit_price.data
            )
            db.session.add(sale_item)
            
            # Update stock
            product.stock_quantity -= item_form.quantity.data
            
            # Add stock history entry
            stock_history = StockHistory(
                product=product,
                quantity=-item_form.quantity.data,
                type='sale',
                notes=f'Sale #{sale.id}',
                user=current_user
            )
            db.session.add(stock_history)
            
            total_amount += sale_item.total_price
        
        # Update sale total
        sale.total_amount = total_amount
        
        try:
            db.session.commit()
            invalidate_dashboard_cache()
            flash('Sale completed successfully!', 'success')
            return redirect(url_for('process_payment', id=sale.id))
        except Exception as e:
            db.session.rollback()
            flash('Error processing sale. Please try again.', 'error')
            return redirect(url_for('new_sale'))
    
    return render_template('sale_form.html', form=form)

@app.route('/api/products/<int:id>/price')
@login_required
def get_product_price(id):
    product = Product.query.get_or_404(id)
    return jsonify({'price': product.price})

@app.route('/employees')
@login_required
def employee_list():
    employees = Employee.query.order_by(Employee.name).all()
    return render_template('employee_list.html', employees=employees)

@app.route('/employees/create', methods=['GET', 'POST'])
@login_required
def employee_create():
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            role=form.role.data,
            department=form.department.data,
            salary=form.salary.data,
            hire_date=form.hire_date.data,
            is_active=form.is_active.data,
            can_manage_employees=form.can_manage_employees.data,
            can_manage_inventory=form.can_manage_inventory.data,
            can_manage_finance=form.can_manage_finance.data,
            can_manage_system=form.can_manage_system.data,
            can_manage_suppliers=form.can_manage_suppliers.data,
            can_process_sales=form.can_process_sales.data,
            can_manage_production=form.can_manage_production.data
        )
        db.session.add(employee)
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Employee created successfully!', 'success')
        return redirect(url_for('employee_list'))
    return render_template('employee_form.html', form=form)

@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def employee_edit(id):
    employee = Employee.query.get_or_404(id)
    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        employee.name = form.name.data
        employee.phone = form.phone.data
        employee.email = form.email.data
        employee.role = form.role.data
        employee.department = form.department.data
        employee.salary = form.salary.data
        employee.hire_date = form.hire_date.data
        employee.is_active = form.is_active.data
        employee.can_manage_employees = form.can_manage_employees.data
        employee.can_manage_inventory = form.can_manage_inventory.data
        employee.can_manage_finance = form.can_manage_finance.data
        employee.can_manage_system = form.can_manage_system.data
        employee.can_manage_suppliers = form.can_manage_suppliers.data
        employee.can_process_sales = form.can_process_sales.data
        employee.can_manage_production = form.can_manage_production.data
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employee_list'))
    return render_template('employee_form.html', form=form, employee=employee)

@app.route('/employees/<int:id>/delete', methods=['POST'])
@login_required
def employee_delete(id):
    employee = Employee.query.get_or_404(id)
    try:
        db.session.delete(employee)
        db.session.commit()
        invalidate_dashboard_cache()
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting employee. They may have associated records.', 'danger')
    return redirect(url_for('employee_list'))

@app.route('/pos/process', methods=['POST'])
@login_required
def process_sale():
    try:
        # Log all form data for debugging
        logger.info(f"Received form data: {request.form}")
        
        # Attempt to parse items
        items_str = request.form.get('items', '[]')
        logger.info(f"Items string: {items_str}")
        
        try:
            items = json.loads(items_str)
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON Decode Error: {json_err}")
            flash(f'Invalid items data: {json_err}', 'error')
            return redirect(url_for('pos'))

        # Validate total amount
        try:
            total_amount = float(request.form.get('total_amount', 0))
        except ValueError as val_err:
            logger.error(f"Total amount conversion error: {val_err}")
            flash('Invalid total amount', 'error')
            return redirect(url_for('pos'))

        # Get other form data with default values
        customer_name = request.form.get('customer_name', '')
        payment_method = request.form.get('payment_method', 'cash')

        # Validate items list
        if not items:
            flash('No items in the sale', 'error')
            return redirect(url_for('pos'))

        # Create new sale
        sale = Sale(
            customer_name=customer_name,
            total_amount=total_amount,
            payment_method=payment_method,
            sale_date=datetime.now(timezone.utc),
            payment_status='completed' if payment_method == 'cash' else 'pending'
        )
        db.session.add(sale)

        # Add sale items
        for item in items:
            # Validate item data
            if not all(key in item for key in ['id', 'quantity', 'price']):
                logger.error(f"Invalid item data: {item}")
                flash('Invalid item data', 'error')
                db.session.rollback()
                return redirect(url_for('pos'))

            product = db.session.get(Product, item['id'])
            if not product:
                logger.error(f"Product not found: {item['id']}")
                flash(f"Product with ID {item['id']} not found", 'error')
                db.session.rollback()
                return redirect(url_for('pos'))
            
            # Update product stock
            if product.stock_quantity < item['quantity']:
                logger.error(f"Insufficient stock for {product.name}")
                flash(f"Insufficient stock for {product.name}", 'error')
                db.session.rollback()
                return redirect(url_for('pos'))
            
            product.stock_quantity -= item['quantity']
            
            # Create sale item
            sale_item = SaleItem(
                sale=sale,
                product=product,
                quantity=item['quantity'],
                unit_price=item['price'],
                total_price=item['price'] * item['quantity']
            )
            db.session.add(sale_item)

            # Add stock history entry
            stock_history = StockHistory(
                product=product,
                quantity=-item['quantity'],
                type='sale',
                notes=f'Sale #{sale.id}',
                user=current_user
            )
            db.session.add(stock_history)

        db.session.commit()
        invalidate_dashboard_cache()
        flash('Sale completed successfully', 'success')
        return redirect(url_for('pos'))
    except Exception as e:
        logger.error(f"Unexpected error processing sale: {str(e)}", exc_info=True)
        db.session.rollback()
        flash(f'Unexpected error: {str(e)}', 'error')
        return redirect(url_for('pos'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Ensure database tables are created
            db.create_all()
            
            # Check if user already exists
            existing_user_by_username = User.query.filter_by(username=form.username.data).first()
            existing_user_by_email = User.query.filter_by(email=form.email.data).first()
            
            if existing_user_by_username:
                flash('Username already taken. Please choose a different one.', 'danger')
                return render_template('register.html', title='Register', form=form)
            
            if existing_user_by_email:
                flash('Email already registered. Please use a different one.', 'danger')
                return render_template('register.html', title='Register', form=form)
            
            # Create new user
            user = User(
                username=form.username.data, 
                email=form.email.data,
                is_active=True
            )
            user.set_password(form.password.data)
            
            # Add and commit the new user
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            # Rollback the session in case of any error
            db.session.rollback()
            
            # Log the specific error
            logger.error(f"Registration error: {str(e)}")
            
            # Check for specific error types
            if 'UNIQUE constraint' in str(e):
                flash('An account with this username or email already exists.', 'danger')
            else:
                flash('An unexpected error occurred. Please try again.', 'danger')
    
    return render_template('register.html', title='Register', form=form)

@app.route('/import/<type>', methods=['GET', 'POST'])
@login_required
def import_data(type):
    if type not in ['products', 'suppliers', 'inventory']:
        flash('Invalid import type', 'danger')
        return redirect(url_for('dashboard'))
    
    form = ImportForm()
    if form.validate_on_submit():
        try:
            file = form.file.data
            if not file:
                flash('Please select a file to import', 'danger')
                return redirect(url_for('import_data', type=type))
            
            # Process the file based on type
            if type == 'products':
                process_product_import(file)
            elif type == 'suppliers':
                process_supplier_import(file)
            elif type == 'inventory':
                process_inventory_import(file)
            
            flash(f'{type.title()} imported successfully', 'success')
            return redirect(url_for(f'{type}_list'))
        except Exception as e:
            logger.error(f"Import error: {str(e)}")
            flash('Error importing data. Please check the file format and try again.', 'danger')
    
    return render_template('import_form.html', type=type, form=form)

def process_product_import(file):
    # Read the file
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    # Process each row
    for _, row in df.iterrows():
        product = Product(
            name=row['name'],
            price=float(row['price']),
            description=row.get('description', ''),
            category=row.get('category', ''),
            stock_quantity=int(row.get('stock_quantity', 0)),
            minimum_stock_level=int(row.get('minimum_stock_level', 0)),
            reorder_quantity=int(row.get('reorder_quantity', 0)),
            is_active=bool(row.get('is_active', True))
        )
        db.session.add(product)
    
    db.session.commit()

def process_supplier_import(file):
    # Read the file
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    # Process each row
    for _, row in df.iterrows():
        supplier = Supplier(
            name=row['name'],
            contact_person=row.get('contact_person', ''),
            phone=row.get('phone', ''),
            email=row.get('email', ''),
            address=row.get('address', ''),
            is_active=bool(row.get('is_active', True))
        )
        db.session.add(supplier)
    
    db.session.commit()

def process_inventory_import(file):
    # Read the file
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    # Process each row
    for _, row in df.iterrows():
        product = Product.query.get(int(row['product_id']))
        if not product:
            continue
        
        quantity = int(row['quantity'])
        if row['type'].lower() == 'in':
            product.stock_quantity += quantity
        else:
            product.stock_quantity -= quantity
        
        # Add stock history entry
        history = StockHistory(
            product=product,
            quantity=quantity if row['type'].lower() == 'in' else -quantity,
            type=row['type'].lower(),
            reference=row.get('reference', ''),
            notes=f'Bulk import - {row.get("reference", "")}'
        )
        db.session.add(history)
    
    db.session.commit()

# Add cache invalidation for relevant operations
def invalidate_dashboard_cache():
    cache.delete_memoized(dashboard)

@app.route('/download/template/<type>')
@login_required
def download_template(type):
    if type == 'products':
        data = {
            'name': ['Sample Product 1', 'Sample Product 2'],
            'price': [100.00, 200.00],
            'description': ['Description 1', 'Description 2'],
            'category': ['Category 1', 'Category 2'],
            'stock_quantity': [10, 20],
            'minimum_stock_level': [5, 10],
            'reorder_quantity': [20, 30],
            'is_active': [True, True]
        }
        filename = 'product_import_template.xlsx'
    elif type == 'suppliers':
        data = {
            'name': ['Supplier 1', 'Supplier 2'],
            'contact_person': ['John Doe', 'Jane Smith'],
            'phone': ['1234567890', '0987654321'],
            'email': ['john@example.com', 'jane@example.com'],
            'address': ['Address 1', 'Address 2'],
            'is_active': [True, True]
        }
        filename = 'supplier_import_template.xlsx'
    elif type == 'inventory':
        data = {
            'product_id': [1, 2],
            'quantity': [10, -5],
            'type': ['in', 'out'],
            'reference': ['PO123', 'SO456'],
            'date': ['2024-03-20', '2024-03-20']
        }
        filename = 'inventory_import_template.xlsx'
    else:
        flash('Invalid template type', 'error')
        return redirect(url_for('dashboard'))
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
        worksheet = writer.sheets['Template']
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = max_length
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('error.html', message=e.description), 400

@app.route('/sales')
@login_required
def sale_list():
    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    form = SaleForm()
    return render_template('sale_list.html', sales=sales, form=form)

@app.route('/import/products', methods=['GET', 'POST'])
@login_required
def import_products():
    form = ImportForm()
    if form.validate_on_submit():
        file = form.file.data
        # Implement file import logic here
        flash('Products imported successfully', 'success')
        return redirect(url_for('product_list'))
    return render_template('import_form.html', form=form, title='Import Products')

@app.route('/sales/<int:id>')
@login_required
def sale_detail(id):
    sale = Sale.query.get_or_404(id)
    
    # Debug logging for sale items
    logger.info(f"Sale {id} details:")
    logger.info(f"Total amount: {sale.total_amount}")
    logger.info("Sale items:")
    for item in sale.items:
        logger.info(f"- Product: {item.product.name}")
        logger.info(f"  Quantity: {item.quantity}")
        logger.info(f"  Unit Price: {item.unit_price}")
        logger.info(f"  Total Price: {item.total_price}")
    
    return render_template('sale_detail.html', sale=sale)

@app.route('/sales/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_sale(id):
    sale = Sale.query.get_or_404(id)
    form = SaleForm(obj=sale)
    
    # Populate product choices
    products = Product.query.filter_by(is_active=True).all()
    product_choices = [(p.id, f"{p.name} (KES {p.price:.2f})") for p in products]
    
    # Dynamically add existing sale items to the form
    while len(form.items) < len(sale.items):
        form.items.append_entry()
    
    # Populate existing sale items
    for i, item in enumerate(sale.items):
        form.items[i].product_id.choices = product_choices
        form.items[i].product_id.data = item.product_id
        form.items[i].quantity.data = item.quantity
        form.items[i].unit_price.data = item.unit_price
    
    if form.validate_on_submit():
        # Restore original stock quantities
        for item in sale.items:
            product = Product.query.get(item.product_id)
            product.stock_quantity += item.quantity
        
        # Remove existing sale items
        SaleItem.query.filter_by(sale_id=sale.id).delete()
        
        # Update sale details
        sale.customer_name = form.customer_name.data
        sale.total_amount = 0  # Will be recalculated
        
        # Process updated sale items
        total_amount = 0
        for item_form in form.items:
            product = Product.query.get(item_form.product_id.data)
            if not product:
                flash('Invalid product selected', 'error')
                return redirect(url_for('edit_sale', id=sale.id))
            
            # Check stock availability
            if product.stock_quantity < item_form.quantity.data:
                flash(f'Insufficient stock for {product.name}. Available: {product.stock_quantity}', 'error')
                return redirect(url_for('edit_sale', id=sale.id))
            
            # Create updated sale item
            sale_item = SaleItem(
                sale=sale,
                product=product,
                quantity=item_form.quantity.data,
                unit_price=item_form.unit_price.data,
                total_price=item_form.quantity.data * item_form.unit_price.data
            )
            db.session.add(sale_item)
            
            # Update stock
            product.stock_quantity -= item_form.quantity.data
            
            # Add stock history entry
            stock_history = StockHistory(
                product=product,
                quantity=-item_form.quantity.data,
                type='sale_edit',
                notes=f'Sale Edit #{sale.id}',
                user=current_user
            )
            db.session.add(stock_history)
            
            total_amount += sale_item.total_price
        
        # Update sale total
        sale.total_amount = total_amount
        
        try:
            db.session.commit()
            invalidate_dashboard_cache()
            flash('Sale updated successfully!', 'success')
            return redirect(url_for('sale_detail', id=sale.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating sale: {str(e)}', 'error')
            return redirect(url_for('edit_sale', id=sale.id))
    
    return render_template('sale_form.html', form=form, title='Edit Sale', sale=sale)

@app.route('/sales/<int:id>/delete', methods=['POST'])
@login_required
def delete_sale(id):
    sale = Sale.query.get_or_404(id)
    
    try:
        # Restore stock quantities for all sale items
        for item in sale.items:
            product = Product.query.get(item.product_id)
            product.stock_quantity += item.quantity
        
        # Delete sale and its associated items
        db.session.delete(sale)
        db.session.commit()
        
        invalidate_dashboard_cache()
        
        return jsonify({'success': True, 'message': 'Sale deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/sales/<int:id>/debug')
@login_required
def sale_debug(id):
    sale = Sale.query.get_or_404(id)
    
    # Detailed debug information
    debug_info = {
        'sale_id': sale.id,
        'customer_name': sale.customer_name,
        'total_amount': sale.total_amount,
        'payment_method': sale.payment_method,
        'payment_status': sale.payment_status,
        'sale_date': sale.sale_date.isoformat(),
        'items': []
    }
    
    for item in sale.items:
        debug_info['items'].append({
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'total_price': item.total_price
        })
    
    return jsonify(debug_info)

@app.route('/inventory/reorder/<int:product_id>', methods=['POST'])
@login_required
def reorder_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        # Calculate reorder quantity
        reorder_qty = max(product.reorder_quantity, product.minimum_stock_level * 2)
        
        # Create a purchase order or log reorder request
        purchase_order = PurchaseOrder(
            supplier_id=product.supplier_id,
            status='pending',
            total_amount=reorder_qty * product.unit_price
        )
        db.session.add(purchase_order)
        
        # Create purchase order item
        purchase_order_item = PurchaseOrderItem(
            purchase_order=purchase_order,
            product=product,
            quantity=reorder_qty,
            unit_price=product.unit_price
        )
        db.session.add(purchase_order_item)
        
        # Log reorder event
        reorder_history = StockHistory(
            product_id=product.id,
            quantity=0,  # No actual stock change yet
            type='reorder',
            notes=f'Reorder request for {reorder_qty} units',
            user_id=current_user.id
        )
        db.session.add(reorder_history)
        
        db.session.commit()
        
        # Send notification (could be email, SMS, or in-app notification)
        logger.info(f"Reorder request created for {product.name}. Quantity: {reorder_qty}")
        
        return jsonify({
            'success': True, 
            'message': f'Reorder request created for {product.name}. Quantity: {reorder_qty}'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating reorder request: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Failed to create reorder request'
        }), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

# test commit verifying git detection

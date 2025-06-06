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
import pathlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the project directory
BASE_DIR = pathlib.Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / 'data'
DATABASE_PATH = DATABASE_DIR / 'bakery.db'

# Create data directory if it doesn't exist
DATABASE_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# Get the database URL from environment variable, with a fallback to SQLite
database_url = os.environ.get('DATABASE_URL', f'sqlite:///{DATABASE_PATH}')
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
login_manager.session_protection = 'strong'
login_manager.needs_refresh_message = 'Please reauthenticate to access this page.'
login_manager.needs_refresh_message_category = 'info'
login_manager.refresh_view = 'login'
login_manager.localize_callback = None
login_manager.use_session = True

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

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard')
            return redirect(next_page)
        flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash('Passwords do not match', 'error')
            return render_template('register.html', form=form)
        
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('login')
        return redirect(next_page)
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    next_page = request.args.get('next')
    if not next_page or urlparse(next_page).netloc != '':
        next_page = url_for('login')
    return redirect(next_page)

@app.route('/dashboard')
@login_required
def dashboard():
    # Get summary statistics
    total_products = Product.query.count()
    active_products = Product.query.filter_by(is_active=True).count()
    low_stock_products = Product.query.filter(Product.stock_quantity <= Product.minimum_stock_level).count()
    
    # Get today's sales
    today = get_current_time().date()
    today_sales = Sale.query.filter(
        db.func.date(Sale.sale_date) == today
    ).all()
    today_revenue = sum(sale.total_amount for sale in today_sales)
    today_transactions = len(today_sales)
    
    # Get this month's sales
    first_day_of_month = today.replace(day=1)
    month_sales = Sale.query.filter(
        db.func.date(Sale.sale_date) >= first_day_of_month
    ).all()
    month_revenue = sum(sale.total_amount for sale in month_sales)
    month_transactions = len(month_sales)
    
    # Get low stock products
    low_stock_products_list = Product.query.filter(
        Product.stock_quantity <= Product.minimum_stock_level
    ).all()
    
    # Get recent sales
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    
    # Get top selling products
    top_products = db.session.query(
        Product,
        db.func.sum(SaleItem.quantity).label('total_quantity')
    ).join(SaleItem).group_by(Product.id).order_by(db.desc('total_quantity')).limit(5).all()
    
    # Get recent stock updates
    recent_stock_updates = StockHistory.query.order_by(StockHistory.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         total_products=total_products,
                         active_products=active_products,
                         low_stock_products=low_stock_products,
                         today_revenue=today_revenue,
                         today_transactions=today_transactions,
                         month_revenue=month_revenue,
                         month_transactions=month_transactions,
                         low_stock_products_list=low_stock_products_list,
                         recent_sales=recent_sales,
                         top_products=top_products,
                         recent_stock_updates=recent_stock_updates)

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
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            category=form.category.data,
            supplier_id=form.supplier_id.data if form.supplier_id.data != 0 else None,
            stock_quantity=form.stock_quantity.data,
            minimum_stock_level=form.minimum_stock_level.data,
            reorder_quantity=form.reorder_quantity.data,
            is_active=form.is_active.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully')
        return redirect(url_for('product_list'))
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
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    notes = request.form.get('notes')
    
    try:
        product = Product.query.get_or_404(product_id)
        product.stock_quantity += int(quantity)
        product.updated_at = get_current_time()
        
        # Create stock history record
        stock_history = StockHistory(
            product_id=product.id,
            quantity=int(quantity),
            type='addition',
            notes=notes,
            user_id=current_user.id
        )
        
        db.session.add(stock_history)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/inventory/adjust-stock/<int:product_id>', methods=['POST'])
@login_required
def adjust_stock(product_id):
    quantity = request.form.get('quantity')
    notes = request.form.get('notes')
    
    try:
        product = Product.query.get_or_404(product_id)
        product.stock_quantity = int(quantity)
        product.updated_at = get_current_time()
        
        # Create stock history record
        stock_history = StockHistory(
            product_id=product.id,
            quantity=int(quantity),
            type='adjustment',
            notes=notes,
            user_id=current_user.id
        )
        
        db.session.add(stock_history)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

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
    form = SupplierForm()
    return render_template('supplier_list.html', suppliers=suppliers, form=form)

@app.route('/suppliers/new', methods=['GET', 'POST'])
@login_required
def new_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            contact_person=form.contact_person.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data,
            is_active=form.is_active.data
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added successfully')
        return redirect(url_for('supplier_list'))
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
        flash('Supplier updated successfully')
        return redirect(url_for('supplier_list'))
    return render_template('supplier_form.html', form=form, title='Edit Supplier', supplier=supplier)

@app.route('/suppliers/<int:id>/delete', methods=['POST'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
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
    recipes = Recipe.query.filter_by(is_active=True).all()
    recent_batches = ProductionBatch.query.order_by(ProductionBatch.start_time.desc()).limit(10).all()
    return render_template('production.html', recipes=recipes, recent_batches=recent_batches)

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
        flash('Expense updated successfully')
        return redirect(url_for('financial'))
    return render_template('expense_form.html', form=form, title='Edit Expense', expense=expense)

@app.route('/expenses/<int:id>/delete', methods=['POST'])
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully')
    return redirect(url_for('financial'))

@app.route('/expenses')
@login_required
def expense_list():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('expense_list.html', expenses=expenses)

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
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting employee. They may have associated records.', 'danger')
    return redirect(url_for('employee_list'))

@app.route('/pos/process', methods=['POST'])
@login_required
def process_sale():
    try:
        items = json.loads(request.form.get('items', '[]'))
        total_amount = float(request.form.get('total_amount', 0))
        customer_name = request.form.get('customer_name', '')
        payment_method = request.form.get('payment_method', 'cash')

        # Create new sale
        sale = Sale(
            customer_name=customer_name,
            total_amount=total_amount,
            payment_method=payment_method,
            sale_date=get_current_time(),
            payment_status='completed' if payment_method == 'cash' else 'pending'
        )
        db.session.add(sale)

        # Add sale items
        for item in items:
            product = db.session.get(Product, item['id'])
            if not product:
                raise ValueError(f"Product with ID {item['id']} not found")
            
            # Update product stock
            if product.stock_quantity < item['quantity']:
                raise ValueError(f"Insufficient stock for {product.name}")
            
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
        flash('Sale completed successfully', 'success')
        return redirect(url_for('pos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing sale: {str(e)}', 'error')
        return redirect(url_for('pos'))

if __name__ == '__main__':
    # For production, use a proper WSGI server like Gunicorn
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)

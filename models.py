from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy import event, Index
from sqlalchemy.orm import validates

def get_current_time():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_current_time)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @validates('email')
    def validate_email(self, key, email):
        if not '@' in email:
            raise ValueError('Invalid email address')
        return email

    def __repr__(self):
        return f'<User {self.username}>'

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    @validates('email')
    def validate_email(self, key, email):
        if email and not '@' in email:
            raise ValueError('Invalid email address')
        return email

    def __repr__(self):
        return f'<Supplier {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, index=True)
    category = db.Column(db.String(50), index=True)
    unit = db.Column(db.String(20), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), index=True)
    stock_quantity = db.Column(db.Integer, default=0, index=True)
    minimum_stock_level = db.Column(db.Integer, default=10)
    reorder_quantity = db.Column(db.Integer, default=20)
    image_path = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=get_current_time, index=True)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    supplier = db.relationship('Supplier', backref='products', lazy=True)

    @validates('price')
    def validate_price(self, key, price):
        if price < 0:
            raise ValueError('Price cannot be negative')
        return price

    @validates('stock_quantity', 'minimum_stock_level', 'reorder_quantity')
    def validate_quantity(self, key, value):
        if value < 0:
            raise ValueError(f'{key} cannot be negative')
        return value

    def needs_restock(self):
        return self.stock_quantity <= self.minimum_stock_level

    def __repr__(self):
        return f'<Product {self.name}>'

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='cash')
    payment_status = db.Column(db.String(20), default='completed')
    sale_date = db.Column(db.DateTime, default=get_current_time, index=True)
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Sale {self.id}>'

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_time)

    product = db.relationship('Product', backref='sale_items', lazy=True)

    @validates('quantity', 'unit_price', 'total_price')
    def validate_values(self, key, value):
        if value < 0:
            raise ValueError(f'{key} cannot be negative')
        return value

    def __repr__(self):
        return f'<SaleItem {self.id}>'

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=get_current_time)
    delivery_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_current_time)

    supplier = db.relationship('Supplier', backref=db.backref('purchases', lazy=True))

    def __repr__(self):
        return f'<Purchase {self.id}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_time)

    def __repr__(self):
        return f'<Expense {self.type} {self.amount}>'

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    ingredients = db.Column(db.Text)
    instructions = db.Column(db.Text)
    preparation_time = db.Column(db.Integer)  # in minutes
    yield_quantity = db.Column(db.Integer)
    yield_unit = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    batches = db.relationship('ProductionBatch', backref='recipe', lazy=True)

    def __repr__(self):
        return f'<Recipe {self.name}>'

class Employee(db.Model):
    __tablename__ = 'employee'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    role = db.Column(db.String(50), nullable=False)  # baker, sales, cleaning, manager, inventory_manager, accountant, system_admin
    department = db.Column(db.String(50))  # production, sales, management, inventory, finance, IT
    salary = db.Column(db.Float)
    hire_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    # Track employee's work
    production_batches = db.relationship('ProductionBatch', backref='employee', lazy=True)
    
    # Role-based permissions
    can_manage_employees = db.Column(db.Boolean, default=False)  # For managers
    can_manage_inventory = db.Column(db.Boolean, default=False)  # For inventory managers
    can_manage_finance = db.Column(db.Boolean, default=False)    # For accountants
    can_manage_system = db.Column(db.Boolean, default=False)     # For system admins
    can_manage_suppliers = db.Column(db.Boolean, default=False)  # For managers/inventory managers
    can_process_sales = db.Column(db.Boolean, default=False)     # For sales staff
    can_manage_production = db.Column(db.Boolean, default=False) # For bakers/managers

    def __repr__(self):
        return f'<Employee {self.name}>'

    @property
    def role_display(self):
        role_display_map = {
            'baker': 'Baker',
            'sales': 'Sales Staff',
            'cleaning': 'Cleaning Staff',
            'manager': 'Manager',
            'inventory_manager': 'Inventory Manager',
            'accountant': 'Accountant',
            'system_admin': 'System Administrator'
        }
        return role_display_map.get(self.role, self.role.title())

    @property
    def department_display(self):
        department_display_map = {
            'production': 'Production',
            'sales': 'Sales',
            'management': 'Management',
            'inventory': 'Inventory',
            'finance': 'Finance',
            'IT': 'IT'
        }
        return department_display_map.get(self.department, self.department.title() if self.department else '')

    def has_permission(self, permission):
        permission_map = {
            'manage_employees': self.can_manage_employees,
            'manage_inventory': self.can_manage_inventory,
            'manage_finance': self.can_manage_finance,
            'manage_system': self.can_manage_system,
            'manage_suppliers': self.can_manage_suppliers,
            'process_sales': self.can_process_sales,
            'manage_production': self.can_manage_production
        }
        return permission_map.get(permission, False)

class ProductionBatch(db.Model):
    __tablename__ = 'production_batch'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.DateTime, default=get_current_time)
    end_time = db.Column(db.DateTime)
    quantity_produced = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_current_time)

    def __repr__(self):
        return f'<ProductionBatch {self.batch_number}>'

class StockHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'addition', 'subtraction', 'sale'
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=get_current_time, index=True)

    product = db.relationship('Product', backref='stock_history', lazy=True)
    user = db.relationship('User', backref='stock_history', lazy=True)

    @validates('quantity')
    def validate_quantity(self, key, value):
        if value == 0:
            raise ValueError('Quantity cannot be zero')
        return value

    def __repr__(self):
        return f'<StockHistory {self.id}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False, index=True)
    transaction_id = db.Column(db.String(100), index=True)
    payment_date = db.Column(db.DateTime, default=get_current_time, index=True)
    status = db.Column(db.String(20), default='pending', index=True)
    created_at = db.Column(db.DateTime, default=get_current_time, index=True)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)

    def __repr__(self):
        return f'<Payment {self.id}>'

class StockAdjustment(db.Model):
    """Model to track stock adjustments for products."""
    __tablename__ = 'stock_adjustments'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    adjustment_type = db.Column(db.String(10), nullable=False)  # 'add' or 'remove'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    product = db.relationship('Product', backref=db.backref('stock_adjustments', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('stock_adjustments', lazy='dynamic'))

    def __repr__(self):
        return f'<StockAdjustment {self.id} - {self.adjustment_type} {self.quantity}>'

# Add event listeners for automatic timestamp updates
@event.listens_for(db.Model, 'before_update')
def receive_before_update(mapper, connection, target):
    if hasattr(target, 'updated_at'):
        target.updated_at = get_current_time()

# Add composite indexes for common queries
Index('idx_sale_date_status', Sale.sale_date, Sale.payment_status)
Index('idx_product_category_active', Product.category, Product.is_active)
Index('idx_stock_history_product_date', StockHistory.product_id, StockHistory.created_at)
Index('idx_payment_sale_date', Payment.sale_id, Payment.payment_date)

if __name__ == '__main__':
    # This is for testing the models
    with app.app_context():
        db.create_all() 
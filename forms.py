from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, BooleanField, DateField, DateTimeField, DecimalField, SubmitField, FieldList, FormField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, NumberRange, ValidationError
from datetime import datetime
from flask_login import current_user
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    category = SelectField('Category', choices=[
        ('bread', 'Bread'),
        ('pastry', 'Pastry'),
        ('cake', 'Cake'),
        ('cookie', 'Cookie'),
        ('other', 'Other')
    ])
    supplier_id = SelectField('Supplier', coerce=int, validators=[Optional()])
    stock_quantity = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)])
    minimum_stock_level = IntegerField('Minimum Stock Level', validators=[DataRequired(), NumberRange(min=0)])
    reorder_quantity = IntegerField('Reorder Quantity', validators=[Optional(), NumberRange(min=0)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Submit')

class SupplierForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    contact_person = StringField('Contact Person')
    phone = StringField('Phone')
    email = StringField('Email', validators=[Optional(), Email()])
    address = TextAreaField('Address')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')

class RecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    ingredients = TextAreaField('Ingredients', validators=[DataRequired()])
    instructions = TextAreaField('Instructions', validators=[DataRequired()])
    preparation_time = IntegerField('Preparation Time (minutes)', validators=[NumberRange(min=0)])
    yield_quantity = IntegerField('Yield Quantity', validators=[NumberRange(min=0)])
    yield_unit = StringField('Yield Unit')
    is_active = BooleanField('Active')

class ProductionBatchForm(FlaskForm):
    recipe_id = SelectField('Recipe', coerce=int, validators=[DataRequired()])
    batch_number = StringField('Batch Number', validators=[DataRequired()])
    start_time = DateTimeField('Start Time', format='%Y-%m-%d %H:%M:%S', default=datetime.utcnow)
    quantity_produced = IntegerField('Quantity Produced', validators=[NumberRange(min=0)])
    notes = TextAreaField('Notes')

class ExpenseForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()])
    type = SelectField('Type', choices=[
        ('ingredients', 'Ingredients'),
        ('utilities', 'Utilities'),
        ('rent', 'Rent'),
        ('equipment', 'Equipment'),
        ('salaries', 'Salaries'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Save')

class PurchaseForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    order_date = DateField('Order Date', format='%Y-%m-%d', default=datetime.utcnow)
    delivery_date = DateField('Delivery Date', format='%Y-%m-%d')
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('delivered', 'Delivered')
    ])
    total_amount = FloatField('Total Amount', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Notes')

class PaymentForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'),
        ('mpesa', 'M-PESA'),
        ('card', 'Card')
    ], validators=[DataRequired()])
    transaction_id = StringField('Transaction ID (for M-PESA/Card)')
    submit = SubmitField('Process Payment')

class SaleItemForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    unit_price = FloatField('Unit Price', validators=[DataRequired(), NumberRange(min=0.01)])

class SaleForm(FlaskForm):
    customer_name = StringField('Customer Name')
    items = FieldList(FormField(SaleItemForm), min_entries=1)
    add_item = SubmitField('Add Item')
    remove_item = SubmitField('Remove Item')
    submit = SubmitField('Complete Sale')

class EmployeeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone = StringField('Phone')
    email = StringField('Email', validators=[Optional(), Email()])
    role = SelectField('Role', choices=[
        ('baker', 'Baker'),
        ('sales', 'Sales Staff'),
        ('cleaning', 'Cleaning Staff'),
        ('manager', 'Manager'),
        ('inventory_manager', 'Inventory Manager'),
        ('accountant', 'Accountant'),
        ('system_admin', 'System Administrator')
    ], validators=[DataRequired()])
    department = SelectField('Department', choices=[
        ('production', 'Production'),
        ('sales', 'Sales'),
        ('management', 'Management'),
        ('inventory', 'Inventory'),
        ('finance', 'Finance'),
        ('IT', 'IT')
    ], validators=[DataRequired()])
    salary = FloatField('Salary', validators=[Optional(), NumberRange(min=0)])
    hire_date = DateField('Hire Date', validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    
    # Role-based permissions
    can_manage_employees = BooleanField('Can Manage Employees')
    can_manage_inventory = BooleanField('Can Manage Inventory')
    can_manage_finance = BooleanField('Can Manage Finance')
    can_manage_system = BooleanField('Can Manage System')
    can_manage_suppliers = BooleanField('Can Manage Suppliers')
    can_process_sales = BooleanField('Can Process Sales')
    can_manage_production = BooleanField('Can Manage Production')
    
    submit = SubmitField('Save Employee') 
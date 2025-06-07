import json
import unittest
from app import app, db
from models import User, Product, Expense, Sale, Supplier, SaleItem
from forms import ExpenseForm, ProductForm, ImportForm
from flask_login import login_user, current_user

class TestRoutes(unittest.TestCase):
    def setUp(self):
        """Set up test client and initialize database"""
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection for testing
        app.config['SERVER_NAME'] = 'localhost'
        
        # Create test client
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Reset the database before each test
        db.drop_all()
        db.create_all()
        
        # Create a test user
        self.test_user = User(
            username='testuser', 
            email='testuser@example.com', 
            is_active=True
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        db.session.commit()

    def tearDown(self):
        """Clean up after each test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self):
        """Helper method to log in the test user"""
        login_response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)
        return login_response

    def test_login(self):
        """Test user login"""
        response = self.login()
        self.assertEqual(response.status_code, 200)
        
    def test_dashboard_route(self):
        """Test dashboard route"""
        self.login()
        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_product_routes(self):
        """Test product-related routes"""
        self.login()
        
        # Test product list
        response = self.app.get('/products')
        self.assertEqual(response.status_code, 200)
        
        # Test new product route
        supplier = Supplier(name='Test Supplier', is_active=True)
        db.session.add(supplier)
        db.session.commit()
        
        product_data = {
            'name': 'Test Product',
            'price': 100.00,
            'category': 'test',
            'unit': 'piece',
            'supplier_id': supplier.id,
            'stock_quantity': 10,
            'minimum_stock_level': 5
        }
        
        response = self.app.post('/products/new', data=product_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_expense_routes(self):
        """Test expense-related routes"""
        self.login()
        
        # Test expense list
        response = self.app.get('/expenses')
        self.assertEqual(response.status_code, 200)
        
        # Test new expense route
        expense_data = {
            'description': 'Test Expense',
            'amount': 100.00,
            'type': 'operational'
        }
        response = self.app.post('/expenses/new', data=expense_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_sale_routes(self):
        """Test sale-related routes"""
        self.login()
        
        # Test sale list
        response = self.app.get('/sales')
        self.assertEqual(response.status_code, 200)
        
        # Create a supplier and product first
        supplier = Supplier(name='Test Supplier', is_active=True)
        db.session.add(supplier)
        
        product = Product(
            name='Test Cake',
            price=500.00,
            category='cake',
            unit='piece',
            minimum_stock_level=5,
            stock_quantity=10,
            supplier_id=supplier.id,
            is_active=True
        )
        db.session.add(product)
        db.session.commit()
        
        # Test new sale route
        sale_data = {
            'customer_name': 'Test Customer',
            'total_amount': 500.00,
            'items-0-product_id': product.id,
            'items-0-quantity': 1,
            'items-0-unit_price': 500.00
        }
        response = self.app.post('/sales/new', data=sale_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_import_routes(self):
        """Test import routes"""
        self.login()
        
        # Test import products route
        response = self.app.get('/import/products')
        self.assertEqual(response.status_code, 200)

    def test_logout_route(self):
        """Test logout route"""
        self.login()
        response = self.app.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_pos_route(self):
        """Test the Point of Sale (POS) route"""
        self.login()
        
        # Create a supplier and products for testing
        supplier = Supplier(name='Test Supplier', is_active=True)
        db.session.add(supplier)
        
        # Create multiple test products
        products = [
            Product(
                name='Test Bread',
                price=50.00,
                category='bread',
                unit='loaf',
                minimum_stock_level=5,
                stock_quantity=20,
                supplier_id=supplier.id,
                is_active=True
            ),
            Product(
                name='Test Cake',
                price=500.00,
                category='cake',
                unit='piece',
                minimum_stock_level=5,
                stock_quantity=10,
                supplier_id=supplier.id,
                is_active=True
            )
        ]
        db.session.add_all(products)
        db.session.commit()

        # Test POS page load
        response = self.app.get('/pos')
        self.assertEqual(response.status_code, 200)
        
        # Test POS sale processing
        sale_data = {
            'items': json.dumps([
                {
                    'id': products[0].id,
                    'name': 'Test Bread',
                    'price': 50.00,
                    'quantity': 2
                },
                {
                    'id': products[1].id,
                    'name': 'Test Cake',
                    'price': 500.00,
                    'quantity': 1
                }
            ]),
            'total_amount': '600.00',
            'customer_name': 'Test Customer',
            'payment_method': 'cash'
        }
        
        # Process the sale
        response = self.app.post('/pos/process', data=sale_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify sale was created
        sale = Sale.query.order_by(Sale.id.desc()).first()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.customer_name, 'Test Customer')
        self.assertEqual(sale.total_amount, 600.00)
        self.assertEqual(sale.payment_method, 'cash')
        self.assertEqual(sale.payment_status, 'completed')
        
        # Verify sale items
        self.assertEqual(len(sale.items), 2)
        
        # Check product stock reduction
        updated_bread = Product.query.get(products[0].id)
        updated_cake = Product.query.get(products[1].id)
        self.assertEqual(updated_bread.stock_quantity, 18)  # 20 - 2
        self.assertEqual(updated_cake.stock_quantity, 9)   # 10 - 1
        
        # Test insufficient stock scenario
        insufficient_sale_data = {
            'items': json.dumps([
                {
                    'id': products[0].id,
                    'name': 'Test Bread',
                    'price': 50.00,
                    'quantity': 25  # More than available stock
                }
            ]),
            'total_amount': '1250.00',
            'customer_name': 'Insufficient Stock Customer',
            'payment_method': 'cash'
        }
        
        # Process sale with insufficient stock
        response = self.app.post('/pos/process', data=insufficient_sale_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify no additional sale was created
        sales_count = Sale.query.count()
        self.assertEqual(sales_count, 1)  # Only the previous sale exists
        
        # Verify product stock remains unchanged
        bread_stock = Product.query.get(products[0].id)
        self.assertEqual(bread_stock.stock_quantity, 18)

    def test_pos_route_validation(self):
        """Test POS route validation and error handling"""
        self.login()
        
        # Test empty cart submission
        empty_sale_data = {
            'items': '[]',
            'total_amount': '0.00',
            'customer_name': '',
            'payment_method': 'cash'
        }
        
        response = self.app.post('/pos/process', data=empty_sale_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify no sale was created
        sales_count = Sale.query.count()
        self.assertEqual(sales_count, 0)
        
        # Test invalid product
        invalid_product_data = {
            'items': json.dumps([
                {
                    'id': 9999,  # Non-existent product ID
                    'name': 'Invalid Product',
                    'price': 100.00,
                    'quantity': 1
                }
            ]),
            'total_amount': '100.00',
            'customer_name': 'Test Customer',
            'payment_method': 'cash'
        }
        
        response = self.app.post('/pos/process', data=invalid_product_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify no sale was created
        sales_count = Sale.query.count()
        self.assertEqual(sales_count, 0)

if __name__ == '__main__':
    unittest.main() 
import unittest
import json
from app import app, db
from models import User, Product, Sale, SaleItem, Supplier

class TestRoutes(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        # Create test user
        user = User(username='testuser', email='test@example.com', is_admin=True)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self):
        return self.app.post('/login', data=dict(
            username='testuser',
            password='password123'
        ), follow_redirects=True)

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_login_logout(self):
        # Test login
        response = self.login()
        self.assertEqual(response.status_code, 200)
        
        # Test logout
        response = self.app.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_access(self):
        # Try accessing dashboard without login
        response = self.app.get('/dashboard', follow_redirects=True)
        self.assertIn(b'login', response.data)

        # Login and try again
        self.login()
        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_product_creation(self):
        self.login()
        # Create a supplier first
        supplier = Supplier(name='Test Supplier', email='supplier@example.com')
        db.session.add(supplier)
        db.session.commit()
        # GET the form to set up choices
        self.app.get('/products/new')
        response = self.app.post('/products/new', data=dict(
            name='Test Product',
            description='Test Description',
            price=10.99,
            category='Test Category',
            supplier_id=str(supplier.id),
            stock_quantity=100,
            minimum_stock_level=10,
            reorder_quantity=20,
            is_active=True
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        product = Product.query.filter_by(name='Test Product').first()
        self.assertIsNotNone(product)
        self.assertEqual(product.price, 10.99)

    def test_sale_processing(self):
        self.login()
        # Create a test product
        product = Product(name='Test Product', price=10, stock_quantity=10)
        db.session.add(product)
        db.session.commit()

        # Process a sale
        sale_data = {
            'items': json.dumps([{
                'id': product.id,
                'name': 'Test Product',
                'price': 10,
                'quantity': 2
            }]),
            'total_amount': '20.00',
            'customer_name': 'Test Customer',
            'payment_method': 'cash'
        }
        
        response = self.app.post('/pos/process', data=sale_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Verify sale was created
        sale = Sale.query.first()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.total_amount, 20.00)
        self.assertEqual(len(sale.items), 1)
        self.assertEqual(sale.items[0].quantity, 2)

    def test_inventory_management(self):
        self.login()
        # Create a test product
        product = Product(name='Test Product', price=10, stock_quantity=10)
        db.session.add(product)
        db.session.commit()

        # Add stock
        response = self.app.post('/inventory/add-stock', data=dict(
            product_id=product.id,
            quantity=5,
            notes='Test addition'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Verify stock was updated
        updated_product = Product.query.get(product.id)
        self.assertEqual(updated_product.stock_quantity, 15)

if __name__ == '__main__':
    unittest.main() 
import unittest
import uuid
from datetime import datetime, timezone
from app import app, db
from models import Product, StockHistory, User, Supplier, PurchaseOrder, PurchaseOrderItem
from flask_login import login_user, current_user, login_manager

class InventoryTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for the entire test class"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test_secret_key'  # Add a secret key for login
        
        # Create application context
        cls.app_context = app.app_context()
        cls.app_context.push()
        
        # Create test database
        db.create_all()
        
        # Generate unique username and email for the test class
        cls.unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
        cls.unique_email = f'test_{uuid.uuid4().hex[:8]}@example.com'
        
        # Create a test user
        cls.test_user = User(
            username=cls.unique_username, 
            email=cls.unique_email, 
            is_active=True
        )
        cls.test_user.set_password('testpassword')
        db.session.add(cls.test_user)
        
        # Create test products
        cls.test_product1 = Product(
            name='Test Product 1', 
            stock_quantity=50, 
            minimum_stock_level=10, 
            price=100.0, 
            reorder_quantity=20,
            unit='kg',
            is_active=True
        )
        cls.test_product2 = Product(
            name='Test Product 2', 
            stock_quantity=20,
            minimum_stock_level=5, 
            price=50.0,
            reorder_quantity=10,
            unit='kg',
            is_active=True
        )
        db.session.add(cls.test_product1)
        db.session.add(cls.test_product2)
        
        # Commit changes
        db.session.commit()

    def setUp(self):
        """Set up for each test method"""
        # Create test client
        self.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()

    def tearDown(self):
        """Reset database state between tests"""
        # Reset product quantities
        self.test_product1.stock_quantity = 50
        self.test_product2.stock_quantity = 20
        db.session.commit()

    def _login_test_user(self):
        """Helper method to log in the test user"""
        # Manually log in the user
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id

    def test_add_stock_success(self):
        """Test successful stock addition"""
        # Log in the test user
        self._login_test_user()
        
        # Prepare data for stock addition
        data = {
            'product_id': self.test_product1.id,
            'quantity': 50,
            'notes': 'Test stock addition'
        }
        
        # Send POST request to add stock
        response = self.client.post('/inventory/add-stock', data=data)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify stock quantity updated
        updated_product = Product.query.get(self.test_product1.id)
        self.assertEqual(updated_product.stock_quantity, 100)
        
        # Verify stock history created
        stock_history = StockHistory.query.filter_by(
            product_id=self.test_product1.id, 
            type='addition'
        ).first()
        self.assertIsNotNone(stock_history)
        self.assertEqual(stock_history.quantity, 50)
        self.assertEqual(stock_history.notes, 'Test stock addition')

    def test_add_stock_invalid_product(self):
        """Test adding stock with invalid product ID"""
        # Log in the test user
        self._login_test_user()
        
        # Prepare data with non-existent product ID
        data = {
            'product_id': 9999,  # Non-existent product
            'quantity': 50,
            'notes': 'Test invalid stock addition'
        }
        
        # Send POST request to add stock
        response = self.client.post('/inventory/add-stock', data=data)
        
        # Check response
        self.assertEqual(response.status_code, 404)

    def test_add_stock_invalid_quantity(self):
        """Test adding stock with invalid quantity"""
        # Log in the test user
        self._login_test_user()
        
        # Prepare data with invalid quantity
        data = {
            'product_id': self.test_product1.id,
            'quantity': 'invalid',  # Invalid quantity
            'notes': 'Test invalid quantity'
        }
        
        # Send POST request to add stock
        response = self.client.post('/inventory/add-stock', data=data)
        
        # Check response
        self.assertEqual(response.status_code, 400)

    def test_adjust_stock(self):
        """Test stock adjustment"""
        # Log in the test user
        self._login_test_user()
        
        # Prepare data for stock adjustment
        data = {
            'quantity': 75,
            'notes': 'Stock adjustment test'
        }
        
        # Send POST request to adjust stock
        response = self.client.post(f'/inventory/adjust-stock/{self.test_product1.id}', data=data)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify stock quantity updated
        updated_product = Product.query.get(self.test_product1.id)
        self.assertEqual(updated_product.stock_quantity, 75)
        
        # Verify stock history created
        stock_history = StockHistory.query.filter_by(
            product_id=self.test_product1.id, 
            type='adjustment'
        ).first()
        self.assertIsNotNone(stock_history)
        self.assertEqual(stock_history.quantity, 75)
        self.assertEqual(stock_history.notes, 'Stock adjustment test')

    def test_low_stock_detection(self):
        """Test low stock detection"""
        # Log in the test user
        self._login_test_user()
        
        # Reduce stock to below minimum level
        self.test_product1.stock_quantity = 5
        db.session.commit()
        
        # Get inventory page
        response = self.client.get('/inventory')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Check that the low stock product is in the context
        self.assertIn(b'Low Stock Alert', response.data)
        self.assertIn(self.test_product1.name.encode(), response.data)

    def test_stock_history(self):
        """Test stock history retrieval"""
        # Log in the test user
        self._login_test_user()
        
        # Create some stock history entries
        stock_history1 = StockHistory(
            product=self.test_product1,
            quantity=20,
            type='addition',
            notes='Initial stock',
            user=self.test_user
        )
        stock_history2 = StockHistory(
            product=self.test_product1,
            quantity=-10,
            type='sale',
            notes='Sale transaction',
            user=self.test_user
        )
        db.session.add(stock_history1)
        db.session.add(stock_history2)
        db.session.commit()
        
        # Get stock history for the product
        response = self.client.get(f'/inventory/history/{self.test_product1.id}')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Check that history entries are present
        self.assertIn(b'Initial stock', response.data)
        self.assertIn(b'Sale transaction', response.data)

    def test_reorder_product(self):
        """Test reorder product functionality"""
        # Log in the test user
        self._login_test_user()
        
        # Create a supplier for the test product
        supplier = Supplier(
            name='Test Supplier', 
            email='supplier@example.com', 
            is_active=True
        )
        db.session.add(supplier)
        
        # Update test product with supplier and reorder details
        self.test_product1.supplier_id = supplier.id
        self.test_product1.reorder_quantity = 20
        self.test_product1.stock_quantity = 5  # Below minimum stock level
        db.session.commit()
        
        # Send POST request to reorder product
        response = self.client.post(f'/inventory/reorder/{self.test_product1.id}')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify purchase order created
        purchase_order = PurchaseOrder.query.filter_by(
            supplier_id=supplier.id, 
            status='pending'
        ).first()
        self.assertIsNotNone(purchase_order)
        
        # Verify purchase order item
        purchase_order_item = PurchaseOrderItem.query.filter_by(
            purchase_order_id=purchase_order.id, 
            product_id=self.test_product1.id
        ).first()
        self.assertIsNotNone(purchase_order_item)
        
        # Verify stock history entry
        stock_history = StockHistory.query.filter_by(
            product_id=self.test_product1.id, 
            type='reorder'
        ).first()
        self.assertIsNotNone(stock_history)
        self.assertIn('Reorder request', stock_history.notes)

if __name__ == '__main__':
    unittest.main()
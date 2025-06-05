import unittest
from datetime import datetime, timezone
from app import app, db
from models import User, Product, Sale, SaleItem, Supplier, StockHistory

class TestModels(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_creation(self):
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

            saved_user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(saved_user)
            self.assertEqual(saved_user.email, 'test@example.com')
            self.assertTrue(saved_user.check_password('password123'))
            self.assertFalse(saved_user.check_password('wrongpassword'))

    def test_product_validation(self):
        with app.app_context():
            # Test negative price
            with self.assertRaises(ValueError):
                product = Product(name='Test Product', price=-10)
                db.session.add(product)
                db.session.commit()

            # Test negative stock
            with self.assertRaises(ValueError):
                product = Product(name='Test Product', price=10, stock_quantity=-5)
                db.session.add(product)
                db.session.commit()

            # Test valid product
            product = Product(name='Test Product', price=10, stock_quantity=5)
            db.session.add(product)
            db.session.commit()
            self.assertEqual(product.price, 10)
            self.assertEqual(product.stock_quantity, 5)

    def test_sale_creation(self):
        with app.app_context():
            # Create a product
            product = Product(name='Test Product', price=10, stock_quantity=10)
            db.session.add(product)
            db.session.commit()

            # Create a sale
            sale = Sale(customer_name='Test Customer', total_amount=20)
            db.session.add(sale)
            db.session.commit()

            # Add sale item
            sale_item = SaleItem(
                sale=sale,
                product=product,
                quantity=2,
                unit_price=10,
                total_price=20
            )
            db.session.add(sale_item)
            db.session.commit()

            # Verify sale
            saved_sale = Sale.query.first()
            self.assertEqual(saved_sale.customer_name, 'Test Customer')
            self.assertEqual(saved_sale.total_amount, 20)
            self.assertEqual(len(saved_sale.items), 1)
            self.assertEqual(saved_sale.items[0].quantity, 2)

    def test_stock_history(self):
        with app.app_context():
            # Create a product
            product = Product(name='Test Product', price=10, stock_quantity=10)
            db.session.add(product)
            db.session.commit()

            # Create a user
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

            # Add stock history
            history = StockHistory(
                product=product,
                quantity=5,
                type='addition',
                notes='Test addition',
                user=user
            )
            db.session.add(history)
            db.session.commit()

            # Verify history
            saved_history = StockHistory.query.first()
            self.assertEqual(saved_history.quantity, 5)
            self.assertEqual(saved_history.type, 'addition')
            self.assertEqual(saved_history.product.name, 'Test Product')

    def test_supplier_validation(self):
        with app.app_context():
            # Test invalid email
            with self.assertRaises(ValueError):
                supplier = Supplier(name='Test Supplier', email='invalid-email')
                db.session.add(supplier)
                db.session.commit()

            # Test valid supplier
            supplier = Supplier(name='Test Supplier', email='valid@example.com')
            db.session.add(supplier)
            db.session.commit()
            self.assertEqual(supplier.email, 'valid@example.com')

if __name__ == '__main__':
    unittest.main() 
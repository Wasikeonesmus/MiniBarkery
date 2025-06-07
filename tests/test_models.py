import unittest
from datetime import datetime, timedelta
from app import app, db
from models import User, Product, Expense, Sale, Supplier

class TestModels(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation(self):
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()

        retrieved_user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(retrieved_user)
        self.assertTrue(retrieved_user.check_password('testpassword'))

    def test_product_creation(self):
        supplier = Supplier(name='Test Supplier', is_active=True)
        db.session.add(supplier)
        db.session.commit()

        product = Product(
            name='Test Bread',
            price=50.00,
            category='bread',
            unit='loaf',
            minimum_stock_level=10,
            stock_quantity=20,
            supplier_id=supplier.id,
            is_active=True
        )
        db.session.add(product)
        db.session.commit()

        retrieved_product = Product.query.filter_by(name='Test Bread').first()
        self.assertIsNotNone(retrieved_product)
        self.assertEqual(retrieved_product.price, 50.00)

    def test_expense_creation(self):
        expense = Expense(
            date=datetime.now().date(),
            type='ingredients',
            amount=1000.00,
            description='Flour purchase'
        )
        db.session.add(expense)
        db.session.commit()

        retrieved_expense = Expense.query.filter_by(description='Flour purchase').first()
        self.assertIsNotNone(retrieved_expense)
        self.assertEqual(retrieved_expense.amount, 1000.00)

    def test_sale_creation(self):
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

        sale = Sale(
            sale_date=datetime.now(),
            total_amount=500.00,
            customer_name='Walk-in Customer'
        )
        db.session.add(sale)
        db.session.commit()

        retrieved_sale = Sale.query.filter_by(customer_name='Walk-in Customer').first()
        self.assertIsNotNone(retrieved_sale)
        self.assertEqual(retrieved_sale.total_amount, 500.00)

if __name__ == '__main__':
    unittest.main() 
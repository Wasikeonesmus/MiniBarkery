# Bakery Management System

A comprehensive bakery management system built with Django that helps manage all aspects of a bakery business.

## Features

1. **Point of Sale (POS) System**
   - Process sales transactions
   - Multiple payment methods (Cash, M-PESA, Card)
   - Customer management
   - Sales tracking and history

2. **Inventory Management**
   - Product catalog with categories
   - Stock level tracking
   - Low stock alerts
   - Automatic reorder suggestions

3. **Supplier Management**
   - Supplier database
   - Contact information tracking
   - Purchase order management
   - Supply tracking

4. **Production Management**
   - Recipe management
   - Production batch tracking
   - Ingredient tracking
   - Yield management

5. **Financial Management**
   - Expense tracking
   - Financial reporting
   - Profit/loss tracking
   - Receipt management

6. **Dashboard and Reporting**
   - Sales dashboard
   - Inventory dashboard
   - Financial dashboard
   - Production dashboard
   - Stock reports

7. **Data Import/Export**
   - CSV import/export
   - Bulk data management
   - Data backup

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bakery_project
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file in the project root and add the following:
```
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
```

5. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

## Usage

1. Access the admin interface at `http://localhost:8000/admin`
2. Log in with your superuser credentials
3. Start managing your bakery operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@bakery.com or create an issue in the repository. 
# Bakery Management System

A comprehensive web-based bakery management system built with Flask that helps manage inventory, sales, employees, and production.

## Live Demo

Visit the live application at: https://minibarkery.onrender.com

## Features

### 1. User Authentication
- Secure login system
- User roles and permissions
- Password protection
- Session management

### 2. Dashboard
- Overview of key metrics
- Recent sales
- Low stock alerts
- Daily and monthly revenue
- Top-selling products

### 3. Inventory Management
- Track product stock levels
- Set minimum stock levels
- Stock history tracking
- Low stock alerts
- Stock adjustments
- Export inventory reports

### 4. Point of Sale (POS)
- Quick sales processing
- Multiple payment methods
- Customer information tracking
- Sales history
- Receipt generation

### 5. Employee Management
- Employee profiles
- Role-based access control
- Department management
- Salary tracking
- Attendance tracking

### 6. Supplier Management
- Supplier profiles
- Contact information
- Order history
- Payment tracking

### 7. Financial Management
- Expense tracking
- Revenue reports
- Payment processing
- Financial reports

### 8. Production Management
- Recipe management
- Production scheduling
- Batch tracking
- Quality control

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Wasikeonesmus/MiniBarkery.git
cd MiniBarkery
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with:
```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///bakery.db
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Run the application:
```bash
python app.py
```

The application will be available at http://localhost:5000

### Default Admin Credentials
- Username: admin
- Password: admin123

## User Guide

### 1. Login
- Visit the login page
- Enter your credentials
- Click "Login"

### 2. Dashboard Navigation
- Use the sidebar menu to navigate between features
- View key metrics and alerts
- Access recent activities

### 3. Managing Products
- Add new products with details
- Update stock levels
- Set minimum stock alerts
- View product history

### 4. Processing Sales
- Select products
- Enter quantities
- Choose payment method
- Complete transaction
- Print receipt

### 5. Inventory Management
- Monitor stock levels
- Receive stock alerts
- Adjust stock quantities
- View stock history

### 6. Employee Management
- Add new employees
- Assign roles and permissions
- Track attendance
- Manage salaries

### 7. Financial Reports
- View daily sales
- Track expenses
- Generate reports
- Monitor revenue

## Security Features
- Password hashing
- Session management
- Role-based access control
- Secure data storage
- Input validation

## Support
For support, please:
- Check the documentation
- Open an issue on GitHub
- Contact the development team

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
- Flask Framework
- SQLAlchemy
- Bootstrap
- All contributors and users

## Running Tests

To run the unit tests for the Barkery System, follow these steps:

1. Ensure you have a virtual environment activated:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the tests using pytest:
```bash
# Run all tests
pytest tests/

# Run tests with coverage report
coverage run -m pytest tests/
coverage report
```

### Test Coverage

The test suite covers:
- Model creation and validation
- Route functionality
- Basic CRUD operations

### Adding New Tests

- Add new test cases in the `tests/` directory
- Follow the existing test structure
- Ensure each test method starts with `test_`
- Use `setUp()` and `tearDown()` for test initialization and cleanup

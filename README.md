# Bakery Management System

A comprehensive bakery management system built with Flask that helps manage inventory, sales, employees, and production.

## Features

- User Authentication and Authorization
- Inventory Management
- Point of Sale (POS) System
- Employee Management
- Supplier Management
- Production Planning
- Financial Tracking
- Sales Reports
- Stock History

## Setup Instructions

1. Clone the repository:
```bash
git clone <your-repository-url>
cd bakery-management-system
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
Create a `.env` file with the following variables:
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

The application will be available at `http://localhost:5000`

## Default Admin Credentials

- Username: admin
- Password: admin123

## Deployment

This application is configured for deployment on Render. The necessary files (`Procfile` and `requirements.txt`) are included in the repository.

## License

MIT License 
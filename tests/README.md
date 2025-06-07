# Inventory Module Unit Tests

## Overview
This test suite covers the inventory management functionality of the Barkery System. The tests are designed to verify the core operations of stock management, including:
- Adding stock
- Adjusting stock
- Detecting low stock
- Tracking stock history

## Test Cases
The `test_inventory.py` file contains the following test scenarios:

1. **`test_add_stock_success`**
   - Verifies successful stock addition
   - Checks stock quantity update
   - Validates stock history creation

2. **`test_add_stock_invalid_product`**
   - Tests adding stock to a non-existent product
   - Ensures proper error handling

3. **`test_add_stock_invalid_quantity`**
   - Checks handling of invalid quantity inputs
   - Validates input validation mechanisms

4. **`test_adjust_stock`**
   - Tests manual stock quantity adjustment
   - Verifies stock history tracking for adjustments

5. **`test_low_stock_detection`**
   - Checks low stock alert functionality
   - Ensures products below minimum stock level are identified

6. **`test_stock_history`**
   - Validates stock history retrieval
   - Checks tracking of stock additions and sales

## Running Tests
To run the inventory module tests:

```bash
# Activate your virtual environment
source venv/bin/activate  # On Unix/macOS
venv\Scripts\activate     # On Windows

# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/test_inventory.py
```

## Best Practices
- Always run tests before committing changes
- Add new test cases for any new inventory functionality
- Maintain test coverage for critical inventory operations

## Notes
- Tests use an in-memory SQLite database
- CSRF protection is disabled for testing
- A test user is created for authentication purposes 
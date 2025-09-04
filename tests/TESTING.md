# Preppr Testing Documentation

This document describes the comprehensive test suite for the Preppr meal planning application.

## Overview

The Preppr test suite has been completely rebuilt from scratch to cover all new features and provide comprehensive testing for the application. The test suite includes:

- **Unit tests** - Fast, isolated tests for individual components
- **Integration tests** - Tests for database operations and component interactions
- **API tests** - Comprehensive endpoint testing with authentication
- **Subscription tests** - Tier-based feature access and limits
- **Performance tests** - Load and concurrency testing

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_nutrition.py        # Nutrition tracking and goals
├── test_subscription.py     # Subscription tiers and limits
├── test_tips.py            # Tips system and rotation logic
├── test_meal_planning.py   # Meal planning and generation
├── test_shopping_pantry.py # Shopping and pantry management
└── test_admin_promo.py     # Admin features and promo codes
```

## Test Categories

The test suite is organized by markers for easy execution:

### Core Categories
- `unit` - Fast unit tests (isolated, no external dependencies)
- `integration` - Integration tests (database, external services)
- `api` - API endpoint tests
- `slow` - Performance and load tests

### Feature Categories
- `nutrition` - Nutrition tracking and goals tests
- `subscription` - Subscription and tier functionality tests
- `tips` - Tips system and rotation tests
- `meal_planning` - Meal planning and generation tests
- `shopping` - Shopping and cart functionality tests
- `pantry` - Pantry management tests
- `admin` - Admin and promotional code tests
- `promo_codes` - Promotional code validation and redemption tests

### Special Categories
- `auth` - Authentication and authorization tests
- `jwt` - JWT authentication tests
- `premium` - Premium tier specific functionality tests

## Running Tests

### Using the Test Runner

The primary way to run tests is using the custom test runner:

```bash
# Run all tests (excludes slow tests by default)
python run_tests.py

# Run specific categories
python run_tests.py --category unit
python run_tests.py --category api,nutrition
python run_tests.py --category subscription,premium

# Run fast tests only
python run_tests.py --fast

# Run with coverage
python run_tests.py --coverage --html-cov

# Run in CI mode (strict, full coverage)
python run_tests.py --ci

# Run specific test files
python run_tests.py --file tests/test_nutrition.py
```

### Using Make Commands

```bash
# Quick commands
make test              # Run all tests
make test-fast         # Run fast tests only
make test-unit         # Run unit tests
make coverage-html     # Generate HTML coverage report

# Feature-specific tests
make test-nutrition    # Nutrition tests
make test-subscription # Subscription tests
make test-meal-planning# Meal planning tests
make test-shopping     # Shopping and pantry tests
make test-admin        # Admin and promo codes

# Development workflow
make dev               # Install deps + run fast tests
make check             # Lint + fast tests
make full-check        # Lint + all tests + coverage
```

### Using Pytest Directly

```bash
# Basic pytest usage
pytest tests/

# Run specific markers
pytest -m unit
pytest -m "api and nutrition"
pytest -m "not slow"

# With coverage
pytest --cov=src --cov-report=html

# Parallel execution
pytest -n auto

# Debug mode
pytest -vvv --pdb --capture=no
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)

The test suite is configured with:
- Coverage reporting (80% minimum)
- Test markers for organization
- Strict marker and config validation
- Automatic test discovery
- Timeout protection (5 minutes)

### Coverage Configuration (`.coveragerc`)

Coverage reporting includes:
- Source code analysis (`src/` directory)
- Branch coverage tracking
- HTML and XML report generation
- Exclusion of test files and templates

## Test Fixtures

The test suite provides comprehensive fixtures in `conftest.py`:

### User Fixtures
- `logged_in_user` - Standard free tier user
- `premium_user` - Active premium subscription user
- `expired_premium_user` - Expired premium subscription user
- `admin_user` - Administrative user

### Data Fixtures
- `sample_nutrition_data` - Sample nutrition goals
- `sample_pantry_items` - Sample pantry items
- `sample_recipe` - Sample recipe data
- `sample_meal_plan` - Sample meal plan data
- `shopping_cart_data` - Sample shopping cart data

### Service Fixtures
- `mock_ai_service` - Mocked AI responses
- `mock_datetime` - Fixed datetime for testing

## Database Testing

### Test Database Setup

Tests use a separate MySQL test database:
- Database: `hacknyu25_test`
- Automatic schema creation and cleanup
- Isolated test data per test
- Foreign key constraint testing

### Data Isolation

Each test gets:
- Fresh database schema
- Isolated test data
- Automatic cleanup after test completion
- No cross-test data contamination

## Subscription Testing

The test suite extensively tests subscription-based features:

### Tier Testing
- Free tier limits (3 meal plans, 50 pantry items, etc.)
- Premium tier unlimited access
- Expired subscription handling
- Tier upgrade/downgrade scenarios

### Feature Access Control
- Nutrition field access (calories/protein for free, all fields for premium)
- UPC scanning limits (10 per trip, 25 per week for free)
- Shopping list limits (2 per day for free)
- Meal planning advance scheduling limits

## Performance Testing

### Test Categories
- Load testing with large datasets (100+ pantry items)
- Concurrent operation testing
- API response time validation
- Database query performance

### Performance Thresholds
- API responses: < 2 seconds
- Database operations: < 1 second
- Concurrent operations: No data corruption

## Continuous Integration

### GitHub Actions Workflow

The CI pipeline includes:
- Multi-Python version testing (3.9-3.12)
- Matrix testing across test categories
- MySQL service container
- Security scanning (Bandit, Safety)
- Code quality checks (Black, isort, flake8, pylint)
- Coverage reporting to Codecov

### Pre-commit Hooks

Automated checks before commits:
- Code formatting (Black)
- Import sorting (isort)
- Linting (flake8)
- Security scanning (Bandit)
- Fast test execution

## Coverage Requirements

### Minimum Coverage
- Overall: 80%
- Branch coverage: Enabled
- Missing lines: Reported

### Coverage Exclusions
- Test files
- Static files and templates
- Migration files
- Debug and development code

## Development Workflow

### TDD Workflow
1. Write failing test
2. Implement minimal code to pass
3. Refactor while keeping tests green
4. Run relevant test category for feedback

### Pre-commit Workflow
1. Code changes trigger pre-commit hooks
2. Automatic formatting and linting
3. Fast test execution
4. Commit blocked if any checks fail

### CI/CD Integration
1. Push triggers full test suite
2. Matrix testing across Python versions
3. Security and quality scans
4. Coverage reporting
5. Deployment gates based on test results

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check MySQL service
brew services start mysql  # macOS
sudo service mysql start   # Linux

# Verify test database exists
mysql -u root -p -e "SHOW DATABASES;"
```

**Import Errors**
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock pytest-timeout

# Check Python path
export PYTHONPATH="${PYTHONPATH}:."
```

**Slow Test Performance**
```bash
# Run fast tests only
python run_tests.py --fast

# Skip slow marker
pytest -m "not slow"

# Use parallel execution
pytest -n auto
```

### Debug Mode

For debugging failing tests:
```bash
# Run with debugging
python run_tests.py --debug

# Or with pytest directly
pytest --pdb --capture=no -vvv
```

## Contributing

### Adding New Tests

1. **Choose appropriate test file** based on feature area
2. **Use descriptive test names** that explain the scenario
3. **Follow AAA pattern** (Arrange, Act, Assert)
4. **Add appropriate markers** for test categorization
5. **Mock external dependencies** (AI services, external APIs)
6. **Test both success and failure scenarios**

### Test Writing Guidelines

```python
@pytest.mark.nutrition
@pytest.mark.api
def test_nutrition_goals_premium_user_full_access(self, client, premium_user):
    """Test that premium users can access all nutrition fields."""
    # Arrange
    goals_data = {...}
    
    # Act
    response = client.post('/api/nutrition/goals', ...)
    
    # Assert
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    # ... specific assertions
```

### Marker Usage

Always add relevant markers to new tests:
```python
@pytest.mark.subscription  # Feature area
@pytest.mark.premium      # Premium functionality
@pytest.mark.integration  # Test type
@pytest.mark.slow         # If test takes >1 second
```

This comprehensive test suite ensures the Preppr application is thoroughly tested, maintainable, and ready for production deployment with confidence in its reliability and performance.
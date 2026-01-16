# Testing Guide for InferX

This document describes the testing infrastructure and how to run tests for the InferX project.

## Overview

The InferX project includes comprehensive test coverage for both backend and frontend:

- **Backend Tests**: Python unit and integration tests using pytest
- **Frontend Tests**: TypeScript/React component tests using Vitest

## Test Structure

```
InferX/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared pytest fixtures
│   ├── requirements.txt         # Test dependencies
│   ├── unit/                    # Unit tests
│   │   ├── test_config.py       # Configuration tests
│   │   ├── test_security.py     # Security utilities tests
│   │   ├── test_model_service.py
│   │   ├── test_gpu_service.py
│   │   └── test_deployment_service.py
│   └── integration/             # Integration tests
│       ├── conftest.py
│       ├── test_chat_api.py
│       ├── test_models_api.py
│       └── test_admin_api.py
└── web/
    └── src/
        └── test/
            ├── setup.ts         # Vitest setup
            ├── test-utils.tsx   # Testing utilities
            └── __tests__/       # Component tests
                ├── MainLayout.test.tsx
                ├── Dashboard.test.tsx
                └── Deployments.test.tsx
```

## Backend Testing

### Installation

Install test dependencies:

```bash
pip install -r tests/requirements.txt
```

### Running Tests

Run all backend tests:

```bash
pytest
```

Run only unit tests:

```bash
pytest -m unit
```

Run only integration tests:

```bash
pytest -m integration
```

Run a specific test file:

```bash
pytest tests/unit/test_security.py
```

Run with coverage:

```bash
pytest --cov=tokenmachine --cov-report=html
```

### Test Configuration

Backend tests are configured in `pytest.ini`:

- Uses in-memory SQLite database for fast testing
- Auto-uses async mode for async tests
- Generates coverage reports in HTML and XML formats
- Configured with various markers for test categorization

### Fixtures

Key fixtures available in `tests/conftest.py`:

- `test_settings`: Test settings with safe defaults
- `db_session`: Database session with transaction rollback
- `test_user`: Test user fixture
- `test_admin_user`: Admin user fixture
- `test_api_key`: API key fixture (returns both record and raw key)
- `test_model`: Test model fixture
- `test_gpu`: Test GPU fixture
- `test_deployment`: Test deployment fixture
- `mock_gpu_manager`: Mocked GPU manager
- `mock_worker_pool`: Mocked worker pool

## Frontend Testing

### Installation

Install frontend dependencies:

```bash
cd web
npm install
```

### Running Tests

Run all frontend tests in watch mode:

```bash
npm test
```

Run tests once:

```bash
npm run test:run
```

Run tests with coverage:

```bash
npm run test:coverage
```

Run tests with UI:

```bash
npm run test:ui
```

### Test Configuration

Frontend tests are configured in `web/vitest.config.ts`:

- Uses jsdom environment for DOM testing
- Includes coverage with v8 provider
- Sets up path aliases (@/ for src/)
- Global test utilities and matchers

### Testing Utilities

Available in `web/src/test/test-utils.tsx`:

- `renderWithProviders`: Render with React Router and Ant Design
- Mock data generators: `mockDeployment`, `mockModel`, `mockGPU`, `mockApiKey`
- `mockFetch`: Mock fetch API responses
- `mockFetchError`: Mock fetch errors

## Writing New Tests

### Backend Unit Test Example

```python
# tests/unit/test_my_service.py
import pytest
from backend.services.my_service import MyService

class TestMyService:
    def test_my_function(self, db_session, patch_gpu_manager):
        service = MyService(db_session)
        result = service.my_function("test")
        assert result == "expected"
```

### Backend Integration Test Example

```python
# tests/integration/test_my_api.py
def test_my_endpoint(client, test_api_key):
    api_key, raw_key = test_api_key

    response = client.get(
        "/api/v1/endpoint",
        headers={"Authorization": f"Bearer {raw_key}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "value"
```

### Frontend Component Test Example

```typescript
// web/src/test/__tests__/MyComponent.test.tsx
import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '../test-utils'
import MyComponent from '@/components/MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run backend tests
  run: |
    pip install -r tests/requirements.txt
    pytest --cov=tokenmachine --cov-report=xml

- name: Run frontend tests
  run: |
    cd web
    npm install
    npm run test:run
```

## Test Markers

Backend tests use pytest markers:

- `unit`: Fast, isolated unit tests
- `integration`: Slower tests using multiple components
- `slow`: Long-running tests
- `gpu`: Tests requiring GPU access
- `auth`: Authentication-related tests

## Troubleshooting

### Backend Tests

**Issue**: Tests failing with database errors
- Ensure SQLite is available
- Check that `test_settings` fixture is being used

**Issue**: Import errors
- Run tests from project root directory
- Ensure PYTHONPATH includes project root

### Frontend Tests

**Issue**: Tests failing with jsdom errors
- Ensure all dependencies are installed
- Check vitest.config.ts configuration

**Issue**: Component not rendering
- Verify test-utils.tsx is properly set up
- Check that required providers are mocked

## Best Practices

1. **Keep tests isolated**: Each test should be independent
2. **Use fixtures**: Reuse common test data via fixtures
3. **Mock external services**: Use mocks for GPU, workers, HTTP calls
4. **Test edge cases**: Include error conditions and boundary values
5. **Maintain coverage**: Aim for >80% code coverage
6. **Run tests locally**: Before committing, run full test suite

## Coverage Goals

- Unit tests: >90% coverage for core modules
- Integration tests: >70% coverage for API endpoints
- Component tests: >60% coverage for React components

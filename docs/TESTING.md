# Testing Guide for TokenMachine

This document describes the testing infrastructure and how to run tests for the TokenMachine project.

## Overview

The TokenMachine project includes comprehensive test coverage for both backend and frontend:

- **Backend Tests**: Python unit and integration tests using pytest
- **Frontend Tests**: TypeScript/React component tests using Vitest

## Test Structure

```
TokenMachine/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared pytest fixtures
│   ├── requirements.txt         # Test dependencies
│   ├── unit/                    # Unit tests
│   │   ├── test_config.py       # Configuration tests
│   │   ├── test_security.py     # Security utilities tests
│   │   ├── test_quota.py        # Quota manager tests
│   │   ├── test_cluster_service.py
│   │   ├── test_worker_service.py
│   │   ├── test_billing_service.py
│   │   ├── test_stats_service.py
│   │   ├── test_model_service.py
│   │   ├── test_gpu_service.py
│   │   └── test_deployment_service.py
│   └── integration/             # Integration tests
│       ├── conftest.py
│       ├── test_chat_api.py
│       ├── test_models_api.py
│       ├── test_admin_api.py
│       ├── test_cluster_api.py
│       ├── test_worker_api.py
│       ├── test_billing_api.py
│       └── test_monitoring_api.py
└── ui/
    └── src/
        └── test/
            ├── setup.ts         # Vitest setup
            ├── test-utils.tsx   # Testing utilities
            └── __tests__/       # Component tests
                ├── MainLayout.test.tsx
                ├── Dashboard.test.tsx
                ├── Deployments.test.tsx
                ├── Clusters.test.tsx
                └── Billing.test.tsx
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
- `test_organization`: Test organization fixture
- `test_user`: Test user fixture
- `test_admin_user`: Admin user fixture
- `test_api_key`: API key fixture (returns both record and raw key)
- `test_model`: Test model fixture
- `test_gpu`: Test GPU fixture
- `test_deployment`: Test deployment fixture
- `test_cluster`: Test cluster fixture
- `test_worker_pool`: Test worker pool fixture
- `test_worker`: Test worker fixture
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
# tests/unit/test_cluster_service.py
import pytest
from backend.services.cluster_service import ClusterService

class TestClusterService:
    def test_create_cluster(self, db_session):
        service = ClusterService(db_session)
        cluster = service.create_cluster(
            name="test-cluster",
            cluster_type="standalone"
        )
        assert cluster.id is not None
        assert cluster.name == "test-cluster"
        assert cluster.type == "standalone"

    def test_list_clusters(self, db_session, test_cluster):
        service = ClusterService(db_session)
        clusters = service.list_clusters()
        assert len(clusters) >= 1
        assert test_cluster in clusters
```

### Backend Integration Test Example

```python
# tests/integration/test_cluster_api.py
def test_create_cluster(client, admin_token):
    response = client.post(
        "/api/v1/admin/clusters",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "test-cluster",
            "type": "standalone",
            "description": "Test cluster"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "test-cluster"
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
- `rbac`: Role-based access control tests
- `quota`: Quota management tests
- `billing`: Billing and invoicing tests
- `cluster`: Cluster management tests
- `worker`: Worker management tests
- `multi_tenant`: Multi-tenancy tests
- `security`: Security-related tests

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

.PHONY: help test test-fast test-compile test-deploy test-install test-service test-api test-heartbeat test-gpu test-systemd test-filter test-e2e install-deps report clean

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[1;33m
NC := \033[0m

help: ## Show this help message
	@echo "$(BLUE)TokenMachine GPU Agent Test Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install-deps: ## Install test dependencies
	@echo "$(BLUE)Installing test dependencies...$(NC)"
	pip install -r tests/requirements.txt

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	pytest

test-fast: ## Run fast tests only (exclude slow)
	@echo "$(BLUE)Running fast tests...$(NC)"
	pytest -m "not slow"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest -m unit

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest -m integration

test-compile: ## Test local compilation
	@echo "$(BLUE)Testing compilation...$(NC)"
	pytest tests/test_gpu_agent.py::TestLocalCompilation -v

test-deploy: ## Test deployment to remote
	@echo "$(BLUE)Testing deployment...$(NC)"
	pytest tests/test_gpu_agent.py::TestDeployment -v

test-install: ## Test complete installation
	@echo "$(BLUE)Testing installation...$(NC)"
	pytest tests/test_gpu_agent.py::TestCleanup tests/test_gpu_agent.py::TestInstallation -v

test-service: ## Test service status
	@echo "$(BLUE)Testing services...$(NC)"
	pytest tests/test_gpu_agent.py::TestServiceStatus -v

test-api: ## Test API endpoints
	@echo "$(BLUE)Testing API endpoints...$(NC)"
	pytest tests/test_gpu_agent.py::TestAPIEndpoints -v

test-config: ## Test configuration files
	@echo "$(BLUE)Testing configuration...$(NC)"
	pytest tests/test_gpu_agent.py::TestConfigFiles -v

test-heartbeat: ## Test heartbeat functionality
	@echo "$(YELLOW)Testing heartbeat (will take ~40s)...$(NC)"
	pytest tests/test_gpu_agent.py::TestHeartbeat -v

test-gpu: ## Test GPU occupation
	@echo "$(BLUE)Testing GPU occupation...$(NC)"
	pytest tests/test_gpu_agent.py::TestGPUOccupation -v

test-systemd: ## Test systemd service
	@echo "$(YELLOW)Testing systemd (will take ~20s)...$(NC)"
	pytest tests/test_gpu_agent.py::TestSystemdService -v

test-filter: ## Test GPU filtering
	@echo "$(BLUE)Testing GPU filter...$(NC)"
	pytest tests/test_gpu_agent.py::TestGPUFilter -v

test-full-deploy: ## Run complete automated deployment and installation (WARNING: takes 2-3 minutes)
	@echo "$(YELLOW)Running complete deployment test (auto-scp + install)..."
	@echo "$(YELLOW)This will: 1) Cleanup old deployment 2) SCP worker 3) Run install.sh 4) Verify all services"
	@echo ""
	@echo "$(YELLOW)Starting deployment...$(NC)"
	pytest tests/test_gpu_agent.py::TestCompleteDeployment -v -s

test-e2e: ## Test end-to-end registration
	@echo "$(BLUE)Testing E2E registration...$(NC)"
	pytest tests/test_gpu_agent.py::TestE2ERegistration -v

test-all-no-backend: ## Run all tests except backend-dependent ones
	@echo "$(BLUE)Running all tests (no backend required)...$(NC)"
	SKIP_FULL_DEPLOYMENT=0 pytest -m "not requires_backend" -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov=worker --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

test-parallel: ## Run tests in parallel
	@echo "$(BLUE)Running tests in parallel...$(NC)"
	pytest -n auto

test-no-backend: ## Run tests without backend dependency
	@echo "$(BLUE)Running tests without backend...$(NC)"
	pytest -m "not requires_backend"

report: ## Open coverage report
	@echo "$(BLUE)Opening coverage report...$(NC)"
	@if [ -f htmlcov/index.html ]; then \
		xdg-open htmlcov/index.html 2>/dev/null || \
		open htmlcov/index.html 2>/dev/null || \
		echo "Open htmlcov/index.html in your browser"; \
	else \
		echo "$(RED)Coverage report not found. Run 'make test-coverage' first.$(NC)"; \
	fi

clean: ## Clean test artifacts
	@echo "$(BLUE)Cleaning test artifacts...$(NC)"
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(NC)"

# Pre-test checks
check-env: ## Check if environment is configured
	@echo "$(BLUE)Checking environment...$(NC)"
	@if [ -z "$$TARGET_HOST" ]; then \
		echo "$(YELLOW)Warning: TARGET_HOST not set (using default ht706@192.168.247.76)$(NC)"; \
	fi
	@if [ -z "$$BACKEND_URL" ]; then \
		echo "$(YELLOW)Warning: BACKEND_URL not set (using default http://localhost:8000)$(NC)"; \
	fi
	@if [ -z "$$WORKER_TOKEN" ]; then \
		echo "$(YELLOW)Warning: WORKER_TOKEN not set (using default test_token_<timestamp>)$(NC)"; \
	fi

# Full test workflow
test-all: check-env install-deps test-coverage ## Install deps and run full test suite
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)All tests completed!$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo "View coverage report: make report"

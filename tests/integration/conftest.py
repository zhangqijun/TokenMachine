"""
Integration test configuration and fixtures.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Override settings BEFORE importing backend modules
os.environ["MODEL_STORAGE_PATH"] = "/tmp/test_tokenmachine/models"
os.environ["LOG_PATH"] = "/tmp/test_tokenmachine/logs"

# Ensure directories exist BEFORE importing
os.makedirs("/tmp/test_tokenmachine/models", exist_ok=True)
os.makedirs("/tmp/test_tokenmachine/logs", exist_ok=True)

# Patch backend.core.database BEFORE importing models
import backend.core.database as db_module
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create test engine and replace the global one
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False}
)
db_module.engine = test_engine
# Also replace get_engine to return test engine
db_module.get_engine = lambda: test_engine

# Now we can import models
from backend.models.database import Base

# Create tables
Base.metadata.create_all(test_engine)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def integration_db_session():
    """Create database session for integration tests."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# Note: We patch backend.core.database.engine to avoid PostgreSQL connection issues


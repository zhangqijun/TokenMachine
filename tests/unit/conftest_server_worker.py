"""
Pytest configuration for Server-Worker architecture tests.
"""
import os
import sys
import pytest
import asyncio
from typing import Generator
from pathlib import Path
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.database import Base
from backend.models.database import (
    Cluster, ClusterType,
    Worker, WorkerStatus,
    Model, ModelCategory, ModelSource, ModelStatus,
    ModelInstance, ModelInstanceStatus
)


@pytest.fixture
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session_factory(db_engine):
    """Create a test database session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture
def db_session(db_session_factory) -> Generator[Session, None, None]:
    """Create a test database session."""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

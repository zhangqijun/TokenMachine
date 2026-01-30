"""
Pytest configuration for GPU Agent tests
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_backend: marks tests that require backend server"
    )
    config.addinivalue_line(
        "markers", "requires_ssh: marks tests that require SSH access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark slow tests
        if "heartbeat" in str(item.fspath) or "gpu_occupation" in str(item.fspath):
            item.add_marker("slow")

        # Mark integration tests
        parent_classname = getattr(item.parent, "classname", "")
        parent_id = getattr(item.parent, "id", "")
        if "TestDeployment" in str(parent_classname) or "TestInstallation" in str(parent_classname) or \
           "TestDeployment" in str(parent_id) or "TestInstallation" in str(parent_id):
            item.add_marker("integration")

        # Mark backend-dependent tests
        if "TestE2ERegistration" in str(parent_classname) or "TestE2ERegistration" in str(parent_id):
            item.add_marker("requires_backend")

        # Mark SSH-dependent tests
        if hasattr(item, "fixturenames") and "ssh_client" in item.fixturenames:
            item.add_marker("requires_ssh")

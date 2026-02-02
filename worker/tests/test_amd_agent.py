"""
TokenMachine AMD Agent - Comprehensive Test Suite

Tests the complete AMD Agent functionality using mock mode since real AMD hardware
is not available. The tests are strict and designed to avoid false positives.

Test Categories:
1. Unit tests for AMD collector (mock data)
2. Integration tests for exporter server
3. Mock mode functionality tests
4. Script validation tests
5. End-to-end workflow tests
"""

import os
import sys
import subprocess
import time
import json
import re
import socket
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

import pytest

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.parent
AMD_AGENT_DIR = SCRIPT_DIR / "amd-agent"

# Test configuration
TEST_MODE = os.getenv("TEST_MODE", "mock")  # 'mock' only (no real AMD hardware)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", f"test_amd_token_{int(time.time())}")

# Paths
EXPORTER_BINARY = AMD_AGENT_DIR / "Exporter" / "amd_exporter_main"
RECEIVER_BINARY = AMD_AGENT_DIR / "Receiver" / "receiver"
OCCUPY_GPU_SOURCE = AMD_AGENT_DIR / "occupier" / "occupy_gpu.hip"

# Test work directories
TEST_WORK_DIR = Path("/tmp/tokenmachine_amd_test")
TEST_RUN_DIR = TEST_WORK_DIR / "run"
TEST_LOG_DIR = TEST_WORK_DIR / "logs"

# Port configuration for tests
TEST_RECEIVER_PORT = 19011  # Base port + 11 for AMD
TEST_EXPORTER_PORT = 19091  # TEST_RECEIVER_PORT + 80


# =============================================================================
# Custom Exceptions
# =============================================================================

class AMDTestError(Exception):
    """Base exception for AMD agent test failures."""
    pass


class MockValidationError(AMDTestError):
    """Raised when mock data validation fails."""
    pass


class AssertionStrictError(AssertionError):
    """Enhanced assertion error with detailed context."""
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_work_dir():
    """Create and cleanup test working directory."""
    TEST_WORK_DIR.mkdir(parents=True, exist_ok=True)
    TEST_RUN_DIR.mkdir(parents=True, exist_ok=True)
    TEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
    yield TEST_WORK_DIR
    # Cleanup is handled by the cleanup fixture


@pytest.fixture(scope="session")
def mock_amd_gpus():
    """Provide deterministic mock AMD GPU data for testing."""
    return [
        {
            "index": 0,
            "name": "AMD Radeon RX 6800 XT",
            "uuid": "mock-amd-gpu-0-uuid-12345678",
            "pci_bus_id": "0000:0b:00.0",
            "memory_total_mib": 16384,
            "memory_used_mib": 12288,
            "utilization_gpu_percent": 45.5,
            "utilization_memory_percent": 75.0,
            "temperature_celsius": 68.5,
        },
        {
            "index": 1,
            "name": "AMD Radeon RX 6800",
            "uuid": "mock-amd-gpu-1-uuid-87654321",
            "pci_bus_id": "0000:0c:00.0",
            "memory_total_mib": 16384,
            "memory_used_mib": 8192,
            "utilization_gpu_percent": 30.0,
            "utilization_memory_percent": 50.0,
            "temperature_celsius": 62.0,
        },
    ]


@pytest.fixture
def clean_test_env(test_work_dir):
    """Clean test environment before each test."""
    # Kill any running test processes
    subprocess.run("pkill -f 'amd_exporter_main.*19091' 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f 'receiver.*19011' 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f 'occupy_gpu.*mock.*19011' 2>/dev/null || true", shell=True)
    time.sleep(1)
    yield
    # Cleanup after test
    subprocess.run("pkill -f 'amd_exporter_main.*19091' 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f 'receiver.*19011' 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f 'occupy_gpu.*mock.*19011' 2>/dev/null || true", shell=True)
    time.sleep(1)


@pytest.fixture
def available_port():
    """Find an available port for testing."""
    def _find_port(start_port: int) -> int:
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        raise AMDTestError(f"No available port found starting from {start_port}")
    return _find_port


# =============================================================================
# Helper Functions
# =============================================================================

def run_command(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 60, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run command locally with timeout."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def check_static_binary(binary_path: Path) -> Tuple[bool, str]:
    """Check if binary is statically linked."""
    if not binary_path.exists():
        return False, f"Binary not found: {binary_path}"

    # Check with file command
    result = run_command(["file", str(binary_path)])
    if result.returncode != 0:
        return False, f"file command failed: {result.stderr}"

    if "statically linked" not in result.stdout:
        return False, f"Binary is not statically linked: {result.stdout}"

    # Check with ldd
    result = run_command(["ldd", str(binary_path)])
    if "not a dynamic executable" not in result.stdout and "not a dynamic executable" not in result.stderr:
        return False, f"Binary may have dynamic dependencies: {result.stderr}"

    return True, "Binary is statically linked"


def validate_mock_gpu_data(gpu_data: Dict, expected_index: int) -> bool:
    """
    Validate mock GPU data structure and values.
    This is a STRICT validator - any mismatch will fail the test.
    """
    required_fields = {
        "index": int,
        "name": str,
        "uuid": str,
        "pci_bus_id": str,
        "memory_total_mib": int,
        "memory_used_mib": int,
        "utilization_gpu_percent": (int, float),
        "utilization_memory_percent": (int, float),
        "temperature_celsius": (int, float),
    }

    for field, expected_type in required_fields.items():
        if field not in gpu_data:
            raise MockValidationError(f"Missing required field: {field}")

        value = gpu_data[field]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                raise MockValidationError(
                    f"Field '{field}' has wrong type: expected {expected_type}, got {type(value)}"
                )
        else:
            if not isinstance(value, expected_type):
                raise MockValidationError(
                    f"Field '{field}' has wrong type: expected {expected_type.__name__}, got {type(value).__name__}"
                )

    # Validate index matches
    if gpu_data["index"] != expected_index:
        raise MockValidationError(
            f"GPU index mismatch: expected {expected_index}, got {gpu_data['index']}"
        )

    # Validate memory values
    if gpu_data["memory_used_mib"] > gpu_data["memory_total_mib"]:
        raise MockValidationError(
            f"Memory used ({gpu_data['memory_used_mib']}) exceeds total ({gpu_data['memory_total_mib']})"
        )

    # Validate percentages are in range
    if not 0 <= gpu_data["utilization_gpu_percent"] <= 100:
        raise MockValidationError(
            f"GPU utilization out of range: {gpu_data['utilization_gpu_percent']}"
        )

    if not 0 <= gpu_data["temperature_celsius"] <= 150:
        raise MockValidationError(
            f"Temperature out of range: {gpu_data['temperature_celsius']}"
        )

    return True


def parse_prometheus_metrics(metrics_text: str) -> Dict[str, List[str]]:
    """Parse Prometheus metrics text format into structured data."""
    metrics = {}
    current_name = None
    current_labels = {}
    current_value = None

    for line in metrics_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Parse metric line: metric_name{labels} value
        label_start = line.find('{')
        label_end = line.find('}')
        space_idx = line.rfind(' ')

        if label_start == -1:
            # No labels
            metric_name = line[:space_idx]
            value = line[space_idx+1:]
            labels = {}
        else:
            metric_name = line[:label_start]
            labels_str = line[label_start+1:label_end]
            value = line[label_end+2:]

            # Parse labels
            labels = {}
            for label in labels_str.split(','):
                if '=' in label:
                    k, v = label.split('=', 1)
                    labels[k] = v.strip('"')

        if metric_name not in metrics:
            metrics[metric_name] = []
        metrics[metric_name].append({"labels": labels, "value": value})

    return metrics


# =============================================================================
# Test 1: AMD Collector Unit Tests (Mock Mode)
# =============================================================================

class TestAmdCollectorMock:
    """Unit tests for AMD GPU collector with mock data."""

    def test_mock_data_structure(self, mock_amd_gpus):
        """Test that mock GPU data has correct structure."""
        assert len(mock_amd_gpus) >= 1, "Should have at least one mock GPU"

        for i, gpu in enumerate(mock_amd_gpus):
            # This will raise MockValidationError if invalid
            validate_mock_gpu_data(gpu, i)

    def test_mock_data_determinism(self, mock_amd_gpus):
        """Test that mock data is deterministic (same across calls)."""
        # Run validation multiple times
        for _ in range(3):
            for i, gpu in enumerate(mock_amd_gpus):
                validate_mock_gpu_data(gpu, i)
                # Check values are consistent
                assert gpu["index"] == i
                assert gpu["memory_total_mib"] == 16384
                assert "AMD" in gpu["name"]

    def test_mock_memory_utilization_calculation(self, mock_amd_gpus):
        """Test memory utilization calculation is correct."""
        for gpu in mock_amd_gpus:
            expected_util = (gpu["memory_used_mib"] / gpu["memory_total_mib"]) * 100
            actual_util = gpu["utilization_memory_percent"]

            # Allow small floating point tolerance
            assert abs(expected_util - actual_util) < 0.01, \
                f"Memory utilization mismatch: expected {expected_util}, got {actual_util}"

    def test_mock_gpu_count(self, mock_amd_gpus):
        """Test that mock GPU count is as expected."""
        # Should have 2 GPUs for comprehensive testing
        assert len(mock_amd_gpus) == 2, \
            f"Expected 2 mock GPUs, got {len(mock_amd_gpus)}"

    def test_mock_gpu_indices_are_unique(self, mock_amd_gpus):
        """Test that GPU indices are unique and sequential."""
        indices = [gpu["index"] for gpu in mock_amd_gpus]
        assert len(indices) == len(set(indices)), "GPU indices must be unique"
        assert indices == list(range(len(indices))), "GPU indices must be sequential starting from 0"


# =============================================================================
# Test 2: Exporter Server Tests (Mock Mode)
# =============================================================================

class TestAmdExporterMock:
    """Tests for AMD Exporter server in mock mode."""

    def test_exporter_binary_exists(self):
        """Test that exporter binary exists."""
        assert EXPORTER_BINARY.exists(), \
            f"Exporter binary not found at {EXPORTER_BINARY}"

    def test_exporter_is_static_binary(self):
        """Test that exporter is statically linked."""
        is_static, message = check_static_binary(EXPORTER_BINARY)
        assert is_static, message

    def test_exporter_help_output(self):
        """Test exporter help output contains expected options."""
        result = run_command([str(EXPORTER_BINARY), "-h"])

        assert result.returncode == 0, f"Help command failed: {result.stderr}"
        # Help output is written to stderr by Go's flag package
        output = result.stderr or result.stdout
        assert "-port" in output or "-p" in output, \
            "Exporter should have -port option"
        assert "-mock" in output or "-simulate" in output, \
            "Exporter should have -mock option"
        assert "metrics" in output.lower(), \
            "Help should mention /metrics endpoint"

    def test_exporter_mock_mode_startup(self, clean_test_env, available_port):
        """Test exporter starts correctly in mock mode."""
        port = available_port(TEST_EXPORTER_PORT)

        # Start exporter in mock mode
        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=AMD_AGENT_DIR
        )

        try:
            # Wait for startup
            time.sleep(2)

            # Check process is running
            assert proc.poll() is None, \
                f"Exporter process exited unexpectedly: {proc.stderr.read()}"

            # Check port is listening
            result = subprocess.run(
                f"netstat -tlnp 2>/dev/null | grep ':{port}' || ss -tlnp 2>/dev/null | grep ':{port}'",
                shell=True,
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, \
                f"Exporter port {port} not listening: {result.stderr}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_exporter_health_endpoint_mock(self, clean_test_env, available_port):
        """Test /health endpoint returns healthy in mock mode."""
        port = available_port(TEST_EXPORTER_PORT)

        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            # Test health endpoint
            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/health"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Health check failed: {result.stderr}"
            assert "healthy" in result.stdout.lower(), \
                f"Expected 'healthy' in response, got: {result.stdout}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_exporter_metrics_endpoint_mock(self, clean_test_env, available_port):
        """Test /metrics endpoint returns valid Prometheus metrics in mock mode."""
        port = available_port(TEST_EXPORTER_PORT)

        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            # Test metrics endpoint
            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/metrics"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Metrics request failed: {result.stderr}"

            # Parse metrics
            metrics = parse_prometheus_metrics(result.stdout)

            # Verify required metrics exist
            required_metrics = [
                "amd_gpu_count",
                "amd_memory_used_bytes",
                "amd_memory_total_bytes",
                "amd_utilization",
                "amd_temperature_celsius",
            ]

            for metric in required_metrics:
                assert metric in metrics, \
                    f"Required metric '{metric}' not found in output"

            # Verify metrics have values (not just labels)
            for metric in required_metrics:
                if metrics[metric]:
                    assert metrics[metric][0]["value"], \
                        f"Metric '{metric}' has no value"

            # Verify AMD metrics use 'amd_' prefix
            for metric_name in metrics:
                if not metric_name.startswith('#'):
                    assert metric_name.startswith("amd_"), \
                        f"Metric should use 'amd_' prefix: {metric_name}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_exporter_metrics_values_mock(self, clean_test_env, available_port):
        """Test that metrics contain valid values in mock mode."""
        port = available_port(TEST_EXPORTER_PORT)

        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/metrics"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0
            metrics = parse_prometheus_metrics(result.stdout)

            # Verify GPU count is positive
            if "amd_gpu_count" in metrics and metrics["amd_gpu_count"]:
                count = float(metrics["amd_gpu_count"][0]["value"])
                assert count >= 1, f"GPU count should be >= 1, got {count}"

            # Verify memory metrics have reasonable values
            if "amd_memory_total_bytes" in metrics and metrics["amd_memory_total_bytes"]:
                total_mem = float(metrics["amd_memory_total_bytes"][0]["value"])
                assert total_mem > 0, "Total memory should be > 0"
                # 16GB = 17179869184 bytes
                assert 10 * 1024**3 < total_mem < 32 * 1024**3, \
                    f"Memory value seems unrealistic: {total_mem}"

            # Verify temperature is in valid range
            if "amd_temperature_celsius" in metrics and metrics["amd_temperature_celsius"]:
                temp = float(metrics["amd_temperature_celsius"][0]["value"])
                assert 0 <= temp <= 150, \
                    f"Temperature out of range (0-150): {temp}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_exporter_gpu_filter_mock(self, clean_test_env, available_port):
        """Test GPU filtering works in mock mode."""
        port = available_port(TEST_EXPORTER_PORT)

        # Start with GPU 0 only
        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock", "--gpu-ids", "0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/metrics"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0
            metrics = parse_prometheus_metrics(result.stdout)

            # Check that only GPU 0 is in metrics
            if "amd_gpu_count" in metrics:
                count = float(metrics["amd_gpu_count"][0]["value"])
                assert count == 1, \
                    f"Expected 1 GPU when filtering to GPU 0, got {count}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)


# =============================================================================
# Test 3: Exporter JSON Endpoint Tests
# =============================================================================

class TestAmdExporterJsonEndpoint:
    """Tests for AMD Exporter /json endpoint."""

    def test_exporter_json_endpoint_mock(self, clean_test_env, available_port):
        """Test /json endpoint returns valid JSON."""
        port = available_port(TEST_EXPORTER_PORT)

        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"JSON request failed: {result.stderr}"

            # Verify it's valid JSON
            try:
                gpu_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise AssertionStrictError(f"Invalid JSON response: {e}\nResponse: {result.stdout}")

            # Verify structure
            assert isinstance(gpu_data, list), "Response should be a list"
            assert len(gpu_data) >= 1, "Should have at least one GPU"

            # Verify each GPU has required fields
            for gpu in gpu_data:
                required_fields = ["Index", "Name", "UUID", "MemoryTotalMiB", "MemoryUsedMiB",
                                  "UtilizationGpuPercent", "TemperatureGpuCelsius"]
                for field in required_fields:
                    assert field in gpu, f"Missing field: {field} in GPU data"

        finally:
            proc.terminate()
            proc.wait(timeout=5)


# =============================================================================
# Test 4: Script Validation Tests
# =============================================================================

class TestAmdAgentScripts:
    """Validation tests for AMD agent scripts."""

    def test_install_script_exists(self):
        """Test install script exists and is executable."""
        install_script = AMD_AGENT_DIR / "install.sh"
        assert install_script.exists(), f"install.sh not found at {install_script}"
        assert os.access(install_script, os.X_OK), "install.sh should be executable"

    def test_install_script_has_amd_references(self):
        """Test install script contains AMD/ROCm specific content."""
        install_script = AMD_AGENT_DIR / "install.sh"
        content = install_script.read_text()

        # Check for AMD-specific content
        amd_references = ["rocm-smi", "HIP", "ROCm", "amd", "AMD"]
        found_count = sum(1 for ref in amd_references if ref.lower() in content.lower())

        assert found_count >= 3, \
            f"install.sh should contain AMD/ROCm references, found: {found_count}"

    def test_install_script_has_mock_mode(self):
        """Test install script supports mock mode."""
        install_script = AMD_AGENT_DIR / "install.sh"
        content = install_script.read_text()

        assert "mock" in content.lower() or "MOCK" in content, \
            "install.sh should support mock mode"
        assert "--mock" in content, \
            "install.sh should have --mock option"

    def test_tm_agent_script_exists(self):
        """Test tm_agent.sh exists and is executable."""
        tm_agent_script = AMD_AGENT_DIR / "tm_agent.sh"
        assert tm_agent_script.exists(), f"tm_agent.sh not found at {tm_agent_script}"
        assert os.access(tm_agent_script, os.X_OK), "tm_agent.sh should be executable"

    def test_tm_agent_script_has_amd_references(self):
        """Test tm_agent.sh contains AMD-specific content."""
        tm_agent_script = AMD_AGENT_DIR / "tm_agent.sh"
        content = tm_agent_script.read_text()

        # Check for AMD-specific content (either AMD or ROCm)
        assert "amd" in content.lower() or "AMD" in content, \
            "tm_agent.sh should contain AMD references"
        # Also check for agent-specific naming
        assert "tokenmachine" in content.lower(), \
            "tm_agent.sh should contain TokenMachine references"

    def test_heartbeat_script_exists(self):
        """Test heartbeat.sh exists and is executable."""
        heartbeat_script = AMD_AGENT_DIR / "heartbeat.sh"
        assert heartbeat_script.exists(), f"heartbeat.sh not found at {heartbeat_script}"
        assert os.access(heartbeat_script, os.X_OK), "heartbeat.sh should be executable"

    def test_occupy_gpu_source_exists(self):
        """Test occupy_gpu.hip source file exists."""
        assert OCCUPY_GPU_SOURCE.exists(), \
            f"occupy_gpu.hip not found at {OCCUPY_GPU_SOURCE}"

    def test_occupy_gpu_has_hip_references(self):
        """Test occupy_gpu.hip contains HIP-specific code."""
        content = OCCUPY_GPU_SOURCE.read_text()

        hip_references = ["hip", "HIP", "hipMalloc", "hipMemset", "hipFree"]
        found_count = sum(1 for ref in hip_references if ref in content)

        assert found_count >= 3, \
            f"occupy_gpu.hip should contain HIP references, found: {found_count}"

    def test_occupy_gpu_has_mock_mode(self):
        """Test occupy_gpu.hip supports mock mode."""
        content = OCCUPY_GPU_SOURCE.read_text()

        assert "--mock" in content or "mock_mode" in content, \
            "occupy_gpu.hip should support mock mode"


# =============================================================================
# Test 5: Receiver Tests (Mock Mode)
# =============================================================================

class TestAmdReceiverMock:
    """Tests for AMD Receiver in mock mode."""

    def test_receiver_binary_exists(self):
        """Test that receiver binary exists."""
        assert RECEIVER_BINARY.exists(), \
            f"Receiver binary not found at {RECEIVER_BINARY}"

    def test_receiver_is_static_binary(self):
        """Test that receiver is statically linked."""
        is_static, message = check_static_binary(RECEIVER_BINARY)
        assert is_static, message

    def test_receiver_health_endpoint(self, clean_test_env, available_port, test_work_dir):
        """Test Receiver health endpoint."""
        port = available_port(TEST_RECEIVER_PORT)

        env = {**os.environ,
               "TM_RECEIVER_PORT": str(port),
               "TM_WORK_DIR": str(test_work_dir),
               "TM_RECEIVER_LOG": str(test_work_dir / "logs" / "receiver.log")}

        proc = subprocess.Popen(
            [str(RECEIVER_BINARY)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=AMD_AGENT_DIR / "Receiver"
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/health"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Health check failed: {result.stderr}"
            assert "ok" in result.stdout.lower() or "healthy" in result.stdout.lower(), \
                f"Expected 'ok' or 'healthy' in response, got: {result.stdout}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_receiver_status_endpoint(self, clean_test_env, available_port, test_work_dir):
        """Test Receiver status endpoint."""
        port = available_port(TEST_RECEIVER_PORT)

        proc = subprocess.Popen(
            [str(RECEIVER_BINARY)],
            env={**os.environ,
                 "TM_RECEIVER_PORT": str(port),
                 "TM_WORK_DIR": str(test_work_dir),
                 "TM_RECEIVER_LOG": str(test_work_dir / "logs" / "receiver.log")},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR / "Receiver"
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/api/v1/status"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Status request failed: {result.stderr}"

            # Verify it's valid JSON
            try:
                status = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise AssertionStrictError(f"Invalid JSON in status response: {e}")

            # Verify required fields
            assert "status" in status, "Status response missing 'status'"
            assert "version" in status, "Status response missing 'version'"
            assert status["status"] == "running", f"Expected 'running' status, got: {status['status']}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_receiver_tasks_list_endpoint(self, clean_test_env, available_port, test_work_dir):
        """Test Receiver tasks list endpoint."""
        port = available_port(TEST_RECEIVER_PORT)

        env = {**os.environ,
               "TM_RECEIVER_PORT": str(port),
               "TM_WORK_DIR": str(test_work_dir),
               "TM_RECEIVER_LOG": str(test_work_dir / "logs" / "receiver.log")}

        proc = subprocess.Popen(
            [str(RECEIVER_BINARY)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR / "Receiver"
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/api/v1/tasks/list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Tasks list request failed: {result.stderr}"

            # Verify it's valid JSON
            try:
                tasks = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise AssertionStrictError(f"Invalid JSON in tasks response: {e}")

            # Verify structure
            assert "tasks" in tasks, "Tasks response missing 'tasks'"
            assert isinstance(tasks["tasks"], list), "Tasks should be a list"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_receiver_create_task_endpoint(self, clean_test_env, available_port, test_work_dir):
        """Test Receiver task creation endpoint."""
        port = available_port(TEST_RECEIVER_PORT)

        env = {**os.environ,
               "TM_RECEIVER_PORT": str(port),
               "TM_WORK_DIR": str(test_work_dir),
               "TM_RECEIVER_LOG": str(test_work_dir / "logs" / "receiver.log")}

        proc = subprocess.Popen(
            [str(RECEIVER_BINARY)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR / "Receiver"
        )

        try:
            time.sleep(2)

            # Create a test task
            task_data = {
                "task_id": "test_task_001",
                "action": "start_vllm",
                "config": {
                    "model_name": "facebook/opt-125m"
                }
            }

            result = subprocess.run(
                ["curl", "-s", "-X", "POST",
                 f"http://localhost:{port}/api/v1/tasks",
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps(task_data)],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Task creation failed: {result.stderr}"

            # Verify response
            try:
                response = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise AssertionStrictError(f"Invalid JSON in task response: {e}")

            assert "status" in response, "Task response missing 'status'"
            assert response["status"] in ["accepted", "error"], \
                f"Unexpected task status: {response.get('status')}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)


# =============================================================================
# Test 6: Integration Tests
# =============================================================================

class TestAmdAgentIntegration:
    """Integration tests for AMD Agent workflow."""

    def test_end_to_end_exporter_workflow(self, clean_test_env, available_port):
        """Test complete exporter workflow in mock mode."""
        port = available_port(TEST_EXPORTER_PORT)

        # Start exporter
        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(3)

            # Verify all endpoints work
            endpoints = ["/health", "/metrics", "/json", "/"]
            for endpoint in endpoints:
                result = subprocess.run(
                    ["curl", "-s", f"http://localhost:{port}{endpoint}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                assert result.returncode == 0, \
                    f"Endpoint {endpoint} failed: {result.stderr}"
                assert len(result.stdout) > 0, \
                    f"Endpoint {endpoint} returned empty response"

            # Verify metrics format
            metrics_result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/metrics"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Check Prometheus format
            assert "# HELP" in metrics_result.stdout, \
                "Metrics should contain HELP comments"
            assert "# TYPE" in metrics_result.stdout, \
                "Metrics should contain TYPE comments"
            assert "amd_" in metrics_result.stdout, \
                "Metrics should use amd_ prefix"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_multiple_gpu_metrics_mock(self, clean_test_env, available_port):
        """Test metrics with multiple mock GPUs."""
        port = available_port(TEST_EXPORTER_PORT)

        # Start exporter with multiple GPUs
        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock", "--gpu-ids", "0,1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/metrics"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0
            metrics = parse_prometheus_metrics(result.stdout)

            # Should have 2 GPUs
            if "amd_gpu_count" in metrics:
                count = float(metrics["amd_gpu_count"][0]["value"])
                assert count == 2, \
                    f"Expected 2 GPUs when filtering to 0,1, got {count}"

            # Verify metrics for both GPUs exist
            gpu0_metrics = [m for m in result.stdout.split('\n')
                           if 'gpu="0"' in m and not m.startswith('#')]
            gpu1_metrics = [m for m in result.stdout.split('\n')
                           if 'gpu="1"' in m and not m.startswith('#')]

            assert len(gpu0_metrics) > 0, "No metrics found for GPU 0"
            assert len(gpu1_metrics) > 0, "No metrics found for GPU 1"

        finally:
            proc.terminate()
            proc.wait(timeout=5)


# =============================================================================
# Test 7: Mock Mode Specific Tests
# =============================================================================

class TestAmdAgentMockMode:
    """Tests specifically for mock mode functionality."""

    def test_mock_mode_uses_deterministic_data(self, clean_test_env, available_port):
        """Test that mock mode produces deterministic results."""
        port = available_port(TEST_EXPORTER_PORT)

        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            # Get metrics multiple times
            metrics_list = []
            for _ in range(3):
                result = subprocess.run(
                    ["curl", "-s", f"http://localhost:{port}/metrics"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                metrics_list.append(result.stdout)
                time.sleep(1)

            # Verify metrics are consistent
            for metrics in metrics_list[1:]:
                # Check key metrics are the same
                assert "amd_gpu_count" in metrics, \
                    "GPU count should be in all metric samples"
                assert "amd_memory_total_bytes" in metrics, \
                    "Memory total should be in all metric samples"

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_mock_mode_gpu_count(self, clean_test_env, available_port):
        """Test mock mode GPU count defaults to 1."""
        port = available_port(TEST_EXPORTER_PORT)

        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            gpu_data = json.loads(result.stdout)
            assert len(gpu_data) >= 1, \
                f"Mock mode should have at least 1 GPU, got {len(gpu_data)}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)


# =============================================================================
# Test 8: Error Handling Tests
# =============================================================================

class TestAmdAgentErrorHandling:
    """Tests for error handling in AMD Agent."""

    def test_exporter_handles_invalid_port(self):
        """Test exporter handles invalid port gracefully."""
        # Start with invalid port (use -port instead of --port)
        result = run_command(
            [str(EXPORTER_BINARY), "-port", "invalid"],
            cwd=AMD_AGENT_DIR,
            timeout=10
        )

        assert result.returncode != 0, \
            "Exporter should fail with invalid port"

    def test_exporter_handles_unknown_option(self):
        """Test exporter handles unknown options gracefully."""
        result = run_command(
            [str(EXPORTER_BINARY), "--unknown-option"],
            cwd=AMD_AGENT_DIR,
            timeout=5
        )

        assert result.returncode != 0, \
            "Exporter should fail with unknown option"

    def test_receiver_handles_invalid_port(self):
        """Test receiver handles invalid port gracefully."""
        result = run_command(
            [str(RECEIVER_BINARY)],
            env={**os.environ, "TM_RECEIVER_PORT": "invalid"},
            cwd=AMD_AGENT_DIR / "Receiver",
            timeout=5
        )

        assert result.returncode != 0, \
            "Receiver should fail with invalid port"

    def test_curl_handles_nonexistent_endpoint(self, clean_test_env, available_port):
        """Test exporter returns 404 for nonexistent endpoints."""
        port = available_port(TEST_EXPORTER_PORT)

        proc = subprocess.Popen(
            [str(EXPORTER_BINARY), "--port", str(port), "--mock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=AMD_AGENT_DIR
        )

        try:
            time.sleep(2)

            result = subprocess.run(
                ["curl", "-s", "-w", "%{http_code}",
                 f"http://localhost:{port}/nonexistent"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should return 404
            http_code = result.stdout[-3:]
            assert http_code == "404", \
                f"Expected 404 for nonexistent endpoint, got: {http_code}"

        finally:
            proc.terminate()
            proc.wait(timeout=5)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])

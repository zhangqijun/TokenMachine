"""
vLLM worker implementation.
"""
import os
import subprocess
import asyncio
import time
from typing import Optional, Dict, Any
from loguru import logger
import httpx

from inferx.core.config import get_settings

settings = get_settings()


class VLLMWorker:
    """
    vLLM worker process manager.

    Manages a single vLLM server process as a subprocess.
    """

    def __init__(
        self,
        deployment_id: int,
        worker_index: int,
        model_path: str,
        model_name: str,
        gpu_id: str,
        port: int,
        config: Dict[str, Any]
    ):
        """
        Initialize vLLM worker.

        Args:
            deployment_id: Associated deployment ID
            worker_index: Worker index for this deployment
            model_path: Path to model files
            model_name: Name for the model
            gpu_id: GPU ID to use (e.g., "gpu:0")
            port: Port number for the worker server
            config: vLLM configuration parameters
        """
        self.deployment_id = deployment_id
        self.worker_index = worker_index
        self.model_path = model_path
        self.model_name = model_name
        self.gpu_id = gpu_id
        self.port = port
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://localhost:{port}"
        self._started = False

        # Extract GPU index from gpu_id (e.g., "gpu:0" -> "0")
        self.gpu_index = gpu_id.replace("gpu:", "")

    async def start(self, timeout: int = 300):
        """
        Start the vLLM worker process.

        Args:
            timeout: Maximum time to wait for worker to become healthy
        """
        if self._started:
            logger.warning(f"Worker {self.worker_index} for deployment {self.deployment_id} already started")
            return

        logger.info(f"Starting vLLM worker {self.worker_index} for deployment {self.deployment_id}")

        # Build vLLM command
        cmd = self._build_command()

        # Set environment variables
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = self.gpu_index

        # Start process
        log_path = os.path.join(settings.log_path, "workers")
        os.makedirs(log_path, exist_ok=True)

        stdout_file = open(os.path.join(log_path, f"worker_{self.deployment_id}_{self.worker_index}.stdout.log"), "w")
        stderr_file = open(os.path.join(log_path, f"worker_{self.deployment_id}_{self.worker_index}.stderr.log"), "w")

        self.process = subprocess.Popen(
            cmd,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True
        )

        # Wait for worker to become healthy
        await self._wait_for_ready(timeout)
        self._started = True
        logger.info(f"vLLM worker {self.worker_index} started successfully at {self.base_url}")

    def _build_command(self) -> list[str]:
        """Build the vLLM command line."""
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_path,
            "--host", "0.0.0.0",
            "--port", str(self.port),
            "--gpu-memory-utilization", str(self.config.get("gpu_memory_utilization", 0.9)),
            "--max-model-len", str(self.config.get("max_model_len", 4096)),
            "--dtype", self.config.get("dtype", "auto"),
        ]

        if self.config.get("trust_remote_code", True):
            cmd.append("--trust-remote-code")

        if self.config.get("tensor_parallel_size", 1) > 1:
            cmd.extend(["--tensor-parallel-size", str(self.config["tensor_parallel_size"])])

        return cmd

    async def _wait_for_ready(self, timeout: int = 300):
        """
        Wait for the worker to become ready.

        Args:
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        check_interval = 2

        while time.time() - start_time < timeout:
            if self.is_healthy():
                return

            # Check if process is still running
            if self.process and self.process.poll() is not None:
                raise RuntimeError(f"Worker process exited with code {self.process.returncode}")

            await asyncio.sleep(check_interval)

        raise TimeoutError(f"Worker failed to start within {timeout}s")

    def is_healthy(self) -> bool:
        """
        Check if the worker is healthy.

        Returns:
            True if worker is responding to health checks
        """
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed for worker {self.worker_index}: {e}")
            return False

    async def stop(self, timeout: int = 30):
        """
        Stop the worker process.

        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if not self._started:
            return

        logger.info(f"Stopping vLLM worker {self.worker_index}")

        if self.process:
            # Try graceful shutdown first
            self.process.terminate()

            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning(f"Worker {self.worker_index} did not terminate gracefully, forcing")
                self.process.kill()
                self.process.wait()

            self.process = None

        self._started = False
        logger.info(f"vLLM worker {self.worker_index} stopped")

    def get_endpoint(self) -> str:
        """Get the endpoint URL for this worker."""
        return self.base_url

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the worker.

        Returns:
            Dictionary containing worker status information
        """
        return {
            "deployment_id": self.deployment_id,
            "worker_index": self.worker_index,
            "port": self.port,
            "gpu_id": self.gpu_id,
            "started": self._started,
            "healthy": self.is_healthy() if self._started else False,
            "process_alive": self.process and self.process.poll() is None if self.process else False,
        }

    def __repr__(self) -> str:
        return f"VLLMWorker(deployment={self.deployment_id}, index={self.worker_index}, port={self.port})"


class VLLMWorkerError(Exception):
    """Exception raised when vLLM worker operations fail."""
    pass

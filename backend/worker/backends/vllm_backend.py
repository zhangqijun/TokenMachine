"""
vLLM Inference Backend.
"""
from typing import Dict, Any
import asyncio
import subprocess
import logging
import httpx

from backend.worker.backends.base import InferenceBackend

logger = logging.getLogger(__name__)


class VLLMBackend(InferenceBackend):
    """vLLM inference backend implementation."""

    def __init__(
        self,
        model_path: str,
        model_name: str,
        config: Dict[str, Any],
    ):
        """Initialize VLLMBackend.

        Args:
            model_path: Path to the model files
            model_name: Name of the model
            config: Backend-specific configuration
        """
        super().__init__(model_path, model_name, config)
        self.port = config.get("port", 8001)
        self.process: subprocess.Popen = None
        self.base_url = f"http://localhost:{self.port}"

    async def start(self):
        """Start the vLLM server."""
        if self._is_running:
            logger.warning("vLLM backend is already running")
            return

        logger.info(f"Starting vLLM backend for {self.model_name}")

        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_path,
            "--host", "0.0.0.0",
            "--port", str(self.port),
            "--gpu-memory-utilization", str(self.config.get("gpu_memory_utilization", 0.9)),
            "--max-model-len", str(self.config.get("max_model_len", 4096)),
        ]

        if self.config.get("tensor_parallel_size", 1) > 1:
            cmd.extend(["--tensor-parallel-size", str(self.config["tensor_parallel_size"])])

        # Set CUDA_VISIBLE_DEVICES if GPU IDs specified
        env = {}
        gpu_ids = self.config.get("gpu_ids", [])
        if gpu_ids:
            env["CUDA_VISIBLE_DEVICES"] = ",".join(map(str, gpu_ids))

        try:
            self.process = subprocess.Popen(
                cmd,
                env={**__import__("os").environ, **env},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for the server to be ready
            await self._wait_for_ready(timeout=300)

            self._is_running = True
            logger.info(f"vLLM backend started for {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to start vLLM backend: {e}")
            raise

    async def _wait_for_ready(self, timeout: int = 300):
        """Wait for the vLLM server to be ready.

        Args:
            timeout: Timeout in seconds
        """
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/health", timeout=5.0)
                    if response.status_code == 200:
                        return
            except Exception:
                pass

            await asyncio.sleep(2)

        raise TimeoutError(f"vLLM server failed to start within {timeout}s")

    async def stop(self):
        """Stop the vLLM server."""
        if not self._is_running:
            return

        logger.info(f"Stopping vLLM backend for {self.model_name}")

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

        self._is_running = False
        logger.info(f"vLLM backend stopped for {self.model_name}")

    async def health_check(self) -> bool:
        """Check if the vLLM server is healthy.

        Returns:
            True if healthy, False otherwise
        """
        if not self._is_running or not self.process:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False

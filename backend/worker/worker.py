"""
TokenMachine Worker - Data plane for model serving.

This module implements the Worker class which runs on worker nodes and manages
model instances, health checks, and communication with the server.
"""
from typing import Optional
import asyncio
import socket
import logging

from backend.worker.config import get_worker_config
from backend.worker.serve_manager import ServeManager
from backend.worker.collector import WorkerStatusCollector
from backend.worker.exporter import MetricExporter

logger = logging.getLogger(__name__)


class Worker:
    """Worker data plane - runs on worker nodes and serves models."""

    def __init__(
        self,
        server_url: str,
        token: str,
        config: Optional[dict] = None,
    ):
        """Initialize the Worker.

        Args:
            server_url: URL of the server (e.g., "http://server:8000")
            token: Authentication token for this worker
            config: Optional configuration dictionary
        """
        self.config = config or get_worker_config()
        self.server_url = server_url
        self.token = token

        # Detect worker information
        self.worker_ip, self.worker_ifname = self._detect_worker_info()
        self.worker_name = self.config.get("worker_name", socket.gethostname())
        self.worker_id: Optional[int] = None
        self.cluster_id: Optional[int] = None

        # Components
        self.status_collector = WorkerStatusCollector(
            worker_ip=self.worker_ip,
            worker_name=self.worker_name,
        )
        self.serve_manager = ServeManager(
            worker_id_getter=lambda: self.worker_id,
            server_url=server_url,
            token=token,
        )
        self.metric_exporter = MetricExporter(
            collector=self.status_collector,
            server_url=server_url,
            token=token,
        )

        # API service (will be initialized later)
        self.api_app = None
        self._api_server = None

        # Background tasks
        self._background_tasks = []
        self._is_running = False

    def _detect_worker_info(self) -> tuple[str, str]:
        """Detect worker IP and interface name.

        Returns:
            Tuple of (ip_address, interface_name)
        """
        # Try to get the first non-loopback IP
        try:
            # Get local IP by connecting to a public DNS
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]

            # Try to determine interface name (simplified)
            ifname = "eth0"  # Default, could be improved with actual detection

            return ip, ifname
        except Exception as e:
            logger.warning(f"Could not detect worker IP: {e}, using localhost")
            return "127.0.0.1", "lo"

    async def register(self) -> dict:
        """Register this worker with the server.

        Returns:
            Registration response from server
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/api/v1/workers/register",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": self.worker_name,
                    "ip": self.worker_ip,
                    "ifname": self.worker_ifname,
                    "hostname": socket.gethostname(),
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            self.worker_id = data["id"]
            self.cluster_id = data.get("cluster_id")

            logger.info(f"Worker registered: {self.worker_id} in cluster {self.cluster_id}")
            return data

    async def start(self):
        """Start the Worker and all background tasks."""
        if self._is_running:
            logger.warning("Worker is already running")
            return

        logger.info("Starting TokenMachine Worker...")

        # Register with server
        await self.register()

        # Start metric collection
        self._background_tasks.append(
            asyncio.create_task(self.metric_exporter.start())
        )

        # Start model instance management
        self._background_tasks.append(
            asyncio.create_task(self.serve_manager.watch_model_instances())
        )
        self._background_tasks.append(
            asyncio.create_task(self.serve_manager.sync_instance_states())
        )

        # Start heartbeat loop
        self._background_tasks.append(
            asyncio.create_task(self._heartbeat_loop())
        )

        self._is_running = True
        logger.info(f"TokenMachine Worker started (ID: {self.worker_id})")

    async def stop(self):
        """Stop the Worker and all background tasks."""
        if not self._is_running:
            logger.warning("Worker is not running")
            return

        logger.info("Stopping TokenMachine Worker...")

        self._is_running = False

        # Stop all model instances
        await self.serve_manager.stop_all_instances()

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self._background_tasks.clear()

        logger.info("TokenMachine Worker stopped")

    async def _heartbeat_loop(self, interval_seconds: int = 30):
        """Send heartbeat to server at regular intervals.

        Args:
            interval_seconds: Interval between heartbeats
        """
        import httpx

        while self._is_running:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.server_url}/api/v1/workers/{self.worker_id}/heartbeat",
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=10.0,
                    )
                    response.raise_for_status()

                logger.debug("Heartbeat sent successfully")
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

            await asyncio.sleep(interval_seconds)

    async def serve_api(self, host: str = "0.0.0.0", port: int = 8001):
        """Start the Worker API server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        import uvicorn
        from fastapi import FastAPI

        app = FastAPI(title="TokenMachine Worker")

        # Include routers
        from backend.worker.api import health, logs, proxy
        app.include_router(health.router)
        app.include_router(logs.router)
        app.include_router(proxy.router)

        self.api_app = app

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        self._api_server = uvicorn.Server(config)

        await self._api_server.serve()

    def is_running(self) -> bool:
        """Check if the worker is running.

        Returns:
            True if worker is running, False otherwise
        """
        return self._is_running

    def get_status(self) -> dict:
        """Get worker status.

        Returns:
            Dictionary containing worker status information
        """
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "worker_ip": self.worker_ip,
            "cluster_id": self.cluster_id,
            "is_running": self._is_running,
        }

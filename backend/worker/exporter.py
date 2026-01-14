"""
Metric Exporter - exports worker metrics to server.
"""
from typing import Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


class MetricExporter:
    """Exports worker metrics to the server."""

    def __init__(self, collector, server_url: str, token: str):
        """Initialize MetricExporter.

        Args:
            collector: WorkerStatusCollector instance
            server_url: Server URL
            token: Authentication token
        """
        self.collector = collector
        self.server_url = server_url
        self.token = token
        self._is_running = False

    async def start(self, interval_seconds: int = 15):
        """Start metric export loop.

        Args:
            interval_seconds: Interval between exports
        """
        if self._is_running:
            logger.warning("Metric exporter is already running")
            return

        self._is_running = True
        logger.info("Starting metric exporter")

        while self._is_running:
            try:
                await self._export_metrics()
            except Exception as e:
                logger.error(f"Error exporting metrics: {e}")

            await asyncio.sleep(interval_seconds)

    def stop(self):
        """Stop metric export loop."""
        self._is_running = False
        logger.info("Metric exporter stopped")

    async def _export_metrics(self):
        """Export current metrics to server."""
        import httpx

        status = self.collector.collect()
        worker_id = self._get_worker_id()

        if worker_id is None:
            logger.debug("Worker ID not set, skipping metric export")
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.server_url}/api/v1/workers/{worker_id}/status",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=status,
                    timeout=10.0,
                )
        except Exception as e:
            logger.error(f"Error sending metrics to server: {e}")

    def _get_worker_id(self) -> int:
        """Get worker ID from collector's context.

        Returns:
            Worker ID or None
        """
        # This should be set by the Worker class
        return None

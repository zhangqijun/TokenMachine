"""
Worker Status Collector - collects worker metrics.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class WorkerStatusCollector:
    """Collects worker status metrics."""

    def __init__(self, worker_ip: str, worker_name: str):
        """Initialize WorkerStatusCollector.

        Args:
            worker_ip: Worker IP address
            worker_name: Worker name
        """
        self.worker_ip = worker_ip
        self.worker_name = worker_name

    def collect(self) -> Dict[str, Any]:
        """Collect current worker status.

        Returns:
            Dictionary containing worker status
        """
        return {
            "worker_ip": self.worker_ip,
            "worker_name": self.worker_name,
            "gpus": self._collect_gpu_info(),
            "system": self._collect_system_info(),
        }

    def _collect_gpu_info(self) -> List[Dict[str, Any]]:
        """Collect GPU information.

        Returns:
            List of GPU info dictionaries
        """
        try:
            from backend.core.gpu import GPUManager

            gpu_manager = GPUManager()
            return gpu_manager.get_all_gpus()
        except Exception as e:
            logger.error(f"Error collecting GPU info: {e}")
            return []

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information.

        Returns:
            System info dictionary
        """
        try:
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_used_mb": psutil.virtual_memory().used // (1024 * 1024),
                "memory_total_mb": psutil.virtual_memory().total // (1024 * 1024),
                "disk_usage_percent": psutil.disk_usage("/").percent,
            }
        except Exception as e:
            logger.error(f"Error collecting system info: {e}")
            return {}

"""
Prometheus service for querying GPU metrics.

This service queries Prometheus for historical GPU utilization and memory data.
Supports two modes:
1. Prometheus mode: Query historical data from Prometheus server
2. Direct mode: Query real-time data from worker Exporter directly
"""
import httpx
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger


class PrometheusService:
    """Service for querying Prometheus metrics."""

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        worker_ip: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize Prometheus service.

        Args:
            prometheus_url: Prometheus server URL
            worker_ip: Worker IP for direct Exporter query (optional)
            timeout: Request timeout in seconds
        """
        self.prometheus_url = prometheus_url.rstrip("/") if prometheus_url else ""
        self.worker_ip = worker_ip
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

        # Determine mode
        self.use_prometheus = bool(prometheus_url and not worker_ip)
        self.use_direct = bool(worker_ip)

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _query_prometheus(self, query: str, time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Query Prometheus server."""
        if not self.prometheus_url:
            return []

        params = {"query": query}
        if time:
            params["time"] = time.isoformat() + "Z"

        try:
            response = self.client.get(
                f"{self.prometheus_url}/api/v1/query",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                logger.error(f"Prometheus query failed: {data.get('error')}")
                return []

            return data.get("data", {}).get("result", [])

        except httpx.RequestError as e:
            logger.error(f"Prometheus request error: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Prometheus response: {e}")
            return []

    def _query_exporter(self, metric: str, gpu_index: int = 0) -> Optional[float]:
        """Query worker Exporter directly for real-time value."""
        if not self.worker_ip:
            return None

        try:
            response = self.client.get(
                f"http://{self.worker_ip}:19090/metrics",
                timeout=5.0
            )
            if response.status_code != 200:
                return None

            # Parse metric from response
            metric_name = f"gpu{gpu_index}_{metric}" if gpu_index > 0 else metric
            for line in response.text.split('\n'):
                if line.startswith(metric_name):
                    parts = line.split()
                    if len(parts) >= 2:
                        return float(parts[1])
            return None

        except Exception as e:
            logger.debug(f"Exporter query error: {e}")
            return None

    def query_instant(
        self,
        query: str,
        time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute an instant query against Prometheus.

        Args:
            query: PromQL query string
            time: Query timestamp (defaults to now)

        Returns:
            List of metric results
        """
        return self._query_prometheus(query, time)

    def get_gpu_utilization_1m(self, gpu_index: int = 0) -> Optional[float]:
        """
        Get average GPU utilization over the past 1 minute.

        Args:
            gpu_index: GPU index (0-based)

        Returns:
            Average utilization percentage or None if unavailable
        """
        if self.use_prometheus:
            # Query from Prometheus (historical data)
            query = f'avg_over_time(gpu{gpu_index}_memory_utilization[1m])'
            results = self._query_prometheus(query)

            if results and len(results) > 0:
                try:
                    value = results[0].get("value", [0, "0"])
                    return float(value[1]) * 100  # Convert to percentage
                except (IndexError, ValueError) as e:
                    logger.error(f"Failed to parse GPU utilization: {e}")
        elif self.use_direct:
            # Direct query from Exporter (real-time)
            return self._query_exporter("memory_utilization", gpu_index)

        return None

    def get_gpu_memory_used_mb(self, gpu_index: int = 0) -> Optional[float]:
        """
        Get current GPU memory used in MB.

        Args:
            gpu_index: GPU index (0-based)

        Returns:
            Memory used in MB or None if unavailable
        """
        if self.use_prometheus:
            query = f'gpu{gpu_index}_memory_used_bytes / 1024 / 1024'
            results = self._query_prometheus(query)

            if results and len(results) > 0:
                try:
                    value = results[0].get("value", [0, "0"])
                    return float(value[1])
                except (IndexError, ValueError) as e:
                    logger.error(f"Failed to parse GPU memory: {e}")
        elif self.use_direct:
            bytes_val = self._query_exporter("memory_used_bytes", gpu_index)
            if bytes_val is not None:
                return bytes_val / 1024 / 1024

        return None

    def get_gpu_memory_total_mb(self, gpu_index: int = 0) -> Optional[float]:
        """
        Get total GPU memory in MB.

        Args:
            gpu_index: GPU index (0-based)

        Returns:
            Total memory in MB or None if unavailable
        """
        if self.use_prometheus:
            query = f'gpu{gpu_index}_memory_total_bytes / 1024 / 1024'
            results = self._query_prometheus(query)

            if results and len(results) > 0:
                try:
                    value = results[0].get("value", [0, "0"])
                    return float(value[1])
                except (IndexError, ValueError) as e:
                    logger.error(f"Failed to parse GPU memory: {e}")
        elif self.use_direct:
            bytes_val = self._query_exporter("memory_total_bytes", gpu_index)
            if bytes_val is not None:
                return bytes_val / 1024 / 1024

        return None

    def get_all_gpu_metrics(self) -> Dict[str, Any]:
        """
        Get all GPU metrics for the local worker.

        Returns:
            Dictionary containing all GPU metrics
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "gpus": []
        }

        # Get number of GPUs
        if self.use_prometheus:
            gpu_count_result = self._query_prometheus("gpu_count")
            gpu_count = 0
            if gpu_count_result:
                try:
                    value = gpu_count_result[0].get("value", [0, "0"])
                    gpu_count = int(float(value[1]))
                except (IndexError, ValueError):
                    gpu_count = 1
        elif self.use_direct:
            # Try to get gpu_count from exporter
            gpu_count = self._query_exporter("count")
            if gpu_count is None:
                gpu_count = 1  # Default to 1 if parsing fails

        # Get metrics for each GPU
        for i in range(gpu_count):
            gpu_metrics = {
                "index": i,
                "memory_utilization": self.get_gpu_utilization_1m(i),
                "memory_used_mb": self.get_gpu_memory_used_mb(i),
                "memory_total_mb": self.get_gpu_memory_total_mb(i),
            }
            metrics["gpus"].append(gpu_metrics)

        return metrics

    def is_available(self) -> bool:
        """Check if Prometheus is available."""
        try:
            if self.use_prometheus:
                response = self.client.get(f"{self.prometheus_url}/-/healthy")
                return response.status_code == 200
            elif self.use_direct:
                response = self.client.get(
                    f"http://{self.worker_ip}:19090/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except httpx.RequestError:
            pass
        return False


# Global instance for local Prometheus
_prometheus_service: Optional[PrometheusService] = None


def get_prometheus_service() -> PrometheusService:
    """Get the global Prometheus service instance."""
    global _prometheus_service
    if _prometheus_service is None:
        _prometheus_service = PrometheusService()
    return _prometheus_service


def get_worker_prometheus_service(worker_ip: str) -> PrometheusService:
    """Get a Prometheus service for querying a specific worker."""
    return PrometheusService(worker_ip=worker_ip)

"""
Worker pool for managing vLLM workers.
"""
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger

from inferx.workers.vllm_worker import VLLMWorker, VLLMWorkerError
from inferx.core.config import get_settings

settings = get_settings()


class VLLMWorkerPool:
    """
    Pool for managing multiple vLLM workers.

    Workers are organized by deployment_id, with each deployment
    potentially having multiple worker replicas.
    """

    def __init__(self):
        """Initialize the worker pool."""
        self.workers: Dict[int, Dict[int, VLLMWorker]] = {}
        self._lock = asyncio.Lock()

    async def create_worker(
        self,
        deployment_id: int,
        worker_index: int,
        model_path: str,
        model_name: str,
        gpu_id: str,
        port: int,
        config: Dict[str, Any]
    ) -> VLLMWorker:
        """
        Create and start a new worker.

        Args:
            deployment_id: Associated deployment ID
            worker_index: Worker index within the deployment
            model_path: Path to model files
            model_name: Name for the model
            gpu_id: GPU ID to use (e.g., "gpu:0")
            port: Port number for the worker server
            config: vLLM configuration parameters

        Returns:
            Started VLLMWorker instance
        """
        async with self._lock:
            if deployment_id not in self.workers:
                self.workers[deployment_id] = {}

            if worker_index in self.workers[deployment_id]:
                raise VLLMWorkerError(
                    f"Worker {worker_index} already exists for deployment {deployment_id}"
                )

            worker = VLLMWorker(
                deployment_id=deployment_id,
                worker_index=worker_index,
                model_path=model_path,
                model_name=model_name,
                gpu_id=gpu_id,
                port=port,
                config=config
            )

            await worker.start(timeout=settings.worker_start_timeout)

            self.workers[deployment_id][worker_index] = worker
            logger.info(f"Created worker {worker_index} for deployment {deployment_id}")

            return worker

    async def stop_worker(self, deployment_id: int, worker_index: int) -> bool:
        """
        Stop a specific worker.

        Args:
            deployment_id: Deployment ID
            worker_index: Worker index

        Returns:
            True if worker was stopped, False if not found
        """
        async with self._lock:
            if deployment_id not in self.workers:
                return False

            if worker_index not in self.workers[deployment_id]:
                return False

            worker = self.workers[deployment_id][worker_index]
            await worker.stop()

            del self.workers[deployment_id][worker_index]

            # Clean up empty deployment entries
            if not self.workers[deployment_id]:
                del self.workers[deployment_id]

            logger.info(f"Stopped worker {worker_index} for deployment {deployment_id}")
            return True

    async def stop_deployment_workers(self, deployment_id: int) -> int:
        """
        Stop all workers for a deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            Number of workers stopped
        """
        async with self._lock:
            if deployment_id not in self.workers:
                return 0

            workers = list(self.workers[deployment_id].values())
            count = len(workers)

            # Stop all workers concurrently
            stop_tasks = [worker.stop() for worker in workers]
            await asyncio.gather(*stop_tasks, return_exceptions=True)

            del self.workers[deployment_id]

            logger.info(f"Stopped {count} workers for deployment {deployment_id}")
            return count

    def get_worker(self, deployment_id: int, worker_index: int) -> Optional[VLLMWorker]:
        """
        Get a specific worker.

        Args:
            deployment_id: Deployment ID
            worker_index: Worker index

        Returns:
            VLLMWorker instance or None if not found
        """
        return self.workers.get(deployment_id, {}).get(worker_index)

    def get_deployment_workers(self, deployment_id: int) -> List[VLLMWorker]:
        """
        Get all workers for a deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            List of VLLMWorker instances
        """
        return list(self.workers.get(deployment_id, {}).values())

    def get_all_workers(self) -> List[VLLMWorker]:
        """Get all workers across all deployments."""
        all_workers = []
        for deployment_workers in self.workers.values():
            all_workers.extend(deployment_workers.values())
        return all_workers

    def get_healthy_worker_endpoint(self, deployment_id: int) -> Optional[str]:
        """
        Get an endpoint for a healthy worker using round-robin.

        Args:
            deployment_id: Deployment ID

        Returns:
            Worker endpoint URL or None if no healthy workers
        """
        workers = self.get_deployment_workers(deployment_id)
        healthy_workers = [w for w in workers if w.is_healthy()]

        if not healthy_workers:
            return None

        # Simple round-robin (could be improved with proper load balancing)
        import random
        return random.choice(healthy_workers).get_endpoint()

    def get_worker_count(self, deployment_id: int) -> int:
        """Get the number of workers for a deployment."""
        return len(self.workers.get(deployment_id, {}))

    def get_all_status(self) -> Dict[int, Dict[int, Dict[str, Any]]]:
        """
        Get status of all workers.

        Returns:
            Nested dictionary of deployment_id -> worker_index -> status
        """
        status = {}
        for deployment_id, workers in self.workers.items():
            status[deployment_id] = {
                worker_index: worker.get_status()
                for worker_index, worker in workers.items()
            }
        return status

    async def health_check_all(self) -> Dict[int, Dict[int, bool]]:
        """
        Perform health check on all workers.

        Returns:
            Nested dictionary of deployment_id -> worker_index -> healthy
        """
        health = {}

        for deployment_id, workers in self.workers.items():
            health[deployment_id] = {}
            for worker_index, worker in workers.items():
                health[deployment_id][worker_index] = worker.is_healthy()

        return health

    async def restart_unhealthy_workers(self, deployment_id: int) -> int:
        """
        Restart unhealthy workers for a deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            Number of workers restarted
        """
        workers = self.get_deployment_workers(deployment_id)
        restarted = 0

        for worker in workers:
            if not worker.is_healthy():
                logger.warning(f"Restarting unhealthy worker {worker.worker_index} for deployment {deployment_id}")
                try:
                    await worker.stop()
                    await worker.start()
                    restarted += 1
                except Exception as e:
                    logger.error(f"Failed to restart worker {worker.worker_index}: {e}")

        return restarted

    async def cleanup(self):
        """Stop all workers and clean up resources."""
        logger.info("Cleaning up worker pool")

        deployment_ids = list(self.workers.keys())
        for deployment_id in deployment_ids:
            await self.stop_deployment_workers(deployment_id)

        logger.info("Worker pool cleaned up")


# Global worker pool instance
_worker_pool: Optional[VLLMWorkerPool] = None


def get_worker_pool() -> VLLMWorkerPool:
    """Get the global worker pool instance."""
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = VLLMWorkerPool()
    return _worker_pool

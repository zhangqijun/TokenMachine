"""
Serve Manager - manages model instances on a worker.
"""
from typing import Dict, Optional, List, Any
import asyncio
import logging

from backend.worker.backends.base import InferenceBackend

logger = logging.getLogger(__name__)


class ServeManager:
    """Manages model instances on a worker."""

    def __init__(
        self,
        worker_id_getter: callable,
        server_url: str,
        token: str,
    ):
        """Initialize ServeManager.

        Args:
            worker_id_getter: Callable that returns the worker ID
            server_url: Server URL
            token: Authentication token
        """
        self.worker_id_getter = worker_id_getter
        self.server_url = server_url
        self.token = token

        # Model cache: {instance_id: model_data}
        self._model_cache_by_instance: Dict[int, dict] = {}

        # Backend cache: {instance_id: InferenceBackend}
        self._backend_by_instance: Dict[int, InferenceBackend] = {}

    async def watch_model_instances(self, interval_seconds: int = 10):
        """Watch for changes in assigned model instances.

        Args:
            interval_seconds: Interval between checks
        """
        import httpx

        last_seen_ids = set()

        while True:
            try:
                worker_id = self.worker_id_getter()
                if worker_id is None:
                    await asyncio.sleep(5)
                    continue

                # Get instances assigned to this worker
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.server_url}/api/v1/workers/{worker_id}/instances",
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    instances = response.json().get("items", [])

                current_ids = {inst["id"] for inst in instances}

                # Start new instances
                new_ids = current_ids - last_seen_ids
                for instance_id in new_ids:
                    instance = next(i for i in instances if i["id"] == instance_id)
                    await self._start_instance(instance)

                # Stop removed instances
                removed_ids = last_seen_ids - current_ids
                for instance_id in removed_ids:
                    await self._stop_instance(instance_id)

                last_seen_ids = current_ids
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error watching instances: {e}")
                await asyncio.sleep(interval_seconds)

    async def _get_instance(self, instance_id: int) -> Optional[dict]:
        """Get instance details from server.

        Args:
            instance_id: Instance ID

        Returns:
            Instance data or None
        """
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/api/v1/instances/{instance_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting instance {instance_id}: {e}")
            return None

    async def _start_instance(self, instance: dict):
        """Start a model instance.

        Args:
            instance: Instance data
        """
        instance_id = instance["id"]
        model = instance.get("model", {})
        backend_name = instance.get("backend", "vllm")

        logger.info(f"Starting instance {instance_id}: {model.get('name', 'unknown')}")

        try:
            # Select backend
            if backend_name == "vllm":
                from backend.worker.backends.vllm_backend import VLLMBackend

                backend = VLLMBackend(
                    model_path=model.get("path", ""),
                    model_name=model.get("name", ""),
                    config=instance.get("config", {}),
                )
            elif backend_name == "sglang":
                from backend.worker.backends.sglang_backend import SGLangBackend

                backend = SGLangBackend(
                    model_path=model.get("path", ""),
                    model_name=model.get("name", ""),
                    config=instance.get("config", {}),
                )
            else:
                raise ValueError(f"Unsupported backend: {backend_name}")

            # Start backend
            await backend.start()

            # Cache
            self._backend_by_instance[instance_id] = backend
            self._model_cache_by_instance[instance_id] = model

            # Update status
            await self._update_instance_status(instance_id, "running")

            logger.info(f"Instance {instance_id} started successfully")
        except Exception as e:
            logger.error(f"Failed to start instance {instance_id}: {e}")
            await self._update_instance_status(instance_id, "error")

    async def _stop_instance(self, instance_id: int):
        """Stop a model instance.

        Args:
            instance_id: Instance ID
        """
        if instance_id not in self._backend_by_instance:
            return

        logger.info(f"Stopping instance {instance_id}")

        try:
            backend = self._backend_by_instance.pop(instance_id)
            await backend.stop()

            self._model_cache_by_instance.pop(instance_id, None)

            logger.info(f"Instance {instance_id} stopped")
        except Exception as e:
            logger.error(f"Error stopping instance {instance_id}: {e}")

    async def _update_instance_status(self, instance_id: int, status: str, health_status: Optional[dict] = None):
        """Update instance status on server.

        Args:
            instance_id: Instance ID
            status: New status
            health_status: Optional health status data
        """
        import httpx

        try:
            payload = {"status": status}
            if health_status:
                payload["health_status"] = health_status

            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{self.server_url}/api/v1/instances/{instance_id}/status",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=payload,
                    timeout=10.0,
                )
        except Exception as e:
            logger.error(f"Error updating instance status: {e}")

    async def sync_instance_states(self, interval_seconds: int = 30):
        """Sync instance health states with server.

        Args:
            interval_seconds: Interval between syncs
        """
        while True:
            try:
                for instance_id, backend in self._backend_by_instance.items():
                    try:
                        is_healthy = await backend.health_check()
                        status = "running" if is_healthy else "error"
                        await self._update_instance_status(
                            instance_id,
                            status,
                            health_status={"healthy": is_healthy, "timestamp": asyncio.get_event_loop().time()},
                        )
                    except Exception as e:
                        logger.error(f"Health check failed for instance {instance_id}: {e}")
                        await self._update_instance_status(instance_id, "error")

                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error syncing states: {e}")
                await asyncio.sleep(interval_seconds)

    async def stop_all_instances(self):
        """Stop all running instances."""
        for instance_id in list(self._backend_by_instance.keys()):
            await self._stop_instance(instance_id)

    def get_running_backends(self) -> Dict[int, InferenceBackend]:
        """Get all running backends.

        Returns:
            Dictionary mapping instance_id to backend
        """
        return self._backend_by_instance.copy()

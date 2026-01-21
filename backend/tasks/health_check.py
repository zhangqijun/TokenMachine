"""
GPU health check task for monitoring worker heartbeats.

This module provides background tasks to check GPU health status
and mark offline GPUs and workers.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.database import GPUDevice, Worker, GPUDeviceState, WorkerStatus

logger = logging.getLogger(__name__)


class GPUHealthChecker:
    """
    GPU health checker for monitoring heartbeats.

    This class runs in the background and periodically checks the last
    heartbeat time of all GPUs to detect offline devices.
    """

    def __init__(self, heartbeat_timeout: int = 90, check_interval: int = 30):
        """
        Initialize the health checker.

        Args:
            heartbeat_timeout: Seconds without heartbeat before marking GPU offline (default: 90s)
            check_interval: Seconds between health checks (default: 30s)
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.check_interval = check_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the health checker background task."""
        if self.running:
            logger.warning("Health checker already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._check_loop())
        logger.info(
            f"GPU health checker started (timeout={self.heartbeat_timeout}s, "
            f"interval={self.check_interval}s)"
        )

    async def stop(self):
        """Stop the health checker background task."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("GPU health checker stopped")

    async def _check_loop(self):
        """Main check loop that runs periodically."""
        while self.running:
            try:
                await self.check_all_gpus()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                logger.info("Health checker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)

    async def check_all_gpus(self):
        """
        Check all GPUs for heartbeat timeout.

        This method:
        1. Finds all GPUs in IN_USE state
        2. Checks their last heartbeat time
        3. Marks GPUs offline if heartbeat timeout exceeded
        4. Updates worker status if needed
        """
        db: Session = next(get_db())

        try:
            # Get all GPUs that are IN_USE
            gpus = db.query(GPUDevice).filter(
                GPUDevice.state == GPUDeviceState.IN_USE
            ).all()

            offline_gpus = []
            now = datetime.now()

            for gpu in gpus:
                # Check last heartbeat time
                if gpu.updated_at:
                    elapsed = (now - gpu.updated_at).total_seconds()

                    if elapsed > self.heartbeat_timeout:
                        # Mark as ERROR (offline)
                        gpu.state = GPUDeviceState.ERROR
                        offline_gpus.append(gpu)
                        logger.warning(
                            f"GPU {gpu.uuid} (worker={gpu.worker_id}, "
                            f"index={gpu.index}) offline: "
                            f"last heartbeat {elapsed:.0f}s ago"
                        )

            if offline_gpus:
                db.commit()

                # Group offline GPUs by worker
                worker_offline_counts = {}
                for gpu in offline_gpus:
                    worker_id = gpu.worker_id
                    if worker_id not in worker_offline_counts:
                        worker_offline_counts[worker_id] = []
                    worker_offline_counts[worker_id].append(gpu)

                # Update worker status
                for worker_id, gpus in worker_offline_counts.items():
                    await self._handle_worker_offline(db, worker_id, gpus)

            # Log summary
            if offline_gpus:
                logger.info(
                    f"Health check completed: {len(offline_gpus)} GPU(s) marked offline"
                )

        finally:
            db.close()

    async def _handle_worker_offline(self, db: Session, worker_id: int, offline_gpus: list):
        """
        Handle worker status when GPUs go offline.

        Args:
            db: Database session
            worker_id: Worker ID
            offline_gpus: List of offline GPUs
        """
        worker = db.query(Worker).filter(Worker.id == worker_id).first()

        if not worker:
            return

        # Count offline and total GPUs for this worker
        offline_count = len(offline_gpus)
        total_count = db.query(GPUDevice).filter(
            GPUDevice.worker_id == worker_id
        ).count()

        # Update worker status based on offline count
        if offline_count == total_count:
            # All GPUs offline
            if worker.status != WorkerStatus.OFFLINE:
                worker.status = WorkerStatus.OFFLINE
                logger.error(
                    f"Worker '{worker.name}' (id={worker_id}) is OFFLINE: "
                    f"all {offline_count}/{total_count} GPUs offline"
                )
        elif worker.status == WorkerStatus.READY:
            # Some GPUs offline - degrade
            worker.status = WorkerStatus.DEGRADED
            logger.warning(
                f"Worker '{worker.name}' (id={worker_id}) is DEGRADED: "
                f"{offline_count}/{total_count} GPUs offline"
            )

        db.commit()

        # Send alert
        await self._send_worker_alert(worker, offline_count, total_count)

    async def _send_worker_alert(self, worker: Worker, offline_count: int, total_count: int):
        """
        Send alert for worker degradation.

        Args:
            worker: Worker that went offline/degraded
            offline_count: Number of offline GPUs
            total_count: Total number of GPUs
        """
        # TODO: Implement alert integration
        # For now, just log
        if offline_count == total_count:
            logger.critical(
                f"ALERT: Worker '{worker.name}' (id={worker.id}) is OFFLINE - "
                f"all GPUs lost"
            )
        else:
            logger.warning(
                f"ALERT: Worker '{worker.name}' (id={worker.id}) is DEGRADED - "
                f"{offline_count}/{total_count} GPUs offline"
            )


# Singleton instance
_health_checker: Optional[GPUHealthChecker] = None


def get_health_checker() -> GPUHealthChecker:
    """Get the singleton health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = GPUHealthChecker()
    return _health_checker


async def start_health_checker():
    """Start the global health checker."""
    checker = get_health_checker()
    await checker.start()


async def stop_health_checker():
    """Stop the global health checker."""
    global _health_checker
    if _health_checker:
        await _health_checker.stop()
        _health_checker = None


# Manual check function (can be called from API or CLI)
async def check_gpu_health_once():
    """
    Perform a one-time health check.

    This function can be called manually to trigger an immediate check.
    """
    checker = get_health_checker()
    await checker.check_all_gpus()


# Standalone execution (for testing)
if __name__ == "__main__":
    import sys

    async def main():
        print("Starting GPU health checker...")
        checker = GPUHealthChecker(
            heartbeat_timeout=90,
            check_interval=30
        )

        try:
            await checker.start()
            # Run forever
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping health checker...")
            await checker.stop()

    asyncio.run(main())

"""
TokenMachine Server - Control plane for worker management.

This module implements the Server class which manages workers, model instances,
and clusters in the TokenMachine system.
"""
from typing import Optional
import asyncio
import logging
from datetime import datetime

from backend.core.config import get_settings
from backend.core.database import get_db_session
from backend.models.database import WorkerStatus

logger = logging.getLogger(__name__)


class Server:
    """Server control plane - manages workers and model instances."""

    def __init__(self, config: Optional[dict] = None):
        """Initialize the Server.

        Args:
            config: Optional configuration dictionary. If not provided, uses default settings.
        """
        self.settings = config or get_settings()
        self.db_session_factory = get_db_session

        # Controllers will be initialized after implementing them
        self.model_controller = None
        self.instance_controller = None
        self.worker_controller = None
        self.cluster_controller = None

        # Scheduler will be initialized after implementing it
        self.scheduler = None

        # Worker Sync Manager will be initialized after implementing it
        self.worker_sync = None

        # Background tasks
        self._background_tasks = []
        self._is_running = False

    async def initialize_controllers(self):
        """Initialize controllers after database session is available."""
        from backend.server.controllers.model_controller import ModelController
        from backend.server.controllers.instance_controller import ModelInstanceController
        from backend.server.controllers.worker_controller import WorkerController
        from backend.server.controllers.cluster_controller import ClusterController

        # Get a database session for controllers
        db_session = self.db_session_factory()

        # Initialize controllers
        self.model_controller = ModelController(db_session)
        self.instance_controller = ModelInstanceController(db_session)
        self.worker_controller = WorkerController(db_session)
        self.cluster_controller = ClusterController(db_session)

        logger.info("Controllers initialized")

    async def start(self):
        """Start the Server and all background tasks."""
        if self._is_running:
            logger.warning("Server is already running")
            return

        logger.info("Starting TokenMachine Server...")

        # Initialize controllers first
        await self.initialize_controllers()

        # Start Worker status sync (placeholder - will be implemented in worker_sync)
        # self._background_tasks.append(
        #     asyncio.create_task(self.worker_sync.sync_worker_statuses())
        # )

        # Start instance health check loop
        if self.instance_controller:
            self._background_tasks.append(
                asyncio.create_task(self.instance_controller.health_check_loop())
            )

        self._is_running = True
        logger.info("TokenMachine Server started")

    async def stop(self):
        """Stop the Server and all background tasks."""
        if not self._is_running:
            logger.warning("Server is not running")
            return

        logger.info("Stopping TokenMachine Server...")

        self._is_running = False

        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to finish
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self._background_tasks.clear()

        logger.info("TokenMachine Server stopped")

    async def serve(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the API server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        import uvicorn
        from backend.api import create_app

        # Create FastAPI app with server context
        app = create_app(server=self)

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        await server.serve()

    def is_running(self) -> bool:
        """Check if the server is running.

        Returns:
            True if server is running, False otherwise
        """
        return self._is_running

    def get_status(self) -> dict:
        """Get server status.

        Returns:
            Dictionary containing server status information
        """
        return {
            "is_running": self._is_running,
            "background_tasks": len(self._background_tasks),
            "timestamp": datetime.utcnow().isoformat(),
        }

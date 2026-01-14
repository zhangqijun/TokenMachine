"""
Inference Backend base class.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class InferenceBackend(ABC):
    """Base class for inference backends."""

    def __init__(
        self,
        model_path: str,
        model_name: str,
        config: Dict[str, Any],
    ):
        """Initialize InferenceBackend.

        Args:
            model_path: Path to the model files
            model_name: Name of the model
            config: Backend-specific configuration
        """
        self.model_path = model_path
        self.model_name = model_name
        self.config = config
        self._is_running = False

    @abstractmethod
    async def start(self):
        """Start the inference backend."""

    @abstractmethod
    async def stop(self):
        """Stop the inference backend."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy.

        Returns:
            True if healthy, False otherwise
        """

    def is_running(self) -> bool:
        """Check if the backend is running.

        Returns:
            True if running, False otherwise
        """
        return self._is_running

"""
SGLang Inference Backend (placeholder).
"""
from typing import Dict, Any
import logging

from backend.worker.backends.base import InferenceBackend

logger = logging.getLogger(__name__)


class SGLangBackend(InferenceBackend):
    """SGLang inference backend implementation (placeholder)."""

    def __init__(
        self,
        model_path: str,
        model_name: str,
        config: Dict[str, Any],
    ):
        """Initialize SGLangBackend.

        Args:
            model_path: Path to the model files
            model_name: Name of the model
            config: Backend-specific configuration
        """
        super().__init__(model_path, model_name, config)
        logger.warning("SGLang backend is not yet implemented")

    async def start(self):
        """Start the SGLang server."""
        raise NotImplementedError("SGLang backend is not yet implemented")

    async def stop(self):
        """Stop the SGLang server."""
        raise NotImplementedError("SGLang backend is not yet implemented")

    async def health_check(self) -> bool:
        """Check if the SGLang server is healthy.

        Returns:
            True if healthy, False otherwise
        """
        raise NotImplementedError("SGLang backend is not yet implemented")

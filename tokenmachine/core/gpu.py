"""
GPU management core module.
"""
from typing import List, Dict, Optional
from loguru import logger

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    logger.warning("pynvml not available. GPU management will be disabled.")


class GPUManager:
    """GPU resource manager."""

    def __init__(self):
        """Initialize GPU manager."""
        self.num_gpus = 0
        self._initialized = False

        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.num_gpus = pynvml.nvmlDeviceGetCount()
                self._initialized = True
                logger.info(f"GPU Manager initialized with {self.num_gpus} GPUs")
            except Exception as e:
                logger.warning(f"Failed to initialize NVIDIA ML: {e}")
        else:
            logger.warning("GPU Manager initialized without NVIDIA support")

    def get_gpu_info(self, gpu_id: int) -> Optional[Dict]:
        """
        Get information about a specific GPU.

        Args:
            gpu_id: GPU index (0-based)

        Returns:
            Dictionary containing GPU information or None if not available
        """
        if not self._initialized:
            return None

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)

            # Basic info
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')

            # Memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

            # Utilization
            try:
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = utilization.gpu
            except:
                gpu_util = 0

            # Temperature
            try:
                temperature = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )
            except:
                temperature = 0

            # Power usage
            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # Convert to watts
            except:
                power_draw = 0

            return {
                "id": f"gpu:{gpu_id}",
                "index": gpu_id,
                "name": name,
                "memory_total_mb": mem_info.total // (1024 * 1024),
                "memory_free_mb": mem_info.free // (1024 * 1024),
                "memory_used_mb": mem_info.used // (1024 * 1024),
                "utilization_percent": gpu_util,
                "temperature_celsius": temperature,
                "power_draw_watts": power_draw,
            }
        except pynvml.NVMLError as e:
            logger.error(f"Error getting GPU {gpu_id} info: {e}")
            return None

    def get_all_gpus(self) -> List[Dict]:
        """
        Get information about all GPUs.

        Returns:
            List of GPU information dictionaries
        """
        gpus = []
        for i in range(self.num_gpus):
            gpu_info = self.get_gpu_info(i)
            if gpu_info:
                gpus.append(gpu_info)
        return gpus

    def find_available_gpus(
        self,
        required_memory_mb: int,
        count: int = 1,
        exclude_gpus: Optional[List[str]] = None
    ) -> List[str]:
        """
        Find available GPUs with sufficient memory.

        Args:
            required_memory_mb: Required memory in MB per GPU
            count: Number of GPUs needed
            exclude_gpus: List of GPU IDs to exclude

        Returns:
            List of available GPU IDs
        """
        exclude_gpus = exclude_gpus or []
        available = []

        gpu_infos = self.get_all_gpus()
        for gpu_info in gpu_infos:
            if gpu_info["id"] in exclude_gpus:
                continue
            if gpu_info["memory_free_mb"] >= required_memory_mb:
                available.append(gpu_info["id"])
                if len(available) >= count:
                    break

        return available

    def check_gpu_compatibility(self, gpu_id: int, requirements: Dict) -> bool:
        """
        Check if a GPU meets specific requirements.

        Args:
            gpu_id: GPU index to check
            requirements: Dictionary of requirements (min_memory_mb, min_compute_capability, etc.)

        Returns:
            True if GPU is compatible, False otherwise
        """
        gpu_info = self.get_gpu_info(gpu_id)
        if not gpu_info:
            return False

        # Check memory
        if "min_memory_mb" in requirements:
            if gpu_info["memory_total_mb"] < requirements["min_memory_mb"]:
                return False

        # Check compute capability
        if "min_compute_capability" in requirements and self._initialized:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
                compute_capability = float(f"{major}.{minor}")
                if compute_capability < requirements["min_compute_capability"]:
                    return False
            except:
                return False

        return True

    def get_total_memory(self) -> int:
        """Get total GPU memory in MB."""
        total = 0
        for gpu in self.get_all_gpus():
            total += gpu["memory_total_mb"]
        return total

    def get_free_memory(self) -> int:
        """Get total free GPU memory in MB."""
        total = 0
        for gpu in self.get_all_gpus():
            total += gpu["memory_free_mb"]
        return total

    def get_average_utilization(self) -> float:
        """Get average GPU utilization percentage."""
        gpus = self.get_all_gpus()
        if not gpus:
            return 0.0
        return sum(gpu["utilization_percent"] for gpu in gpus) / len(gpus)

    def get_average_temperature(self) -> float:
        """Get average GPU temperature in Celsius."""
        gpus = self.get_all_gpus()
        if not gpus:
            return 0.0
        return sum(gpu["temperature_celsius"] for gpu in gpus) / len(gpus)

    def is_available(self) -> bool:
        """Check if GPU manager is available."""
        return self._initialized and self.num_gpus > 0

    def __del__(self):
        """Cleanup on destruction."""
        if self._initialized and PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except:
                pass


# Global GPU manager instance
_gpu_manager: Optional[GPUManager] = None


def get_gpu_manager() -> GPUManager:
    """Get the global GPU manager instance."""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()
    return _gpu_manager

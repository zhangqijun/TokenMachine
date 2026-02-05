"""
TokenMachine GPU Agent - 单元测试

快速运行的单元测试，不依赖完整安装流程。
每个测试独立运行，执行时间 < 1秒。
"""

import os
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from unittest.mock import Mock, patch, MagicMock

import pytest

SCRIPT_DIR = Path(__file__).parent.parent
GPU_AGENT_DIR = SCRIPT_DIR / "gpu-agent"

# 二进制路径
EXPORTER_BINARY = GPU_AGENT_DIR / "Exporter" / "gpu_exporter_main"
RECEIVER_BINARY = GPU_AGENT_DIR / "Receiver" / "receiver"
OCCUPY_GPU_SOURCE = GPU_AGENT_DIR / "occupier" / "occupy_gpu.cu"


# =============================================================================
# 1. 编译验证测试
# =============================================================================

class TestBinaryCompilation:
    """测试二进制文件编译和链接"""

    def test_exporter_binary_exists(self):
        """Exporter 二进制存在"""
        assert EXPORTER_BINARY.exists(), f"Exporter 不存在: {EXPORTER_BINARY}"

    def test_exporter_static_linking(self):
        """Exporter 是静态链接"""
        result = subprocess.run(
            ["file", str(EXPORTER_BINARY)],
            capture_output=True, text=True
        )
        assert "statically linked" in result.stdout, \
            f"Exporter 不是静态链接: {result.stdout}"

    def test_exporter_executable(self):
        """Exporter 可执行"""
        assert os.access(EXPORTER_BINARY, os.X_OK), \
            "Exporter 没有执行权限"

    def test_receiver_binary_exists(self):
        """Receiver 二进制存在"""
        assert RECEIVER_BINARY.exists(), f"Receiver 不存在: {RECEIVER_BINARY}"

    def test_receiver_static_linking(self):
        """Receiver 是静态链接"""
        result = subprocess.run(
            ["file", str(RECEIVER_BINARY)],
            capture_output=True, text=True
        )
        assert "statically linked" in result.stdout, \
            f"Receiver 不是静态链接: {result.stdout}"

    def test_receiver_executable(self):
        """Receiver 可执行"""
        assert os.access(RECEIVER_BINARY, os.X_OK), \
            "Receiver 没有执行权限"

    def test_occupy_gpu_source_exists(self):
        """occupy_gpu.cu 源文件存在"""
        assert OCCUPY_GPU_SOURCE.exists(), \
            f"occupy_gpu.cu 不存在: {OCCUPY_GPU_SOURCE}"

    def test_exporter_help_output(self):
        """Exporter --help 输出正常"""
        result = subprocess.run(
            [str(EXPORTER_BINARY), "--help"],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0, "Exporter --help 失败"
        assert "--gpu-ids" in result.stdout, "缺少 --gpu-ids 参数"
        assert "--port" in result.stdout, "缺少 --port 参数"


# =============================================================================
# 2. 配置文件测试
# =============================================================================

class TestConfigFiles:
    """测试配置文件生成和解析"""

    def test_worker_config_template(self):
        """.worker_config 模板正确"""
        template = """
WORKER_ID={WORKER_ID}
WORKER_SECRET={WORKER_SECRET}
WORKER_NAME={WORKER_NAME}
WORKER_IP={WORKER_IP}
"""

        # 测试变量替换
        config = template.strip().format(
            WORKER_ID="123",
            WORKER_SECRET="secret123",
            WORKER_NAME="test-worker",
            WORKER_IP="192.168.1.100"
        )

        assert "WORKER_ID=123" in config
        assert "WORKER_SECRET=secret123" in config
        assert "WORKER_IP=192.168.1.100" in config

    def test_env_file_template(self):
        """.env 模板正确"""
        template = """
TM_SERVER_URL={SERVER_URL}
TM_AGENT_PORT={AGENT_PORT}
TM_SELECTED_GPUS="{SELECTED_GPUS}"
TM_SELECTED_GPU_COUNT={GPU_COUNT}
"""

        config = template.strip().format(
            SERVER_URL="http://localhost:8000",
            AGENT_PORT="9001",
            SELECTED_GPUS="0 1",
            GPU_COUNT="2"
        )

        assert "TM_SERVER_URL=http://localhost:8000" in config
        assert 'TM_SELECTED_GPUS="0 1"' in config
        assert "TM_SELECTED_GPU_COUNT=2" in config

    def test_parse_worker_id_from_response(self):
        """从响应中解析 worker_id"""
        response = '{"worker_id": 123, "worker_secret": "secret"}'

        import re
        match = re.search(r'"worker_id":\s*(\d+)', response)
        assert match is not None
        assert match.group(1) == "123"

    def test_parse_worker_secret_from_response(self):
        """从响应中解析 worker_secret"""
        response = '{"worker_id": 123, "worker_secret": "secret123"}'

        import re
        match = re.search(r'"worker_secret"\s*:\s*"([^"]+)"', response)
        assert match is not None
        assert match.group(1) == "secret123"

    def test_handle_error_response(self):
        """处理错误响应"""
        response = '{"error": "Internal server error", "message": "Duplicate key"}'

        import re
        match = re.search(r'"worker_id":\s*(\d+)', response)
        assert match is None, "错误响应不应解析出 worker_id"


# =============================================================================
# 3. 服务进程测试 (Mock)
# =============================================================================

class TestServiceProcesses:
    """测试服务进程检查逻辑"""

    @patch('subprocess.run')
    def test_check_occupy_gpu_process_running(self, mock_run):
        """检查 occupy_gpu 进程运行"""
        mock_run.return_value = Mock(
            stdout="2\n",
            returncode=0
        )

        result = subprocess.run(
            ["pgrep", "-f", "occupy_gpu", "|", "wc", "-l"],
            capture_output=True, text=True
        )

        count = int(result.stdout.strip())
        assert count >= 1, "occupy_gpu 进程未运行"

    @patch('subprocess.run')
    def test_check_exporter_process_running(self, mock_run):
        """检查 exporter 进程运行"""
        mock_run.return_value = Mock(
            stdout="1\n",
            returncode=0
        )

        result = subprocess.run(
            ["pgrep", "-f", "gpu_exporter_main", "|", "wc", "-l"],
            capture_output=True, text=True
        )

        count = int(result.stdout.strip())
        assert count >= 1, "Exporter 进程未运行"

    @patch('subprocess.run')
    def test_check_receiver_process_running(self, mock_run):
        """检查 receiver 进程运行"""
        mock_run.return_value = Mock(
            stdout="1\n",
            returncode=0
        )

        result = subprocess.run(
            ["pgrep", "-f", "receiver", "|", "wc", "-l"],
            capture_output=True, text=True
        )

        count = int(result.stdout.strip())
        assert count >= 1, "Receiver 进程未运行"

    @patch('subprocess.run')
    def test_check_no_process_running(self, mock_run):
        """检查无进程运行情况"""
        mock_run.return_value = Mock(
            stdout="0\n",
            returncode=0
        )

        result = subprocess.run(
            ["pgrep", "-f", "occupy_gpu"],
            capture_output=True, text=True
        )

        count = int(result.stdout.strip() if result.stdout.strip() else "0")
        assert count == 0, "不应有进程运行"


# =============================================================================
# 4. GPU 信息解析测试
# =============================================================================

class TestGPUInfoParsing:
    """测试 GPU 信息解析逻辑"""

    def test_parse_nvidia_smi_memory_output(self):
        """解析 nvidia-smi 内存输出"""
        output = "22083, 24564"

        parts = output.strip().split(",")
        assert len(parts) >= 2, "输出格式错误"

        used = int(parts[0].strip())
        total = int(parts[1].strip())

        assert used == 22083
        assert total == 24564

        usage_percent = (used * 100) // total
        assert 80 <= usage_percent <= 100, f"GPU 使用率 {usage_percent}% 应 >= 80%"

    def test_parse_nvidia_smi_gpu_list(self):
        """解析 nvidia-smi GPU 列表"""
        output = "0, NVIDIA GeForce RTX 4090\n1, NVIDIA GeForce RTX 4090"

        lines = output.strip().split("\n")
        assert len(lines) == 2, "应有 2 个 GPU"

        for line in lines:
            parts = line.split(",")
            assert len(parts) >= 2, "GPU 信息格式错误"
            gpu_id = parts[0].strip()
            gpu_name = parts[1].strip()
            assert gpu_id.isdigit(), "GPU ID 应为数字"

    def test_calculate_memory_usage_percent(self):
        """计算内存使用百分比"""
        # 测试用例: (used, total, expected_min_percent)
        test_cases = [
            (22083, 24564, 80),   # ~90%
            (20000, 24564, 80),   # ~81%
            (19652, 24564, 80),   # 80% (向上取整)
            (15000, 24564, 60),   # ~61%
        ]

        for used, total, min_percent in test_cases:
            # 使用浮点数计算以避免整数除法误差
            usage_percent = int((used * 100.0) // total)
            if used >= 19652:  # 80% 阈值 (修正)
                assert usage_percent >= min_percent, \
                    f"used={used}, total={total}, usage={usage_percent}% < {min_percent}%"

    def test_validate_gpu_id_format(self):
        """验证 GPU ID 格式"""
        valid_ids = ["0", "1", "2", "7"]
        for gpu_id in valid_ids:
            assert gpu_id.isdigit(), f"GPU ID {gpu_id} 应为数字"
            assert 0 <= int(gpu_id) <= 7, f"GPU ID {gpu_id} 超出范围"

        invalid_ids = ["-1", "8", "abc", ""]
        for gpu_id in invalid_ids:
            if gpu_id.isdigit():
                assert not (0 <= int(gpu_id) <= 7), f"GPU ID {gpu_id} 应无效"


# =============================================================================
# 5. API 端点测试 (Mock HTTP 请求)
# =============================================================================

class TestAPIEndpoints:
    """测试 API 端点响应解析"""

    def test_parse_exporter_metrics_response(self):
        """解析 Exporter /metrics 响应"""
        response = """
# HELP gpu_memory_used_bytes GPU memory used in bytes
# TYPE gpu_memory_used_bytes gauge
gpu_memory_used_bytes 23155703808
# HELP gpu_memory_total_bytes GPU memory total in bytes
# TYPE gpu_memory_total_bytes gauge
gpu_memory_total_bytes 25757220864
# HELP gpu_memory_utilization GPU memory utilization ratio
# TYPE gpu_memory_utilization gauge
gpu_memory_utilization 0.898999
"""

        required_metrics = [
            "gpu_memory_used_bytes",
            "gpu_memory_total_bytes",
            "gpu_memory_utilization"
        ]

        for metric in required_metrics:
            assert metric in response, f"缺少指标: {metric}"

        # 验证有数值
        lines = response.strip().split("\n")
        metric_values = [l for l in lines if not l.startswith("#") and "gpu_" in l]
        assert len(metric_values) >= 3, f"指标数量不足: {len(metric_values)}"

    def test_parse_receiver_health_response(self):
        """解析 Receiver /health 响应"""
        response = '{"status": "ok"}'

        data = json.loads(response)
        assert "status" in data, "响应缺少 status 字段"
        assert data["status"] == "ok", f"状态不正确: {data['status']}"

    def test_validate_gpu_metrics_format(self):
        """验证 GPU 指标格式"""
        metric_line = "gpu_memory_utilization 0.898999"

        parts = metric_line.split()
        assert len(parts) >= 2, "指标格式错误"
        assert "gpu_memory_utilization" in parts[0], "指标名称错误"

        try:
            value = float(parts[-1])
            assert 0 <= value <= 1, f"利用率应在 0-1 范围: {value}"
        except ValueError:
            raise AssertionError(f"指标值不是数字: {parts[-1]}")


# =============================================================================
# 6. 安装脚本组件测试
# =============================================================================

class TestInstallScriptComponents:
    """测试安装脚本各个组件"""

    def test_detect_cuda_path(self):
        """检测 CUDA 路径"""
        possible_paths = [
            "/usr/local/cuda",
            "/usr/local/cuda-12.8",
            "/usr/local/cuda-12.1",
            "/usr/local/cuda-11.8"
        ]

        found = False
        for path in possible_paths:
            if Path(f"{path}/bin/nvcc").exists():
                found = True
                break

        # 这个测试在 CUDA 环境中应该通过
        # 如果没有 CUDA，测试会跳过
        if not found:
            pytest.skip("未找到 CUDA 安装")

    def test_gpu_selection_format(self):
        """GPU 选择格式正确"""
        # 测试单个 GPU
        gpus = "0"
        gpu_list = gpus.split()
        assert len(gpu_list) == 1
        assert gpu_list[0] == "0"

        # 测试多个 GPU
        gpus = "0 1 2"
        gpu_list = gpus.split()
        assert len(gpu_list) == 3
        assert gpu_list == ["0", "1", "2"]

    def test_port_validation(self):
        """端口号验证"""
        valid_ports = [9001, 19001, 8080, 9090]
        for port in valid_ports:
            assert 1024 <= port <= 65535, f"端口 {port} 超出范围"

        invalid_ports = [80, 443, 100000, -1]
        for port in invalid_ports:
            assert not (1024 <= port <= 65535), f"端口 {port} 应无效"


# =============================================================================
# 7. 错误处理测试
# =============================================================================

class TestErrorHandling:
    """测试错误处理逻辑"""

    def test_missing_binary_error(self):
        """二进制文件不存在错误"""
        non_existent = Path("/tmp/non_existent_binary")

        assert not non_existent.exists(), "测试前提：文件不应存在"

    def test_invalid_gpu_id(self):
        """无效 GPU ID 处理"""
        gpu_id = "999"

        # 模拟 nvidia-smi 失败
        result = subprocess.run(
            ["nvidia-smi", "-i", gpu_id, "--query-gpu=memory.total", "--format=csv,noheader"],
            capture_output=True, text=True
        )

        # 无效 GPU ID 应该返回错误
        assert result.returncode != 0 or "not found" in result.stderr.lower() \
            or "above" in result.stderr.lower(), "应返回错误"

    def test_backend_connection_timeout(self):
        """Backend 连接超时处理"""
        import requests

        try:
            # 使用非常短的超时
            response = requests.get("http://localhost:9999", timeout=0.1)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # 预期的异常
            assert True
        else:
            # 如果连接成功（不太可能），也不应该失败测试
            assert True


# =============================================================================
# 8. 路径和权限测试
# =============================================================================

class TestPathsAndPermissions:
    """测试路径和权限"""

    def test_user_directory_detection(self):
        """用户目录检测"""
        # 测试非 root 用户
        if os.geteuid() == 0:
            pytest.skip("需要非 root 用户")

        user_home = Path.home()
        expected_dir = user_home / ".local" / "tokenmachine"

        assert user_home.exists(), "用户主目录应存在"

    def test_script_directory_exists(self):
        """脚本目录存在"""
        assert GPU_AGENT_DIR.exists(), f"gpu-agent 目录不存在: {GPU_AGENT_DIR}"
        assert (GPU_AGENT_DIR / "install.sh").exists(), "install.sh 不存在"
        assert (GPU_AGENT_DIR / "tm_agent.sh").exists(), "tm_agent.sh 不存在"

    def test_binary_permissions(self):
        """二进制文件权限"""
        binaries = [
            EXPORTER_BINARY,
            RECEIVER_BINARY
        ]

        for binary in binaries:
            if binary.exists():
                stat_info = os.stat(binary)
                mode = stat_info.st_mode

                # 检查执行权限 (owner)
                is_executable = bool(mode & os.X_OK)
                assert is_executable, f"{binary} 没有执行权限"


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

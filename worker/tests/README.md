# GPU Agent 测试指南

## 测试模式

本测试套件支持两种测试模式：

### 1. 远程测试模式（默认）

测试通过SSH部署到远程机器并运行。

```bash
# 默认远程测试
cd worker/tests
pytest test_gpu_agent.py

# 或显式指定
TEST_MODE=remote pytest test_gpu_agent.py
```

### 2. 本地测试模式

测试在本地机器上运行，不使用SSH/SCP。

```bash
# 本地测试模式
TEST_MODE=local pytest test_gpu_agent.py
```

## 环境变量

### 通用变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TEST_MODE` | `remote` | 测试模式：`local` 或 `remote` |
| `BACKEND_URL` | `http://localhost:8000` | Backend服务器地址 |
| `WORKER_TOKEN` | 自动生成 | Worker注册token |

### 远程模式变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TARGET_HOST` | `ht706@192.168.247.76` | SSH目标主机 |
| `TARGET_IP` | `192.168.247.76` | 目标主机IP |

### GPU配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GPU_COUNT` | `1` | GPU数量 |
| `SELECTED_GPUS` | `0` | 要使用的GPU ID列表（空格分隔） |

## 使用示例

### 本地单GPU测试

```bash
# 测试本地的GPU 0
TEST_MODE=local SELECTED_GPUS="0" pytest test_gpu_agent.py::TestCompleteDeployment -v
```

### 远程测试

```bash
# 测试远程机器
TEST_MODE=remote TARGET_HOST="user@remote-host" pytest test_gpu_agent.py::TestCompleteDeployment -v
```

### 只运行编译测试

```bash
# 只测试本地编译，不部署
pytest test_gpu_agent.py::TestLocalCompilation -v
```

## install.sh GPU参数

install.sh支持 `--gpus` 参数来指定要使用的GPU：

```bash
# 使用GPU 0
sudo ./install.sh install -s http://localhost:8000 -p 9001 -t token123 --gpus "0"

# 使用GPU 0和1
sudo ./install.sh install -s http://localhost:8000 -p 9001 -t token123 --gpus "0 1"

# 不指定，自动检测（单卡使用GPU 0，多卡使用GPU 0和1）
sudo ./install.sh install -s http://localhost:8000 -p 9001 -t token123
```

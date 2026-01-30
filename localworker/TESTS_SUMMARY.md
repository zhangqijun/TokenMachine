# GPU Agent Pytest 测试套件 - 创建完成

## 创建的文件

### 1. 主测试文件
- **worker/tests/test_gpu_agent.py** (600+ 行)
  - 12个测试类，覆盖完整工作流
  - 使用 pytest + paramiko + requests
  - SSH远程执行测试
  - API端点测试

### 2. 配置文件
- **worker/tests/conftest.py** - pytest配置和marker定义
- **worker/pytest.ini** - pytest主配置文件
- **worker/Makefile** - 快捷命令

### 3. 依赖和环境
- **worker/tests/requirements.txt** - Python依赖
- **worker/tests/.env.test.example** - 环境变量模板
- **worker/tests/setup.sh** - 自动化环境设置脚本

### 4. 文档
- **worker/tests/README.md** - 详细测试文档
- **worker/README.md** - 已更新，添加测试章节

## 测试覆盖

| 测试类 | 测试内容 | 测试数量 |
|--------|----------|----------|
| TestLocalCompilation | 本地编译验证（静态链接、GPU过滤） | 6 |
| TestDeployment | 远程部署验证 | 4 |
| TestCleanup | 环境清理 | 1 |
| TestInstallation | 完整安装流程 | 2 |
| TestServiceStatus | 服务状态（进程、端口） | 6 |
| TestAPIEndpoints | API端点（/health、/metrics） | 4 |
| TestConfigFiles | 配置文件验证 | 6 |
| TestHeartbeat | 心跳功能 | 3 |
| TestGPUOccupation | GPU内存占用 | 2 |
| TestSystemdService | systemd服务管理 | 4 |
| TestGPUFilter | GPU过滤功能 | 2 |
| TestE2ERegistration | 端到端注册（需Backend） | 2 |

**总计**: 46个测试用例

## 快速开始

### 方法1: 使用 setup.sh（推荐）

```bash
cd /home/ht706/Documents/TokenMachine/worker/tests
./setup.sh
```

### 方法2: 手动设置

```bash
# 1. 安装依赖
cd /home/ht706/Documents/TokenMachine/worker/tests
pip install -r requirements.txt

# 2. 配置环境
cp .env.test.example .env.test
# 编辑 .env.test 填入你的配置

# 3. 运行测试
cd ..
pytest
```

### 方法3: 使用 Makefile

```bash
cd /home/ht706/Documents/TokenMachine/worker

# 查看所有命令
make help

# 运行所有测试
make test

# 运行快速测试
make test-fast

# 运行特定测试
make test-compile    # 编译测试
make test-deploy     # 部署测试
make test-install    # 安装测试
make test-service    # 服务测试
make test-api        # API测试
make test-heartbeat  # 心跳测试
make test-gpu        # GPU测试
make test-systemd    # systemd测试
make test-filter     # GPU过滤测试
make test-e2e        # 端到端测试

# 生成覆盖率报告
make test-coverage

# 清理测试文件
make clean
```

## 常用命令

```bash
# 运行所有测试
pytest

# 运行特定测试类
pytest tests/test_gpu_agent.py::TestLocalCompilation

# 运行特定测试
pytest tests/test_gpu_agent.py::TestLocalCompilation::test_exporter_exists

# 只运行快速测试（跳过慢速测试）
pytest -m "not slow"

# 并行运行（更快）
pytest -n auto

# 详细输出
pytest -v

# 生成覆盖率报告
pytest --cov=worker --cov-report=html

# 停止在第一个失败
pytest -x

# 调试模式
pytest --pdb
```

## 环境变量

在 `.env.test` 或环境变量中设置：

```bash
TARGET_HOST=ht706@192.168.247.76  # SSH目标
TARGET_IP=192.168.247.76           # 目标IP
BACKEND_URL=http://localhost:8000  # Backend URL
WORKER_TOKEN=test_token_123        # Worker token
```

## 下一步

1. **编译二进制** (如果还没有):
   ```bash
   cd gpu-agent/Exporter
   ./build.sh

   cd ../Receiver
   ./build.sh
   ```

2. **设置测试环境**:
   ```bash
   cd tests
   ./setup.sh
   ```

3. **运行测试**:
   ```bash
   cd ..
   make test
   ```

## 与 bash 测试脚本对比

| 特性 | bash test_all.sh | pytest test_gpu_agent.py |
|------|------------------|-------------------------|
| 并行执行 | ❌ | ✅ (pytest-xdist) |
| fixtures | ❌ | ✅ (自动资源管理) |
| markers | ❌ | ✅ (分组测试) |
| 覆盖率 | ❌ | ✅ (pytest-cov) |
| 断言 | 文本比较 | ✅ (Python assert) |
| 报告 | 自定义 | ✅ (HTML, JSON) |
| CI集成 | 难 | ✅ (标准pytest) |
| 调试 | 难 | ✅ (pdb支持) |
| 扩展性 | 低 | ✅ (插件生态) |

## 注意事项

1. **SSH访问**: 确保能SSH到目标机器
2. **权限**: 某些测试需要sudo权限
3. **Backend**: E2E测试需要Backend运行
4. **时间**: 心跳测试需要~40秒，systemd测试需要~20秒
5. **清理**: 测试失败后可能需要手动清理

## 文件位置

```
worker/
├── tests/
│   ├── test_gpu_agent.py       # 主测试文件
│   ├── conftest.py             # pytest配置
│   ├── requirements.txt        # 依赖
│   ├── setup.sh                # 设置脚本
│   ├── .env.test.example       # 环境模板
│   └── README.md               # 详细文档
├── Makefile                     # 快捷命令
├── pytest.ini                   # pytest配置
└── README.md                    # 已更新
```

## 需要的Python依赖

- pytest >= 7.4.0
- pytest-cov >= 4.1.0
- pytest-xdist >= 3.3.0
- pytest-timeout >= 2.1.0
- requests >= 2.31.0
- paramiko >= 3.3.0
- pyyaml >= 6.0

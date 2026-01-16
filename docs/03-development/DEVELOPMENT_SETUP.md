# TokenMachine 开发环境搭建指南

本文档详细说明如何搭建 TokenMachine 的本地开发环境，包括依赖安装、环境配置和常用命令。

---

## 目录

- [系统要求](#系统要求)
- [环境概览](#环境概览)
- [开发环境安装](#开发环境安装)
- [生产环境部署](#生产环境部署)
- [常用命令](#常用命令)
- [故障排除](#故障排除)

---

## 系统要求

### 硬件要求

**最低配置:**
- CPU: 8核心
- RAM: 32GB
- 存储: 100GB SSD
- GPU: NVIDIA GPU with 24GB VRAM (RTX 3090/4090)

**推荐配置:**
- CPU: 16核心+
- RAM: 64GB+
- 存储: 500GB NVMe SSD
- GPU: 2x+ NVIDIA RTX 3090/4090 with 24GB VRAM each

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / macOS (部分功能受限)
- **Python**: 3.10 或 3.11
- **CUDA**: 11.8 或 12.1+ (GPU 推理)
- **Docker**: 24.0+ (生产环境)
- **Docker Compose**: v2.0+ (生产环境)
- **Git**: 2.40+

---

## 环境概览

TokenMachine 有两种运行环境：

### 开发环境 (Development)

- **用途**: 本地开发和调试
- **特点**:
  - 直接使用 Python 运行，便于调试
  - 支持完整的 GPU 加速
  - 热重载，快速迭代
  - 安装 PyTorch 和 vLLM 等推理引擎

### 生产环境 (Production)

- **用途**: 容器化部署
- **特点**:
  - 使用 Docker Compose 编排
  - 服务隔离，易于管理
  - 适合多服务器集群部署
  - 包含完整的监控栈

---

## 开发环境安装

### 1. 克隆项目

```bash
git clone https://github.com/your-org/TokenMachine.git
cd TokenMachine
```

### 2. 创建 Python 虚拟环境

**使用 pyenv (推荐):**

```bash
# 安装 pyenv (如果没有)
curl https://pyenv.run | bash

# 安装 Python 3.10
pyenv install 3.10.18
pyenv local 3.10.18

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

**使用 conda:**

```bash
conda create -n tokenmachine python=3.10
conda activate tokenmachine
```

### 3. 安装依赖

```bash
# 安装开发依赖 (包含 PyTorch 和 vLLM)
pip install -r requirements-dev.txt
```

**如果网络较慢，可以使用代理:**

```bash
export http_proxy=http://your-proxy:port
export https_proxy=http://your-proxy:port
pip install -r requirements-dev.txt
```

**如果不需要 GPU 支持，可以安装 CPU 版本的 PyTorch:**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt  # 不包含推理引擎
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，修改必要的配置
nano .env
```

**关键配置项:**

```bash
# 数据库连接
DATABASE_URL=postgresql://tokenmachine:your-password@localhost:5432/tokenmachine

# Redis 连接
REDIS_URL=redis://localhost:6379/0

# GPU 配置
GPU_MEMORY_UTILIZATION=0.9
MAX_MODEL_LEN=4096

# 开发模式
ENVIRONMENT=development
DEBUG=true
```

### 5. 初始化数据库

```bash
# 启动 Docker Compose 基础服务 (PostgreSQL + Redis)
docker-compose -f infra/docker/docker-compose.yml up -d postgres redis

# 运行数据库迁移
alembic upgrade head
```

**或直接使用 SQLAlchemy 创建表:**

```bash
python -c "
from sqlalchemy import create_engine
from backend.models.database import Base

engine = create_engine('postgresql://tokenmachine:your-password@localhost:5432/tokenmachine')
Base.metadata.create_all(engine)
print('✅ Database tables created successfully!')
"
```

### 6. 启动开发服务器

```bash
# 启动后端 API
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 在另一个终端启动前端
cd ui
npm install
npm run dev
```

### 7. 验证安装

```bash
# 检查 PyTorch 和 CUDA
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'GPU Count: {torch.cuda.device_count()}')
for i in range(torch.cuda.device_count()):
    print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
"

# 检查 vLLM
python -c "import vllm; print(f'vLLM: {vllm.__version__}')"

# 测试 API
curl http://localhost:8000/health
```

---

## 生产环境部署

生产环境使用 Docker Compose 进行容器化部署。

### 1. 配置代理 (可选)

如果需要通过代理拉取 Docker 镜像：

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf << EOF
[Service]
Environment="HTTP_PROXY=http://your-proxy:port"
Environment="HTTPS_PROXY=http://your-proxy:port"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 2. 配置环境变量

```bash
cp .env.example .env.production
# 编辑 .env.production 设置生产环境配置
```

### 3. 启动所有服务

```bash
cd infra/docker
docker-compose up -d
```

这将启动以下服务：

- **PostgreSQL** (端口 5432) - 数据库
- **Redis** (端口 6379) - 缓存
- **API** (端口 8000) - FastAPI 后端
- **Web** (端口 8081) - React 前端
- **Prometheus** (端口 9091) - 监控
- **Grafana** (端口 3001) - 监控面板

### 4. 查看服务状态

```bash
docker-compose ps

# 查看日志
docker-compose logs -f api
docker-compose logs -f web

# 进入容器
docker-compose exec api bash
docker-compose exec web sh
```

### 5. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷 (慎用！)
docker-compose down -v
```

---

## 常用命令

### 开发环境

```bash
# 运行后端 (开发模式)
uvicorn backend.main:app --reload

# 运行后端 (生产模式)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# 运行测试
pytest tests/unit/
pytest tests/integration/
pytest --cov=backend

# 代码格式化
black backend/
isort backend/

# 代码检查
flake8 backend/
mypy backend/

# 数据库迁移
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# 启动 Worker (手动)
python -m backend.worker.worker --mode worker
```

### 前端开发

```bash
cd ui

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# 运行测试
npm test
npm run test:coverage
```

### Docker 环境

```bash
# 查看所有容器
docker-compose ps

# 重启服务
docker-compose restart api
docker-compose restart web

# 查看日志
docker-compose logs -f --tail=100 api

# 重新构建镜像
docker-compose build api
docker-compose build web

# 进入容器调试
docker-compose exec api bash
docker-compose exec postgres psql -U tokenmachine -d tokenmachine
```

---

## 依赖版本说明

### PyTorch

当前使用 PyTorch 2.8.0 with CUDA 12.8:

```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CPU only
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### vLLM

vLLM 是高性能 LLM 推理引擎，支持 PagedAttention:

```bash
# 最新稳定版
pip install vllm

# 指定版本
pip install vllm==0.10.2
```

**vLLM 支持的模型:**
- LLaMA 系列 (llama, llama2, llama3)
- Mistral 系列
- Mixtral 系列
- Qwen 系列
- ChatGLM 系列
- 其他 HuggingFace 模型

---

## 故障排除

### GPU 相关问题

**问题: `torch.cuda.is_available()` 返回 False**

```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 CUDA 版本
nvcc --version

# 重新安装 PyTorch with CUDA
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**问题: vLLM 加载模型失败**

```bash
# 检查 GPU 内存
nvidia-smi

# 减少 GPU 内存使用
export VLLM_WORKER_MULTIPROC_METHOD=spawn

# 使用更小的模型或调整 batch size
```

### 数据库连接问题

**问题: `psycopg2.OperationalError: could not connect`**

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 启动 PostgreSQL
docker-compose -f infra/docker/docker-compose.yml up -d postgres

# 检查连接
psql -h localhost -U tokenmachine -d tokenmachine
```

### Docker 相关问题

**问题: 容器无法启动**

```bash
# 查看详细日志
docker-compose logs api

# 重新构建镜像
docker-compose build --no-cache api

# 检查端口占用
lsof -i :8000
```

**问题: 网络连接问题**

```bash
# 配置 Docker 代理 (见上文)

# 或使用镜像加速
sudo tee /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
EOF

sudo systemctl restart docker
```

### 依赖安装问题

**问题: pip 安装速度慢**

```bash
# 使用国内镜像
pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用代理
export http_proxy=http://your-proxy:port
export https_proxy=http://your-proxy:port
```

---

## 性能优化建议

### GPU 优化

1. **使用多 GPU**: vLLM 支持张量并行
   ```bash
   vllm serve model_name --tensor-parallel-size 2
   ```

2. **调整 GPU 内存使用率**:
   ```bash
   # 在 .env 中设置
   GPU_MEMORY_UTILIZATION=0.95  # 默认 0.9
   ```

3. **使用量化模型**:
   ```bash
   # AWQ 量化
   vllm serve model_name --quantization awq

   # GPTQ 量化
   vllm serve model_name --quantization gptq
   ```

### 数据库优化

1. **连接池配置**:
   ```python
   # 在 backend/core/database.py 中
   engine = create_engine(
       DATABASE_URL,
       pool_size=20,
       max_overflow=40,
       pool_pre_ping=True
   )
   ```

2. **索引优化**:
   ```sql
   -- 为常用查询添加索引
   CREATE INDEX idx_deployments_status_created ON deployments(status, created_at);
   CREATE INDEX idx_usage_logs_api_created ON usage_logs(api_key_id, created_at);
   ```

---

## 开发工作流

### 典型开发流程

1. **创建功能分支**:
   ```bash
   git checkout -b feature/your-feature
   ```

2. **开发并测试**:
   ```bash
   # 启动开发服务器
   uvicorn backend.main:app --reload

   # 运行测试
   pytest tests/ -v

   # 代码格式化
   black backend/
   isort backend/
   ```

3. **提交代码**:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin feature/your-feature
   ```

4. **创建 Pull Request**

### 调试技巧

1. **使用 Python 调试器**:
   ```python
   import pdb; pdb.set_trace()  # 设置断点
   ```

2. **查看日志**:
   ```bash
   # 开发环境
   tail -f /var/log/tokenmachine/*.log

   # Docker 环境
   docker-compose logs -f api
   ```

3. **性能分析**:
   ```bash
   # 使用 cProfile
   python -m cProfile -o profile.stats your_script.py

   # 使用 Py-Spy
   py-spy record --output profile.svg --pid <PID>
   ```

---

## 参考资源

- [PyTorch 官方文档](https://pytorch.org/docs/stable/index.html)
- [vLLM 官方文档](https://docs.vllm.ai/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/)
- [React 官方文档](https://react.dev/)

---

## 更新日志

- **2026-01-14**: 初始版本，支持 PyTorch 2.8.0 + vLLM 0.10.2
- 支持本地开发和 Docker 部署两种模式

---

**文档版本**: v1.0
**最后更新**: 2026-01-14
**维护者**: TokenMachine Team

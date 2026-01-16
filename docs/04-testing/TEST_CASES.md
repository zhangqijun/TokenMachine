# TokenMachine 测试用例文档

> 基于 MVP 架构设计的完整测试用例规范

**版本**: v1.0
**最后更新**: 2025-01-14
**覆盖目标**: 单元测试 >90%, 集成测试 >70%, 组件测试 >60%

---

## 目录

- [1. 测试策略概述](#1-测试策略概述)
- [2. 后端单元测试用例](#2-后端单元测试用例)
- [3. 后端集成测试用例](#3-后端集成测试用例)
- [4. 前端组件测试用例](#4-前端组件测试用例)
- [5. 性能测试用例](#5-性能测试用例)
- [6. 安全测试用例](#6-安全测试用例)
- [7. 端到端测试用例](#7-端到端测试用例)

---

## 1. 测试策略概述

### 1.1 测试金字塔

```
        /\
       /  \        E2E Tests (5%)
      /____\       - 关键业务流程
     /      \      - 用户场景验证
    /        \
   /          \    Integration Tests (25%)
  /____________\   - API 端点测试
 /              \  - 服务间交互
/                \
/__________________\ Unit Tests (70%)
- 单个函数/类测试
- 业务逻辑验证
- 边界条件测试
```

### 1.2 测试分类

| 类型 | 工具/框架 | 覆盖目标 | 执行频率 |
|-----|----------|---------|---------|
| **单元测试** | pytest | >90% | 每次 CI |
| **集成测试** | pytest | >70% | 每次 CI |
| **组件测试** | vitest | >60% | 每次 CI |
| **性能测试** | pytest-benchmark | 关键路径 | 每周 |
| **E2E 测试** | playwright | 核心流程 | 发布前 |

### 1.3 测试标记体系

```python
@pytest.mark.unit          # 单元测试 (快速、隔离)
@pytest.mark.integration   # 集成测试 (需要数据库)
@pytest.mark.slow          # 慢速测试 (>5s)
@pytest.mark.gpu           # 需要 GPU 硬件
@pytest.mark.auth          # 认证相关
@pytest.mark.security      # 安全测试
@pytest.mark.performance   # 性能测试
```

---

## 2. 后端单元测试用例

### 2.1 核心模块 (core/)

#### 2.1.1 配置管理 (`test_config.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| CONF-001 | 默认配置加载 | 无环境变量 | 默认值正确加载 | P0 |
| CONF-002 | 环境变量覆盖 | 设置 DATABASE_URL | 使用环境变量值 | P0 |
| CONF-003 | 必填项缺失 | 缺少 DATABASE_URL | 抛出 ValidationError | P0 |
| CONF-004 | 无效端口号 | PORT=99999 | 抛出 ValidationError | P1 |
| CONF-005 | GPU 内存利用率 | GPU_MEMORY_UTILIZATION=0.95 | 验证范围 0.1-1.0 | P1 |
| CONF-006 | 模型存储路径 | MODEL_STORAGE_PATH | 验证路径可访问 | P0 |
| CONF-007 | 日志级别 | LOG_LEVEL=debug | 大小写不敏感 | P2 |
| CONF-008 | CORS 配置 | CORS_ORIGINS | 正确解析列表 | P1 |

**示例代码**:
```python
@pytest.mark.unit
def test_config_load_with_env_override(monkeypatch):
    """测试环境变量覆盖默认配置"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:1234/localhost/testdb")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6380")

    settings = get_settings()

    assert settings.database_url == "postgresql://test:1234/localhost/testdb"
    assert settings.redis_url == "redis://localhost:6380"
```

#### 2.1.2 GPU 管理器 (`test_gpu_manager.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| GPU-001 | 初始化 GPU 管理器 | 无 | 成功初始化，检测 GPU 数量 | P0 |
| GPU-002 | 获取单个 GPU 信息 | gpu_id=0 | 返回完整 GPU 信息 | P0 |
| GPU-003 | 获取所有 GPU 信息 | 无 | 返回所有 GPU 列表 | P0 |
| GPU-004 | 查找可用 GPU | required_mb=8000, count=2 | 返回 2 个满足条件的 GPU | P0 |
| GPU-005 | 显存不足 | required_mb=100000 | 返回空列表或报错 | P1 |
| GPU-006 | GPU 兼容性检查 | 通过 | 返回 True | P1 |
| GPU-007 | GPU 兼容性检查失败 | 显存不足 | 返回 False | P1 |
| GPU-008 | GPU 不可用异常 | GPU 进程崩溃 | 抛出 GPUUnavailableError | P0 |
| GPU-009 | 异构 GPU 混合 | NVIDIA + 其他 | 正确识别不同类型 | P2 |
| GPU-010 | GPU 温度监控 | 温度 > 85°C | 标记为警告状态 | P1 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.gpu
def test_find_available_gpus_sufficient_memory(mock_gpu_manager):
    """测试查找显存足够的 GPU"""
    mock_gpu_manager.get_all_gpus.return_value = [
        {"id": "gpu:0", "memory_free_mb": 10000, "name": "RTX 3090"},
        {"id": "gpu:1", "memory_free_mb": 12000, "name": "RTX 3090"},
    ]

    available = mock_gpu_manager.find_available_gpus(required_mb=8000, count=2)

    assert len(available) == 2
    assert "gpu:0" in available
    assert "gpu:1" in available

@pytest.mark.unit
def test_find_available_gpus_insufficient_memory(mock_gpu_manager):
    """测试显存不足场景"""
    mock_gpu_manager.get_all_gpus.return_value = [
        {"id": "gpu:0", "memory_free_mb": 4000, "name": "RTX 3090"},
    ]

    available = mock_gpu_manager.find_available_gpus(required_mb=8000, count=1)

    assert len(available) == 0
```

#### 2.1.3 安全工具 (`test_security.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| SEC-001 | 密码哈希成功 | 有效密码 | 返回哈希值 | P0 |
| SEC-002 | 密码验证成功 | 正确密码 | 返回 True | P0 |
| SEC-003 | 密码验证失败 | 错误密码 | 返回 False | P0 |
| SEC-004 | API Key 生成 | user_id | 返回符合格式的 key | P0 |
| SEC-005 | API Key 前缀提取 | 完整 key | 返回前 8 字符 | P0 |
| SEC-006 | JWT Token 生成 | 有效 payload | 返回有效 token | P0 |
| SEC-007 | JWT Token 验证成功 | 有效 token | 返回 decoded payload | P0 |
| SEC-008 | JWT Token 过期 | 过期 token | 抛出 ExpiredSignatureError | P0 |
| SEC-009 | JWT Token 无效 | 篡改的 token | 抛出 InvalidTokenError | P0 |
| SEC-010 | 密码强度检查 | 弱密码 | 抛出 WeakPasswordError | P1 |

**示例代码**:
```python
@pytest.mark.unit
def test_verify_password_success():
    """测试密码验证成功"""
    password = "SecurePass123!"
    hash_result = hash_password(password)

    assert verify_password(password, hash_result) is True

@pytest.mark.unit
def test_verify_password_failure():
    """测试密码验证失败"""
    password = "SecurePass123!"
    hash_result = hash_password(password)
    wrong_password = "WrongPass456!"

    assert verify_password(wrong_password, hash_result) is False

@pytest.mark.unit
def test_generate_api_key():
    """测试 API Key 生成"""
    api_key = generate_api_key()

    assert api_key.startswith("tm_sk_")
    assert len(api_key) == 40  # tm_sk_ + 32 random chars

    key_hash, key_prefix = hash_api_key(api_key)
    assert key_prefix == api_key[:8]
    assert len(key_hash) == 64  # SHA-256 hex
```

#### 2.1.4 数据库连接 (`test_database.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| DB-001 | 获取数据库会话 | 无 | 返回有效 session | P0 |
| DB-002 | 会话上下文管理 | with 语句 | 正确关闭连接 | P0 |
| DB-003 | 连接池配置 | 正确配置 | 连接复用 | P1 |
| DB-004 | 数据库连接失败 | 无效 URL | 抛出 ConnectionError | P0 |
| DB-005 | 事务回滚 | 异常发生 | 回滚所有更改 | P0 |
| DB-006 | 异步会话 | async/await | 正确处理异步 | P0 |

---

### 2.2 服务层 (services/)

#### 2.2.1 模型服务 (`test_model_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| MS-001 | 创建模型记录 | 有效 model 数据 | 返回 Model 对象 | P0 |
| MS-002 | 下载模型 - HuggingFace | name, source | 状态变为 downloading | P0 |
| MS-003 | 下载进度更新 | progress=50 | 更新 download_progress | P1 |
| MS-004 | 下载成功 | 下载完成 | 状态变为 ready | P0 |
| MS-005 | 下载失败 | 网络错误 | 状态变为 error，记录错误信息 | P0 |
| MS-006 | 获取模型 | model_id | 返回模型详情 | P0 |
| MS-007 | 列出所有模型 | 无 | 返回模型列表 | P0 |
| MS-008 | 按状态筛选 | status="ready" | 只返回 ready 的模型 | P1 |
| MS-009 | 删除模型 | model_id | 软删除或级联删除 | P1 |
| MS-010 | 模型路径验证 | 无效路径 | 抛出 ValidationError | P1 |
| MS-011 | 断点续传 | 中断后重试 | 从断点继续 | P2 |
| MS-012 | 计算模型大小 | 有效路径 | 返回正确大小(GB) | P1 |

**示例代码**:
```python
@pytest.mark.unit
def test_create_model(db_session):
    """测试创建模型记录"""
    model_service = ModelService(db_session)

    model = model_service.create_model(
        name="meta-llama/Llama-3-8B-Instruct",
        version="v1.0",
        source="huggingface",
        category="llm"
    )

    assert model.id is not None
    assert model.name == "meta-llama/Llama-3-8B-Instruct"
    assert model.status == ModelStatus.DOWNLOADING
    assert model.download_progress == 0

@pytest.mark.unit
def test_get_model_not_found(db_session):
    """测试获取不存在的模型"""
    model_service = ModelService(db_session)

    model = model_service.get_model(99999)

    assert model is None
```

#### 2.2.2 部署服务 (`test_deployment_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| DS-001 | 创建部署 | 有效 deployment 数据 | 返回 Deployment 对象 | P0 |
| DS-002 | 部署模型未就绪 | model status=downloading | 抛出 ModelNotReadyError | P0 |
| DS-003 | 部署 GPU 不足 | required > available | 抛出 InsufficientGPUError | P0 |
| DS-004 | 启动 Workers | deployment_id | workers 状态变为 running | P0 |
| DS-005 | 停止部署 | deployment_id | 状态变为 stopped | P0 |
| DS-006 | 停止不存在的部署 | invalid_id | 抛出 DeploymentNotFoundError | P1 |
| DS-007 | 获取部署详情 | deployment_id | 返回完整信息 | P0 |
| DS-008 | 列出部署 | 无 | 返回部署列表 | P0 |
| DS-009 | 按状态筛选 | status="running" | 只返回 running 的 | P1 |
| DS-010 | 更新副本数 | replicas=4 | 成功扩展 | P0 |
| DS-011 | 健康检查 | deployment_id | 返回所有副本状态 | P0 |
| DS-012 | Worker 崩溃处理 | worker 异常退出 | 标记为 error，记录日志 | P0 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_deployment_success(db_session, mock_worker_pool, test_model):
    """测试成功创建部署"""
    # 设置模型为 ready
    test_model.status = ModelStatus.READY

    deployment_service = DeploymentService(db_session, mock_worker_pool)
    mock_worker_pool.create_worker.return_value = MockWorker(id=1)

    deployment = await deployment_service.create_deployment(
        model_id=test_model.id,
        name="test-deployment",
        replicas=2,
        gpu_ids=["gpu:0", "gpu:1"],
        config={"backend": "vllm"}
    )

    assert deployment.status == DeploymentStatus.STARTING
    assert deployment.replicas == 2
    mock_worker_pool.create_worker.assert_called twice()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_deployment_model_not_ready(db_session, mock_worker_pool, test_model):
    """测试模型未就绪时创建部署"""
    test_model.status = ModelStatus.DOWNLOADING

    deployment_service = DeploymentService(db_session, mock_worker_pool)

    with pytest.raises(ModelNotReadyError):
        await deployment_service.create_deployment(
            model_id=test_model.id,
            name="test-deployment",
            replicas=1,
            gpu_ids=["gpu:0"],
            config={}
        )
```

#### 2.2.3 GPU 服务 (`test_gpu_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| GS-001 | 获取所有 GPU 状态 | 无 | 返回 GPU 列表 | P0 |
| GS-002 | 分配 GPU | required_mb=8000 | 返回可用 GPU ID | P0 |
| GS-003 | GPU 已分配 | deployment_id | 更新 GPU 状态为 in_use | P0 |
| GS-004 | 释放 GPU | deployment_id | 状态变为 available | P0 |
| GS-005 | GPU 监控数据 | 无 | 返回实时指标 | P0 |
| GS-006 | GPU 温度警告 | temp > 85°C | 标记为警告 | P1 |
| GS-007 | GPU 利用率统计 | 无 | 返回平均利用率 | P2 |
| GS-008 | 异构 GPU 分配 | NVIDIA + 昇腾 | 正确分配 | P2 |

---

### 2.3 Worker 层 (workers/)

#### 2.3.1 Worker Pool (`test_worker_pool.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| WP-001 | 创建 Worker | 有效参数 | 返回 Worker 对象 | P0 |
| WP-002 | Worker 启动成功 | worker | 状态变为 running | P0 |
| WP-003 | Worker 启动失败 | 无效配置 | 抛出 WorkerStartupError | P0 |
| WP-004 | Worker 健康检查 | healthy worker | 返回 True | P0 |
| WP-005 | Worker 不健康 | crashed worker | 返回 False | P0 |
| WP-006 | 停止所有 Workers | deployment_id | 所有 workers 停止 | P0 |
| WP-007 | 负载均衡 | 3 个 workers | 轮询返回不同 endpoint | P0 |
| WP-008 | Worker 自动重启 | worker 崩溃 | 自动重启 (可配置) | P1 |
| WP-009 | Worker 端口冲突 | 端口被占用 | 自动选择新端口 | P1 |
| WP-010 | 获取 Worker 统计 | deployment_id | 返回请求数、错误数 | P2 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_worker_success(mock_gpu_manager):
    """测试成功创建 Worker"""
    pool = VLLMWorkerPool(mock_gpu_manager)

    worker = await pool.create_worker(
        deployment_id=1,
        model_path="/models/llama-3-8b",
        model_name="llama-3-8b-prod",
        gpu_id="gpu:0",
        port=8001,
        config={"gpu_memory_utilization": 0.9}
    )

    assert worker.deployment_id == 1
    assert worker.is_healthy() is True
    assert 8001 in pool.get_workers(1)

@pytest.mark.unit
def test_load_balancing_round_robin():
    """测试轮询负载均衡"""
    pool = VLLMWorkerPool()
    pool.workers[1] = [
        MockWorker(endpoint="http://localhost:8001"),
        MockWorker(endpoint="http://localhost:8002"),
        MockWorker(endpoint="http://localhost:8003"),
    ]

    endpoint1 = pool.get_worker_endpoint(1)
    endpoint2 = pool.get_worker_endpoint(1)
    endpoint3 = pool.get_worker_endpoint(1)
    endpoint4 = pool.get_worker_endpoint(1)  # 回到第一个

    assert endpoint1 == "http://localhost:8001"
    assert endpoint2 == "http://localhost:8002"
    assert endpoint3 == "http://localhost:8003"
    assert endpoint4 == "http://localhost:8001"
```

#### 2.3.2 vLLM Worker (`test_vllm_worker.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| VW-001 | 启动 vLLM 进程 | 有效配置 | 进程启动成功 | P0 |
| VW-002 | 等待服务就绪 | timeout=300 | 300s 内返回 True | P0 |
| VW-003 | 启动超时 | 进程卡死 | 抛出 TimeoutError | P0 |
| VW-004 | 健康检查 | /health 返回 200 | 返回 True | P0 |
| VW-005 | 健康检查失败 | /health 返回 500 | 返回 False | P0 |
| VW-006 | 优雅停止 | worker 调用 stop | 发送 SIGTERM | P0 |
| VW-007 | 强制停止 | timeout 过期 | 发送 SIGKILL | P0 |
| VW-008 | 环境变量设置 | CUDA_VISIBLE_DEVICES | 正确设置 GPU | P0 |
| VW-009 | 命令行参数 | tensor_parallel_size=2 | 参数正确传递 | P1 |
| VW-010 | 日志输出 | stdout/stderr | 日志正确捕获 | P2 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_worker_start_success():
    """测试 Worker 启动成功"""
    worker = VLLMWorker(
        deployment_id=1,
        model_path="/models/llama-3-8b",
        model_name="llama-3-8b-prod",
        gpu_id="gpu:0",
        port=8001,
        config={"gpu_memory_utilization": 0.9, "max_model_len": 4096}
    )

    await worker.start()

    assert worker.process is not None
    assert worker.is_healthy() is True

@pytest.mark.unit
@pytest.mark.asyncio
async def test_worker_start_timeout():
    """测试 Worker 启动超时"""
    worker = VLLMWorker(
        deployment_id=1,
        model_path="/invalid/path",
        model_name="invalid",
        gpu_id="gpu:0",
        port=8001,
        config={}
    )

    with pytest.raises(TimeoutError):
        await worker.start(timeout=5)
```

---

### 2.4 API 层 (api/)

#### 2.4.1 API Dependencies (`test_api_deps.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| DEP-001 | API Key 认证成功 | 有效 Bearer token | 返回 API Key 对象 | P0 |
| DEP-002 | API Key 不存在 | 无效 key | 抛出 401 Unauthorized | P0 |
| DEP-003 | API Key 已过期 | 过期 key | 抛出 401 Unauthorized | P0 |
| DEP-004 | API Key 已撤销 | is_active=False | 抛出 401 Unauthorized | P0 |
| DEP-005 | Authorization 缺失 | 无 header | 抛出 401 Unauthorized | P0 |
| DEP-006 | Authorization 格式错误 | "Bearer" 格式错误 | 抛出 401 Unauthorized | P1 |
| DEP-007 | 获取 DB 会话 | 无 | 返回有效 session | P0 |
| DEP-008 | 管理员权限验证 | admin user | 通过验证 | P0 |
| DEP-009 | 管理员权限不足 | normal user | 抛出 403 Forbidden | P0 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.auth
async def test_verify_api_key_success(test_api_key):
    """测试 API Key 认证成功"""
    api_key_record, raw_key = test_api_key

    result = await verify_api_key_auth(f"Bearer {raw_key}")

    assert result.id == api_key_record.id
    assert result.is_active is True

@pytest.mark.unit
@pytest.mark.auth
async def test_verify_api_key_invalid():
    """测试无效 API Key"""
    with pytest.raises(HTTPException) as exc:
        await verify_api_key_auth("Bearer invalid_key_12345")

    assert exc.value.status_code == 401
    assert "Invalid API key" in exc.value.detail

@pytest.mark.unit
@pytest.mark.auth
async def test_verify_api_key_expired(db_session):
    """测试过期 API Key"""
    api_key = APIKey(
        key_hash=hash_api_key("tm_sk_expired")[0],
        key_prefix="tm_sk_ex",
        user_id=1,
        name="Expired Key",
        expires_at=datetime.now() - timedelta(days=1),
        is_active=True
    )
    db_session.add(api_key)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await verify_api_key_auth("Bearer tm_sk_expired1234567890123456789012345678")

    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()
```

---

### 2.5 监控层 (monitoring/)

#### 2.5.1 Prometheus 指标 (`test_metrics.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| MET-001 | API 请求计数 | endpoint="/v1/chat" | counter +1 | P0 |
| MET-002 | API 延迟记录 | latency_ms=500 | histogram 记录 | P0 |
| MET-003 | Token 计数 | input=10, output=20 | counter 正确累加 | P0 |
| MET-004 | GPU 利用率 | gpu_id="gpu:0", percent=75 | gauge 更新 | P0 |
| MET-005 | GPU 温度 | temp=80 | gauge 更新 | P1 |
| MET-006 | Worker 状态 | status=running | gauge=1 | P0 |
| MET-007 | 活跃请求数 | active=5 | gauge=5 | P1 |
| MET-008 | 系统 CPU | percent=60 | gauge 更新 | P2 |
| MET-009 | 系统内存 | used_mb=4096 | gauge 更新 | P2 |

**示例代码**:
```python
@pytest.mark.unit
def test_api_request_metrics():
    """测试 API 请求指标"""
    api_requests_total.labels(
        method="POST",
        endpoint="/v1/chat/completions",
        status="200"
    ).inc()

    # 验证指标
    metric = api_requests_total.collect()
    assert len(metric) > 0

@pytest.mark.unit
def test_model_tokens_metrics():
    """测试模型 Token 指标"""
    model_tokens_total.labels(
        model_name="llama-3-8b-prod",
        token_type="input"
    ).inc(100)

    model_tokens_total.labels(
        model_name="llama-3-8b-prod",
        token_type="output"
    ).inc(50)

    # 验证指标
    metric = model_tokens_total.collect()
    sample = metric[0].samples[0]
    assert sample.value == 100  # input tokens
```

---

### 2.6 数据模型 (models/)

#### 2.6.1 SQLAlchemy 模型 (`test_database_models.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| DM-001 | 创建用户 | 有效数据 | User 对象创建成功 | P0 |
| DM-002 | 用户唯一性 | 重复 username | 抛出 IntegrityError | P0 |
| DM-003 | 模型部署关系 | deployment.model_id | 正确关联 Model | P0 |
| DM-004 | API Key 关联 | api_key.user_id | 正确关联 User | P0 |
| DM-005 | 级联删除 | 删除 Model | 关联的 Deployment 删除 | P0 |
| DM-006 | 使用日志关联 | usage_log.api_key_id | 正确关联 API Key | P0 |
| DM-007 | GPU 状态更新 | deployment_id | GPU 正确分配/释放 | P0 |
| DM-008 | 时间戳自动更新 | 更新记录 | updated_at 自动更新 | P1 |
| DM-009 | 软删除 | 删除模型 | is_deleted=True | P2 |

**示例代码**:
```python
@pytest.mark.integration
def test_user_deployment_relationship(db_session, test_user, test_model):
    """测试用户-部署关系"""
    deployment = Deployment(
        model_id=test_model.id,
        name="test-deployment",
        status=DeploymentStatus.RUNNING,
        replicas=1,
        gpu_ids=["gpu:0"],
        backend="vllm"
    )
    db_session.add(deployment)
    db_session.commit()

    # 通过 user 获取部署 (假设有 user.deployments 关系)
    # 通过 deployment 获取 model
    assert deployment.model.id == test_model.id
    assert deployment.model.name == test_model.name
```

---

## 3. 后端集成测试用例

### 3.1 OpenAI 兼容 API

#### 3.1.1 Chat Completions API (`test_chat_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| CHAT-001 | 基础对话 | 有效 messages | 返回 assistant 消息 | P0 |
| CHAT-002 | 流式输出 | stream=true | 返回 SSE 流 | P0 |
| CHAT-003 | 多轮对话 | 上下文 messages | 正确理解上下文 | P0 |
| CHAT-004 | Temperature 参数 | temperature=0.7 | 影响输出随机性 | P1 |
| CHAT-005 | Max tokens | max_tokens=100 | 限制输出长度 | P1 |
| CHAT-006 | 模型不存在 | model=invalid | 返回 404 | P0 |
| CHAT-007 | API Key 无效 | 无效 key | 返回 401 | P0 |
| CHAT-008 | 空消息 | messages=[] | 返回 400 | P1 |
| CHAT-009 | 超长上下文 | 超过 model_len | 返回 400 或截断 | P1 |
| CHAT-010 | 并发请求 | 10 个并发 | 全部成功，无死锁 | P0 |
| CHAT-011 | Token 统计 | 完成请求 | 返回 usage 信息 | P0 |
| CHAT-012 | 系统提示词 | system message | 正确应用系统提示 | P1 |

**示例代码**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_completion_success(async_client, test_api_key, test_deployment):
    """测试聊天补全成功"""
    api_key, raw_key = test_api_key

    response = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "model": test_deployment.name,
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert "id" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "message" in data["choices"][0]
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert "usage" in data
    assert "total_tokens" in data["usage"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_completion_streaming(async_client, test_api_key, test_deployment):
    """测试流式输出"""
    api_key, raw_key = test_api_key

    response = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "model": test_deployment.name,
            "messages": [{"role": "user", "content": "Count to 10"}],
            "stream": True
        }
    )

    assert response.status_code == 200

    # 验证 SSE 格式
    content = response.text
    assert "data:" in content
    assert "[DONE]" in content

    # 解析 SSE 流
    lines = content.split("\n")
    data_lines = [l for l in lines if l.startswith("data: ") and l != "data: [DONE]"]
    assert len(data_lines) > 0
```

#### 3.1.2 Models API (`test_models_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| MODEL-001 | 列出模型 | GET /v1/models | 返回模型列表 | P0 |
| MODEL-002 | 模型对象格式 | - | 符合 OpenAI 格式 | P0 |
| MODEL-003 | 只返回 running | - | 只包含运行中的部署 | P1 |
| MODEL-004 | 分页支持 | limit=10 | 正确分页 | P2 |

**示例代码**:
```python
@pytest.mark.integration
async def test_list_models(async_client, test_api_key, test_deployment):
    """测试列出模型"""
    api_key, raw_key = test_api_key

    response = await async_client.get(
        "/v1/models",
        headers={"Authorization": f"Bearer {raw_key}"}
    )

    assert response.status_code == 200

    data = response.json()
    assert data["object"] == "list"
    assert "data" in data
    assert len(data["data"]) > 0

    model = data["data"][0]
    assert model["id"] == test_deployment.name
    assert model["object"] == "model"
    assert "created" in model
```

---

### 3.2 Admin API

#### 3.2.1 模型管理 API (`test_admin_models_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| ADM-001 | 下载模型 | POST /admin/models | 返回 model_id | P0 |
| ADM-002 | 列出模型 | GET /admin/models | 返回模型列表 | P0 |
| ADM-003 | 获取模型详情 | GET /admin/models/{id} | 返回完整信息 | P0 |
| ADM-004 | 删除模型 | DELETE /admin/models/{id} | 成功删除 | P1 |
| ADM-005 | 重复下载 | 已存在的模型 | 返回已存在或更新 | P1 |
| ADM-006 | 无效源 | source="invalid" | 返回 400 | P1 |

#### 3.2.2 部署管理 API (`test_admin_deployments_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| DEP-101 | 创建部署 | POST /admin/deployments | 返回 deployment_id | P0 |
| DEP-102 | 列出部署 | GET /admin/deployments | 返回部署列表 | P0 |
| DEP-103 | 获取部署详情 | GET /admin/deployments/{id} | 返回完整信息 | P0 |
| DEP-104 | 停止部署 | DELETE /admin/deployments/{id} | 状态变为 stopped | P0 |
| DEP-105 | 扩容 | PATCH /admin/deployments/{id} | 副本数更新 | P0 |
| DEP-106 | 模型未就绪 | model_id not ready | 返回 400 | P0 |
| DEP-107 | GPU 不足 | 超过可用 GPU | 返回 400 | P0 |

#### 3.2.3 API Key 管理 API (`test_admin_api_keys_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| KEY-001 | 创建 API Key | POST /admin/api-keys | 返回完整 key | P0 |
| KEY-002 | 列出 API Keys | GET /admin/api-keys | 返回 key 列表 | P0 |
| KEY-003 | 撤销 API Key | DELETE /admin/api-keys/{id} | is_active=False | P0 |
| KEY-004 | 设置配额 | quota_tokens | 更新配额 | P1 |
| KEY-005 | API Key 只显示一次 | 创建后再次查询 | 不返回完整 key | P0 |

**示例代码**:
```python
@pytest.mark.integration
@pytest.mark.auth
async def test_create_api_key(async_client, admin_user):
    """测试创建 API Key"""
    # 先登录获取 token
    login_response = await async_client.post(
        "/api/v1/admin/login",
        json={"username": admin_user.username, "password": "password"}
    )
    token = login_response.json()["access_token"]

    # 创建 API Key
    response = await async_client.post(
        "/api/v1/admin/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Key",
            "user_id": admin_user.id,
            "quota_tokens": 1000000
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert "key" in data
    assert data["key"].startswith("tm_sk_")
    assert len(data["key"]) == 40
    assert data["key_prefix"] == data["key"][:8]

    # 验证 key 只返回一次
    detail_response = await async_client.get(
        f"/api/v1/admin/api-keys/{data['id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    detail_data = detail_response.json()
    assert "key" not in detail_data
    assert "key_prefix" in detail_data
```

#### 3.2.4 GPU 管理 API (`test_admin_gpus_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| GPU-101 | 获取 GPU 状态 | GET /admin/gpus | 返回 GPU 列表 | P0 |
| GPU-102 | GPU 实时指标 | - | 包含利用率、温度、显存 | P0 |
| GPU-103 | GPU 分配状态 | - | 显示当前 deployment_id | P0 |

---

## 4. 前端组件测试用例

### 4.1 基础组件 (`test_components.py`)

| 用例 ID | 组件 | 测试场景 | 预期结果 | 优先级 |
|--------|-----|---------|---------|--------|
| UI-001 | MainLayout | 渲染布局 | 显示导航栏、内容区 | P0 |
| UI-002 | MainLayout | 菜单导航 | 点击路由正确跳转 | P0 |
| UI-003 | Dashboard | 显示统计卡片 | API 调用量、Token 数 | P0 |
| UI-004 | Dashboard | 图表渲染 | ECharts 图表正确显示 | P1 |
| UI-005 | Deployments | 列表渲染 | 显示部署列表 | P0 |
| UI-006 | Deployments | 状态显示 | 正确显示 running/stopped | P0 |
| UI-007 | Deployments | 操作按钮 | 停止/启动按钮功能 | P0 |
| UI-008 | ModelCard | 模型信息显示 | 显示名称、版本、状态 | P0 |
| UI-009 | ApiKeyList | Key 列表 | 显示所有 keys | P0 |
| UI-010 | ApiKeyList | 复制功能 | 点击复制到剪贴板 | P1 |

**示例代码**:
```typescript
// ui/src/components/__tests__/Dashboard.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Dashboard } from '@/pages/Dashboard'

describe('Dashboard', () => {
  it('renders statistics cards', () => {
    render(<Dashboard />)

    expect(screen.getByText('API 调用量')).toBeInTheDocument()
    expect(screen.getByText('Token 消耗')).toBeInTheDocument()
    expect(screen.getByText('GPU 利用率')).toBeInTheDocument()
    expect(screen.getByText('运行模型')).toBeInTheDocument()
  })

  it('displays correct statistics', async () => {
    const mockStats = {
      apiCalls: 125430,
      tokensUsed: 12500000,
      gpuUtilization: 78.5,
      runningModels: 8
    }

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockStats)
      })
    ) as any

    render(<Dashboard />)

    expect(await screen.findByText('125,430')).toBeInTheDocument()
    expect(screen.getByText('12.5M')).toBeInTheDocument()
  })
})
```

---

### 4.2 页面组件 (`test_pages.py`)

| 用例 ID | 页面 | 测试场景 | 预期结果 | 优先级 |
|--------|-----|---------|---------|--------|
| PAGE-001 | LoginPage | 登录成功 | 跳转到 Dashboard | P0 |
| PAGE-002 | LoginPage | 登录失败 | 显示错误提示 | P0 |
| PAGE-003 | ModelsPage | 显示模型列表 | 列出所有模型 | P0 |
| PAGE-004 | ModelsPage | 下载模型 | 弹出下载对话框 | P0 |
| PAGE-005 | DeploymentsPage | 创建部署向导 | 显示步骤条 | P0 |
| PAGE-006 | DeploymentsPage | 配置参数 | 表单验证正确 | P0 |
| PAGE-007 | DeploymentsPage | 确认部署 | 显示配置摘要 | P0 |
| PAGE-008 | MonitoringPage | 实时监控 | 显示实时图表 | P1 |
| PAGE-009 | SettingsPage | 修改配置 | 保存成功 | P2 |

---

### 4.3 状态管理 (`test_stores.py`)

| 用例 ID | Store | 测试场景 | 预期结果 | 优先级 |
|--------|-------|---------|---------|--------|
| STORE-001 | authStore | 登录 | token 正确保存 | P0 |
| STORE-002 | authStore | 登出 | 清除 token | P0 |
| STORE-003 | authStore | token 过期 | 自动跳转登录 | P0 |
| STORE-004 | modelStore | 获取模型列表 | models 状态更新 | P0 |
| STORE-005 | modelStore | 下载模型 | status 变为 downloading | P0 |
| STORE-006 | deploymentStore | 创建部署 | deployments 列表更新 | P0 |
| STORE-007 | deploymentStore | 停止部署 | status 变为 stopped | P0 |

**示例代码**:
```typescript
// ui/src/store/__tests__/authStore.test.ts
import { describe, it, expect } from 'vitest'
import { useAuthStore } from '@/store/authStore'

describe('authStore', () => {
  it('sets token on login', () => {
    const { login, token } = useAuthStore.getState()

    login('test_token_123')

    expect(useAuthStore.getState().token).toBe('test_token_123')
    expect(localStorage.getItem('token')).toBe('test_token_123')
  })

  it('clears token on logout', () => {
    const { logout } = useAuthStore.getState()

    logout()

    expect(useAuthStore.getState().token).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('checks authentication status', () => {
    useAuthStore.getState().login('valid_token')

    expect(useAuthStore.getState().isAuthenticated()).toBe(true)
  })
})
```

---

### 4.4 API 集成 (`test_api_client.py`)

| 用例 ID | 客户端 | 测试场景 | 预期结果 | 优先级 |
|--------|-------|---------|---------|--------|
| API-001 | apiClient | 请求拦截 | 添加 Authorization header | P0 |
| API-002 | apiClient | 响应拦截 | 401 自动跳转登录 | P0 |
| API-003 | apiClient | 错误处理 | 显示错误提示 | P0 |
| API-004 | modelsApi | 获取模型列表 | 返回 Model[] | P0 |
| API-005 | deploymentsApi | 创建部署 | 返回 Deployment | P0 |

---

## 5. 性能测试用例

### 5.1 API 性能 (`test_api_performance.py`)

| 用例 ID | 测试场景 | 指标 | 目标 | 优先级 |
|--------|---------|------|------|--------|
| PERF-001 | 单个聊天请求 | 延迟 (P50) | < 500ms | P0 |
| PERF-002 | 单个聊天请求 | 延迟 (P99) | < 2000ms | P0 |
| PERF-003 | 并发聊天 | 100 并发 | 全部成功 | P0 |
| PERF-004 | 吞吐量 | requests/min | > 1000 | P0 |
| PERF-005 | 流式输出 | 首字延迟 (TTFT) | < 500ms | P0 |
| PERF-006 | 长上下文 | 4K tokens | 延迟 < 5s | P1 |
| PERF-007 | 批量请求 | 10 batch | 提升吞吐量 | P1 |
| PERF-008 | 模型切换 | 不同模型轮换 | 无明显延迟 | P2 |

**示例代码**:
```python
@pytest.mark.performance
def test_chat_completion_latency(benchmark, async_client, test_api_key, test_deployment):
    """测试聊天补全延迟"""
    api_key, raw_key = test_api_key

    async def make_request():
        response = await async_client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={
                "model": test_deployment.name,
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        return response

    result = benchmark(make_request)

    assert result.status_code == 200
    # P50 延迟应 < 500ms
    # benchmark 统计会自动计算百分位数

@pytest.mark.performance
@pytest.mark.slow
def test_concurrent_requests(async_client, test_api_key, test_deployment):
    """测试并发请求"""
    import asyncio

    api_key, raw_key = test_api_key

    async def make_request(i):
        response = await async_client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={
                "model": test_deployment.name,
                "messages": [{"role": "user", "content": f"Request {i}"}]
            }
        )
        return response

    # 100 个并发请求
    results = await asyncio.gather(*[make_request(i) for i in range(100)])

    success_count = sum(1 for r in results if r.status_code == 200)
    assert success_count == 100
```

---

### 5.2 数据库性能 (`test_db_performance.py`)

| 用例 ID | 测试场景 | 操作 | 目标 | 优先级 |
|--------|---------|------|------|--------|
| DB-PERF-001 | 查询性能 | 获取 API Key | < 10ms | P0 |
| DB-PERF-002 | 写入性能 | 插入使用日志 | < 50ms | P1 |
| DB-PERF-003 | 连接池 | 100 并发连接 | 无等待 | P1 |
| DB-PERF-004 | 索引效果 | 按时间查询 | < 100ms | P2 |

---

### 5.3 GPU 性能 (`test_gpu_performance.py`)

| 用例 ID | 测试场景 | 指标 | 目标 | 优先级 |
|--------|---------|------|------|--------|
| GPU-PERF-001 | GPU 利用率 | 推理时 | > 80% | P0 |
| GPU-PERF-002 | 显存占用 | 加载模型后 | 预估值 ±10% | P0 |
| GPU-PERF-003 | 批处理 | batch_size=32 | 提升吞吐量 >2x | P1 |
| GPU-PERF-004 | 多 GPU | 2 GPU | 线性扩展 | P2 |

---

## 6. 安全测试用例

### 6.1 认证授权 (`test_auth_security.py`)

| 用例 ID | 测试场景 | 攻击向量 | 预期防御 | 优先级 |
|--------|---------|---------|---------|--------|
| SEC-AUTH-001 | SQL 注入 | username="admin' OR '1'='1" | 登录失败 | P0 |
| SEC-AUTH-002 | 暴力破解 | 连续错误密码 | 账户锁定 | P1 |
| SEC-AUTH-003 | Token 篡改 | 修改 JWT payload | 验证失败 | P0 |
| SEC-AUTH-004 | Token 重放 | 过期 token | 拒绝访问 | P0 |
| SEC-AUTH-005 | 权限提升 | normal user 访问 admin | 返回 403 | P0 |
| SEC-AUTH-006 | 会话固定 | 重用 session ID | 生成新 session | P1 |

**示例代码**:
```python
@pytest.mark.integration
@pytest.mark.security
async def test_sql_injection_protection(async_client):
    """测试 SQL 注入防护"""
    response = await async_client.post(
        "/api/v1/admin/login",
        json={
            "username": "admin' OR '1'='1' --",
            "password": "anything"
        }
    )

    # 应该登录失败
    assert response.status_code == 401

@pytest.mark.integration
@pytest.mark.security
async def test_permission_normal_user_access_admin(async_client, normal_user_api_key):
    """测试普通用户无权访问 admin API"""
    response = await async_client.get(
        "/api/v1/admin/models",
        headers={"Authorization": f"Bearer {normal_user_api_key}"}
    )

    assert response.status_code == 403
```

---

### 6.2 输入验证 (`test_input_validation.py`)

| 用例 ID | 测试场景 | 恶意输入 | 预期防御 | 优先级 |
|--------|---------|---------|---------|--------|
| SEC-INP-001 | XSS 攻击 | message="<script>alert(1)</script>" | 转义或拒绝 | P0 |
| SEC-INP-002 | 路径遍历 | model_path="../../../etc/passwd" | 拒绝 | P0 |
| SEC-INP-003 | 超长输入 | 1MB 消息 | 拒绝或截断 | P1 |
| SEC-INP-004 | 特殊字符 | model="\x00\x01\x02" | 拒绝 | P1 |
| SEC-INP-005 | JSON 炸弹 | 嵌套 1000 层 | 解析限制 | P2 |

---

### 6.3 API 安全 (`test_api_security.py`)

| 用例 ID | 测试场景 | 攻击向量 | 预期防御 | 优先级 |
|--------|---------|---------|---------|--------|
| SEC-API-001 | 缺少认证 | 无 Authorization header | 401 | P0 |
| SEC-API-002 | 无效格式 | Authorization="Invalid token" | 401 | P0 |
| SEC-API-003 | CORS | Origin=evil.com | 拒绝或预检失败 | P0 |
| SEC-API-004 | 速率限制 | 100 req/s | 429 Too Many Requests | P1 |
| SEC-API-005 | 参数污染 | ?id=1&id=2 | 使用第一个或拒绝 | P2 |

---

## 7. 端到端测试用例

### 7.1 核心业务流程

#### E2E-001: 完整的模型部署和使用流程

| 步骤 | 操作 | 验证点 |
|-----|------|-------|
| 1 | 管理员登录 | 登录成功，跳转到 Dashboard |
| 2 | 下载模型 | 模型列表中显示 downloading |
| 3 | 等待模型就绪 | 状态变为 ready |
| 4 | 创建部署 | 填写配置，提交成功 |
| 5 | 等待部署启动 | 状态变为 running |
| 6 | 创建 API Key | 获得完整的 API Key |
| 7 | 使用 API 调用 | Chat API 返回正常响应 |
| 8 | 查看使用统计 | Dashboard 显示调用量 +1 |

**示例代码**:
```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_deployment_workflow(browser):
    """端到端测试：完整部署流程"""

    # 1. 管理员登录
    await browser.goto("http://localhost:3000/login")
    await browser.fill("input[name='username']", "admin")
    await browser.fill("input[name='password']", "admin123")
    await browser.click("button[type='submit']")
    await browser.wait_for_url("http://localhost:3000/dashboard")

    # 2. 下载模型
    await browser.click("text=模型管理")
    await browser.click("button:has-text('下载模型')")
    await browser.fill("input[name='model_name']", "meta-llama/Llama-3-8B-Instruct")
    await browser.select_option("select[name='source']", "huggingface")
    await browser.click("button:has-text('开始下载')")

    # 3. 等待模型就绪
    await browser.wait_for_selector(".model-status.ready", timeout=300000)  # 5 分钟

    # 4. 创建部署
    await browser.click("button:has-text('部署')")
    await browser.fill("input[name='deployment_name']", "llama-3-8b-prod")
    await browser.fill("input[name='replicas']", "2")
    await browser.click("button:has-text('创建部署')")

    # 5. 等待部署运行
    await browser.wait_for_selector(".deployment-status.running", timeout=300000)

    # 6. 创建 API Key
    await browser.click("text=API Keys")
    await browser.click("button:has-text('创建 API Key')")
    await browser.fill("input[name='key_name']", "Test Key")
    await browser.click("button:has-text('创建')")
    api_key = await browser.text_content(".api-key-value")

    # 7. 使用 API 调用
    response = requests.post(
        "http://localhost:8000/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "llama-3-8b-prod",
            "messages": [{"role": "user", "content": "Hello!"}]
        }
    )
    assert response.status_code == 200
    assert "assistant" in response.json()["choices"][0]["message"]["role"]

    # 8. 验证统计更新
    await browser.goto("http://localhost:3000/dashboard")
    await browser.wait_for_selector("text=1", timeout=10000)  # 调用量更新
```

#### E2E-002: 模型更新和灰度发布

| 步骤 | 操作 | 验证点 |
|-----|------|-------|
| 1 | 下载新版本模型 | v2.0 下载成功 |
| 2 | 创建新部署 | v2.0 部署成功 |
| 3 | 设置流量权重 | v1.0: 80%, v2.0: 20% |
| 4 | 验证流量分配 | 请求按比例路由 |
| 5 | 逐步切换 | v2.0: 100% |
| 6 | 停止旧版本 | v1.0 状态 stopped |

---

#### E2E-003: 错误恢复流程

| 步骤 | 操作 | 验证点 |
|-----|------|-------|
| 1 | 部署模型 | 部署成功 |
| 2 | 模拟 Worker 崩溃 | kill worker 进程 |
| 3 | 观察自动恢复 | Worker 自动重启 |
| 4 | 验证服务可用 | API 仍然正常 |
| 5 | 查看错误日志 | 日志记录崩溃事件 |

---

## 8. 测试数据管理

### 8.1 Fixtures

```python
# tests/conftest.py

@pytest.fixture
async def test_user(db_session):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("password123"),
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
async def test_admin_user(db_session):
    """创建管理员用户"""
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        is_admin=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin

@pytest.fixture
async def test_api_key(db_session, test_user):
    """创建测试 API Key"""
    raw_key = generate_api_key()
    key_hash, key_prefix = hash_api_key(raw_key)

    api_key = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        user_id=test_user.id,
        name="Test API Key",
        quota_tokens=1000000,
        is_active=True
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    return api_key, raw_key

@pytest.fixture
async def test_model(db_session):
    """创建测试模型"""
    model = Model(
        name="test-model",
        version="v1.0",
        source="huggingface",
        category="llm",
        status=ModelStatus.READY,
        path="/models/test-model",
        size_gb=1.0
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model

@pytest.fixture
async def test_deployment(db_session, test_model):
    """创建测试部署"""
    deployment = Deployment(
        model_id=test_model.id,
        name="test-deployment",
        status=DeploymentStatus.RUNNING,
        replicas=1,
        gpu_ids=["gpu:0"],
        backend="vllm",
        config={"gpu_memory_utilization": 0.9}
    )
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)
    return deployment

@pytest.fixture
def mock_gpu_manager():
    """Mock GPU Manager"""
    with patch("backend.core.gpu.GPUManager") as mock:
        mock_instance = Mock()
        mock_instance.get_all_gpus.return_value = [
            {
                "id": "gpu:0",
                "name": "NVIDIA RTX 3090",
                "memory_total_mb": 24576,
                "memory_free_mb": 24576,
                "utilization_percent": 0.0,
                "temperature_celsius": 30.0
            }
        ]
        mock_instance.find_available_gpus.return_value = ["gpu:0"]
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_worker_pool():
    """Mock Worker Pool"""
    with patch("backend.workers.worker_pool.VLLMWorkerPool") as mock:
        mock_instance = Mock()
        mock_instance.create_worker = AsyncMock(return_value=MockWorker())
        mock_instance.stop_deployment_workers = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance
```

---

## 9. 测试执行计划

### 9.1 CI/CD 集成

```yaml
# .github/workflows/test.yml

name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements.txt
      - name: Run unit tests
        run: pytest -m unit --cov=backend --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements.txt
      - name: Run integration tests
        run: pytest -m integration
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd ui && npm install
      - name: Run tests
        run: cd ui && npm run test:run
      - name: Upload coverage
        run: cd ui && npm run test:coverage

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose up -d
      - name: Run E2E tests
        run: pytest -m e2e
      - name: Cleanup
        run: docker-compose down
```

---

### 9.2 本地测试命令

```bash
# 运行所有单元测试
pytest -m unit

# 运行所有集成测试
pytest -m integration

# 运行特定文件的测试
pytest tests/unit/test_gpu_manager.py

# 运行带覆盖率的测试
pytest --cov=backend --cov-report=html

# 运行慢速测试
pytest -m slow

# 运行性能测试
pytest -m performance

# 运行安全测试
pytest -m security

# 并行运行测试 (加速)
pytest -n auto

# 前端测试
cd ui
npm test              # 监视模式
npm run test:run      # 运行一次
npm run test:coverage # 带覆盖率
```

---

## 10. 测试覆盖度目标

### 10.1 当前 vs 目标

| 模块 | 当前覆盖 | 目标覆盖 | 差距 |
|-----|---------|---------|------|
| `backend/core/gpu.py` | 0% | >90% | -90% 🔴 |
| `backend/core/security.py` | ~60% | >90% | -30% 🟡 |
| `backend/services/*` | ~70% | >90% | -20% 🟡 |
| `backend/workers/*` | 0% | >90% | -90% 🔴 |
| `backend/api/deps.py` | 0% | >90% | -90% 🔴 |
| `backend/api/v1/*` | ~60% | >70% (集成) | -10% 🟡 |
| `backend/monitoring/*` | 0% | >80% | -80% 🔴 |
| `ui/src/components/` | ~15% | >60% | -45% 🔴 |
| `ui/src/store/` | 0% | >80% | -80% 🔴 |

### 10.2 优先修复路线图

**Phase 1: 关键缺失 (2 周)**
- GPU Manager 单元测试
- Worker Pool 单元测试
- API Dependencies 测试

**Phase 2: 核心功能 (2 周)**
- vLLM Worker 测试
- Monitoring 测试
- 扩充前端组件测试

**Phase 3: 质量提升 (1 周)**
- 性能测试
- 安全测试
- E2E 测试

---

## 11. 附录

### 11.1 测试工具链

```txt
# 后端
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-benchmark==4.0.0
pytest-xdist==3.5.0  # 并行测试

# 前端
vitest==1.0.4
@testing-library/react==14.1.2
@testing-library/jest-dom==6.1.5
@testing-library/user-event==14.5.1

# E2E
playwright==1.40.1
```

### 11.2 Mock 数据示例

```python
# tests/fixtures/mock_data.py

MOCK_GPU_INFO = {
    "id": "gpu:0",
    "name": "NVIDIA RTX 3090",
    "memory_total_mb": 24576,
    "memory_free_mb": 20480,
    "utilization_percent": 15.5,
    "temperature_celsius": 45.0
}

MOCK_CHAT_REQUEST = {
    "model": "llama-3-8b-prod",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
}

MOCK_CHAT_RESPONSE = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1699012345,
    "model": "llama-3-8b-prod",
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "Hello! How can I help you today?"
        },
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 9,
        "total_tokens": 19
    }
}
```

---

**文档版本**: v1.0
**维护者**: TokenMachine Team
**最后更新**: 2025-01-14

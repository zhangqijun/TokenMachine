# TokenMachine 测试用例文档

> 基于完整后端架构设计的综合测试用例规范

**版本**: v2.0
**最后更新**: 2026-01-16
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
@pytest.mark.rbac          # RBAC 权限测试
@pytest.mark.quota         # 配额管理测试
@pytest.mark.billing       # 计费相关测试
@pytest.mark.cluster       # 集群管理测试
@pytest.mark.worker        # Worker 管理测试
@pytest.mark.multi_tenant  # 多租户测试
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

#### 2.1.2 安全工具 (`test_security.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| SEC-001 | 密码哈希成功 | 有效密码 | 返回哈希值 | P0 |
| SEC-002 | 密码验证成功 | 正确密码 | 返回 True | P0 |
| SEC-003 | 密码验证失败 | 错误密码 | 返回 False | P0 |
| SEC-004 | API Key 生成 | user_id | 返回符合格式的 key | P0 |
| SEC-005 | JWT Token 生成 | 有效 payload | 返回有效 token | P0 |
| SEC-006 | JWT Token 验证成功 | 有效 token | 返回 decoded payload | P0 |

#### 2.1.3 配额管理器 (`test_quota.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| QUOTA-001 | API Key 配额检查 | 有足够配额 | (True, "OK") | P0 |
| QUOTA-002 | API Key 配额不足 | 超出配额 | (False, "Insufficient quota") | P0 |
| QUOTA-003 | API Key 已过期 | 过期 key | (False, "API key has expired") | P0 |
| QUOTA-004 | 组织配额检查 | 有足够配额 | (True, "OK") | P0 |
| QUOTA-005 | 组织配额超出 | 超出配额 | (False, "Quota exceeded") | P0 |
| QUOTA-006 | 速率限制检查 | 未超限 | (True, "OK") | P1 |
| QUOTA-007 | 速率限制超出 | 超出限制 | (False, "Rate limit exceeded") | P1 |
| QUOTA-008 | RBAC 权限检查 | admin 用户 | True | P0 |
| QUOTA-009 | RBAC 权限不足 | readonly 用户 | False (非 read 操作) | P0 |
| QUOTA-010 | 资源所有权检查 | 资源所有者 | True | P1 |
| QUOTA-011 | 计划升级检查 | Free -> Pro | True | P1 |
| QUOTA-012 | 计划降级检查 | Pro -> Free | False | P1 |
| QUOTA-013 | 获取配额信息 | organization_id | 返回完整配额信息 | P0 |
| QUOTA-014 | 升级组织计划 | org_id, new_plan | 计划更新成功 | P1 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.quota
def test_check_api_key_quota_sufficient(db_session, test_api_key):
    """测试 API Key 配额充足"""
    from backend.core.quota import QuotaManager

    quota_manager = QuotaManager(db_session)
    api_key, _ = test_api_key

    allowed, message = quota_manager.check_api_key_quota(
        api_key.id, tokens_needed=1000
    )

    assert allowed is True
    assert message == "OK"

@pytest.mark.unit
@pytest.mark.quota
def test_check_api_key_quota_insufficient(db_session, test_api_key):
    """测试 API Key 配额不足"""
    from backend.core.quota import QuotaManager

    quota_manager = QuotaManager(db_session)
    api_key, _ = test_api_key

    # 设置已用配额接近限制
    api_key.tokens_used = api_key.quota_tokens - 100
    db_session.commit()

    allowed, message = quota_manager.check_api_key_quota(
        api_key.id, tokens_needed=1000
    )

    assert allowed is False
    assert "Insufficient quota" in message

@pytest.mark.unit
@pytest.mark.rbac
def test_check_permission_admin_user(db_session, test_admin_user):
    """测试管理员权限检查"""
    from backend.core.quota import QuotaManager

    quota_manager = QuotaManager(db_session)

    # 管理员应该有所有权限
    assert quota_manager.check_permission(
        test_admin_user.id, "deployment", "delete", 1
    ) is True

    assert quota_manager.check_permission(
        test_admin_user.id, "user", "create", None
    ) is True

@pytest.mark.unit
@pytest.mark.rbac
def test_check_permission_readonly_user(db_session):
    """测试只读用户权限检查"""
    from backend.core.quota import QuotaManager
    from models.database import User, UserRole

    user = User(
        username="readonly",
        email="readonly@example.com",
        password_hash="hash",
        organization_id=1,
        role=UserRole.READONLY
    )
    db_session.add(user)
    db_session.commit()

    quota_manager = QuotaManager(db_session)

    # 只读用户只能读取
    assert quota_manager.check_permission(
        user.id, "deployment", "read", 1
    ) is True

    assert quota_manager.check_permission(
        user.id, "deployment", "delete", 1
    ) is False
```

---

### 2.2 服务层 (services/)

#### 2.2.1 集群服务 (`test_cluster_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| CLUS-001 | 创建集群 | 有效参数 | 返回 Cluster 对象 | P0 |
| CLUS-002 | 创建重复名称集群 | 已存在名称 | 抛出 ValueError | P0 |
| CLUS-003 | 获取集群 | cluster_id | 返回 Cluster 对象 | P0 |
| CLUS-004 | 获取不存在的集群 | invalid_id | 返回 None | P1 |
| CLUS-005 | 列出所有集群 | 无 | 返回集群列表 | P0 |
| CLUS-006 | 按类型筛选 | type="kubernetes" | 只返回 K8s 集群 | P1 |
| CLUS-007 | 更新集群 | 有效更新 | 更新成功 | P0 |
| CLUS-008 | 设置默认集群 | cluster_id | is_default=True | P0 |
| CLUS-009 | 删除空集群 | cluster_id | 删除成功 | P1 |
| CLUS-010 | 删除有 Worker 的集群 | 有运行中 Worker | 抛出 ValueError | P0 |
| CLUS-011 | 获取集群统计 | cluster_id | 返回统计信息 | P1 |
| CLUS-012 | 集群健康检查 | cluster_id | 返回健康状态 | P0 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.cluster
def test_create_cluster_success(db_session):
    """测试成功创建集群"""
    from backend.services.cluster_service import ClusterService

    service = ClusterService(db_session)
    cluster = service.create_cluster(
        name="test-cluster",
        cluster_type="standalone",
        description="Test cluster"
    )

    assert cluster.id is not None
    assert cluster.name == "test-cluster"
    assert cluster.type == "standalone"
    assert cluster.status == "running"

@pytest.mark.unit
@pytest.mark.cluster
def test_create_cluster_duplicate_name(db_session, test_cluster):
    """测试创建重复名称的集群"""
    from backend.services.cluster_service import ClusterService

    service = ClusterService(db_session)

    with pytest.raises(ValueError, match="already exists"):
        service.create_cluster(
            name=test_cluster.name,
            cluster_type="standalone"
        )

@pytest.mark.unit
@pytest.mark.cluster
def test_create_worker_pool(db_session, test_cluster):
    """测试创建 Worker Pool"""
    from backend.services.cluster_service import ClusterService

    service = ClusterService(db_session)
    pool = service.create_worker_pool(
        cluster_id=test_cluster.id,
        name="test-pool",
        min_workers=1,
        max_workers=5
    )

    assert pool.id is not None
    assert pool.name == "test-pool"
    assert pool.min_workers == 1
    assert pool.max_workers == 5

@pytest.mark.unit
@pytest.mark.cluster
def test_scale_worker_pool(db_session, test_worker_pool):
    """测试扩缩容 Worker Pool"""
    from backend.services.cluster_service import ClusterService

    service = ClusterService(db_session)

    updated_pool = service.scale_worker_pool(
        test_worker_pool.id,
        min_workers=2,
        max_workers=10
    )

    assert updated_pool.min_workers == 2
    assert updated_pool.max_workers == 10

@pytest.mark.unit
@pytest.mark.cluster
def test_scale_worker_pool_invalid_range(db_session, test_worker_pool):
    """测试扩缩容参数无效"""
    from backend.services.cluster_service import ClusterService

    service = ClusterService(db_session)

    with pytest.raises(ValueError, match="min_workers cannot be greater"):
        service.scale_worker_pool(
            test_worker_pool.id,
            min_workers=10,
            max_workers=5
        )
```

#### 2.2.2 Worker 服务 (`test_worker_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| WORK-001 | 注册新 Worker | 有效参数 | 返回 Worker 对象 | P0 |
| WORK-002 | 重新注册 Worker | 已存在的 name | 更新现有 Worker | P0 |
| WORK-003 | Worker 心跳 | worker_id | last_heartbeat_at 更新 | P0 |
| WORK-004 | 更新 Worker 状态 | worker_id, status | status_json 更新 | P0 |
| WORK-005 | 更新 GPU 设备 | worker_id, gpu_devices | GPUDevice 更新 | P0 |
| WORK-006 | 获取 Worker | worker_id | 返回 Worker 对象 | P0 |
| WORK-007 | 列出 Workers | 无 | 返回 Worker 列表 | P0 |
| WORK-008 | 按状态筛选 | status="ready" | 只返回 ready 的 | P1 |
| WORK-009 | 按标签筛选 | labels={"gpu": "nvidia"} | 返回匹配的 Worker | P1 |
| WORK-010 | 更新 Worker | worker_id, 更新数据 | 更新成功 | P0 |
| WORK-011 | 设置 Worker 为 drain | worker_id | status=draining | P0 |
| WORK-012 | 设置 Worker 维护模式 | worker_id | status=maintenance | P1 |
| WORK-013 | 删除空闲 Worker | worker_id | 删除成功 | P1 |
| WORK-014 | 删除有实例的 Worker | 有运行实例 | 抛出 ValueError | P0 |
| WORK-015 | 检查离线 Workers | 无 | 返回离线 Worker 列表 | P0 |
| WORK-016 | 获取不健康 Workers | 无 | 返回不健康列表 | P1 |
| WORK-017 | 获取 Worker 统计 | worker_id | 返回详细统计 | P1 |
| WORK-018 | 获取可调度 Workers | 无 | 返回可用 Workers | P0 |
| WORK-019 | 清理离线 Workers | 无 | 删除长时间离线的 | P2 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.worker
def test_register_worker_success(db_session, test_cluster):
    """测试成功注册 Worker"""
    from backend.services.worker_service import WorkerService

    service = WorkerService(db_session)
    worker = service.register_worker(
        name="test-worker",
        cluster_id=test_cluster.id,
        ip="192.168.1.100",
        port=8080,
        hostname="worker-1"
    )

    assert worker.id is not None
    assert worker.name == "test-worker"
    assert worker.cluster_id == test_cluster.id
    assert worker.status == "registering"

@pytest.mark.unit
@pytest.mark.worker
def test_worker_heartbeat(db_session, test_worker):
    """测试 Worker 心跳"""
    from backend.services.worker_service import WorkerService
    from datetime import datetime, timedelta

    service = WorkerService(db_session)
    old_heartbeat = test_worker.last_heartbeat_at

    result = service.heartbeat(test_worker.id)

    assert result is True
    assert test_worker.last_heartbeat_at > old_heartbeat

@pytest.mark.unit
@pytest.mark.worker
def test_update_worker_status(db_session, test_worker):
    """测试更新 Worker 状态"""
    from backend.services.worker_service import WorkerService

    service = WorkerService(db_session)

    status_data = {
        "cpu": {"usage": 45.5},
        "memory": {"total": 32000000000, "used": 16000000000},
        "gpu_devices": [
            {
                "uuid": "GPU-123",
                "name": "NVIDIA RTX 3090",
                "vendor": "nvidia",
                "index": 0,
                "core_total": 10496,
                "core_utilization_rate": 50.0,
                "memory_total": 24000000000,
                "memory_used": 12000000000,
                "memory_utilization_rate": 50.0,
                "temperature": 65.0,
                "state": "available"
            }
        ]
    }

    result = service.update_status(test_worker.id, status_data)

    assert result is True
    assert test_worker.status_json is not None
    assert test_worker.gpu_count == 1

@pytest.mark.unit
@pytest.mark.worker
def test_drain_worker(db_session, test_worker):
    """测试将 Worker 设置为 drain 状态"""
    from backend.services.worker_service import WorkerService

    service = WorkerService(db_session)
    updated = service.drain_worker(test_worker.id)

    assert updated is not None
    assert updated.status == "draining"

@pytest.mark.unit
@pytest.mark.worker
def test_get_workers_for_scheduling(db_session, test_worker):
    """测试获取可调度的 Workers"""
    from backend.services.worker_service import WorkerService

    service = WorkerService(db_session)

    # 设置 worker 为 ready 状态
    test_worker.status = "ready"
    test_worker.gpu_count = 2
    db_session.commit()

    workers = service.get_workers_for_scheduling(
        cluster_id=test_worker.cluster_id,
        gpu_count=1
    )

    assert len(workers) >= 1
    assert test_worker in workers
```

#### 2.2.3 计费服务 (`test_billing_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| BILL-001 | 记录使用情况 | 有效 usage log | 返回 UsageLog 对象 | P0 |
| BILL-002 | 更新 API Key 使用量 | tokens=1000 | tokens_used 增加 | P0 |
| BILL-003 | 计算成本 | input=1000, output=500 | 返回正确成本 | P0 |
| BILL-004 | 获取 API Key 成本 | api_key_id | 返回成本信息 | P1 |
| BILL-005 | 获取使用统计 | org_id, 日期范围 | 返回统计信息 | P0 |
| BILL-006 | 按模型统计 | org_id, 日期范围 | 返回模型使用 | P1 |
| BILL-007 | 按天统计 | org_id, days=30 | 返回每日数据 | P1 |
| BILL-008 | 创建发票 | org_id, 期间 | 返回 Invoice 对象 | P0 |
| BILL-009 | 创建重复发票 | 已存在的期间 | 抛出 ValueError | P1 |
| BILL-010 | 获取发票 | invoice_id | 返回 Invoice 对象 | P0 |
| BILL-011 | 列出发票 | org_id | 返回发票列表 | P0 |
| BILL-012 | 标记发票已支付 | invoice_id | status=paid | P0 |
| BILL-013 | 取消发票 | invoice_id | status=cancelled | P1 |
| BILL-014 | 获取组织计费摘要 | org_id | 返回完整摘要 | P0 |

**示例代码**:
```python
@pytest.mark.unit
@pytest.mark.billing
def test_record_usage(db_session, test_api_key, test_deployment):
    """测试记录 API 使用"""
    from backend.services.billing_service import BillingService

    service = BillingService(db_session)
    api_key, _ = test_api_key

    usage = service.record_usage(
        api_key_id=api_key.id,
        deployment_id=test_deployment.id,
        model_id=test_deployment.model_id,
        input_tokens=100,
        output_tokens=50,
        latency_ms=500,
        status="success"
    )

    assert usage.id is not None
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50

    # 验证 API Key 使用量更新
    assert api_key.tokens_used == 150

@pytest.mark.unit
@pytest.mark.billing
def test_calculate_cost():
    """测试计算成本"""
    from backend.services.billing_service import BillingService

    service = BillingService(db_session)

    cost = service.calculate_cost(
        input_tokens=1000,
        output_tokens=500
    )

    # input: 1000/1000 * 0.001 = 0.001
    # output: 500/1000 * 0.002 = 0.001
    # total: 0.002
    assert cost > 0

@pytest.mark.unit
@pytest.mark.billing
def test_get_usage_stats(db_session, test_organization, test_api_key):
    """测试获取使用统计"""
    from backend.services.billing_service import BillingService
    from datetime import date, timedelta

    service = BillingService(db_session)

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    stats = service.get_usage_stats(
        test_organization.id,
        start_date,
        end_date
    )

    assert "organization_id" in stats
    assert "total_input_tokens" in stats
    assert "total_output_tokens" in stats
    assert "total_cost" in stats
    assert "by_model" in stats
    assert "by_day" in stats

@pytest.mark.unit
@pytest.mark.billing
def test_create_invoice(db_session, test_organization):
    """测试创建发票"""
    from backend.services.billing_service import BillingService
    from datetime import date, timedelta

    service = BillingService(db_session)

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    invoice = service.create_invoice(
        organization_id=test_organization.id,
        period_start=start_date,
        period_end=end_date
    )

    assert invoice.id is not None
    assert invoice.organization_id == test_organization.id
    assert invoice.status == "pending"

@pytest.mark.unit
@pytest.mark.billing
def test_pay_invoice(db_session, test_invoice):
    """测试支付发票"""
    from backend.services.billing_service import BillingService

    service = BillingService(db_session)

    updated = service.pay_invoice(test_invoice.id)

    assert updated is not None
    assert updated.status == "paid"
```

#### 2.2.4 统计服务 (`test_stats_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| STAT-001 | 获取仪表盘统计 | 无 | 返回完整统计 | P0 |
| STAT-002 | 统计 GPU 数量 | 无 | total/available/in_use | P0 |
| STAT-003 | 统计模型数量 | 无 | total/ready | P0 |
| STAT-004 | 统计部署数量 | 无 | total/running | P0 |
| STAT-005 | 统计 Worker 状态 | 无 | 按状态分组 | P0 |
| STAT-006 | 统计 API 调用 | 无 | today/success/error | P0 |
| STAT-007 | 统计 Token 使用 | 无 | today/month/total | P0 |
| STAT-008 | 获取系统健康 | 无 | 返回健康状态 | P0 |
| STAT-009 | 检查组件健康 | 无 | workers/deployments/instances | P0 |
| STAT-010 | 获取资源利用率 | 无 | GPU/Worker 利用率 | P0 |
| STAT-011 | 获取 Top 模型 | limit=10 | 按使用排序 | P1 |
| STAT-012 | 获取 Top 部署 | limit=10 | 按使用排序 | P1 |
| STAT-013 | 获取 Top 组织 | limit=10 | 按 Token 排序 | P1 |
| STAT-014 | 获取时间序列 | metric=tokens, days=30 | 返回每日数据 | P2 |

**示例代码**:
```python
@pytest.mark.unit
def test_get_dashboard_stats(db_session):
    """测试获取仪表盘统计"""
    from backend.services.stats_service import StatsService

    service = StatsService(db_session)
    stats = service.get_dashboard_stats()

    assert "gpu" in stats
    assert "model" in stats
    assert "deployment" in stats
    assert "worker" in stats
    assert "api_calls" in stats
    assert "token_usage" in stats

    # 验证 GPU 统计
    assert "total" in stats["gpu"]
    assert "available" in stats["gpu"]
    assert "in_use" in stats["gpu"]

@pytest.mark.unit
def test_get_system_health(db_session, test_worker):
    """测试获取系统健康状态"""
    from backend.services.stats_service import StatsService
    from datetime import datetime, timedelta

    service = StatsService(db_session)

    # 设置 worker 为健康状态
    test_worker.last_heartbeat_at = datetime.utcnow()
    test_worker.status = "ready"
    db_session.commit()

    health = service.get_system_health()

    assert "status" in health
    assert "components" in health
    assert "workers" in health["components"]
    assert "deployments" in health["components"]

@pytest.mark.unit
def test_get_resource_utilization(db_session, test_gpu_device):
    """测试获取资源利用率"""
    from backend.services.stats_service import StatsService

    service = StatsService(db_session)
    utilization = service.get_resource_utilization()

    assert "gpu" in utilization
    assert "worker" in utilization

    # 验证 GPU 利用率
    assert "total_devices" in utilization["gpu"]
    assert "avg_memory_utilization" in utilization["gpu"]

@pytest.mark.unit
def test_get_top_models(db_session, test_model, test_deployment):
    """测试获取 Top 模型"""
    from backend.services.stats_service import StatsService

    service = StatsService(db_session)
    top_models = service.get_top_models(limit=10)

    assert isinstance(top_models, list)
    # 每个模型应该包含这些字段
    if len(top_models) > 0:
        assert "id" in top_models[0]
        assert "name" in top_models[0]
        assert "usage_count" in top_models[0]
```

#### 2.2.5 模型服务 (`test_model_service.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| MS-001 | 创建模型记录 | 有效 model 数据 | 返回 Model 对象 | P0 |
| MS-002 | 下载模型 - HuggingFace | name, source | 状态变为 downloading | P0 |
| MS-003 | 下载进度更新 | progress=50 | 更新 download_progress | P1 |
| MS-004 | 下载成功 | 下载完成 | 状态变为 ready | P0 |
| MS-005 | 获取模型 | model_id | 返回模型详情 | P0 |
| MS-006 | 列出所有模型 | 无 | 返回模型列表 | P0 |
| MS-007 | 按状态筛选 | status="ready" | 只返回 ready 的模型 | P1 |

---

### 2.3 API 层 (api/)

#### 2.3.1 API Dependencies (`test_api_deps.py`)

| 用例 ID | 测试场景 | 输入 | 预期输出 | 优先级 |
|--------|---------|------|---------|--------|
| DEP-001 | API Key 认证成功 | 有效 Bearer token | 返回 API Key 对象 | P0 |
| DEP-002 | API Key 不存在 | 无效 key | 抛出 401 Unauthorized | P0 |
| DEP-003 | API Key 已过期 | 过期 key | 抛出 401 Unauthorized | P0 |
| DEP-004 | 组织隔离检查 | 跨组织请求 | 抛出 403 Forbidden | P0 |
| DEP-005 | 管理员权限验证 | admin user | 通过验证 | P0 |
| DEP-006 | 组织管理员权限 | org_admin | 通过验证 | P0 |
| DEP-007 | 普通用户权限 | normal user | 部分功能受限 | P0 |

---

## 3. 后端集成测试用例

### 3.1 集群管理 API (`test_cluster_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| CLUS-API-001 | 创建集群 | POST /admin/clusters | 返回 cluster 对象 | P0 |
| CLUS-API-002 | 列出集群 | GET /admin/clusters | 返回集群列表 | P0 |
| CLUS-API-003 | 获取集群详情 | GET /admin/clusters/{id} | 返回完整信息 | P0 |
| CLUS-API-004 | 更新集群 | PATCH /admin/clusters/{id} | 更新成功 | P0 |
| CLUS-API-005 | 删除集群 | DELETE /admin/clusters/{id} | 删除成功 | P1 |
| CLUS-API-006 | 设置默认集群 | POST /admin/clusters/{id}/set-default | is_default=true | P0 |
| CLUS-API-007 | 获取集群统计 | GET /admin/clusters/{id}/stats | 返回统计信息 | P1 |
| CLUS-API-008 | 集群健康检查 | GET /admin/clusters/{id}/health | 返回健康状态 | P0 |
| CLUS-API-009 | 创建 Worker Pool | POST /admin/clusters/{id}/pools | 返回 pool 对象 | P0 |
| CLUS-API-010 | 列出 Worker Pools | GET /admin/clusters/{id}/pools | 返回 pool 列表 | P0 |
| CLUS-API-011 | 扩缩容 Pool | PATCH /admin/pools/{id} | 更新成功 | P0 |
| CLUS-API-012 | 删除 Pool | DELETE /admin/pools/{id} | 删除成功 | P1 |

**示例代码**:
```python
@pytest.mark.integration
@pytest.mark.cluster
async def test_create_cluster(async_client, admin_token):
    """测试创建集群"""
    response = await async_client.post(
        "/api/v1/admin/clusters",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "test-cluster",
            "type": "standalone",
            "description": "Test cluster"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "test-cluster"
    assert data["type"] == "standalone"

@pytest.mark.integration
@pytest.mark.cluster
async def test_list_clusters(async_client, admin_token, test_cluster):
    """测试列出集群"""
    response = await async_client.get(
        "/api/v1/admin/clusters",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) >= 1
```

### 3.2 Worker 管理 API (`test_worker_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| WORK-API-001 | 注册 Worker | POST /admin/workers | 返回 worker 对象 | P0 |
| WORK-API-002 | 列出 Workers | GET /admin/workers | 返回 worker 列表 | P0 |
| WORK-API-003 | 获取 Worker 详情 | GET /admin/workers/{id} | 返回完整信息 | P0 |
| WORK-API-004 | 更新 Worker | PATCH /admin/workers/{id} | 更新成功 | P0 |
| WORK-API-005 | Worker 心跳 | POST /admin/workers/{id}/heartbeat | heartbeat_at 更新 | P0 |
| WORK-API-006 | 上报状态 | POST /admin/workers/{id}/status | status_json 更新 | P0 |
| WORK-API-007 | Drain Worker | POST /admin/workers/{id}/drain | status=draining | P0 |
| WORK-API-008 | 删除 Worker | DELETE /admin/workers/{id} | 删除成功 | P1 |
| WORK-API-009 | 获取 Worker 统计 | GET /admin/workers/{id}/stats | 返回统计信息 | P1 |
| WORK-API-010 | 获取不健康 Workers | GET /admin/workers/unhealthy | 返回列表 | P1 |

### 3.3 计费管理 API (`test_billing_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| BILL-API-001 | 获取使用统计 | GET /admin/billing/usage | 返回统计信息 | P0 |
| BILL-API-002 | 获取每日使用 | GET /admin/billing/daily | 返回每日数据 | P1 |
| BILL-API-003 | 创建发票 | POST /admin/billing/invoices | 返回 invoice 对象 | P0 |
| BILL-API-004 | 列出发票 | GET /admin/billing/invoices | 返回发票列表 | P0 |
| BILL-API-005 | 获取发票详情 | GET /admin/billing/invoices/{id} | 返回完整信息 | P0 |
| BILL-API-006 | 支付发票 | POST /admin/billing/invoices/{id}/pay | status=paid | P0 |
| BILL-API-007 | 取消发票 | POST /admin/billing/invoices/{id}/cancel | status=cancelled | P1 |
| BILL-API-008 | 获取组织计费 | GET /admin/billing/summary | 返回完整摘要 | P0 |

### 3.4 监控管理 API (`test_monitoring_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| MON-API-001 | 获取仪表盘统计 | GET /admin/monitoring/dashboard | 返回统计信息 | P0 |
| MON-API-002 | 获取系统健康 | GET /admin/monitoring/health | 返回健康状态 | P0 |
| MON-API-003 | 获取资源利用率 | GET /admin/monitoring/resources | 返回利用率 | P0 |
| MON-API-004 | 获取 Top 模型 | GET /admin/monitoring/top-models | 返回 Top 列表 | P1 |
| MON-API-005 | 获取时间序列 | GET /admin/monitoring/timeseries | 返回时间序列数据 | P1 |
| MON-API-006 | 获取 Prometheus 指标 | GET /metrics | 返回 Prometheus 格式 | P0 |

### 3.5 OpenAI 兼容 API (`test_chat_api.py`)

| 用例 ID | 测试场景 | 请求 | 预期响应 | 优先级 |
|--------|---------|------|---------|--------|
| CHAT-001 | 基础对话 | 有效 messages | 返回 assistant 消息 | P0 |
| CHAT-002 | 流式输出 | stream=true | 返回 SSE 流 | P0 |
| CHAT-003 | 模型不存在 | model=invalid | 返回 404 | P0 |
| CHAT-004 | API Key 无效 | 无效 key | 返回 401 | P0 |
| CHAT-005 | 超出配额 | 配额不足 | 返回 429 | P0 |

---

## 4. 前端组件测试用例

### 4.1 新增组件测试

| 用例 ID | 组件 | 测试场景 | 预期结果 | 优先级 |
|--------|-----|---------|---------|--------|
| UI-020 | ClusterList | 渲染集群列表 | 显示所有集群 | P0 |
| UI-021 | ClusterList | 筛选集群类型 | 正确筛选 | P1 |
| UI-022 | ClusterDetail | 显示集群统计 | 显示 Worker 数量 | P0 |
| UI-023 | WorkerPoolCard | 显示 Pool 信息 | min/max workers | P0 |
| UI-024 | WorkerList | 渲染 Worker 列表 | 显示所有 Worker | P0 |
| UI-025 | WorkerStatus | 显示状态颜色 | green=ready, red=error | P0 |
| UI-026 | BillingSummary | 显示计费信息 | tokens/cost | P0 |
| UI-027 | InvoiceList | 显示发票列表 | 支付状态 | P1 |
| UI-028 | UsageChart | 渲染使用图表 | ECharts 图表 | P1 |
| UI-029 | QuotaIndicator | 显示配额进度 | 进度条正确 | P0 |

---

## 5. 性能测试用例

### 5.1 API 性能 (`test_api_performance.py`)

| 用例 ID | 测试场景 | 指标 | 目标 | 优先级 |
|--------|---------|------|------|--------|
| PERF-001 | 单个聊天请求 | 延迟 (P50) | < 500ms | P0 |
| PERF-002 | 单个聊天请求 | 延迟 (P99) | < 2000ms | P0 |
| PERF-003 | 并发聊天 | 100 并发 | 全部成功 | P0 |
| PERF-004 | 列出集群 | 延迟 | < 100ms | P1 |
| PERF-005 | 获取仪表盘统计 | 延迟 | < 200ms | P1 |
| PERF-006 | 创建 Worker Pool | 延迟 | < 500ms | P2 |
| PERF-007 | 计费统计查询 | 延迟 (30 天) | < 1s | P2 |

---

## 6. 安全测试用例

### 6.1 多租户安全 (`test_multi_tenant_security.py`)

| 用例 ID | 测试场景 | 攻击向量 | 预期防御 | 优先级 |
|--------|---------|---------|---------|--------|
| MT-SEC-001 | 跨组织访问 | org A 访问 org B 资源 | 403 Forbidden | P0 |
| MT-SEC-002 | 组织 ID 篡改 | 修改 org_id 参数 | 拒绝 | P0 |
| MT-SEC-003 | 权限提升 | user → admin | 403 Forbidden | P0 |
| MT-SEC-004 | 配额绕过 | 超出配额后继续请求 | 429 Too Many Requests | P0 |
| MT-SEC-005 | 审计日志记录 | 敏感操作 | 记录到 audit_logs | P1 |

---

## 7. 端到端测试用例

### 7.1 多租户业务流程

#### E2E-MT-001: 组织注册和使用流程

| 步骤 | 操作 | 验证点 |
|-----|------|-------|
| 1 | 创建新组织 | organization_id 生成 |
| 2 | 创建组织用户 | 用户关联到组织 |
| 3 | 创建 API Key | API Key 关联到组织 |
| 4 | 使用 API 调用 | 请求成功，计入组织配额 |
| 5 | 检查配额使用 | 配额统计正确 |
| 6 | 查看使用统计 | 显示组织使用情况 |

#### E2E-CLUSTER-001: 集群管理完整流程

| 步骤 | 操作 | 验证点 |
|-----|------|-------|
| 1 | 创建集群 | 集群状态为 running |
| 2 | 创建 Worker Pool | Pool 创建成功 |
| 3 | Worker 注册 | Worker 状态变为 ready |
| 4 | 部署模型到集群 | 模型实例创建 |
| 5 | 检查集群健康 | 健康状态正常 |
| 6 | Drain Worker | Worker 状态变为 draining |
| 7 | 删除集群 | 集群删除成功 |

---

## 8. 测试数据管理

### 8.1 新增 Fixtures

```python
# tests/conftest.py 新增 fixtures

@pytest.fixture
def test_organization(db_session):
    """创建测试组织"""
    from models.database import Organization, OrganizationPlan

    org = Organization(
        name="test-org",
        plan=OrganizationPlan.FREE,
        quota_tokens=10000,
        quota_models=1,
        quota_gpus=1,
        max_workers=2
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org

@pytest.fixture
def test_cluster(db_session, test_organization):
    """创建测试集群"""
    from models.database import Cluster, ClusterType

    cluster = Cluster(
        name="test-cluster",
        type=ClusterType.STANDALONE,
        is_default=True,
        status="running"
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster

@pytest.fixture
def test_worker_pool(db_session, test_cluster):
    """创建测试 Worker Pool"""
    from models.database import WorkerPool, WorkerPoolStatus

    pool = WorkerPool(
        cluster_id=test_cluster.id,
        name="test-pool",
        min_workers=1,
        max_workers=5,
        status=WorkerPoolStatus.RUNNING
    )
    db_session.add(pool)
    db_session.commit()
    db_session.refresh(pool)
    return pool

@pytest.fixture
def test_worker(db_session, test_cluster):
    """创建测试 Worker"""
    from models.database import Worker, WorkerStatus

    worker = Worker(
        cluster_id=test_cluster.id,
        name="test-worker",
        ip="192.168.1.100",
        port=8080,
        status=WorkerStatus.READY,
        gpu_count=2
    )
    db_session.add(worker)
    db_session.commit()
    db_session.refresh(worker)
    return worker

@pytest.fixture
def test_gpu_device(db_session, test_worker):
    """创建测试 GPU 设备"""
    from models.database import GPUDevice, GPUVendor, GPUDeviceState

    gpu = GPUDevice(
        worker_id=test_worker.id,
        uuid="GPU-12345",
        name="NVIDIA RTX 3090",
        vendor=GPUVendor.NVIDIA,
        index=0,
        core_total=10496,
        memory_total=24000000000,
        state=GPUDeviceState.AVAILABLE
    )
    db_session.add(gpu)
    db_session.commit()
    db_session.refresh(gpu)
    return gpu

@pytest.fixture
def test_invoice(db_session, test_organization):
    """创建测试发票"""
    from models.database import Invoice, InvoiceStatus
    from datetime import date, timedelta

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    invoice = Invoice(
        organization_id=test_organization.id,
        amount=100.00,
        currency="USD",
        status=InvoiceStatus.PENDING,
        period_start=datetime.combine(start_date, datetime.min.time()),
        period_end=datetime.combine(end_date, datetime.max.time()),
        tokens_used=50000
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice
```

---

## 9. 测试覆盖度目标

### 9.1 当前 vs 目标 (v2.0)

| 模块 | 当前覆盖 | 目标覆盖 | 差距 |
|-----|---------|---------|------|
| `backend/core/quota.py` | 0% | >90% | -90% 🔴 |
| `backend/services/cluster_service.py` | 0% | >90% | -90% 🔴 |
| `backend/services/worker_service.py` | 0% | >90% | -90% 🔴 |
| `backend/services/billing_service.py` | 0% | >90% | -90% 🔴 |
| `backend/services/stats_service.py` | 0% | >90% | -90% 🔴 |
| `backend/api/v1/admin/clusters.py` | 0% | >70% (集成) | -70% 🔴 |
| `backend/api/v1/admin/workers.py` | 0% | >70% (集成) | -70% 🔴 |
| `backend/api/v1/admin/billing.py` | 0% | >70% (集成) | -70% 🔴 |
| `backend/api/v1/admin/monitoring.py` | 0% | >70% (集成) | -70% 🔴 |

---

## 10. 附录

### 10.1 测试工具链

```txt
# 后端
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-benchmark==4.0.0
pytest-xdist==3.5.0
pytest-timeout==2.2.0

# 前端
vitest==1.0.4
@testing-library/react==14.1.2
@testing-library/jest-dom==6.1.5
@testing-library/user-event==14.5.1

# E2E
playwright==1.40.1
```

---

**文档版本**: v2.0
**维护者**: TokenMachine Team
**最后更新**: 2026-01-16
**更新内容**: 添加多租户、集群管理、Worker 管理、计费系统、统计服务、配额管理的完整测试用例

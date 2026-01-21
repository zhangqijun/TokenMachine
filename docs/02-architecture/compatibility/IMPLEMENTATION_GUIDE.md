# 兼容性组件实施指南

## 概述

本指南提供兼容性组件的分阶段实施计划，包括开发步骤、测试策略和部署流程。

---

## 实施阶段

### 阶段 1: 基础设施 (Week 1-2)

#### 目标
- 建立数据库架构
- 实现基础 API 端点
- 搭建数据收集管道

#### 任务清单

##### 1.1 数据库设置

```sql
-- 创建数据库迁移
cd backend
alembic revision --autogenerate -m "Add compatibility records table"

-- 编辑生成的迁移文件，添加索引和约束
# migrations/versions/xxx_add_compatibility_records.py

# 应用迁移
alembic upgrade head
```

**验收标准**:
- [ ] compatibility_records 表创建成功
- [ ] 所有索引正确创建
- [ ] 外键约束正常工作

##### 1.2 基础模型定义

```python
# backend/models/compatibility.py
from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, DateTime
from sqlalchemy.sql import func
from models.database import Base

class CompatibilityRecord(Base):
    __tablename__ = "compatibility_records"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 元数据
    source = Column(String(50), nullable=False)
    confidence = Column(String(20), nullable=False)
    verified = Column(Boolean, default=False)

    # 后端信息
    backend_name = Column(String(20), nullable=False)
    backend_version = Column(String(50))

    # 硬件信息
    hardware_vendor = Column(String(50))
    hardware_model = Column(String(100))
    hardware_count = Column(Integer)
    # ... 更多字段

    def __repr__(self):
        return f"<CompatibilityRecord(id={self.id}, backend={self.backend_name})>"
```

##### 1.3 Pydantic 模型

```python
# backend/api/schemas/compatibility.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class CompatibilityCheckRequest(BaseModel):
    backend: str = Field(..., regex="^(vllm|sglang|llamacpp)$")
    hardware_vendor: str = Field(..., min_length=1)
    hardware_model: str = Field(..., min_length=1)
    hardware_count: int = Field(..., ge=1, le=256)
    model_architecture: Optional[str] = None
    model_dtype: Optional[str] = None
    tensor_parallel_size: Optional[int] = Field(None, ge=1)

    class Config:
        schema_extra = {
            "example": {
                "backend": "vllm",
                "hardware_vendor": "NVIDIA",
                "hardware_model": "H100",
                "hardware_count": 4,
                "tensor_parallel_size": 4
            }
        }

class CompatibilityCheckResponse(BaseModel):
    compatible: bool
    confidence: str
    verified_count: int
    status: str
    recommendations: Optional[dict] = None
    alternatives: Optional[List[dict]] = None
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None
```

##### 1.4 API 路由

```python
# backend/api/v1/compatibility.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from api.schemas.compatibility import CompatibilityCheckRequest, CompatibilityCheckResponse

router = APIRouter()

@router.post("/check", response_model=CompatibilityCheckResponse)
async def check_compatibility(
    request: CompatibilityCheckRequest,
    db: AsyncSession = Depends(get_db)
):
    """检查配置兼容性"""
    # 实现检查逻辑
    pass

# 注册路由
# backend/api/v1/__init__.py
from api.v1 import compatibility
api_router.include_router(compatibility.router, prefix="/compatibility", tags=["compatibility"])
```

**测试**:
```bash
# 启动开发服务器
uvicorn backend.main:app --reload

# 测试 API
curl -X POST http://localhost:8000/api/v1/compatibility/check \
  -H "Content-Type: application/json" \
  -d '{"backend":"vllm","hardware_vendor":"NVIDIA","hardware_model":"H100","hardware_count":4}'
```

---

### 阶段 2: 数据收集 (Week 3-4)

#### 目标
- 实现 vLLM usage_stats 收集器
- 实现 SGLang CI 提取器
- 建立定时同步任务

#### 任务清单

##### 2.1 vLLM usage_stats 收集器

```python
# backend/workers/compatibility/vllm_collector.py
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

class VLLMStatsCollector:
    def __init__(self):
        self.stats_path = Path.home() / ".config" / "vllm" / "usage_stats.json"

    def collect(self, deployment_id: Optional[str] = None) -> Optional[dict]:
        """收集 vLLM 使用统计"""
        if not self.stats_path.exists():
            return None

        with open(self.stats_path) as f:
            raw = json.load(f)

        # 匿名化并转换格式
        record = self._transform(raw, deployment_id)
        return record

    def _transform(self, raw: dict, deployment_id: Optional[str]) -> dict:
        """转换为兼容性记录格式"""
        return {
            "metadata": {
                "source": "vllm_usage_stats",
                "collected_at": datetime.utcnow().isoformat(),
                "confidence": "high",
                "verified": True
            },
            "backend": {
                "name": "vllm",
                "version": raw.get("vllm_version", "unknown")
            },
            "hardware": {
                "vendor": self._extract_vendor(raw["gpu_info"]["gpu_type"]),
                "model": raw["gpu_info"]["gpu_type"],
                "count": raw["gpu_info"]["gpu_count"],
                "memory_per_device": raw["gpu_info"].get("gpu_memory_per_device")
            },
            # ... 更多字段
        }

    def _extract_vendor(self, gpu_type: str) -> str:
        """从 GPU 型号推断厂商"""
        if any(x in gpu_type.upper() for x in ["NVIDIA", "RTX", "H100", "H200"]):
            return "NVIDIA"
        elif any(x in gpu_type.upper() for x in ["AMD", "MI", "RX"]):
            return "AMD"
        elif any(x in gpu_type.upper() for x in ["ASCEND", "A2", "A3"]):
            return "Huawei"
        return "Unknown"
```

**测试**:
```python
# tests/unit/test_vllm_collector.py
import pytest
from workers.compatibility.vllm_collector import VLLMStatsCollector

def test_collect_vllm_stats(tmp_path):
    """测试 vLLM stats 收集"""
    # 创建临时测试文件
    stats_file = tmp_path / "usage_stats.json"
    stats_file.write_text('''
    {
        "vllm_version": "v0.6.0",
        "gpu_info": {
            "gpu_count": 4,
            "gpu_type": "NVIDIA H100",
            "gpu_memory_per_device": 80
        },
        "model_info": {
            "model_architecture": "llama",
            "dtype": "float16"
        }
    }
    ''')

    collector = VLLMStatsCollector()
    collector.stats_path = stats_file

    record = collector.collect()

    assert record is not None
    assert record["backend"]["name"] == "vllm"
    assert record["hardware"]["vendor"] == "NVIDIA"
    assert record["hardware"]["model"] == "H100"
```

##### 2.2 SGLang CI 提取器

```python
# backend/workers/compatibility/sglang_ci_extractor.py
import requests
from typing import List, Dict
from datetime import datetime, timedelta

class SGLangCIExtractor:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.base_url = "https://api.github.com/repos/sgl-project/sglang"

    def extract(self, days: int = 7) -> List[dict]:
        """提取最近 N 天的 CI 数据"""
        records = []
        workflows = ['pr-test', 'pr-test-amd', 'pr-test-npu']

        for workflow in workflows:
            workflow_records = self._extract_workflow(workflow, days)
            records.extend(workflow_records)

        return records

    def _extract_workflow(self, workflow: str, days: int) -> List[dict]:
        """提取单个工作流的数据"""
        url = f"{self.base_url}/actions/workflows/{workflow}.yml/runs"
        params = {
            "status": "success",
            "per_page": 100,
            "created": f">={(datetime.utcnow() - timedelta(days=days)).isoformat()}"
        }

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        response = requests.get(url, params=params, headers=headers)
        runs = response.json().get("workflow_runs", [])

        records = []
        for run in runs:
            record = self._parse_run(run, workflow)
            if record:
                records.append(record)

        return records

    def _parse_run(self, run: dict, workflow: str) -> Optional[dict]:
        """解析单个运行记录"""
        # 从 runner 标签提取硬件信息
        hardware = self._parse_hardware(run.get("runner_group_name", ""))

        # 从日志提取测试信息
        test_info = self._parse_test_logs(run)

        return {
            "metadata": {
                "source": "sglang_ci",
                "run_id": str(run["id"]),
                "run_date": run["created_at"],
                "commit_sha": run["head_sha"],
                "workflow": workflow
            },
            "hardware": hardware,
            "test": test_info,
            "result": {
                "status": "success" if run["conclusion"] == "success" else "failure",
                "duration_seconds": self._calculate_duration(run)
            }
        }

    def _parse_hardware(self, runner_label: str) -> dict:
        """从 runner 标签解析硬件信息"""
        mapping = {
            "1-gpu-5090": {"vendor": "NVIDIA", "model": "RTX-5090", "count": 1},
            "4-gpu-h100": {"vendor": "NVIDIA", "model": "H100", "count": 4},
            "linux-mi325-gpu-2": {"vendor": "AMD", "model": "MI325", "count": 2},
            "linux-aarch64-a2-4": {"vendor": "Huawei", "model": "Ascend-A2", "count": 4},
        }

        return mapping.get(runner_label, {
            "vendor": "Unknown",
            "model": runner_label,
            "count": 1
        })
```

**测试**:
```python
# tests/unit/test_sglang_extractor.py
from workers.compatibility.sglang_ci_extractor import SGLangCIExtractor

def test_hardware_parsing():
    """测试硬件解析"""
    extractor = SGLangCIExtractor()

    hardware = extractor._parse_hardware("4-gpu-h100")
    assert hardware["vendor"] == "NVIDIA"
    assert hardware["model"] == "H100"
    assert hardware["count"] == 4

    hardware = extractor._parse_hardware("linux-mi325-gpu-2")
    assert hardware["vendor"] == "AMD"
    assert hardware["model"] == "MI325"
```

##### 2.3 定时同步任务

```python
# backend/workers/compatibility/sync_tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session_maker
from workers.compatibility.sglang_ci_extractor import SGLangCIExtractor

scheduler = AsyncIOScheduler()

async def sync_sglang_ci():
    """同步 SGLang CI 数据"""
    extractor = SGLangCIExtractor(github_token=settings.github_token)

    try:
        records = extractor.extract(days=7)

        async with async_session_maker() as db:
            for record in records:
                await save_record(db, record)

        print(f"Synced {len(records)} records from SGLang CI")
    except Exception as e:
        print(f"Failed to sync SGLang CI: {e}")

async def save_record(db: AsyncSession, record: dict):
    """保存单条记录"""
    from models.compatibility import CompatibilityRecord

    # 检查是否已存在
    from sqlalchemy import select
    query = select(CompatibilityRecord).where(
        CompatibilityRecord.metadata['run_id'].astext == record['metadata']['run_id']
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        return  # 已存在，跳过

    # 创建新记录
    db_record = CompatibilityRecord(**record)
    db.add(db_record)
    await db.commit()

# 添加定时任务
scheduler.add_job(sync_sglang_ci, 'cron', hour=2)  # 每日凌晨 2 点
```

---

### 阶段 3: 前端集成 (Week 5-6)

#### 目标
- 创建兼容性查询页面
- 集成到部署流程
- 实现数据可视化

#### 任务清单

##### 3.1 Zustand Store

```typescript
// ui/src/store/compatibility.ts
import { create } from 'zustand';
import { compatibilityAPI } from '@/api/compatibility';

interface CompatibilityState {
  records: CompatibilityRecord[];
  stats: CompatibilityStats | null;
  loading: boolean;
  error?: string;

  fetchRecords: (filters?: any) => Promise<void>;
  fetchStats: () => Promise<void>;
  checkCompatibility: (request: CompatibilityCheckRequest) => Promise<CompatibilityCheckResponse>;
}

export const useCompatibilityStore = create<CompatibilityState>((set, get) => ({
  records: [],
  stats: null,
  loading: false,

  fetchRecords: async (filters) => {
    set({ loading: true, error: undefined });
    try {
      const response = await compatibilityAPI.listRecords(filters);
      set({ records: response.records, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const stats = await compatibilityAPI.getStats();
      set({ stats });
    } catch (error) {
      set({ error: error.message });
    }
  },

  checkCompatibility: async (request) => {
    return await compatibilityAPI.check(request);
  },
}));
```

##### 3.2 兼容性矩阵页面

```typescript
// ui/src/pages/Compatibility.tsx
import { useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag } from 'antd';
import { useCompatibilityStore } from '@/store/compatibility';
import { CompatibilityCharts } from '@/components/compatibility/CompatibilityCharts';

export const CompatibilityPage = () => {
  const { records, stats, loading, fetchRecords, fetchStats } = useCompatibilityStore();

  useEffect(() => {
    fetchRecords();
    fetchStats();
  }, []);

  const columns = [
    { title: '后端', dataIndex: ['backend', 'name'], key: 'backend' },
    { title: '硬件', key: 'hardware', render: (_, r) => `${r.hardware.vendor} ${r.hardware.model} × ${r.hardware.count}` },
    { title: '模型', dataIndex: ['model', 'architecture'], key: 'model' },
    {
      title: '状态',
      dataIndex: ['compatibility', 'status'],
      key: 'status',
      render: (status) => {
        const colors = { compatible: 'success', partial: 'warning', incompatible: 'error' };
        return <Tag color={colors[status]}>{status}</Tag>;
      }
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card><Statistic title="总记录数" value={stats?.total_records} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="兼容率" value={stats?.compatibility_rate * 100} suffix="%" /></Card>
        </Col>
      </Row>

      <CompatibilityCharts data={records} />

      <Card title="兼容性记录">
        <Table dataSource={records} columns={columns} rowKey="id" loading={loading} />
      </Card>
    </div>
  );
};
```

##### 3.3 部署流程集成

```typescript
// ui/src/pages/models/components/CreateDeploymentModal.tsx
import { useState } from 'react';
import { Modal, Form, Button, message } from 'antd';
import { useCompatibilityStore } from '@/store/compatibility';
import { CompatibilityCheckModal } from '@/components/models/CompatibilityCheckModal';

export const CreateDeploymentModal = ({ visible, model, onCancel }) => {
  const [form] = Form.useForm();
  const [checking, setChecking] = useState(false);
  const [compatibilityResult, setCompatibilityResult] = useState(null);
  const { checkCompatibility } = useCompatibilityStore();

  const handleCheck = async () => {
    try {
      const values = await form.validateFields();
      setChecking(true);

      const result = await checkCompatibility({
        backend: values.backend,
        hardware_vendor: values.hardware_vendor,
        hardware_model: values.hardware_model,
        hardware_count: values.gpu_count,
        model_architecture: model.architecture,
      });

      setCompatibilityResult(result);
    } catch (error) {
      message.error('检查失败: ' + error.message);
    } finally {
      setChecking(false);
    }
  };

  return (
    <>
      <Modal
        title="创建部署"
        open={visible}
        onCancel={onCancel}
        footer={
          <Button type="primary" onClick={handleCheck} loading={checking}>
            检查兼容性
          </Button>
        }
      >
        <Form form={form}>
          {/* 部署配置表单 */}
        </Form>
      </Modal>

      {compatibilityResult && (
        <CompatibilityCheckModal
          visible
          data={compatibilityResult}
          onConfirm={() => {
            // 创建部署
          }}
          onCancel={() => setCompatibilityResult(null)}
        />
      )}
    </>
  );
};
```

---

### 阶段 4: 测试与优化 (Week 7-8)

#### 目标
- 完成单元测试和集成测试
- 性能优化
- 文档完善

#### 任务清单

##### 4.1 单元测试

```python
# tests/unit/test_compatibility_check.py
import pytest
from api.v1.compatibility import check_compatibility
from api.schemas.compatibility import CompatibilityCheckRequest

@pytest.mark.asyncio
async def test_check_compatibility_exact_match(db_session):
    """测试精确匹配"""
    # 插入测试数据
    # ...

    request = CompatibilityCheckRequest(
        backend="vllm",
        hardware_vendor="NVIDIA",
        hardware_model="H100",
        hardware_count=4
    )

    result = await check_compatibility(request, db_session)

    assert result.compatible == True
    assert result.confidence == "high"
    assert result.verified_count > 0

@pytest.mark.asyncio
async void test_check_compatibility_no_match(db_session):
    """测试无匹配情况"""
    request = CompatibilityCheckRequest(
        backend="unknown_backend",
        hardware_vendor="Unknown",
        hardware_model="Unknown",
        hardware_count=1
    )

    result = await check_compatibility(request, db_session)

    assert result.compatible == False
    assert result.status == "unknown"
```

##### 4.2 性能测试

```python
# tests/performance/test_compatibility_query.py
import pytest
import time

@pytest.mark.asyncio
async def test_query_performance(db_session):
    """测试查询性能"""
    # 插入 1000 条测试数据
    # ...

    start = time.time()

    # 执行查询
    result = await check_compatibility(request, db_session)

    duration = time.time() - start

    assert duration < 1.0  # 响应时间应小于 1 秒
```

##### 4.3 缓存优化

```python
# backend/core/cache.py
from functools import lru_cache
from redis import Redis

redis = Redis.from_url(settings.redis_url)

def cache_compatibility_check(ttl: int = 3600):
    """缓存兼容性检查结果"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = args[0]
            cache_key = f"compat:check:{hash_frozenset(request.dict())}"

            # 尝试从缓存获取
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)

            # 执行查询
            result = await func(*args, **kwargs)

            # 缓存结果
            await redis.setex(cache_key, ttl, json.dumps(result))

            return result
        return wrapper
    return decorator

@router.post("/check")
@cache_compatibility_check(ttl=3600)
async def check_compatibility(...):
    # ... 实现
```

---

## 部署清单

### 前置条件

- [ ] PostgreSQL 15+ 已安装并运行
- [ ] Redis 7+ 已安装并运行
- [ ] GitHub Token 已配置（用于 SGLang CI 提取）
- [ ] 环境变量已设置

### 部署步骤

#### 1. 数据库迁移

```bash
cd backend

# 检查迁移状态
alembic current

# 执行迁移
alembic upgrade head

# 验证表已创建
psql -U postgres -d tokenmachine -c "\d compatibility_records"
```

#### 2. 配置环境变量

```bash
# backend/.env
GITHUB_TOKEN=ghp_xxxxx  # 用于访问 GitHub API
REDIS_URL=redis://localhost:6379/0
ENABLE_COMPATIBILITY_COLLECTION=true
```

#### 3. 启动服务

```bash
# 启动后端
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动前端
cd ui
npm run dev
```

#### 4. 初始化数据

```bash
# 导入初始兼容性数据
cd backend
python scripts/import_initial_compat_data.py

# 验证数据
curl http://localhost:8000/api/v1/compatibility/stats
```

#### 5. 启动定时任务

```bash
# 启动 Celery worker
celery -A workers.compat_tasks worker --loglevel=info

# 启动定时任务调度器
celery -A workers.compat_tasks beat --loglevel=info
```

---

## 验收标准

### 功能验收

- [ ] 用户可以通过 API 检查配置兼容性
- [ ] vLLM usage_stats 自动收集功能正常工作
- [ ] SGLang CI 数据定时同步
- [ ] 前端可以正确展示兼容性矩阵
- [ ] 部署创建时自动执行兼容性检查

### 性能验收

- [ ] 兼容性检查 API 响应时间 < 1 秒
- [ ] 数据库查询使用索引，无全表扫描
- [ ] 缓存命中率 > 70%

### 安全验收

- [ ] 所有用户数据已匿名化
- [ ] 敏感信息不记录到日志
- [ ] API 速率限制正常工作

### 文档验收

- [ ] API 文档完整
- [ ] 用户指南清晰
- [ ] 开发者文档详细

---

## 监控指标

### 关键指标

- **数据收集量**: 每日新增记录数
- **API 调用量**: 兼容性检查次数
- **缓存命中率**: 缓存效果
- **响应时间**: P50, P95, P99
- **错误率**: API 失败率

### 监控设置

```python
# backend/monitoring/compatibility_metrics.py
from prometheus_client import Counter, Histogram

# 数据收集指标
records_collected = Counter(
    'compatibility_records_collected_total',
    'Total number of compatibility records collected',
    ['source']
)

# API 调用指标
compat_checks_total = Counter(
    'compatibility_checks_total',
    'Total number of compatibility checks',
    ['backend', 'status']
)

compat_check_duration = Histogram(
    'compatibility_check_duration_seconds',
    'Compatibility check duration',
    ['backend']
)
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-21

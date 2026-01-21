# Playground Backend Design

## 概述

Playground 是 TokenMachine 提供的模型测试与评估平台，包含两个核心功能模块：

1. **对话测试 (ChatTest)**: 实时对话交互测试，支持模型参数调整、历史记录管理、Token 统计
2. **批量测试 (BenchmarkTest)**: 基于 EvalScope 框架的模型批量评测，支持性能测试和效果评估

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  ┌──────────────┐              ┌─────────────────┐              │
│  │  ChatTest    │              │  BenchmarkTest  │              │
│  └──────┬───────┘              └────────┬────────┘              │
└─────────┼───────────────────────────────┼──────────────────────┘
          │                               │
          ▼                               ▼
┌───────────────────────┐    ┌─────────────────────────────────┐
│   API Layer (FastAPI) │    │   API Layer (FastAPI)           │
│  /api/v1/playground/  │    │  /api/v1/benchmark/             │
└───────────┬───────────┘    └─────────────┬───────────────────┘
            │                               │
            ▼                               ▼
┌───────────────────────┐    ┌─────────────────────────────────┐
│  PlaygroundService    │    │   BenchmarkService              │
│  - Chat sessions      │    │   - Create task                 │
│  - Message history    │    │   - Query status                │
│  - Token counting     │    │   - Get results                 │
└───────────────────────┘    └─────────────┬───────────────────┘
                                            │
                                            ▼
                                    ┌──────────────────┐
                                    │  Celery Worker   │
                                    │  - run_eval_task │
                                    │  - run_perf_task │
                                    └─────────┬────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │   EvalScope      │
                                    │   HTTP API       │
                                    └──────────────────┘
```

## 数据库模型设计

### 1. 对话测试表 (playground_sessions)

```sql
CREATE TABLE playground_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    deployment_id BIGINT REFERENCES deployments(id) ON DELETE SET NULL,
    session_name VARCHAR(255) DEFAULT 'Untitled Session',
    model_config JSONB NOT NULL,  -- {model, temperature, topP, maxTokens, ...}
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0.0000,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at DESC)
);
```

**字段说明**:
- `model_config`: 存储模型配置参数（temperature, topP, maxTokens 等）
- `input_tokens/output_tokens`: 累计 Token 使用量
- `total_cost`: 累计费用（按 Token 计算）

### 2. 对话消息表 (playground_messages)

```sql
CREATE TABLE playground_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES playground_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_session_id (session_id),
    INDEX idx_timestamp (timestamp DESC)
);
```

**字段说明**:
- `role`: 消息角色（user/assistant/system）
- `input_tokens/output_tokens`: 单条消息的 Token 统计

### 3. 批量测试任务表 (benchmark_tasks)

```sql
CREATE TABLE benchmark_tasks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    deployment_id BIGINT REFERENCES deployments(id) ON DELETE SET NULL,
    task_name VARCHAR(255) NOT NULL,
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('eval', 'perf')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'cancelled'
    )),
    config JSONB NOT NULL,  -- EvalScope 配置
    result JSONB,  -- 评测结果
    output_dir VARCHAR(1024),  -- EvalScope 输出目录路径
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    celery_task_id VARCHAR(255),  -- Celery 任务 ID（用于取消任务）
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_celery_task_id (celery_task_id)
);
```

**字段说明**:
- `task_type`: 任务类型（eval=效果评测, perf=性能测试）
- `status`: 任务状态流转：pending → running → completed/failed
- `config`: EvalScope API 请求配置
- `result`: EvalScope 返回的评测结果
- `output_dir`: EvalScope 生成的报告文件路径
- `celery_task_id`: Celery 任务标识，用于任务控制和状态查询

### 4. 评测数据集表 (benchmark_datasets)

```sql
CREATE TABLE benchmark_datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100),  -- mmlu, gsm8k, ceval, custom, etc.
    description TEXT,
    dataset_size INT,
    metadata JSONB,  -- 数据集元信息
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_category (category),
    INDEX idx_name (name)
);
```

**字段说明**:
- `category`: 数据集分类（MMLU, GSM8K, C-Eval 等）
- `dataset_size`: 数据集样本数量
- `metadata`: 数据集详细配置

## 数据模型定义

### SQLAlchemy Models

```python
# backend/models/database.py

from sqlalchemy import Column, BigInteger, Integer, String, Text, DECIMAL, JSON, TIMESTAMP, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

class PlaygroundSession(Base):
    """对话测试会话"""
    __tablename__ = "playground_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    session_name = Column(String(255), default="Untitled Session")
    model_config = Column(JSON, nullable=False)  # {model, temperature, topP, maxTokens, ...}
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    total_cost = Column(DECIMAL(10, 6), default=0.0000)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    messages = relationship("PlaygroundMessage", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_playground_session_user_id', 'user_id'),
        Index('ix_playground_session_created_at', 'created_at'),
    )


class PlaygroundMessage(Base):
    """对话消息"""
    __tablename__ = "playground_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("playground_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    timestamp = Column(TIMESTAMP, default=func.now(), nullable=False)

    # Relationships
    session = relationship("PlaygroundSession", back_populates="messages")

    __table_args__ = (
        Index('ix_playground_message_session_id', 'session_id'),
        Index('ix_playground_message_timestamp', 'timestamp'),
    )


class TaskType(str, Enum):
    """批量测试任务类型"""
    EVAL = "eval"   # 效果评测
    PERF = "perf"   # 性能测试


class TaskStatus(str, Enum):
    """批量测试任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkTask(Base):
    """批量测试任务"""
    __tablename__ = "benchmark_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    task_name = Column(String(255), nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    config = Column(JSON, nullable=False)  # EvalScope 配置
    result = Column(JSON)  # 评测结果
    output_dir = Column(String(1024))  # EvalScope 输出目录
    error_message = Column(Text)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    celery_task_id = Column(String(255), index=True)  # Celery 任务 ID
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_benchmark_task_user_id', 'user_id'),
        Index('ix_benchmark_task_status', 'status'),
        Index('ix_benchmark_task_created_at', 'created_at'),
        Index('ix_benchmark_task_celery_task_id', 'celery_task_id'),
    )


class BenchmarkDataset(Base):
    """评测数据集"""
    __tablename__ = "benchmark_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(100), index=True)  # mmlu, gsm8k, ceval, custom
    description = Column(Text)
    dataset_size = Column(Integer)
    metadata = Column(JSON)  # 数据集元信息
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_benchmark_dataset_category', 'category'),
        Index('ix_benchmark_dataset_name', 'name'),
    )
```

### Pydantic Schemas

```python
# backend/models/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# ============================================================================
# Playground (对话测试) Schemas
# ============================================================================

class PlaygroundSessionCreate(BaseModel):
    """创建会话请求"""
    deployment_id: Optional[int] = None
    session_name: Optional[str] = "Untitled Session"
    model_config: Dict[str, Any] = Field(
        ...,
        example={
            "model": "llama-3-8b-instruct",
            "temperature": 0.7,
            "topP": 0.9,
            "maxTokens": 2048,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0,
            "systemPrompt": "You are a helpful assistant"
        }
    )


class PlaygroundMessageCreate(BaseModel):
    """发送消息请求"""
    content: str = Field(..., min_length=1)


class PlaygroundMessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaygroundSessionResponse(BaseModel):
    """会话响应"""
    id: int
    user_id: int
    deployment_id: Optional[int]
    session_name: str
    model_config: Dict[str, Any]
    input_tokens: int
    output_tokens: int
    total_cost: float
    created_at: datetime
    updated_at: datetime
    messages: List[PlaygroundMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Benchmark (批量测试) Schemas
# ============================================================================

class BenchmarkTaskCreate(BaseModel):
    """创建评测任务请求"""
    deployment_id: Optional[int] = None
    task_name: str = Field(..., min_length=1, max_length=255)
    task_type: TaskType
    config: Dict[str, Any] = Field(
        ...,
        example={
            "model": "llama-3-8b-instruct",
            "dataset": "mmlu",
            "data_type": "all",
            "limit": 100,
            "generation_config": {
                "max_tokens": 2048,
                "temperature": 0.7
            }
        }
    )


class BenchmarkTaskResponse(BaseModel):
    """评测任务响应"""
    id: int
    user_id: int
    deployment_id: Optional[int]
    task_name: str
    task_type: str
    status: str
    config: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    output_dir: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BenchmarkDatasetResponse(BaseModel):
    """评测数据集响应"""
    id: int
    name: str
    category: Optional[str]
    description: Optional[str]
    dataset_size: Optional[int]
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

## API 接口设计

### 1. 对话测试 API

```python
# backend/api/v1/playground.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.models.schemas import (
    PlaygroundSessionCreate,
    PlaygroundSessionResponse,
    PlaygroundMessageCreate,
    PlaygroundMessageResponse
)
from backend.services.playground_service import PlaygroundService
from backend.api.deps import get_current_db, get_current_user

router = APIRouter()


@router.post("/sessions", response_model=PlaygroundSessionResponse)
async def create_session(
    session_data: PlaygroundSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """
    创建对话测试会话

    - **deployment_id**: 部署 ID（可选，用于指定模型服务）
    - **session_name**: 会话名称
    - **model_config**: 模型配置参数
    """
    service = PlaygroundService(db)
    return service.create_session(current_user.id, session_data)


@router.get("/sessions", response_model=List[PlaygroundSessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """
    获取用户的对话会话列表

    - **skip**: 跳过记录数
    - **limit**: 返回记录数（最大 100）
    """
    service = PlaygroundService(db)
    return service.list_sessions(current_user.id, skip, limit)


@router.get("/sessions/{session_id}", response_model=PlaygroundSessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """获取单个会话详情（包含消息历史）"""
    service = PlaygroundService(db)
    session = service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/messages", response_model=PlaygroundMessageResponse)
async def send_message(
    session_id: int,
    message: PlaygroundMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """
    发送消息并获取 AI 响应

    - **content**: 用户消息内容
    - 返回：assistant 的回复消息
    """
    service = PlaygroundService(db)
    try:
        return service.send_message(session_id, current_user.id, message.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """删除对话会话"""
    service = PlaygroundService(db)
    service.delete_session(session_id, current_user.id)
    return {"message": "Session deleted"}
```

### 2. 批量测试 API

```python
# backend/api/v1/benchmark.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.models.schemas import (
    BenchmarkTaskCreate,
    BenchmarkTaskResponse,
    BenchmarkDatasetResponse
)
from backend.services.benchmark_service import BenchmarkService
from backend.api.deps import get_current_db, get_current_user

router = APIRouter()


@router.post("/tasks", response_model=BenchmarkTaskResponse, status_code=201)
async def create_benchmark_task(
    task_data: BenchmarkTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """
    创建批量测试任务（异步执行）

    - **task_name**: 任务名称
    - **task_type**: 任务类型（eval=效果评测, perf=性能测试）
    - **deployment_id**: 部署 ID
    - **config**: EvalScope 配置参数

    返回任务信息（任务在后台异步执行）
    """
    service = BenchmarkService(db)
    return service.create_task(current_user.id, task_data)


@router.get("/tasks", response_model=List[BenchmarkTaskResponse])
async def list_benchmark_tasks(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """
    获取批量测试任务列表

    - **status**: 过滤状态（pending/running/completed/failed）
    - **skip**: 跳过记录数
    - **limit**: 返回记录数
    """
    service = BenchmarkService(db)
    return service.list_tasks(current_user.id, status, skip, limit)


@router.get("/tasks/{task_id}", response_model=BenchmarkTaskResponse)
async def get_benchmark_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """
    获取单个任务详情

    包含任务状态、配置、结果等信息
    """
    service = BenchmarkService(db)
    task = service.get_task(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}")
async def cancel_benchmark_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_db)
):
    """
    取消/删除批量测试任务

    - 如果任务正在运行，尝试取消 Celery 任务
    - 如果任务已完成，仅删除记录
    """
    service = BenchmarkService(db)
    service.cancel_task(task_id, current_user.id)
    return {"message": "Task cancelled"}


@router.get("/datasets", response_model=List[BenchmarkDatasetResponse])
async def list_benchmark_datasets(
    category: Optional[str] = None,
    db: Session = Depends(get_current_db)
):
    """
    获取可用的评测数据集列表

    - **category**: 数据集分类过滤（mmlu/gsm8k/ceval）
    """
    service = BenchmarkService(db)
    return service.list_datasets(category)
```

## 服务层设计

### 1. PlaygroundService（对话测试服务）

```python
# backend/services/playground_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.database import PlaygroundSession, PlaygroundMessage
from backend.models.schemas import PlaygroundSessionCreate
from backend.core.config import settings
import httpx
import tiktoken


class PlaygroundService:
    """对话测试服务"""

    def __init__(self, db: Session):
        self.db = db
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def create_session(
        self,
        user_id: int,
        data: PlaygroundSessionCreate
    ) -> PlaygroundSession:
        """创建新会话"""
        session = PlaygroundSession(
            user_id=user_id,
            deployment_id=data.deployment_id,
            session_name=data.session_name,
            model_config=data.model_config
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def list_sessions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[PlaygroundSession]:
        """获取会话列表"""
        return self.db.query(PlaygroundSession)\
            .filter(PlaygroundSession.user_id == user_id)\
            .order_by(PlaygroundSession.updated_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    def get_session(
        self,
        session_id: int,
        user_id: int
    ) -> Optional[PlaygroundSession]:
        """获取会话详情（包含消息）"""
        return self.db.query(PlaygroundSession)\
            .filter(
                PlaygroundSession.id == session_id,
                PlaygroundSession.user_id == user_id
            )\
            .first()

    def send_message(
        self,
        session_id: int,
        user_id: int,
        content: str
    ) -> PlaygroundMessage:
        """
        发送消息并获取 AI 响应

        流程：
        1. 保存用户消息
        2. 调用 OpenAI 兼容 API
        3. 保存 AI 响应
        4. 更新会话统计
        """
        session = self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")

        # 1. 保存用户消息
        user_message = PlaygroundMessage(
            session_id=session_id,
            role="user",
            content=content,
            input_tokens=len(self.encoding.encode(content))
        )
        self.db.add(user_message)

        # 2. 准备请求历史
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages[-10:]  # 最近 10 条消息
        ]
        messages.append({"role": "user", "content": content})

        # 系统提示词
        if session.model_config.get("systemPrompt"):
            messages.insert(0, {
                "role": "system",
                "content": session.model_config["systemPrompt"]
            })

        # 3. 调用推理 API
        api_url = f"{settings.INFERENCE_SERVICE_URL}/v1/chat/completions"
        response = httpx.post(api_url, json={
            "model": session.model_config["model"],
            "messages": messages,
            "temperature": session.model_config.get("temperature", 0.7),
            "max_tokens": session.model_config.get("maxTokens", 2048),
            "top_p": session.model_config.get("topP", 0.9)
        }, timeout=60)

        response_data = response.json()
        assistant_content = response_data["choices"][0]["message"]["content"]
        usage = response_data.get("usage", {})

        # 4. 保存 AI 响应
        assistant_message = PlaygroundMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            output_tokens=usage.get("completion_tokens", 0)
        )
        self.db.add(assistant_message)

        # 5. 更新会话统计
        session.input_tokens += usage.get("prompt_tokens", user_message.input_tokens)
        session.output_tokens += usage.get("completion_tokens", assistant_message.output_tokens)
        session.total_cost = (session.input_tokens + session.output_tokens) * 0.0001

        self.db.commit()
        self.db.refresh(assistant_message)
        return assistant_message

    def delete_session(self, session_id: int, user_id: int):
        """删除会话"""
        session = self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        self.db.delete(session)
        self.db.commit()
```

### 2. BenchmarkService（批量测试服务）

```python
# backend/services/benchmark_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.database import BenchmarkTask, BenchmarkDataset, TaskStatus
from backend.models.schemas import BenchmarkTaskCreate
from backend.workers.benchmark_tasks import run_eval_task, run_perf_task
from backend.core.celery_app import celery_app


class BenchmarkService:
    """批量测试服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        user_id: int,
        data: BenchmarkTaskCreate
    ) -> BenchmarkTask:
        """
        创建评测任务并提交到 Celery

        流程：
        1. 创建任务记录（状态：pending）
        2. 提交到 Celery 异步执行
        3. 更新 celery_task_id
        """
        task = BenchmarkTask(
            user_id=user_id,
            deployment_id=data.deployment_id,
            task_name=data.task_name,
            task_type=data.task_type,
            status=TaskStatus.PENDING,
            config=data.config
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        # 提交到 Celery
        if data.task_type == "eval":
            celery_task = run_eval_task.delay(task.id)
        else:  # perf
            celery_task = run_perf_task.delay(task.id)

        # 更新 Celery 任务 ID
        task.celery_task_id = celery_task.id
        self.db.commit()

        return task

    def list_tasks(
        self,
        user_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[BenchmarkTask]:
        """获取任务列表"""
        query = self.db.query(BenchmarkTask)\
            .filter(BenchmarkTask.user_id == user_id)

        if status:
            query = query.filter(BenchmarkTask.status == status)

        return query.order_by(BenchmarkTask.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    def get_task(
        self,
        task_id: int,
        user_id: int
    ) -> Optional[BenchmarkTask]:
        """获取任务详情"""
        return self.db.query(BenchmarkTask)\
            .filter(
                BenchmarkTask.id == task_id,
                BenchmarkTask.user_id == user_id
            )\
            .first()

    def cancel_task(self, task_id: int, user_id: int):
        """
        取消任务

        1. 如果任务正在运行，撤销 Celery 任务
        2. 更新状态为 cancelled
        """
        task = self.get_task(task_id, user_id)
        if not task:
            raise ValueError("Task not found")

        if task.celery_task_id and task.status == TaskStatus.RUNNING:
            # 撤销 Celery 任务
            celery_app.control.revoke(task.celery_task_id, terminate=True)

        task.status = TaskStatus.CANCELLED
        self.db.commit()

    def list_datasets(
        self,
        category: Optional[str] = None
    ) -> List[BenchmarkDataset]:
        """获取可用的评测数据集"""
        query = self.db.query(BenchmarkDataset)\
            .filter(BenchmarkDataset.is_active == True)

        if category:
            query = query.filter(BenchmarkDataset.category == category)

        return query.order_by(BenchmarkDataset.name).all()
```

## Celery 配置与任务实现

### 1. Celery 配置

```python
# backend/core/celery_app.py

from celery import Celery
from backend.core.config import settings

celery_app = Celery(
    "tokenmachine",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.workers.benchmark_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
```

### 2. Celery 任务定义

```python
# backend/workers/benchmark_tasks.py

import os
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from backend.core.celery_app import celery_app
from backend.core.database import SessionLocal
from backend.models.database import BenchmarkTask, TaskStatus
from backend.core.config import settings


@celery_app.task(bind=True, max_retries=3)
def run_eval_task(self, task_id: int):
    """
    执行效果评测任务（调用 EvalScope API）

    流程：
    1. 更新任务状态为 running
    2. 同步调用 EvalScope /api/v1/eval
    3. 解析结果并更新数据库
    4. 状态改为 completed/failed

    注意：
    - EvalScope API 是同步阻塞调用
    - 任务执行时间可能长达数十分钟
    - 完成后更新数据库，前端通过轮询获取结果
    """
    db: Session = SessionLocal()
    try:
        task = db.query(BenchmarkTask).filter(BenchmarkTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # 更新状态：运行中
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        db.commit()

        # 调用 EvalScope API
        evalscope_url = os.getenv("EVALSCOPE_SERVICE_URL", "http://localhost:9000")

        with httpx.Client(timeout=3600) as client:
            response = client.post(
                f"{evalscope_url}/api/v1/eval",
                json=task.config,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()

        # 保存结果
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.output_dir = result.get("output_dir")
        task.completed_at = datetime.now()
        db.commit()

        return {"task_id": task_id, "status": "completed"}

    except Exception as e:
        # 任务失败
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            db.commit()

        # 重试逻辑
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {"task_id": task_id, "status": "failed", "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def run_perf_task(self, task_id: int):
    """
    执行性能测试任务（调用 EvalScope API）

    流程：
    1. 更新任务状态为 running
    2. 同步调用 EvalScope /api/v1/perf
    3. 解析结果（QPS、延迟、吞吐量等）
    4. 状态改为 completed/failed

    性能指标：
    - QPS (Queries Per Second)
    - Token 吞吐量 (tokens/second)
    - P50/P95/P99 延迟
    - GPU 利用率
    """
    db: Session = SessionLocal()
    try:
        task = db.query(BenchmarkTask).filter(BenchmarkTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # 更新状态：运行中
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        db.commit()

        # 调用 EvalScope API
        evalscope_url = os.getenv("EVALSCOPE_SERVICE_URL", "http://localhost:9000")

        with httpx.Client(timeout=3600) as client:
            response = client.post(
                f"{evalscope_url}/api/v1/perf",
                json=task.config,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()

        # 保存结果
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.output_dir = result.get("output_dir")
        task.completed_at = datetime.now()
        db.commit()

        return {"task_id": task_id, "status": "completed"}

    except Exception as e:
        # 任务失败
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            db.commit()

        # 重试逻辑
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {"task_id": task_id, "status": "failed", "error": str(e)}

    finally:
        db.close()
```

## 部署配置

### 1. 环境变量

```bash
# backend/.env

# EvalScope 服务地址
EVALSCOPE_SERVICE_URL=http://localhost:9000

# Celery 配置
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# 推理服务地址
INFERENCE_SERVICE_URL=http://localhost:8000

# Token 费率（元/token）
TOKEN_COST_RATE=0.0001
```

### 2. 启动 Celery Worker

```bash
# 开发环境
celery -A backend.core.celery_app worker --loglevel=info --concurrency=2

# 生产环境（使用 Supervisor）
# /etc/supervisor/conf.d/celery.conf
[program:celery]
command=/opt/tokenmachine/venv/bin/celery -A backend.core.celery_app worker --loglevel=info --concurrency=4
directory=/opt/tokenmachine
user=tokenmachine
numprocs=1
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log
```

### 3. Docker Compose 配置

```yaml
# infra/docker/docker-compose.yml

services:
  # FastAPI Backend
  api:
    build:
      context: ../..
      dockerfile: infra/docker/Dockerfile.backend
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - EVALSCOPE_SERVICE_URL=http://evalscope:9000
    depends_on:
      - postgres
      - redis

  # Celery Worker
  celery-worker:
    build:
      context: ../..
      dockerfile: infra/docker/Dockerfile.backend
    command: celery -A backend.core.celery_app worker --loglevel=info --concurrency=2
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - EVALSCOPE_SERVICE_URL=http://evalscope:9000
    depends_on:
      - redis
    volumes:
      - ./benchmark_outputs:/app/outputs  # EvalScope 输出目录

  # EvalScope Service（可选，用于评测）
  evalscope:
    image: modelscope/evalscope:latest
    ports:
      - "9000:9000"
    volumes:
      - ./benchmark_outputs:/app/outputs

  # Redis（Broker + Backend）
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## 数据保留策略

### 1. 对话测试数据
- **保留时间**: 30 天
- **清理方式**: 定时任务每天清理过期会话
- **实现**: 使用 PostgreSQL `pg_cron` 扩展

```sql
-- 每天凌晨 2 点清理 30 天前的会话
SELECT cron.schedule('cleanup_old_sessions', '0 2 * * *', $$
    DELETE FROM playground_messages
    WHERE session_id IN (
        SELECT id FROM playground_sessions
        WHERE created_at < NOW() - INTERVAL '30 days'
    );
    DELETE FROM playground_sessions
    WHERE created_at < NOW() - INTERVAL '30 days';
$$);
```

### 2. 批量测试数据
- **任务记录**: 永久保留（用于历史查询）
- **输出文件**: 90 天后自动清理
- **清理方式**: 定时任务删除文件系统中过期报告

```python
# backend/scripts/cleanup_benchmark_outputs.py

import os
from datetime import datetime, timedelta
from backend.models.database import BenchmarkTask
from backend.core.database import SessionLocal

def cleanup_old_outputs():
    """清理 90 天前的 EvalScope 输出文件"""
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=90)

        # 查找过期任务
        old_tasks = db.query(BenchmarkTask)\
            .filter(
                BenchmarkTask.completed_at < cutoff_date,
                BenchmarkTask.output_dir.isnot(None)
            )\
            .all()

        for task in old_tasks:
            # 删除文件
            if os.path.exists(task.output_dir):
                import shutil
                shutil.rmtree(task.output_dir)

            # 清空路径字段
            task.output_dir = None

        db.commit()
        print(f"Cleaned up {len(old_tasks)} old benchmark outputs")

    finally:
        db.close()
```

## 前端集成示例

### 1. 对话测试组件集成

```typescript
// ui/src/api/playground.ts

export interface PlaygroundSession {
  id: number;
  session_name: string;
  model_config: {
    model: string;
    temperature: number;
    topP: number;
    maxTokens: number;
    systemPrompt?: string;
  };
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
  messages: Message[];
}

export const playgroundApi = {
  // 创建会话
  createSession: (data: PlaygroundSessionCreate) =>
    request.post<PlaygroundSession>('/api/v1/playground/sessions', data),

  // 获取会话列表
  listSessions: () =>
    request.get<PlaygroundSession[]>('/api/v1/playground/sessions'),

  // 发送消息
  sendMessage: (sessionId: number, content: string) =>
    request.post<Message>(`/api/v1/playground/sessions/${sessionId}/messages`, {
      content
    })
};
```

### 2. 批量测试组件集成

```typescript
// ui/src/api/benchmark.ts

export const benchmarkApi = {
  // 创建评测任务
  createTask: (data: BenchmarkTaskCreate) =>
    request.post<BenchmarkTask>('/api/v1/benchmark/tasks', data),

  // 获取任务列表
  listTasks: (status?: string) =>
    request.get<BenchmarkTask[]>('/api/v1/benchmark/tasks', {
      params: { status }
    }),

  // 获取任务详情
  getTask: (taskId: number) =>
    request.get<BenchmarkTask>(`/api/v1/benchmark/tasks/${taskId}`),

  // 取消任务
  cancelTask: (taskId: number) =>
    request.delete(`/api/v1/benchmark/tasks/${taskId}`),

  // 获取数据集列表
  listDatasets: (category?: string) =>
    request.get<BenchmarkDataset[]>('/api/v1/benchmark/datasets', {
      params: { category }
    })
};
```

### 3. 任务状态轮询

```typescript
// ui/src/components/playground/BenchmarkTest.tsx

const useTaskPolling = (taskId: number) => {
  const [task, setTask] = useState<BenchmarkTask | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 轮询间隔（3 秒）
    const interval = setInterval(async () => {
      const result = await benchmarkApi.getTask(taskId);
      setTask(result);

      // 任务完成或失败时停止轮询
      if (result.status === 'completed' || result.status === 'failed') {
        setLoading(false);
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [taskId]);

  return { task, loading };
};
```

## 测试策略

### 1. 单元测试

```python
# tests/unit/test_playground_service.py

import pytest
from backend.services.playground_service import PlaygroundService
from backend.models.schemas import PlaygroundSessionCreate

def test_create_session(db_session, test_user):
    """测试创建会话"""
    service = PlaygroundService(db_session)
    data = PlaygroundSessionCreate(
        session_name="Test Session",
        model_config={"model": "llama-3-8b", "temperature": 0.7}
    )

    session = service.create_session(test_user.id, data)

    assert session.user_id == test_user.id
    assert session.session_name == "Test Session"
    assert session.model_config["temperature"] == 0.7
```

### 2. 集成测试

```python
# tests/integration/test_benchmark_tasks.py

import pytest
from backend.workers.benchmark_tasks import run_eval_task
from backend.models.database import BenchmarkTask, TaskStatus

@pytest.mark.integration
def test_eval_task_execution(db_session, test_deployment):
    """测试 EvalScope 任务执行（集成测试）"""
    # 创建测试任务
    task = BenchmarkTask(
        user_id=1,
        deployment_id=test_deployment.id,
        task_name="Integration Test",
        task_type="eval",
        status=TaskStatus.PENDING,
        config={"model": "llama-3-8b", "dataset": "mmlu"}
    )
    db_session.add(task)
    db_session.commit()

    # 执行任务
    result = run_eval_task(task.id)

    assert result["status"] in ["completed", "failed"]

    # 验证数据库更新
    updated_task = db_session.query(BenchmarkTask).filter_by(id=task.id).first()
    assert updated_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
```

## 总结

Playground 后端设计采用以下架构：

1. **对话测试 (ChatTest)**:
   - 基于 REST API 的实时交互
   - Session + Message 两层模型
   - 集成现有 OpenAI 兼容 API
   - Token 计费和统计

2. **批量测试 (BenchmarkTest)**:
   - Celery 异步任务队列
   - EvalScope 框架集成
   - 任务状态跟踪
   - 文件系统 + 数据库混合存储

3. **部署要求**:
   - Redis（Celery Broker + Backend）
   - Celery Worker（独立进程）
   - EvalScope Service（可选）

该设计平衡了功能完整性和系统复杂度，适合生产环境部署。

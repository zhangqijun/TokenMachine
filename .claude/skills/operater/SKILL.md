---
name: operater
description: 使用本机开发环境部署后端接口和数据库，帮助前端和后端等开发提供基础环境。
---

部署本机开发环境时:

1. 只允许修改配置文件，修改启动参数。不允许修改代码文件。
2. 使用机器开发环境，如redis和其他数据库。不使用docker环境
3. 本地后端代码用uvicorn启动，端口8000
4. 确认后端8000可访问health接口

---

## 已探查结果记录清单（可直接使用）

### 1. 项目结构
- **配置文件位置**：根目录`.env.development`
- **backend/.env**：软链接`→ ../.env.development`
- **backend/main.py**：FastAPI应用入口
- **数据库迁移**：`migrations/versions/`，当前版本`007_seed_initial_data`

### 2. 数据库配置
- **用户名**：`tokenmachine`
- **密码**：`tokenmachine_password`
- **数据库**：`tokenmachine`
- **连接URL**：`postgresql://tokenmachine:tokenmachine_password@localhost:5432/tokenmachine`
- **服务状态**：已启动
- **迁移状态**：已是最新版本（无需执行alembic upgrade）

### 3. Redis配置
- **连接URL**：`redis://localhost:6379/0`
- **服务状态**：已启动（`redis-cli ping`返回`PONG`）

### 4. 命令环境
- **Python命令**：`python3`（Python 3.12.3）
- **Uvicorn路径**：`/home/ht706/.local/bin/uvicorn`
- **启动命令**：`uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`

### 5. 服务部署信息
- **端口**：8000
- **工作目录**：项目根目录
- **日志文件**：`/tmp/backend.log`
- **后台启动**：`set -a; source .env.development; set +a; nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &`

### 6. 健康检查
- **Health端点**：`http://localhost:8000/health`
- **正常响应**：`{"status":"healthy","version":"0.1.0"}`
- **API文档**：`http://localhost:8000/docs`

### 7. 操作命令速查
```bash
# 检查端口占用
lsof -i :8000

# 查看后端进程
ps aux | grep "uvicorn.*main:app" | grep -v grep

# 停止服务
pkill -f "uvicorn.*main:app"

# 测试数据库
PGPASSWORD=tokenmachine_password psql -h localhost -U tokenmachine -d tokenmachine -c "SELECT 1;"

# 测试Redis
redis-cli ping

# 测试health
curl http://localhost:8000/health

# 查看日志
tail -f /tmp/backend.log
```

**下次部署时直接使用以上信息，跳过探查步骤。**

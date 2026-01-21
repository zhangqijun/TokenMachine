# TokenMachine 部署指南

## 概述

TokenMachine 支持多环境部署，通过智能环境识别和自动化部署脚本实现一键部署。

### 支持的环境

| 环境 | 描述 | 硬件 | 用途 |
|------|------|------|------|
| **development** | 开发环境 | 单卡 RTX 4090 | 本地开发和调试 |
| **test** | 测试环境 | 7卡 RTX 3090 (Bulbaser) | 多节点分布式测试 |
| **production** | 生产环境 | RTX 3090 (Bowser) | 公网生产服务 |

### 环境识别机制

项目通过以下方式自动识别环境：

1. **后端**: `ENVIRONMENT` 环境变量 → Pydantic Enum
2. **前端**: nginx 注入环境变量 → `window.__ENV__` → TypeScript config
3. **部署脚本**: 命令行参数 → 自动选择对应配置

---

## 快速开始

### 前置要求

- Docker & Docker Compose
- NVIDIA GPU (或华为昇腾 NPU)
- 16GB+ 内存
- Python 3.10+ (本地开发)

### 一键部署

```bash
# 开发环境
./scripts/deploy.sh development

# 测试环境
./scripts/deploy.sh test

# 生产环境
./scripts/deploy.sh production
```

### 部署脚本功能

部署脚本自动完成以下操作：

1. ✅ 复制对应环境的配置文件
2. ✅ 检查环境配置（SSL、密码等）
3. ✅ 停止现有服务
4. ✅ 构建 Docker 镜像
5. ✅ 启动所有服务
6. ✅ **自动初始化 mock 数据**（开发/测试环境）
7. ✅ 显示访问地址

---

## 详细部署步骤

### 1. 准备环境配置文件

环境配置文件位于项目根目录：

```bash
.env.development   # 开发环境
.env.test          # 测试环境
.env.production    # 生产环境
```

#### 配置项说明

```env
# === 基础配置 ===
ENVIRONMENT=production               # 环境标识
DEBUG=false                          # 调试模式

# === 数据库 ===
POSTGRES_PASSWORD=your_secure_password

# === API 安全 ===
SECRET_KEY=$(openssl rand -hex 32)  # 生成安全密钥
API_KEY_PREFIX=tmachine_sk_

# === 功能开关 ===
USE_MOCK_DATA=false                  # 是否使用 mock 数据（生产环境设为 false）
```

#### 生产环境安全配置

生产环境需要以下额外配置：

```bash
# 1. 生成 SECRET_KEY
openssl rand -hex 32

# 2. 配置 SSL 证书路径
SSL_CERT_PATH=/etc/nginx/ssl/zhangqijun.cn.crt
SSL_KEY_PATH=/etc/nginx/ssl/zhangqijun.cn.key

# 3. 配置公网域名和 IP
PUBLIC_DOMAIN=zhangqijun.cn
PUBLIC_IP=10.0.0.147
```

---

### 2. 开发环境部署

#### 硬件配置
- **GPU**: 单卡 RTX 4090
- **内存**: 32GB+
- **存储**: 100GB+

#### 部署命令

```bash
# 基础部署
./scripts/deploy.sh development

# 部署并初始化 mock 数据（默认）
./scripts/deploy.sh development --init-mock

# 重新初始化数据
./scripts/deploy.sh development --init-mock --clear-data

# 部署但不初始化数据
./scripts/deploy.sh development --skip-mock
```

#### 服务端口

| 服务 | 端口 | 访问地址 |
|------|------|----------|
| Web UI | 8081 | http://localhost:8081 |
| API | 8000 | http://localhost:8000 |
| API 文档 | 8000 | http://localhost:8000/docs |
| Grafana | 3001 | http://localhost:3001 |
| Prometheus | 9091 | http://localhost:9091 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |

#### 特点

- ✅ 使用 mock 数据（可切换到真实 API）
- ✅ DEBUG 模式启用
- ✅ 热重载（API Reload = true）
- ✅ 较高的 GPU 内存利用率 (0.85)
- ✅ 支持更长的模型长度 (8192)

---

### 3. 测试环境部署

#### 硬件配置
- **GPU**: 7卡 RTX 3090
- **机器**: Bulbaser (10.0.0.100)
- **网络**: 多节点分布式部署

#### 部署命令

```bash
# 基础部署（包含 mock 数据初始化）
./scripts/deploy.sh test

# 清空数据并重新初始化
./scripts/deploy.sh test --init-mock --clear-data
```

#### 多节点配置

测试环境支持多节点分布式部署，在 `.env.test` 中配置：

```env
# 节点配置
NODE_ID=node1
NODE_LIST=node1:10.0.0.100,node2:10.0.0.101,node3:10.0.0.102
WORKER_COUNT=7

# GPU 配置
VLLM_TENSOR_PARALLEL_SIZE=2
```

#### 服务端口

| 服务 | 局域网地址 |
|------|-----------|
| Web UI | http://10.0.0.100:8081 |
| API | http://10.0.0.100:8000 |
| API 文档 | http://10.0.0.100:8000/docs |
| Grafana | http://10.0.0.100:3001 |
| Prometheus | http://10.0.0.100:9091 |

#### 特点

- ✅ 7 个 Worker 并行
- ✅ 多节点分布式部署
- ✅ 启用性能日志
- ✅ 允许测试模型
- ✅ 使用 mock 数据

---

### 4. 生产环境部署

#### 硬件配置
- **GPU**: RTX 3090
- **机器**: Bowser (10.0.0.147)
- **网络**: 公网访问

#### 部署命令

```bash
# 基础部署（不初始化 mock 数据）
./scripts/deploy.sh production

# 部署并初始化数据（需要确认）
./scripts/deploy.sh production --init-mock
```

#### SSL 证书配置

1. **准备证书文件**

```bash
mkdir -p ~/zhangqijun.cn_apache
cd ~/zhangqijun.cn_apache

# 上传以下文件：
# - zhangqijun.cn.crt       # 证书文件
# - zhangqijun.cn.key       # 私钥文件
# - root_bundle.crt         # 证书链
```

2. **验证证书**

```bash
ls -la ~/zhangqijun.cn_apache/
```

#### 路由器端口转发配置

SSH 到路由器 (10.0.0.1)，添加端口转发规则：

```bash
# SSH 到路由器
ssh root@10.0.0.1

# HTTPS 转发 (8443 -> 10.0.0.147:8443)
uci add firewall redirect
uci set firewall.@redirect[-1].name='tokenmachine-https'
uci set firewall.@redirect[-1].src='wan'
uci set firewall.@redirect[-1].dest='lan'
uci set firewall.@redirect[-1].src_dport='8443'
uci set firewall.@redirect[-1].dest_ip='10.0.0.147'
uci set firewall.@redirect[-1].dest_port='8443'
uci set firewall.@redirect[-1].target='DNAT'
uci commit firewall
/etc/init.d/firewall restart

# HTTP 转发 (8080 -> 10.0.0.147:8080)
uci add firewall redirect
uci set firewall.@redirect[-1].name='tokenmachine-http'
uci set firewall.@redirect[-1].src='wan'
uci set firewall.@redirect[-1].dest='lan'
uci set firewall.@redirect[-1].src_dport='8080'
uci set firewall.@redirect[-1].dest_ip='10.0.0.147'
uci set firewall.@redirect[-1].dest_port='8080'
uci set firewall.@redirect[-1].target='DNAT'
uci commit firewall
/etc/init.d/firewall restart

# Grafana 转发 (3001 -> 10.0.0.147:3001)
uci add firewall redirect
uci set firewall.@redirect[-1].name='tokenmachine-grafana'
uci set firewall.@redirect[-1].src='wan'
uci set firewall.@redirect[-1].dest='lan'
uci set firewall.@redirect[-1].src_dport='3001'
uci set firewall.@redirect[-1].dest_ip='10.0.0.147'
uci set firewall.@redirect[-1].dest_port='3001'
uci set firewall.@redirect[-1].target='DNAT'
uci commit firewall
/etc/init.d/firewall restart
```

#### 服务端口

| 服务 | 局域网地址 | 公网地址 |
|------|-----------|----------|
| Web UI (HTTPS) | https://10.0.0.147:8443 | https://zhangqijun.cn:8443 |
| API | https://10.0.0.147:8443/api | https://zhangqijun.cn:8443/api |
| API 文档 | https://10.0.0.147:8443/docs | https://zhangqijun.cn:8443/docs |
| Grafana | http://10.0.0.147:3001 | http://zhangqijun.cn:3001 |
| Prometheus | http://10.0.0.147:9091 | http://zhangqijun.cn:9091 |

#### 特点

- ✅ HTTPS 加密访问
- ✅ SSL 证书配置
- ✅ 路由器端口转发
- ✅ **不使用 mock 数据**（真实 API）
- ✅ GPU 驱动兼容配置
- ✅ 安全加固配置

---

## Mock 数据管理

### 自动初始化

开发/测试环境部署时会自动初始化 mock 数据，包括：

- 2 个组织
- 2 个用户
- 3 个 API Keys
- 6 个模型
- 4 个部署
- 8 个 GPU
- 4 条使用日志

### 手动初始化

```bash
# 进入 docker 目录
cd infra/docker

# 初始化当前环境数据
docker compose exec api python scripts/init_mock_data.py

# 指定环境
docker compose exec api python scripts/init_mock_data.py --environment development

# 清空现有数据后初始化
docker compose exec api python scripts/init_mock_data.py --environment test --clear

# 生产环境初始化（需要确认）
docker compose exec api python scripts/init_mock_data.py --environment production --force
```

### 数据切换

#### 前端切换 mock/真实数据

1. **环境变量方式**（推荐）：

在 `.env.*` 文件中设置：
```env
USE_MOCK_DATA=true   # 使用 mock 数据
USE_MOCK_DATA=false  # 使用真实 API
```

重新部署后生效。

2. **运行时方式**：

在浏览器控制台中：
```javascript
// 临时切换到 mock 数据
window.__ENV__.USE_MOCK_DATA = 'true';
location.reload();

// 临时切换到真实 API
window.__ENV__.USE_MOCK_DATA = 'false';
location.reload();
```

#### 后端切换 mock/真实数据

后端通过 `Settings.use_mock_data` 配置项控制，用于：
- API 响应中是否返回 mock 数据
- 数据库查询是否被 mock 数据替代

---

## 常用命令

### 服务管理

```bash
# 进入 docker 目录
cd infra/docker

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f [service_name]

# 查看特定服务日志
docker compose logs -f api
docker compose logs -f web

# 重启服务
docker compose restart [service_name]

# 停止服务
docker compose down

# 停止并删除数据卷
docker compose down -v

# 重新构建并启动
docker compose up -d --build

# 进入容器
docker compose exec api bash
docker compose exec web sh
```

### 数据库操作

```bash
# 进入 PostgreSQL 容器
docker compose exec postgres psql -U tokenmachine -d tokenmachine

# 备份数据库
docker compose exec postgres pg_dump -U tokenmachine tokenmachine > backup.sql

# 恢复数据库
docker compose exec -T postgres psql -U tokenmachine tokenmachine < backup.sql

# 运行数据库迁移
docker compose exec api alembic upgrade head

# 回滚迁移
docker compose exec api alembic downgrade -1
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# Prometheus 指标
curl http://localhost:9090/metrics

# 测试 API 调用
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5-7b-instruct", "messages": [{"role": "user", "content": "Hello!"}]}'
```

---

## 故障排查

### 端口被占用

```bash
# 查找占用端口的进程
sudo lsof -i :<port>

# 或使用 netstat
sudo netstat -tulpn | grep :<port>

# 停止占用端口的容器
docker compose down
```

### 容器启动失败

```bash
# 查看容器日志
docker compose logs [service_name]

# 检查容器状态
docker compose ps

# 查看详细信息
docker inspect [container_name]
```

### 数据库连接问题

```bash
# 检查 PostgreSQL 容器健康状态
docker compose ps postgres

# 查看 PostgreSQL 日志
docker compose logs postgres

# 测试数据库连接
docker compose exec postgres pg_isready -U tokenmachine
```

### GPU 相关问题

```bash
# 检查 GPU 状态
nvidia-smi

# 检查容器 GPU 访问
docker compose exec api nvidia-smi

# 检查 GPU 内存使用
docker compose exec api python -c "import pynvml; pynvml.nvmlInit(); print(pynvml.nvmlDeviceGetMemoryInfo(pynvml.nvmlDeviceGetHandleByIndex(0)))"
```

### SSL 证书问题

```bash
# 检查证书文件
ls -la ~/zhangqijun.cn_apache/

# 验证证书
openssl x509 -in ~/zhangqijun.cn_apache/zhangqijun.cn.crt -text -noout

# 检查证书有效期
openssl x509 -in ~/zhangqijun.cn_apache/zhangqijun.cn.crt -noout -dates
```

### Mock 数据未初始化

```bash
# 检查初始化脚本
docker compose exec api python scripts/init_mock_data.py --help

# 手动初始化
docker compose exec api python scripts/init_mock_data.py --environment development

# 查看数据库中的数据
docker compose exec postgres psql -U tokenmachine -d tokenmachine -c "SELECT COUNT(*) FROM models;"
```

### 前端无法连接后端

```bash
# 检查环境变量
docker compose exec web env | grep -E "ENVIRONMENT|API_BASE_URL"

# 检查 nginx 配置
docker compose exec web cat /etc/nginx/nginx.conf

# 测试 API 连接
docker compose exec web wget -O- http://api:8000/health

# 检查前端配置
# 打开浏览器控制台，查看:
console.log(window.__ENV__);
```

---

## 监控与维护

### Prometheus 监控

访问 Prometheus: http://localhost:9091

关键指标：
- `tokenmachine_api_requests_total`: API 请求总数
- `tokenmachine_tokens_used_total`: Token 使用总量
- `tokenmachine_gpu_utilization`: GPU 利用率
- `tokenmachine_deployment_status`: 部署状态

### Grafana 仪表盘

访问 Grafana: http://localhost:3001 (默认账号: admin/admin)

配置数据源：
1. 添加 Prometheus 数据源 (http://prometheus:9090)
2. 导入仪表盘模板

### 日志管理

```bash
# 查看应用日志
docker compose logs -f api | grep -E "ERROR|WARN"

# 查看访问日志
docker compose logs -f web

# 导出日志
docker compose logs api > api.log

# 日志轮转配置
# 在 .env 文件中配置
LOG_ROTATION=500 MB
LOG_RETENTION=30 days
```

### 数据备份

#### 自动备份脚本

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backup/tokenmachine"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
docker compose exec -T postgres pg_dump -U tokenmachine tokenmachine > $BACKUP_DIR/db_$DATE.sql

# 备份 Docker volumes
docker run --rm \
  -v tokenmachine_postgres_data:/data \
  -v $BACKUP_DIR:/backup \
  ubuntu tar czf /backup/postgres_$DATE.tar.gz /data

# 保留最近 7 天的备份
find $BACKUP_DIR -mtime +7 -delete
```

#### 恢复数据

```bash
# 恢复数据库
docker compose exec -T postgres psql -U tokenmachine tokenmachine < backup.sql

# 恢复 volume
docker run --rm \
  -v tokenmachine_postgres_data:/data \
  -v $(pwd):/backup \
  ubuntu tar xzf /backup/postgres_backup.tar.gz -C /
```

---

## 安全建议

### 部署前检查清单

- [ ] 修改所有默认密码
- [ ] 生成安全的 SECRET_KEY (`openssl rand -hex 32`)
- [ ] 配置正确的 CORS 源
- [ ] 设置防火墙规则
- [ ] 配置 SSL 证书（生产环境）
- [ ] 限制数据库和 Redis 仅内部访问
- [ ] 定期备份数据
- [ ] 配置日志监控和告警

### 密码管理

```bash
# 生成安全密码
openssl rand -base64 32

# 或使用
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### API Key 管理

```bash
# 创建 API Key
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -d '{"name": "Production Key", "quota_tokens": 100000000}'

# 轮换 API Key
# 1. 创建新 Key
# 2. 更新应用配置
# 3. 停用旧 Key
```

---

## 多环境切换

### 在机器之间切换

```bash
# 1. SSH 到目标机器
ssh bowser      # 生产环境
ssh bulbaser    # 测试环境
# 当前机器      # 开发环境

# 2. 运行部署脚本
./scripts/deploy.sh [environment]

# 3. 验证部署
curl http://localhost:8000/health
```

### 环境迁移

```bash
# 从开发环境导出数据
docker compose exec postgres pg_dump -U tokenmachine tokenmachine > dev_data.sql

# 在测试环境导入
scp dev_data.sql bulbaser:~/
ssh bulbaser
cd /home/ht706/Documents/TokenMachine/infra/docker
cat ~/dev_data.sql | docker compose exec -T postgres psql -U tokenmachine tokenmachine
```

---

## 性能优化

### GPU 配置优化

```env
# 提高 GPU 内存利用率
GPU_MEMORY_UTILIZATION=0.95

# 增加模型长度
MAX_MODEL_LEN=16384

# 张量并行度（多 GPU）
VLLM_TENSOR_PARALLEL_SIZE=2
```

### 数据库连接池

```env
# 连接池大小
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### Redis 缓存

```env
# Redis 连接池大小
REDIS_POOL_SIZE=20
```

---

## 附录

### A. 环境变量完整列表

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ENVIRONMENT` | 环境标识 | development |
| `DEBUG` | 调试模式 | true |
| `USE_MOCK_DATA` | 使用 mock 数据 | false |
| `DATABASE_URL` | PostgreSQL 连接字符串 | - |
| `REDIS_URL` | Redis 连接字符串 | - |
| `SECRET_KEY` | JWT 密钥 | - |
| `GPU_MEMORY_UTILIZATION` | GPU 内存利用率 | 0.9 |
| `MAX_MODEL_LEN` | 最大模型长度 | 4096 |

### B. 端口映射表

| 内部端口 | 外部端口 | 服务 | 说明 |
|---------|---------|------|------|
| 80 | 8081/8080 | Web | HTTP |
| 443 | 8443 | Web | HTTPS |
| 8000 | 8000 | API | FastAPI |
| 9090 | 9090 | Metrics | Prometheus |
| 5432 | 5432 | PostgreSQL | 数据库 |
| 6379 | 6379 | Redis | 缓存 |
| 3000 | 3001 | Grafana | 监控 |
| 9090 | 9091 | Prometheus | 指标 |

### C. 目录结构

```
TokenMachine/
├── backend/              # Python 后端
├── ui/                   # React 前端
├── infra/
│   └── docker/          # Docker 配置
│       ├── docker-compose.yml
│       ├── docker-compose.test.yml
│       ├── docker-compose.production.yml
│       └── nginx/       # Nginx 配置
├── scripts/             # 部署脚本
│   ├── deploy.sh       # 一键部署脚本
│   └── init_mock_data.py  # 数据初始化脚本
├── migrations/          # 数据库迁移
├── docs/                # 文档
├── .env.development     # 开发环境配置
├── .env.test            # 测试环境配置
└── .env.production      # 生产环境配置
```

### D. 相关文档

- [产品设计](docs/PRODUCT_DESIGN.md)
- [后端设计](docs/BACKEND_DESIGN.md)
- [前端设计](docs/FRONTEND_DESIGN.md)
- [测试指南](docs/TESTING.md)

### E. 获取帮助

- GitHub Issues: https://github.com/your-org/tokenmachine/issues
- 文档: https://docs.tokenmachine.com
- 邮件: support@tokenmachine.com

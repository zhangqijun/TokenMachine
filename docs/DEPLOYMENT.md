# TokenMachine 部署文档

## 概述

TokenMachine 支持多环境部署，使用 Docker Compose 进行管理：

- **开发环境** (development): 当前机器 - 单卡 RTX 4090
- **测试环境** (test): Bulbaser - 7卡 RTX 3090 - 多节点分布式部署
- **生产环境** (production): Bowser - RTX 3090 - HTTPS 证书 + 路由器配置

## 环境配置

### 开发环境 (Development)

- **硬件**: 单卡 RTX 4090
- **用途**: 本地开发和调试
- **特点**:
  - 完整服务栈 (API, Web, Database, Redis, Monitoring)
  - DEBUG 模式启用
  - 无 HTTPS (HTTP only)
  - 较高的 GPU 内存利用率 (0.85)
  - 支持更长的模型长度 (8192)

### 测试环境 (Test)

- **硬件**: 7卡 RTX 3090
- **机器**: Bulbaser (10.0.0.100)
- **用途**: 多节点分布式测试
- **特点**:
  - 多节点部署配置
  - 支持 7 个 Worker
  - 启用性能日志
  - 允许测试模型

### 生产环境 (Production)

- **硬件**: RTX 3090
- **机器**: Bowser (10.0.0.147)
- **用途**: 公网生产服务
- **特点**:
  - HTTPS 证书配置
  - 路由器端口转发
  - 驱动问题兼容配置
  - 安全加固配置

## 服务端口

| 服务 | 开发环境 | 测试环境 | 生产环境 |
|------|----------|----------|----------|
| Web HTTP | 8081 | 8081 | 8080 (重定向) |
| Web HTTPS | - | - | 8443 |
| API | 8000 | 8000 | 8000 |
| API Metrics | 9090 | 9090 | 9090 |
| Grafana | 3001 | 3001 | 3001 |
| Prometheus | 9091 | 9091 | 9091 |
| PostgreSQL | 5432 | 5432 | 5432 |
| Redis | 6379 | 6379 | 6379 |

## 快速开始

### 一键部署

使用部署脚本自动部署到指定环境：

```bash
# 开发环境
./scripts/deploy.sh development

# 测试环境
./scripts/deploy.sh test

# 生产环境
./scripts/deploy.sh production
```

### 手动部署

如果需要手动部署，请按照以下步骤：

#### 1. 准备环境配置文件

```bash
# 复制对应环境的配置文件
cp .env.development infra/docker/.env    # 开发环境
# 或
cp .env.test infra/docker/.env          # 测试环境
# 或
cp .env.production infra/docker/.env    # 生产环境
```

#### 2. 修改敏感配置

编辑环境文件，修改以下变量：

```env
# 数据库密码
POSTGRES_PASSWORD=your_secure_password

# API 密钥
SECRET_KEY=your_secret_key

# Grafana 密码
GRAFANA_PASSWORD=your_grafana_password
```

生成安全的 SECRET_KEY:
```bash
openssl rand -hex 32
```

#### 3. 部署服务

```bash
cd infra/docker

# 开发环境
docker compose up -d

# 测试环境 (使用多 GPU)
docker compose -f docker-compose.yml -f docker-compose.test.yml --profile multi-gpu up -d

# 生产环境 (使用 SSL)
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

## 生产环境配置

### SSL 证书配置

生产环境需要 HTTPS 证书。将证书文件放在服务器目录：

```bash
~/zhangqijun.cn_apache/
├── zhangqijun.cn.crt       # 证书文件
├── zhangqijun.cn.key       # 私钥文件
└── root_bundle.crt         # 证书链
```

### 路由器端口转发配置

SSH 到路由器 (10.0.0.1)，添加以下端口转发规则：

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

### GPU 驱动问题处理

生产环境 (Bowser) 的 RTX 3090 存在驱动问题，已在配置中添加以下兼容选项：

```env
VLLM_DISABLE_CUSTOM_ALL_REDUCE=true
```

如果遇到其他 GPU 相关问题，可能需要：
1. 更新 NVIDIA 驱动
2. 降低 GPU 内存利用率
3. 减小张量并行度

## 访问地址

### 开发环境 (当前机器)

```
API:         http://localhost:8000
API 文档:    http://localhost:8000/docs
Web UI:      http://localhost:8081
Grafana:     http://localhost:3001 (admin/admin)
Prometheus:  http://localhost:9091
```

### 测试环境 (Bulbaser)

```
API:         http://10.0.0.100:8000
API 文档:    http://10.0.0.100:8000/docs
Web UI:      http://10.0.0.100:8081
Grafana:     http://10.0.0.100:3001
Prometheus:  http://10.0.0.100:9091
```

### 生产环境 (Bowser)

#### 局域网访问

```
API:         https://10.0.0.147:8443/api
API 文档:    https://10.0.0.147:8443/docs
Web UI:      https://10.0.0.147:8443
Grafana:     http://10.0.0.147:3001
Prometheus:  http://10.0.0.147:9091
```

#### 公网访问

```
API:         https://zhangqijun.cn:8443/api
API 文档:    https://zhangqijun.cn:8443/docs
Web UI:      https://zhangqijun.cn:8443
Grafana:     http://zhangqijun.cn:3001
Prometheus:  http://zhangqijun.cn:9091
```

## 常用命令

```bash
# 进入 docker 目录
cd infra/docker

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f [service_name]

# 重启服务
docker compose restart [service_name]

# 停止服务
docker compose down

# 重新构建并启动
docker compose up -d --build

# 进入容器
docker compose exec api bash
docker compose exec web sh

# 清理所有数据 (危险操作)
docker compose down -v
```

## 环境切换

在机器之间切换部署环境时，需要：

1. **SSH 到目标机器**
   ```bash
   ssh bowser     # 生产环境
   ssh bulbaser   # 测试环境
   # 当前机器     # 开发环境
   ```

2. **运行部署脚本**
   ```bash
   ./scripts/deploy.sh [environment]
   ```

3. **验证部署**
   ```bash
   curl http://localhost:8000/health
   ```

## 数据持久化

以下数据通过 Docker volumes 持久化：

- `postgres_data`: PostgreSQL 数据
- `redis_data`: Redis 数据
- `model_data`: 模型文件
- `log_data`: 应用日志
- `prometheus_data`: Prometheus 监控数据
- `grafana_data`: Grafana 配置

## 备份与恢复

### 备份

```bash
# 备份数据卷
docker run --rm \
  -v tokenmachine_postgres_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

### 恢复

```bash
# 恢复数据卷
docker run --rm \
  -v tokenmachine_postgres_data:/data \
  -v $(pwd):/backup \
  ubuntu tar xzf /backup/postgres_backup.tar.gz -C /
```

## 监控

服务通过 Prometheus 和 Grafana 进行监控：

- Prometheus 收集所有服务的指标
- Grafana 提供可视化面板
- 默认监控端口：9091 (Prometheus), 3001 (Grafana)

## 故障排查

### 端口被占用

```bash
# 查找占用端口的进程
sudo lsof -i :<port>

# 或使用 netstat
sudo netstat -tulpn | grep :<port>
```

### 容器启动失败

查看容器日志：
```bash
docker compose logs [service_name]
```

### 数据库连接问题

确保 PostgreSQL 容器健康：
```bash
docker compose ps postgres
```

### GPU 相关问题

```bash
# 检查 GPU 状态
nvidia-smi

# 检查容器 GPU 访问
docker compose exec api nvidia-smi
```

### SSL 证书问题

确保证书文件存在且权限正确：
```bash
ls -la ~/zhangqijun.cn_apache/
```

## 安全建议

1. **修改默认密码**: 部署前修改所有默认密码
2. **生成安全密钥**: 使用 `openssl rand -hex 32` 生成 SECRET_KEY
3. **限制内部端口**: 数据库和 Redis 端口仅内部访问
4. **定期备份**: 定期备份数据卷
5. **启用防火墙**: 配置适当的防火墙规则
6. **HTTPS 证书**: 生产环境必须使用 HTTPS
7. **监控日志**: 定期检查应用和访问日志

## 多节点部署 (测试环境)

测试环境 (Bulbaser) 支持多节点分布式部署：

### 配置说明

在 `.env.test` 中配置节点信息：

```env
NODE_ID=node1
NODE_LIST=node1:10.0.0.100,node2:10.0.0.101,node3:10.0.0.102
WORKER_COUNT=7
```

### 启动多节点

```bash
# 启动多 GPU 配置
docker compose -f docker-compose.yml -f docker-compose.test.yml --profile multi-gpu up -d
```

## 生产环境检查清单

部署到生产环境前，确认：

- [ ] SSL 证书已配置
- [ ] 路由器端口转发已设置
- [ ] 所有默认密码已修改
- [ ] SECRET_KEY 已生成
- [ ] CORS 配置正确
- [ ] GPU 驱动兼容配置已添加
- [ ] 数据备份计划已制定
- [ ] 监控和日志已配置
- [ ] 防火墙规则已配置

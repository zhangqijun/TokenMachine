# TokenMachine 部署文档

## 概述

TokenMachine 使用 Docker Compose 进行部署，包含以下服务：

- **postgres**: PostgreSQL 15 数据库
- **redis**: Redis 7 缓存
- **api**: FastAPI 后端服务 (端口 8000)
- **web**: React 前端服务 (端口 8080/8443)
- **prometheus**: 监控指标收集 (端口 9091)
- **grafana**: 监控可视化面板 (端口 3001)

## 服务端口

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| Web | 80 | 8080 | HTTP (自动重定向到 HTTPS) |
| Web | 443 | 8443 | HTTPS |
| API | 8000 | 8000 | 后端 API |
| API | 9090 | 9090 | Prometheus Metrics |
| Prometheus | 9090 | 9091 | 监控数据 |
| Grafana | 3000 | 3001 | 监控面板 |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存 |

> 注意：由于公网限制，Web 服务使用非标准端口 (8080/8443)

## 前置要求

- Docker 27.0+
- Docker Compose 2.38+
- SSL 证书文件 (用于 HTTPS)

## 部署步骤

### 1. 准备 SSL 证书

将 SSL 证书文件放在服务器的指定目录，例如 `~/zhangqijun.cn_apache/`：

```
~/zhangqijun.cn_apache/
├── zhangqijun.cn.crt       # 证书文件
├── zhangqijun.cn.key       # 私钥文件
└── root_bundle.crt         # 证书链
```

### 2. 配置环境变量

复制并编辑 `.env` 文件：

```bash
cp .env.production .env
```

修改以下变量：

```env
# 数据库密码
POSTGRES_PASSWORD=your_secure_password

# API 密钥
SECRET_KEY=your_secret_key

# Grafana 密码
GRAFANA_PASSWORD=your_grafana_password
```

### 3. 修改证书路径 (如果需要)

如果证书路径与默认不同，编辑 `docker-compose.yml` 中的 `web` 服务卷挂载：

```yaml
volumes:
  - ~/your_cert_path:/etc/nginx/ssl:ro
```

### 4. 调整端口映射 (如有冲突)

如果默认端口与现有服务冲突，修改 `docker-compose.yml` 中的端口映射。

例如 Grafana 默认使用 3001 端口（避免与其他服务冲突）：

```yaml
ports:
  - "3001:3000"
```

### 5. 构建并启动服务

```bash
# 构建镜像
docker compose build

# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 6. 验证部署

```bash
# 检查后端健康
curl http://localhost:8000/health

# 检查前端
curl -k https://localhost/

# 检查监控指标
curl http://localhost:9090/metrics
```

## 访问地址

### 局域网访问
- **前端**: https://10.0.0.147:8443
- **API 文档**: https://10.0.0.147:8443/docs
- **API 指标**: http://10.0.0.147:9090/metrics
- **Grafana**: http://10.0.0.147:3001 (默认用户名 admin，密码见 .env)
- **Prometheus**: http://10.0.0.147:9091

### 公网访问 (需配置路由器端口转发)
- **前端**: https://zhangqijun.cn:8443
- **API 文档**: https://zhangqijun.cn:8443/docs
- **Grafana**: https://zhangqijun.cn:3001

#### 路由器端口转发配置
需要在路由器上添加以下转发规则：
```bash
# SSH 到路由器
ssh root@10.0.0.1

# 添加 HTTPS 转发 (8443 -> 10.0.0.147:8443)
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

# 添加 HTTP 转发 (8080 -> 10.0.0.147:8080，自动重定向到 HTTPS)
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

# 添加 Grafana 转发 (3001 -> 10.0.0.147:3001)
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

## 常用命令

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 查看日志
docker compose logs -f [service_name]

# 重新构建并启动
docker compose up -d --build

# 进入容器
docker compose exec api bash
docker compose exec web sh

# 清理所有数据 (危险操作)
docker compose down -v
```

## 故障排查

### 端口被占用

如果遇到端口占用错误，使用以下命令查找占用进程：

```bash
# 查找占用端口的进程
sudo lsof -i :<port>

# 或使用 netstat
sudo netstat -tulpn | grep :<port>
```

解决方案：
1. 停止占用端口的服务
2. 或修改 `docker-compose.yml` 中的端口映射

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

如果容器不健康，检查数据卷权限或重建容器。

### 证书问题

确保证书文件存在且 nginx 配置路径正确：

```bash
ls -la ~/zhangqijun.cn_apache/
```

## 数据持久化

以下数据通过 Docker volumes 持久化：

- `postgres_data`: PostgreSQL 数据
- `redis_data`: Redis 数据
- `model_data`: 模型文件
- `log_data`: 应用日志
- `prometheus_data`: Prometheus 监控数据
- `grafana_data`: Grafana 配置

## 安全建议

1. 修改默认密码
2. 使用强密码生成 SECRET_KEY: `openssl rand -hex 32`
3. 限制数据库和 Redis 端口仅内部访问
4. 定期备份数据卷
5. 启用防火墙规则

## 备份与恢复

### 备份

```bash
# 备份数据卷
docker run --rm -v add-deploy-method_188a3c406eb78b61_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

### 恢复

```bash
# 恢复数据卷
docker run --rm -v add-deploy-method_188a3c406eb78b61_postgres_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/postgres_backup.tar.gz -C /
```

## 监控

服务通过 Prometheus 和 Grafana 进行监控：

- Prometheus 收集所有服务的指标
- Grafana 提供可视化面板
- 默认监控端口：9091 (Prometheus), 3001 (Grafana)

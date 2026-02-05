# UI 需要后端提供的 Worker 注册接口

## 1. 创建 Worker 接口

### 接口信息
- **路径**: `POST /api/v1/workers`
- **认证**: 需要 JWT Bearer Token
- **Content-Type**: `application/json`

### 请求参数
```typescript
{
  name: string;              // Worker 名称，必填
  labels?: Record<string, string>;  // 标签，可选
  expected_gpu_count?: number;      // 期望的 GPU 数量，可选
  cluster_id?: number;              // 集群 ID，可选
}
```

### 响应数据（成功）
```typescript
{
  id: number;                // Worker ID
  name: string;              // Worker 名称
  status: string;            // 初始状态，应该是 "REGISTERING"
  register_token: string;    // 注册 Token，格式如 "tm_worker_xxxxxxxxxxxxx"
  install_command?: string;  // 可选：后端生成的安装命令（如果后端生成的话）
  expected_gpu_count: number;
  current_gpu_count: number; // 初始为 0
  created_at: string;        // ISO 8601 格式时间戳
}
```

### 响应数据（失败）

#### 情况 1: Worker 名称已存在
```typescript
{
  detail: string;  // "Worker with name 'xxx' already exists"
}
```
**HTTP Status**: `409 Conflict` 或 `400 Bad Request`

#### 情况 2: 参数验证失败
```typescript
{
  detail: string;  // 具体验证错误信息
}
```
**HTTP Status**: `422 Unprocessable Entity`

### 名称验证规则
- Worker 名称必须唯一
- 只能包含字母、数字、横线（-）和下划线（_）
- 长度限制：建议 1-64 个字符
- 不区分大小写（建议后端统一转为小写存储）

---

## 2. 查询 Worker 状态接口

### 接口信息
- **路径**: `GET /api/v1/workers/{worker_id}`
- **认证**: 需要 JWT Bearer Token

### 响应数据
```typescript
{
  id: number;
  name: string;
  status: 'REGISTERING' | 'READY' | 'BUSY' | 'DRAINING' | 'UNHEALTHY' | 'OFFLINE';
  ip?: string;
  hostname?: string;
  gpu_count: number;              // 当前 GPU 数量
  expected_gpu_count: number;     // 期望 GPU 数量
  labels?: Record<string, string>;
  agent_type?: string;
  agent_version?: string;
  last_heartbeat_at?: string;     // ISO 8601 格式
  created_at: string;
  updated_at: string;
}
```

### 轮询说明
- UI 每 2 秒轮询一次此接口
- 当 `status === 'READY'` 时，UI 停止轮询并显示成功
- 轮询超时时间：3 分钟

---

## 3. Worker 安装脚本接口

### 接口信息
- **路径**: `GET /install.sh`
- **认证**: 不需要认证（公开接口）
- **Content-Type**: `text/plain` 或 `application/x-sh`

### 功能说明
此接口返回 Worker agent 安装脚本，脚本应该：
1. 接收注册 Token 作为参数
2. 从当前访问的 URL 自动提取后端地址
3. 下载并安装必要的依赖
4. 配置并启动 Worker agent 服务
5. 使用 Token 向后端注册

### 脚本使用方式
```bash
curl -sfL http://<后端地址>:8000/install.sh | bash -s -- <register_token>
```

### 脚本参数
- `$1`: 注册 Token（必需）

### 脚本行为要求
1. **自动获取后端地址**：从脚本下载 URL 中提取主机和端口
2. **依赖检查**：
   - 检查操作系统（Linux）
   - 检查必要的工具（curl, docker, nvidia-smi 等）
3. **安装 GPU Agent**：
   - 下载 GPU agent 二进制文件
   - 安装到系统目录（如 `/usr/local/bin/tm-agent`）
   - 创建 systemd 服务（如果适用）
4. **配置**：
   - 使用提供的 Token
   - 配置后端 API 地址
   - 配置必要的端口（Receiver: 9001, Exporter: 9090）
5. **启动服务**：
   - 启动 GPU agent
   - Agent 使用 Token 向后端注册
6. **错误处理**：
   - 每一步失败时输出清晰的错误信息
   - 提供故障排查建议

### 脚本输出示例
```
>>> TokenMachine GPU Agent Installer
>>>
>>> Backend URL: http://192.168.1.100:8000
>>> Register Token: tm_worker_abc123...
>>>
[✓] Checking system requirements...
[✓] Installing GPU agent...
[✓] Configuring agent...
[✓] Starting agent service...
>>>
>>> Installation completed!
>>> Worker is registering with the backend...
>>> Please check the backend UI for status.
```

---

## 4. 按名称查询 Worker 接口（可选）

### 接口信息
- **路径**: `GET /api/v1/workers?name={worker_name}`
- **认证**: 需要 JWT Bearer Token

### 功能说明
用于在创建前检查 Worker 名称是否已存在

### 响应数据
```typescript
{
  items: Worker[];  // 匹配的 Worker 列表（通常为空或1个）
  total: number;
  page: number;
  page_size: number;
}
```

---

## 5. 错误处理要求

### 统一错误格式
```typescript
{
  detail: string;  // 人类可读的错误信息
}
```

### 常见错误码
- `400 Bad Request`: 参数错误
- `401 Unauthorized`: 未认证
- `409 Conflict`: Worker 名称已存在
- `422 Unprocessable Entity`: 验证失败
- `500 Internal Server Error`: 服务器错误

---

## 6. 其他建议

### CORS 配置
确保后端允许来自前端域名的跨域请求

### Rate Limiting
建议对 Worker 创建接口进行速率限制，防止滥用

### 日志
后端应记录以下事件：
- Worker 创建请求
- Worker 注册成功/失败
- Worker 状态变更
- 安装脚本下载

### WebSocket（可选）
未来可以考虑使用 WebSocket 推送 Worker 状态变更，替代轮询

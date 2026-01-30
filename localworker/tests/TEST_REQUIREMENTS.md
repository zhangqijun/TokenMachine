# GPU Agent 本地测试通过条件

## 概述

本文档列出了本地测试（`TEST_MODE=local`）通过所需的**所有严格条件**。

## 必须满足的条件

### 1. 部署和安装 ✅

#### 1.1 文件部署
- ✅ 文件复制到 `/tmp/tokenmachine_test` 成功
- ✅ 安装目录 `/tmp/tokenmachine_test_opt` 已创建

#### 1.2 二进制文件
必须存在以下3个二进制文件：
```
/tmp/tokenmachine_test_opt/
├── Exporter/gpu_exporter_main  ✅ 静态编译
├── Receiver/receiver            ✅ 静态编译
└── occupier/occupy_gpu          ✅ CUDA编译
```

### 2. 服务进程 ✅

必须满足**6个条件**：

#### 2.1 进程检查（3个进程都运行）
```bash
pgrep -f 'occupy_gpu'        # ≥ 1 个进程
pgrep -f 'gpu_exporter_main' # ≥ 1 个进程
pgrep -f 'receiver'          # ≥ 1 个进程
```

#### 2.2 端口监听（2个端口都监听）
```bash
netstat -tlnp | grep ':9090'  # Exporter端口
netstat -tlnp | grep ':9001'  # Receiver端口
```

### 3. GPU指标（严格验证）⚠️

Exporter必须返回**真实GPU数据**，不能只有元数据：

#### 3.1 必须包含4个核心指标
```bash
curl http://localhost:9090/metrics
```
必须包含：
- ✅ `gpu_memory_used_bytes`
- ✅ `gpu_memory_total_bytes`
- ✅ `gpu_temperature_celsius`
- ✅ `gpu_utilization`

#### 3.2 指标数量要求
- ✅ **至少10条** GPU metrics（非注释行）
- ✅ **至少5条** metrics有数值（不是标签）

### 4. GPU显存占用（严格>=80%）⚠️

**所有选中的GPU**必须满足：
```bash
nvidia-smi -i 0 --query-gpu=memory.used,memory.total
```

- ✅ 显存占用率 **≥ 80%**
- ❌ 如果低于80%，**测试失败**（不再只是警告）

### 5. API端点 ✅

#### 5.1 Exporter
```bash
curl http://localhost:9090/health
# 返回: 包含 "healthy"

curl http://localhost:9090/metrics
# 返回: 包含至少10条GPU metrics
```

#### 5.2 Receiver
```bash
curl http://localhost:9001/health
# 返回: 包含 "ok"

curl http://localhost:9001/api/v1/tasks/list
# 返回: 包含 "tasks"
```

### 6. 配置文件 ✅

必须创建2个配置文件：

#### 6.1 .env 文件
```
/tmp/tokenmachine_test_opt/.env
```
必须包含：
- ✅ `TM_SERVER_URL=http://...`
- ✅ `TM_AGENT_PORT=9001`

#### 6.2 .worker_config 文件
```
/tmp/tokenmachine_test_opt/.worker_config
```
必须包含：
- ✅ `WORKER_ID=<数字>`
- ✅ `WORKER_SECRET=<字符串>`

### 7. Systemd服务 ✅

```
/etc/systemd/system/tokenmachine-gpu-agent.service  ✅ 存在
```

### 8. 心跳进程 ✅

- ✅ `heartbeat.sh` 进程运行中
- ✅ 日志存在：`/var/run/tokenmachine/heartbeat.log`
- ✅ 日志有内容（非空）

### 9. 数据库验证 🆕（严格要求）

⚠️ **新增：必须验证数据库中有worker记录**

#### 9.1 Worker记录存在
```python
GET http://localhost:8000/workers/{worker_id}
```
- ✅ HTTP 200响应
- ✅ 返回的worker ID与配置文件一致
- ✅ `gpu_devices` 字段存在且为列表
- ✅ GPU数量 ≥ 选中的GPU数量

#### 9.2 验证逻辑
1. 读取 `.worker_config` 获取 `WORKER_ID`
2. 调用 Backend API 查询该 worker
3. 验证返回数据包含 GPU 设备列表

## 测试失败示例

### ❌ 假阳性示例（已修复）

**问题1：GPU占用不足但测试通过**
```python
# 旧代码：只打印警告
if usage_percent >= 85:
    print("✓ Good")
else:
    print("Warning: Low usage")  # 不失败！
```

**修复：** 现在使用 `assert`，<80%直接失败

**问题2：配置文件路径错误**
```python
# 旧代码：本地模式也用REMOTE_OPT_DIR
cat /opt/tokenmachine/.env  # 实际在 /tmp/tokenmachine_test_opt/.env
```

**修复：** 根据 `TEST_MODE` 动态选择路径

**问题3：没有验证数据库**
```python
# 旧代码：只在本地检查文件存在
cat .worker_config  # 不验证backend是否真的有这条记录
```

**修复：** 新增 `test_worker_registered_in_database` 测试

## 运行测试

### 本地测试
```bash
cd worker/tests

# 单GPU测试
TEST_MODE=local SELECTED_GPUS="0" pytest test_gpu_agent.py::TestCompleteDeployment -v

# 查看详细输出
TEST_MODE=local pytest test_gpu_agent.py::TestCompleteDeployment -v -s
```

### 检查清单

测试前手动验证：

```bash
# 1. Backend运行
curl http://localhost:8000/health

# 2. GPU可用
nvidia-smi

# 3. 端口未占用
netstat -tlnp | grep -E '9090|9001'

# 4. 有sudo权限
sudo -v
```

## 常见失败原因

### 1. Backend不可达
```
AssertionError: Failed to connect to backend at http://localhost:8000
```
**解决：** 确保backend运行

### 2. GPU占用不足
```
AssertionError: GPU 0 memory usage too low: 45% (required >= 80%)
```
**解决：** occupy_gpu必须成功运行并占用显存

### 3. GPU指标缺失
```
AssertionError: Too few GPU metrics found (3), expected at least 10
```
**解决：** Exporter必须从nvidia-smi获取真实GPU数据

### 4. Worker未注册
```
AssertionError: Backend returned 404 for worker 123
```
**解决：** install.sh必须成功调用 `/workers/register` API

### 5. 配置文件路径错误
```
AssertionError: .env file does not exist at /opt/tokenmachine/.env
```
**解决：** 使用 `TEST_MODE=local`

## 严格性保证

所有测试都使用 `assert` 而非 `print`：
- ✅ 任何条件不满足立即失败
- ✅ 错误消息包含具体期望值和实际值
- ✅ 没有假阳性通过的可能

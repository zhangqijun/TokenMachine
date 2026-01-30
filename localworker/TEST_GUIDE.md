# TokenMachine GPU Agent 测试指南

## 测试环境

- **本地机器**: 开发机（编译机）
- **GPU机器**: Bulbasaur (192.168.247.76)
- **后端服务器**: 本机或独立服务器（http://本机IP:8000）

---

## 测试1: 本地编译测试

### 目标
验证静态编译功能正常

### 步骤

```bash
# 1. 清理旧文件
cd /home/ht706/Documents/TokenMachine/worker/gpu-agent
rm -f Exporter/gpu_exporter_main Receiver/receiver occupy_gpu

# 2. 编译 Exporter
cd Exporter
./build.sh

# 预期输出:
# ✓ 静态链接检查通过
# ✓ 无动态依赖检查通过
# ✓ 无GLIBC动态依赖检查通过
# ✓ 所有静态编译检查通过，二进制可在任何Linux系统运行

# 3. 验证 Exporter
file gpu_exporter_main
# 预期: statically linked

ldd gpu_exporter_main
# 预期: not a dynamic executable

# 4. 编译 Receiver
cd ../Receiver
./build.sh

# 预期输出: 同上

# 5. 验证 Receiver
file receiver
# 预期: statically linked

# 6. 检查GPU过滤功能
cd Exporter
./gpu_exporter_main --help | grep gpu-ids
# 预期显示: --gpu-ids strings    Comma-separated GPU IDs to monitor

# ✅ 测试通过条件:
# - 二进制文件显示 "statically linked"
# - ldd显示 "not a dynamic executable"
# - build.sh所有验证通过
# - --gpu-ids参数存在
```

---

## 测试2: 部署到Bulbasaur

### 目标
验证整个worker目录可以正确部署

### 步骤

```bash
# 1. 清理旧部署（如果存在）
ssh ht706@192.168.247.76 "rm -rf /home/ht706/worker"

# 2. 部署worker目录
cd /home/ht706/Documents/TokenMachine
scp -r worker ht706@192.168.247.76:/home/ht706/

# 3. 验证部署
ssh ht706@192.168.247.76 "ls -lh /home/ht706/worker/gpu-agent/Exporter/gpu_exporter_main"
# 预期: 文件存在，大小约4-5MB

ssh ht706@192.168.247.76 "ls -lh /home/ht706/worker/gpu-agent/Receiver/receiver"
# 预期: 文件存在，大小约4-5MB

ssh ht706@192.168.247.76 "ls -lh /home/ht706/worker/gpu-agent/occupier/occupy_gpu.cu"
# 预期: CUDA源文件存在

# 4. 验证静态链接
ssh ht706@192.168.247.76 "file /home/ht706/worker/gpu-agent/Exporter/gpu_exporter_main"
# 预期: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked

# ✅ 测试通过条件:
# - 所有文件成功复制
# - 二进制文件为静态链接
```

---

## 测试3: 完整安装测试

### 目标
验证install.sh能完成所有步骤

### 步骤

```bash
# SSH到Bulbasaur
ssh ht706@192.168.247.76
cd /home/ht706/worker/gpu-agent

# 停止旧服务（如果有）
sudo ./tm_agent.sh stop 2>/dev/null || true
sudo systemctl stop tokenmachine-gpu-agent 2>/dev/null || true

# 运行安装（使用假token进行测试）
sudo ./install.sh install \
  -s http://本机IP:8000 \
  -p 9001 \
  -t "test_token_$(date +%s)"

# 预期输出流程:
# [INFO] 开始安装 TokenMachine GPU Agent (预编译 + CUDA编译)
# [INFO] 服务器地址: http://本机IP:8000
# [INFO] Agent 端口: 9001
# [INFO] Worker Token: test_token_xxxxx...
# [INFO] 检查系统依赖...
# ✓ 所有依赖检查通过
# [INFO] CUDA 版本: Cuda compilation tools, release 12.8
# [INFO] GPU 环境检查通过
# 0, NVIDIA GeForce RTX 3090
# 1, NVIDIA GeForce RTX 3090
# ...
# [INFO] 检测本地IP地址...
# [INFO] 检测到 X 个IP地址:
#   - 192.168.247.76
# [INFO] 注册Worker到Backend...
# [INFO] 验证IP连通性...
# [INFO] 注册Worker...
# ✓ Worker注册成功
#   Worker ID: 1
# [INFO] 编译 occupy_gpu（CUDA 程序）...
# ✓ occupy_gpu 编译完成
# [INFO] 创建systemd服务...
# ✓ systemd服务已创建并启用
# [INFO] 启动服务...
# [INFO] 注册GPU 0...
# ✓ GPU 0 注册成功
# [INFO] 注册GPU 1...
# ✓ GPU 1 注册成功
# ========================================
#       安装完成！
# ========================================

# ✅ 测试通过条件:
# - 所有步骤无致命错误
# - Worker ID获取成功
# - systemd服务创建成功
```

---

## 测试4: 服务状态验证

### 目标
验证所有服务正常运行

### 步骤

```bash
# 1. 使用tm_agent.sh检查状态
/opt/tokenmachine/tm_agent.sh status

# 预期输出:
# ==================================================
# TokenMachine GPU Agent Status
# ==================================================
# ✓ GPU 占用: 4 个进程
# ✓ Exporter: 1 个进程
# ✓ Receiver: 1 个进程
# ✓ Heartbeat: 1 个进程

# 端口占用情况:
# ✓ Receiver: 端口 9001 正在使用
# ✓ Exporter: 端口 9090 正在使用

# 2. 使用systemctl检查
sudo systemctl status tokenmachine-gpu-agent

# 预期: Active (running)

# 3. 检查进程
ps aux | grep -E "occupy_gpu|gpu_exporter_main|receiver|heartbeat.sh" | grep -v grep

# 预期: 看到所有进程

# 4. 检查GPU占用
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv

# 预期: GPU 0和GPU 1占用约90%内存

# ✅ 测试通过条件:
# - GPU占用: 4个进程
# - Exporter: 1个进程
# - Receiver: 1个进程
# - Heartbeat: 1个进程
# - 端口9001和9090正常监听
# - GPU 0和1内存被占用
```

---

## 测试5: API端点测试

### 目标
验证Exporter和Receiver的API正常工作

### 步骤

```bash
# 1. 测试Exporter健康检查
curl -s http://localhost:9090/health

# 预期: {"status":"healthy"}

# 2. 测试Receiver健康检查
curl -s http://localhost:9001/health

# 预期: {"status":"ok"}

# 3. 测试Exporter指标
curl -s http://localhost:9090/metrics | grep "^gpu_"

# 预期: 看到GPU相关指标
# gpu_memory_used_bytes{gpu="0"} 22253312000
# gpu_memory_total_bytes{gpu="0"} 25952256000
# gpu_utilization{gpu="0"} 0.75
# gpu_temperature_celsius{gpu="0"} 65

# 4. 测试Receiver状态
curl -s http://localhost:9001/api/v1/status

# 预期: JSON格式的状态信息

# 5. 测试Receiver任务列表
curl -s http://localhost:9001/api/v1/tasks/list

# 预期: {"status":"ok","tasks":[]} (空列表)

# ✅ 测试通过条件:
# - /health返回正确状态
# - /metrics有GPU指标
# - /api/v1/status可访问
# - /api/v1/tasks/list返回空列表
```

---

## 测试6: GPU过滤功能测试

### 目标
验证Exporter的GPU过滤功能

### 步骤

```bash
# 1. 停止当前Exporter
sudo /opt/tokenmachine/tm_agent.sh stop
sudo pkill -f gpu_exporter_main

# 2. 手动启动Exporter，指定只监控GPU 0
cd /opt/tokenmachine/Exporter
sudo nohup ./gpu_exporter_main serve --gpu-ids 0 --port 9090 > /var/run/tokenmachine/exporter.log 2>&1 &
echo $! > /var/run/tokenmachine/exporter.pid

# 3. 检查日志
tail -20 /var/run/tokenmachine/exporter.log

# 预期看到: "Monitoring specific GPUs: [0]"

# 4. 检查指标
curl -s http://localhost:9090/metrics | grep "gpu=\""

# 预期: 只看到gpu="0"的指标，没有gpu="1"

# 5. 恢复正常模式（监控所有GPU）
sudo pkill -f gpu_exporter_main
/opt/tokenmachine/tm_agent.sh start

# ✅ 测试通过条件:
# - 启动日志显示"Monitoring specific GPUs: [0]"
# - 指标只有gpu="0"
# - 恢复后监控所有GPU
```

---

## 测试7: 配置文件验证

### 目标
验证配置文件正确创建

### 步骤

```bash
# 1. 检查.env文件
cat /opt/tokenmachine/.env

# 预期:
# TM_SERVER_URL=http://本机IP:8000
# TM_AGENT_PORT=9001

# 2. 检查.worker_config文件
cat /opt/tokenmachine/.worker_config

# 预期:
# WORKER_ID=1
# WORKER_SECRET=xxxxx
# WORKER_NAME=bulbasaur-gpu-xxxxxxxx
# WORKER_IP=192.168.247.76

# 3. 检查GPU配置
cat /var/run/tokenmachine/selected_gpus

# 预期:
# 0
# 1

# 4. 检查systemd服务文件
cat /etc/systemd/system/tokenmachine-gpu-agent.service

# 预期: 看到完整的service配置

# ✅ 测试通过条件:
# - .env包含TM_SERVER_URL和TM_AGENT_PORT
# - .worker_config包含WORKER_ID、WORKER_SECRET等
# - selected_gpus包含0和1
# - systemd服务文件存在且配置正确
```

---

## 测试8: 心跳功能测试

### 目标
验证心跳机制正常工作

### 步骤

```bash
# 1. 检查心跳进程
ps aux | grep heartbeat.sh | grep -v grep

# 预期: 看到heartbeat.sh进程

# 2. 查看心跳日志
tail -f /var/run/tokenmachine/heartbeat.log

# 预期每30秒看到:
# [2026-01-29 XX:XX:XX] [INFO] Worker配置加载成功: ID=X
# [2026-01-29 XX:XX:XX] [INFO] 心跳守护进程启动
# [2026-01-29 XX:XX:XX] [INFO] 心跳间隔: 30秒
# [2026-01-29 XX:XX:XX] [INFO] Worker ID: X
# [2026-01-29 XX:XX:XX] [INFO] 心跳发送成功

# 观察约60秒，应该看到至少2次心跳

# 3. 测试心跳重启
sudo pkill -f heartbeat.sh
sleep 35

# 检查心跳是否自动重启（systemd会重启）
ps aux | grep heartbeat.sh | grep -v grep

# 4. 查看Backend日志（如果可以访问）
# 验证Backend是否收到心跳

# ✅ 测试通过条件:
# - heartbeat.sh进程运行
# - 每30秒发送一次心跳
# - 日志记录正常
# - 进程崩溃后自动重启
```

---

## 测试9: 服务重启测试

### 目标
验证systemd服务能正确管理进程

### 步骤

```bash
# 1. 重启服务
sudo systemctl restart tokenmachine-gpu-agent

# 2. 等待启动
sleep 5

# 3. 检查状态
/opt/tokenmachine/tm_agent.sh status

# 预期: 所有服务都是1个进程

# 4. 检查systemctl状态
sudo systemctl status tokenmachine-gpu-agent

# 预期: Active (running)

# 5. 测试停止
sudo systemctl stop tokenmachine-gpu-agent
sleep 3
/opt/tokenmachine/tm_agent.sh status

# 预期: 所有服务都是0个进程

# 6. 测试启动
sudo systemctl start tokenmachine-gpu-agent
sleep 5
/opt/tokenmachine/tm_agent.sh status

# 预期: 所有服务恢复运行

# 7. 模拟进程崩溃
sudo pkill -f receiver
sleep 35  # 等待systemd自动重启
/opt/tokenmachine/tm_agent.sh status

# 预期: Receiver进程自动恢复

# ✅ 测试通过条件:
# - systemctl能正确启动/停止服务
# - 进程崩溃后自动重启
# - 所有组件都能正确管理
```

---

## 测试10: 完整卸载测试

### 目标
验证卸载功能正常

### 步骤

```bash
# 1. 停止服务
sudo systemctl stop tokenmachine-gpu-agent

# 2. 运行卸载
cd /home/ht706/worker/gpu-agent
sudo ./install.sh uninstall

# 预期输出:
# [INFO] 停止服务...
# [INFO] 移除systemd服务...
# [INFO] 删除文件...
# [INFO] 卸载完成

# 3. 验证清理结果
ls /opt/tokenmachine 2>/dev/null
# 预期: No such file or directory

systemctl status tokenmachine-gpu-agent 2>&1 | grep "not found"
# 预期: 服务不存在

ps aux | grep -E "occupy_gpu|gpu_exporter_main|receiver" | grep -v grep
# 预期: 没有进程

# 4. 清理测试
rm -rf /home/ht706/worker

# ✅ 测试通过条件:
# - /opt/tokenmachine目录删除
# - systemd服务移除
# - 所有进程停止
# - 相关文件清理干净
```

---

## 测试11: 端到端注册测试（需要Backend运行）

### 目标
验证Worker和GPU能成功注册到Backend

### 前置条件
- Backend服务器运行在 http://本机IP:8000
- Backend数据库正常
- 网络连通

### 步骤

```bash
# 1. 确保Backend运行
curl -s http://本机IP:8000/health 2>/dev/null || echo "Backend未运行"

# 2. 在Bulbasaur上重新安装
ssh ht706@192.168.247.76
cd /home/ht706/worker/gpu-agent
sudo ./install.sh uninstall 2>/dev/null || true
sudo ./install.sh install \
  -s http://本机IP:8000 \
  -p 9001 \
  -t "test_token_$(date +%s)"

# 3. 检查Worker配置
cat /opt/tokenmachine/.worker_config

# 4. 在Backend上查询Worker（使用API或数据库）
# 如果有API:
curl -s http://本机IP:8000/api/v1/workers

# 预期: 看到新注册的Worker，name格式为 bulbasaur-gpu-xxxxxxxx

# 5. 查询GPU
curl -s http://本机IP:8000/api/v1/gpus

# 预期: 看到GPU 0和GPU 1，关联到Worker

# 6. 检查Backend日志
tail -f /path/to/backend/logs | grep -i "worker.*register"

# 预期: 看到注册日志

# ✅ 测试通过条件:
# - install.sh成功调用注册API
# - Backend创建Worker记录
# - Backend创建GPU记录
# - WORKER_ID正确保存
```

---

## 故障排查手册

### 问题1: install.sh提示"IP验证失败"

**原因**:
- Backend服务器未运行
- 网络不通
- 防火墙阻止

**解决**:
```bash
# 1. 检查Backend是否运行
curl http://本机IP:8000/health

# 2. 从Bulbasaur测试连接
curl http://本机IP:8000/api/v1/workers/verify-ips

# 3. 检查防火墙
sudo iptables -L | grep 8000
```

### 问题2: GPU注册失败

**原因**:
- WORKER_SECRET未正确保存
- Backend API问题

**解决**:
```bash
# 1. 检查配置文件
cat /opt/tokenmachine/.worker_config

# 2. 手动测试注册
curl -X POST http://本机IP:8000/api/v1/workers/register-gpu \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -d '{...}'

# 3. 查看Backend日志
tail -f /path/to/backend/logs
```

### 问题3: 心跳进程未运行

**原因**:
- .worker_config不存在
- SERVER_URL未设置

**解决**:
```bash
# 1. 检查配置文件
ls -la /opt/tokenmachine/.worker_config /opt/tokenmachine/.env

# 2. 检查心跳日志
tail -50 /var/run/tokenmachine/heartbeat.log

# 3. 手动运行测试
cd /opt/tokenmachine
./heartbeat.sh
```

### 问题4: systemd服务无法启动

**原因**:
- ExecStart路径错误
- 环境变量文件缺失

**解决**:
```bash
# 1. 检查服务文件
cat /etc/systemd/system/tokenmachine-gpu-agent.service

# 2. 测试手动启动
/opt/tokenmachine/tm_agent.sh start

# 3. 查看journalctl
journalctl -u tokenmachine-gpu-agent -n 50
```

---

## 快速测试清单

```bash
# 编译测试
[ ] Exporter编译成功，静态链接
[ ] Receiver编译成功，静态链接
[ ] build.sh所有验证通过

# 部署测试
[ ] worker目录复制成功
[ ] 所有文件完整

# 安装测试
[ ] install.sh无致命错误
[ ] 获取WORKER_ID成功
[ ] systemd服务创建成功

# 服务测试
[ ] GPU占用: 4进程
[ ] Exporter: 1进程
[ ] Receiver: 1进程
[ ] Heartbeat: 1进程
[ ] 端口9090和9001正常

# API测试
[ ] /health正常
[ ] /metrics有数据
[ ] /api/v1/tasks/list正常

# 注册测试
[ ] Worker注册成功
[ ] GPU注册成功
[ ] 心跳正常发送

# 功能测试
[ ] GPU过滤功能正常
[ ] 重启自动恢复
[ ] 卸载清理干净
```

---

## 测试记录模板

```markdown
## 测试执行记录

**日期**: 2026-01-29
**测试人**: XXX
**环境**:
- 本机IP: xxx.xxx.xxx.xxx
- Bulbasaur: 192.168.247.76
- Backend版本: xxx

### 测试1: 本地编译
- [ ] 通过 / 失败
- 备注: xxx

### 测试2: 部署
- [ ] 通过 / 失败
- 备注: xxx

### ... 其他测试

### 问题记录
1. 问题描述
   - 解决方案
   - 状态

### 总结
- 通过率: X/Y
- 遗留问题: xxx
```

---

测试时按照此指南逐项验证，每完成一项在对应项前打勾 ✅

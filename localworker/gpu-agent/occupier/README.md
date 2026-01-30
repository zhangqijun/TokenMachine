# TokenMachine GPU Occupier

GPU Occupier 是一个用 CUDA C++ 编写的轻量级程序，用于预占 GPU 内存。通过预先占用 90% 的 GPU 内存，确保 GPU 资源不会被其他进程抢占，保障 TokenMachine 平台的资源隔离和稳定性。

## 特性

- ✅ **高效内存占用** - 快速预占指定比例的 GPU 内存
- 🎯 **精确控制** - 支持精确指定内存大小和占用比例
- 📊 **实时监控** - 提供内存使用情况的实时监控
- 🚀 **轻量级** - 最小化 CPU 和内存占用
- 🔧 **易于使用** - 简单的命令行接口
- 📝 **日志记录** - 详细的日志记录功能

## 系统要求

### 硬件要求
- NVIDIA GPU（支持 CUDA 11.0+）
- GPU 内存（建议至少 8GB）
- x86_64 架构的 Linux 系统

### 软件要求
- NVIDIA 驱动（包含 nvidia-smi）
- CUDA Toolkit 11.0+
- GNU Make（可选）

## 构建和安装

### 编译程序

```bash
# 进入 occupier 目录
cd /path/to/occupier

# 编译 CUDA 程序
nvcc -O3 -o occupy_gpu occupy_gpu.cu

# 优化二进制文件（可选，减小体积）
strip occupy_gpu

# 验证编译
./occupy_gpu --help
```

### 编译选项

```bash
# 调试编译（包含调试信息）
nvcc -g -o occupy_gpu occupy_gpu.cu

# 发布编译（优化性能）
nvcc -O3 -o occupy_gpu occupy_gpu.cu

# 自定义架构编译
nvcc -arch=sm_80 -o occupy_gpu occupy_gpu.cu
```

## 使用方法

### 基本用法

```bash
# 占用 GPU 0 的 90% 内存（默认）
./occupy_gpu --gpu 0

# 占用 GPU 1 的 90% 内存
./occupy_gpu --gpu 1

# 占用 GPU 0 的 50% 内存
./occupy_gpu --gpu 0 --memory-ratio 0.5

# 占用 GPU 0 的 16GB 内存
./occupy_gpu --gpu 0 --memory 16384

# 指定日志文件
./occupy_gpu --gpu 0 --log /var/log/tokenmachine/occupy_0.log

# 仅监控不占用
./occupy_gpu --gpu 0 --monitor
```

### 高级选项

```bash
# 组合使用所有选项
./occupy_gpu \
  --gpu 0 \
  --memory 32768 \
  --log /var/log/tokenmachine/occupy_gpu.log \
  --monitor \
  --verbose
```

## 命令行选项

| 选项 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| `--gpu` | `N` | 0 | 指定 GPU 编号 |
| `--memory` | `MB` | 自动计算 | 指定内存大小（MB） |
| `--memory-ratio` | `0.0-1.0` | 0.9 | 内存占用比例 |
| `--log` | `FILE` | stdout | 日志文件路径 |
| `--monitor` | 无 | false | 仅监控模式，不占用内存 |
| `--verbose` | 无 | false | 详细输出 |
| `--help` | 无 | - | 显示帮助信息 |

### 选项详解

#### --gpu
指定要操作的 GPU 编号。可以使用 `nvidia-smi --query-gpu=index --format=csv` 查看可用的 GPU。

```bash
# 查看可用 GPU
nvidia-smi --query-gpu=index,name --format=csv

# 输出示例
# 0, NVIDIA A100-SXM4-80GB
# 1, NVIDIA A100-SXM4-80GB
# 2, NVIDIA H100-SXM5-80GB
```

#### --memory
指定要占用的内存大小，单位为 MB。如果不指定，则根据 `--memory-ratio` 自动计算。

```bash
# 占用 16GB 内存
./occupy_gpu --gpu 0 --memory 16384

# 占用 32GB 内存
./occupy_gpu --gpu 0 --memory 32768
```

#### --memory-ratio
指定内存占用比例，范围 0.0 到 1.0。默认为 0.9（90%）。

```bash
# 占用 50% 内存
./occupy_gpu --gpu 0 --memory-ratio 0.5

# 占用 80% 内存
./occupy_gpu --gpu 0 --memory-ratio 0.8
```

#### --monitor
仅监控模式，不实际占用内存。程序会持续监控 GPU 内存使用情况并输出日志。

```bash
# 仅监控 GPU 0 的内存使用
./occupy_gpu --gpu 0 --monitor

# 日志示例
[2026-01-28 16:49:23] GPU 0 - Total: 16384 MB, Used: 8192 MB, Free: 8192 MB, Ratio: 0.50
[2026-01-28 16:49:24] GPU 0 - Total: 16384 MB, Used: 8192 MB, Free: 8192 MB, Ratio: 0.50
```

#### --log
指定日志文件路径。如果不指定，日志将输出到标准输出。

```bash
# 写入到文件
./occupy_gpu --gpu 0 --log /var/log/tokenmachine/occupy_0.log

# 查看日志
tail -f /var/log/tokenmachine/occupy_0.log
```

## 运行示例

### 示例 1：基本使用

```bash
# 启动 GPU 0 的内存占用
./occupy_gpu --gpu 0
```

输出：
```
[2026-01-28 16:49:23] Starting GPU memory occupier for GPU 0
[2026-01-28 16:49:23] GPU 0: NVIDIA A100-SXM4-80GB, Total Memory: 16384 MB
[2026-01-28 16:49:23] Allocating 14745 MB (90% of total memory)
[2026-01-28 16:49:23] Memory allocation successful
[2026-01-28 16:49:23] Monitoring GPU memory...
```

### 示例 2：精确内存控制

```bash
# 占用 GPU 1 的 8GB 内存
./occupy_gpu --gpu 1 --memory 8192
```

输出：
```
[2026-01-28 16:49:23] Starting GPU memory occupier for GPU 1
[2026-01-28 16:49:23] GPU 1: NVIDIA A100-SXM4-80GB, Total Memory: 16384 MB
[2026-01-28 16:49:23] Allocating 8192 MB (50% of total memory)
[2026-01-28 16:49:23] Memory allocation successful
[2026-01-28 16:49:23] Monitoring GPU memory...
```

### 示例 3：监控模式

```bash
# 仅监控 GPU 内存使用情况
./occupy_gpu --gpu 0 --monitor --verbose
```

输出：
```
[2026-01-28 16:49:23] Monitoring GPU 0 memory usage
[2026-01-28 16:49:23] GPU 0 - Total: 16384 MB, Used: 8192 MB, Free: 8192 MB, Ratio: 0.50
[2026-01-28 16:49:24] GPU 0 - Total: 16384 MB, Used: 8192 MB, Free: 8192 MB, Ratio: 0.50
[2026-01-28 16:49:25] GPU 0 - Total: 16384 MB, Used: 8192 MB, Free: 8192 MB, Ratio: 0.50
```

### 示例 4：后台运行

```bash
# 后台运行并记录日志
nohup ./occupy_gpu --gpu 0 --log /var/log/tokenmachine/occupy_0.log > /dev/null 2>&1 &

# 查看进程
ps aux | grep occupy_gpu

# 查看日志
tail -f /var/log/tokenmachine/occupy_0.log
```

## 集成到系统服务

### systemd 服务配置

```ini
# /etc/systemd/system/tokenmachine-occupy.service
[Unit]
Description=TokenMachine GPU Memory Occupier
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/tokenmachine/occupier/occupy_gpu --gpu 0 --log /var/log/tokenmachine/occupy_0.log
Restart=always
RestartSec=5
StandardOutput=file:/var/log/tokenmachine/occupy_0.log
StandardError=file:/var/log/tokenmachine/occupy_0.log

[Install]
WantedBy=multi-user.target
```

### 启动多个 GPU 占用进程

```bash
# 为每个 GPU 创建单独的服务
# /etc/systemd/system/tokenmachine-occupy-0.service
[Unit]
Description=TokenMachine GPU Memory Occupier for GPU 0
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/tokenmachine/occupier/occupy_gpu --gpu 0 --log /var/log/tokenmachine/occupy_0.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

# /etc/systemd/system/tokenmachine-occupy-1.service
[Unit]
Description=TokenMachine GPU Memory Occupier for GPU 1
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/tokenmachine/occupier/occupy_gpu --gpu 1 --log /var/log/tokenmachine/occupy_1.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 管理服务

```bash
# 启用服务
sudo systemctl enable tokenmachine-occupy-0
sudo systemctl enable tokenmachine-occupy-1

# 启动服务
sudo systemctl start tokenmachine-occupy-0
sudo systemctl start tokenmachine-occupy-1

# 查看状态
sudo systemctl status tokenmachine-occupy-0
sudo systemctl status tokenmachine-occupy-1

# 查看日志
sudo journalctl -u tokenmachine-occupy-0 -f
sudo journalctl -u tokenmachine-occupy-1 -f
```

## 监控和调试

### 内存使用检查

```bash
# 查看 GPU 内存使用情况
nvidia-smi --query-gpu=index,memory.used,memory.total,memory.free --format=csv

# 输出示例
# index, memory.used [MiB], memory.total [MiB], memory.free [MiB]
# 0, 14745, 16384, 1639
# 1, 14745, 16384, 1639
```

### 进程监控

```bash
# 查看 occupy_gpu 进程
ps aux | grep occupy_gpu

# 查看进程详细信息
ps -eo pid,ppid,cmd,%mem,%cpu --grep=occupy_gpu

# 查看进程资源使用
top -p $(pgrep -f occupy_gpu)
```

### 日志分析

```bash
# 查看最近的日志
tail -n 50 /var/log/tokenmachine/occupy_0.log

# 过滤错误信息
grep -i error /var/log/tokenmachine/occupy_*.log

# 统计内存分配次数
grep "Memory allocation" /var/log/tokenmachine/occupy_*.log | wc -l
```

## 性能优化

### 1. 内存分配策略

程序使用以下策略进行内存分配：

1. **快速分配**：使用 `cudaMalloc` 快速分配所需内存
2. **保持分配**：内存保持分配状态直到程序终止
3. **零拷贝**：避免不必要的数据拷贝

### 2. 监控频率控制

```bash
# 默认监控间隔：1秒
# 可以通过修改代码调整监控频率

// 在代码中调整
#define MONITOR_INTERVAL_MS 1000  // 监控间隔（毫秒）
```

### 3. 多 GPU 支持

```bash
# 并行启动多个 GPU 占用进程
for gpu_id in 0 1 2 3; do
    ./occupy_gpu --gpu $gpu_id --log /var/log/tokenmachine/occupy_${gpu_id}.log &
done

# 等待所有进程
wait
```

## 故障排查

### 常见问题

#### 1. 内存分配失败

```bash
# 错误信息
[2026-01-28 16:49:23] Memory allocation failed for GPU 0
```

**解决方案**：
- 检查 GPU 是否可用
- 确认内存大小不超过 GPU 总内存
- 检查是否有其他进程占用大量内存

#### 2. 权限问题

```bash
# 错误信息
[2026-01-28 16:49:23] CUDA initialization failed
```

**解决方案**：
```bash
# 检查用户权限
groups

# 将用户加入 video 组
sudo usermod -a -G video $USER

# 重新登录或重新加载组
newgrp video
```

#### 3. CUDA 版本不匹配

```bash
# 检查 CUDA 版本
nvcc --version

# 检查 GPU 架构
nvidia-smi --query-gpu=compute_cap --format=csv
```

**解决方案**：
- 确保使用兼容的 CUDA 版本
- 使用正确的架构参数编译
```bash
# 针对特定 GPU 架构编译
nvcc -arch=sm_80 -O3 -o occupy_gpu occupy_gpu.cu
```

#### 4. GPU 被其他进程占用

```bash
# 检查 GPU 状态
nvidia-smi

# 查看占用 GPU 的进程
nvidia-smi --query-gpu=processes --format=csv
```

**解决方案**：
- 终止占用 GPU 的进程
- 选择其他 GPU 或调整内存占用比例

### 调试技巧

#### 1. 启用详细输出

```bash
# 启用详细日志
./occupy_gpu --gpu 0 --verbose

# 输出详细的调试信息
[2026-01-28 16:49:23] CUDA runtime version: 11.8
[2026-01-28 16:49:23] Device name: NVIDIA A100-SXM4-80GB
[2026-01-28 16:49:23] Memory alignment: 4096 bytes
[2026-01-28 16:49:23] Allocating memory with flags: 0
```

#### 2. 使用监控模式诊断

```bash
# 使用监控模式查看 GPU 状态
./occupy_gpu --gpu 0 --monitor --verbose --log /tmp/diag.log

# 分析日志
cat /tmp/diag.log
```

#### 3. 内存泄漏检测

```bash
# 使用 valgrind 检测内存泄漏（需要支持 CUDA 的版本）
valgrind --tool=memcheck ./occupy_gpu --gpu 0 --monitor
```

## 源码结构

```c++
// occupy_gpu.cu 主要结构
class GPUOccupier {
private:
    int gpu_id;                    // GPU 编号
    size_t memory_size;            // 内存大小
    float memory_ratio;            // 内存比例
    void* device_ptr;              // 设备内存指针
    int verbose;                   // 详细输出标志

public:
    // 构造函数和析构函数
    GPUOccupier(int gpu, size_t size, float ratio);
    ~GPUOccupier();

    // 主要功能
    bool allocate_memory();         // 分配内存
    void free_memory();             // 释放内存
    void monitor_memory();          // 监控内存
    void log_info(const char* msg); // 日志输出
};
```

## 性能基准

### 内存分配时间

| GPU 模型 | 内存大小 | 分配时间 | 占用 CPU |
|----------|----------|----------|----------|
| A100-SXM4-80GB | 16GB | ~50ms | <1% |
| H100-SXM5-80GB | 32GB | ~80ms | <1% |
| RTX 4090 | 24GB | ~30ms | <1% |

### 内存占用

| 组件 | 内存占用 | 说明 |
|------|----------|------|
| 主程序 | ~10MB | 包含 CUDA 运行时 |
| 分配的内存 | 可配置 | 用户指定的内存大小 |
| 日志文件 | 可配置 | 根据日志内容大小 |

## 版本历史

- **v1.0.0**: 初始版本，支持基本内存占用功能
- **v1.1.0**: 添加监控模式和详细日志
- **v1.2.0**: 支持精确内存大小控制

## 许可证

MIT License
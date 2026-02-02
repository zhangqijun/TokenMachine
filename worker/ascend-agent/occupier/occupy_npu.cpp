/**
 * Ascend NPU Memory Occupation Tool
 *
 * 使用 ACL (Ascend Computing Language) API 占用 NPU 内存
 * 适配华为昇腾 NPU (Ascend 910/310 等)
 *
 * 编译方法:
 *   g++ -O3 -std=c++17 \
 *       -I${ASCEND_HOME}/ascend-toolkit/latest/include \
 *       -L${ASCEND_HOME}/ascend-toolkit/latest/lib64 \
 *       -o occupy_npu occupy_npu.cpp \
 *       -lacl_op_compiler -lascendcl -lpthread -ldl
 *
 * 使用方法:
 *   ./occupy_npu --npu 0 --log /var/run/occupy.log
 *   ./occupy_npu --npu 0 --percentage 85
 */

#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <atomic>
#include <vector>
#include <cstring>
#include <signal.h>
#include <unistd.h>

// ACL 头文件
#include "acl/acl.h"
#include "acl/ops/acl_conv.h"

// 命令行参数
static int npu_id = 0;
static int target_percentage = 80;
static std::string log_file = "";

// 全局状态
static std::atomic<bool> g_running(true);
static aclrtContext g_context = nullptr;
static aclrtStream g_stream = nullptr;
static std::vector<void*> g_buffers;

// 信号处理
void signal_handler(int signum) {
    std::cout << "收到信号 " << signum << "，正在清理..." << std::endl;
    g_running = false;
}

// 打印日志
void log_info(const std::string& msg) {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;

    std::string time_str = std::ctime(&time);
    time_str.pop_back();  // 移除换行符

    std::string log_msg = "[" + time_str + "." +
                          std::to_string(ms.count()).pad_start(3, '0') + "] " + msg;

    std::cout << log_msg << std::endl;

    if (!log_file.empty()) {
        FILE* fp = fopen(log_file.c_str(), "a");
        if (fp) {
            fprintf(fp, "%s\n", log_msg.c_str());
            fclose(fp);
        }
    }
}

// 获取 NPU 内存信息
bool get_npu_memory_info(size_t& total, size_t& used) {
    aclError ret;

    // 获取设备内存信息
    aclrtGetMemInfo(ACL_HOST, &total, &used);

    if (ret != ACL_ERROR_NONE) {
        log_info("获取内存信息失败: " + std::to_string(ret));
        return false;
    }

    return true;
}

// 初始化 ACL
bool init_acl() {
    aclError ret;

    // 初始化 ACL
    ret = aclInit(nullptr);
    if (ret != ACL_ERROR_NONE) {
        log_info("aclInit 失败: " + std::to_string(ret));
        return false;
    }
    log_info("ACL 初始化成功");

    // 设置设备
    ret = aclrtSetDevice(npu_id);
    if (ret != ACL_ERROR_NONE) {
        log_info("aclrtSetDevice 失败: " + std::to_string(ret));
        return false;
    }
    log_info("设置设备 " + std::to_string(npu_id) + " 成功");

    // 获取上下文
    ret = aclrtCreateContext(&g_context, npu_id);
    if (ret != ACL_ERROR_NONE) {
        log_info("aclrtCreateContext 失败: " + std::to_string(ret));
        return false;
    }
    log_info("创建上下文成功");

    // 创建流
    ret = aclrtCreateStream(&g_stream);
    if (ret != ACL_ERROR_NONE) {
        log_info("aclrtCreateStream 失败: " + std::to_string(ret));
        return false;
    }
    log_info("创建流成功");

    return true;
}

// 清理 ACL
void cleanup_acl() {
    // 同步流
    if (g_stream) {
        aclrtSynchronizeStream(g_stream);
        aclrtDestroyStream(g_stream);
        g_stream = nullptr;
    }

    // 释放所有缓冲区
    for (auto& buf : g_buffers) {
        if (buf) {
            aclrtFree(buf);
            buf = nullptr;
        }
    }
    g_buffers.clear();

    // 销毁上下文
    if (g_context) {
        aclrtDestroyContext(g_context);
        g_context = nullptr;
    }

    // 重置设备
    aclrtResetDevice(npu_id);

    // 退出 ACL
    aclFinalize();
}

// 分配内存以占用 NPU
bool allocate_memory(size_t target_size) {
    aclError ret;
    void* buffer = nullptr;

    // 使用 aclrtMalloc 分配内存
    ret = aclrtMalloc(&buffer, target_size, ACL_MEM_MALLOC_NORMAL_ONLY);
    if (ret != ACL_ERROR_NONE) {
        log_info("aclrtMalloc 失败: " + std::to_string(ret));
        return false;
    }

    // 确保内存被实际使用（写入数据）
    if (buffer) {
        ret = aclrtMemset(buffer, target_size, 0xAB, target_size);
        if (ret != ACL_ERROR_NONE) {
            log_info("aclrtMemset 失败: " + std::to_string(ret));
            aclrtFree(buffer);
            return false;
        }
    }

    g_buffers.push_back(buffer);
    log_info("成功分配 " + std::to_string(target_size / 1024 / 1024) + " MB 内存");

    return true;
}

// 获取设备总内存
size_t get_device_memory_size() {
    // Ascend 910 通常有 32GB HBM 内存
    // 可以通过设备信息获取实际大小
    size_t total, free_size;
    aclrtGetMemInfo(ACL_DEVICE, &total, &free_size);
    return total;
}

// 内存占用主循环
void memory_occupation_loop() {
    size_t device_memory = get_device_memory_size();
    size_t target_size = (size_t)(device_memory * target_percentage / 100);

    log_info("设备总内存: " + std::to_string(device_memory / 1024 / 1024) + " MB");
    log_info("目标占用: " + std::to_string(target_percentage) + "%");
    log_info("目标内存: " + std::to_string(target_size / 1024 / 1024) + " MB");

    // 渐进式分配内存
    size_t current_allocated = 0;
    const size_t chunk_size = 1024 * 1024 * 1024;  // 每次分配 1GB

    while (g_running && current_allocated < target_size) {
        size_t remaining = target_size - current_allocated;
        size_t alloc_size = std::min(chunk_size, remaining);

        if (!allocate_memory(alloc_size)) {
            log_info("内存分配失败，可能已达到设备限制");
            break;
        }

        current_allocated += alloc_size;

        // 显示进度
        float progress = (float)current_allocated / target_size * 100;
        log_info("当前占用: " + std::to_string(current_allocated / 1024 / 1024) +
                 " MB (" + std::to_string((int)progress) + "%)");

        // 短暂休眠，避免过快分配
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    log_info("内存占用完成，当前已分配: " +
             std::to_string(current_allocated / 1024 / 1024) + " MB");
}

// 监控循环
void monitor_loop() {
    while (g_running) {
        size_t total, used;
        if (get_npu_memory_info(total, used)) {
            float usage_percent = (float)used / total * 100;
            log_info("NPU " + std::to_string(npu_id) +
                     " 内存使用: " + std::to_string(used / 1024 / 1024) +
                     " MB / " + std::to_string(total / 1024 / 1024) +
                     " MB (" + std::to_string((int)usage_percent) + "%)");
        }

        // 每 30 秒报告一次
        std::this_thread::sleep_for(std::chrono::seconds(30));
    }
}

// 打印使用帮助
void print_help(const char* prog_name) {
    std::cout << "用法: " << prog_name << " [选项]" << std::endl;
    std::cout << std::endl;
    std::cout << "选项:" << std::endl;
    std::cout << "  -n, --npu ID        NPU 设备 ID (默认: 0)" << std::endl;
    std::cout << "  -p, --percentage %  内存占用百分比 (默认: 80)" << std::endl;
    std::cout << "  -l, --log FILE      日志文件路径" << std::endl;
    std::cout << "  -h, --help          显示此帮助信息" << std::endl;
    std::cout << std::endl;
    std::cout << "示例:" << std::endl;
    std::cout << "  " << prog_name << " --npu 0 --percentage 85" << std::endl;
    std::cout << "  " << prog_name << " -n 0 -p 80 -l /var/run/occupy.log" << std::endl;
}

// 解析命令行参数
void parse_args(int argc, char* argv[]) {
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "-h" || arg == "--help") {
            print_help(argv[0]);
            exit(0);
        } else if (arg == "-n" || arg == "--npu") {
            if (i + 1 < argc) {
                npu_id = std::stoi(argv[++i]);
            }
        } else if (arg == "-p" || arg == "--percentage") {
            if (i + 1 < argc) {
                target_percentage = std::stoi(argv[++i]);
                if (target_percentage < 1) target_percentage = 1;
                if (target_percentage > 99) target_percentage = 99;
            }
        } else if (arg == "-l" || arg == "--log") {
            if (i + 1 < argc) {
                log_file = argv[++i];
            }
        }
    }
}

int main(int argc, char* argv[]) {
    std::cout << "======================================" << std::endl;
    std::cout << "Ascend NPU Memory Occupation Tool" << std::endl;
    std::cout << "======================================" << std::endl;

    // 解析命令行参数
    parse_args(argc, argv);

    // 注册信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // 初始化 ACL
    if (!init_acl()) {
        log_info("ACL 初始化失败");
        return 1;
    }

    log_info("开始 NPU " + std::to_string(npu_id) + " 内存占用...");

    // 启动内存占用线程
    std::thread occupy_thread(memory_occupation_loop);

    // 启动监控线程
    std::thread monitor_thread(monitor_loop);

    // 等待内存占用完成
    occupy_thread.join();

    // 保持运行直到收到信号
    while (g_running) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    // 停止监控线程
    monitor_thread.detach();

    // 清理
    log_info("正在清理...");
    cleanup_acl();

    log_info("程序退出");
    return 0;
}

#include <cuda_runtime.h>
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <fstream>
#include <string>
#include <signal.h>
#include <unistd.h>

// 全局变量用于程序退出控制
volatile sig_atomic_t keep_running = 1;

// 信号处理函数
void signal_handler(int signal) {
    if (signal == SIGTERM || signal == SIGINT) {
        keep_running = 0;
    }
}

// 检查 CUDA 错误
#define CHECK_CUDA_ERROR(err) { \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error: %s at %s:%d\n", cudaGetErrorString(err), __FILE__, __LINE__); \
        exit(EXIT_FAILURE); \
    } \
}

// GPU 内存占用结构体
struct GPUInfo {
    int device_id;
    size_t total_memory;
    size_t occupied_memory;
    float utilization_rate;
};

// 获取 GPU 信息
GPUInfo get_gpu_info(int device_id) {
    cudaError_t err;
    size_t free_memory, total_memory;
    GPUInfo gpu_info;

    gpu_info.device_id = device_id;

    // 获取 GPU 内存信息
    err = cudaMemGetInfo(&free_memory, &total_memory);
    CHECK_CUDA_ERROR(err);

    gpu_info.total_memory = total_memory;
    gpu_info.occupied_memory = total_memory - free_memory;
    gpu_info.utilization_rate = (float)gpu_info.occupied_memory / total_memory;

    return gpu_info;
}

// 占用指定 GPU 内存
void occupy_gpu_memory(int device_id, size_t memory_to_occupy, const std::string& log_file) {
    cudaError_t err;
    float* gpu_memory = nullptr;
    size_t actual_occupied = 0;

    // 切换到指定 GPU
    cudaSetDevice(device_id);

    // 如果没有指定内存大小，则使用90%的可用内存
    if (memory_to_occupy == 0) {
        size_t free_memory, total_memory;
        err = cudaMemGetInfo(&free_memory, &total_memory);
        if (err == cudaSuccess) {
            memory_to_occupy = static_cast<size_t>(total_memory * 0.9); // 使用90%的内存
        } else {
            // 如果无法获取内存信息，使用默认值
            memory_to_occupy = 1024 * 1024 * 1024; // 1GB
        }
    }

    // 打开日志文件
    std::ofstream log_file_stream(log_file, std::ios::app);
    if (log_file_stream.is_open()) {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        log_file_stream << "[" << std::ctime(&time) << "] Starting GPU " << device_id << " memory occupation: "
            << (memory_to_occupy / 1024 / 1024) << " MB (90% of available)" << std::endl;
        log_file_stream.close();
    }

    try {
        // 分配 GPU 内存
        err = cudaMalloc(&gpu_memory, memory_to_occupy);
        if (err != cudaSuccess) {
            if (log_file_stream.is_open()) {
                log_file_stream.open(log_file, std::ios::app);
                log_file_stream << "[ERROR] Failed to allocate GPU memory: " << cudaGetErrorString(err) << std::endl;
                log_file_stream.close();
            }
            return;
        }

        actual_occupied = memory_to_occupy;

        if (log_file_stream.is_open()) {
            log_file_stream.open(log_file, std::ios::app);
            auto now = std::chrono::system_clock::now();
            auto time = std::chrono::system_clock::to_time_t(now);
            log_file_stream << "[" << std::ctime(&time) << "] Successfully allocated "
                << (actual_occupied / 1024 / 1024) << " MB on GPU " << device_id << std::endl;
            log_file_stream.close();
        }

        // 保持内存占用直到收到退出信号
        while (keep_running) {
            // 可以在这里添加一些填充操作来保持内存活跃
            // 但简单的内存占用也可以，不需要额外的操作

            // 每隔一段时间更新状态
            static int counter = 0;
            if (++counter % 100 == 0) {  // 每100次循环更新一次
                GPUInfo info = get_gpu_info(device_id);
                if (log_file_stream.is_open()) {
                    log_file_stream.open(log_file, std::ios::app);
                    auto now = std::chrono::system_clock::now();
                    auto time = std::chrono::system_clock::to_time_t(now);
                    log_file_stream << "[" << std::ctime(&time) << "] GPU " << device_id
                        << " occupied: " << (info.occupied_memory / 1024 / 1024)
                        << " MB / " << (info.total_memory / 1024 / 1024) << " MB"
                        << " (" << (info.utilization_rate * 100) << "%)" << std::endl;
                    log_file_stream.close();
                }
            }

            // 休眠一段时间避免过度占用 CPU
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }

    } catch (const std::exception& e) {
        std::ofstream log_stream(log_file, std::ios::app);
        if (log_stream.is_open()) {
            auto now = std::chrono::system_clock::now();
            auto time = std::chrono::system_clock::to_time_t(now);
            log_stream << "[" << std::ctime(&time) << "] [ERROR] Exception in occupy_gpu_memory: " << e.what() << std::endl;
            log_stream.close();
        }
    }

    // 清理资源
    if (gpu_memory != nullptr) {
        cudaFree(gpu_memory);
        if (log_file_stream.is_open()) {
            log_file_stream.open(log_file, std::ios::app);
            auto now = std::chrono::system_clock::now();
            auto time = std::chrono::system_clock::to_time_t(now);
            log_file_stream << "[" << std::ctime(&time) << "] Freed GPU " << device_id << " memory" << std::endl;
            log_file_stream.close();
        }
    }
}

// 监控 GPU 状态
void monitor_gpu_status(int device_id, const std::string& log_file) {
    while (keep_running) {
        GPUInfo info = get_gpu_info(device_id);

        std::ofstream log_stream(log_file, std::ios::app);
        if (log_stream.is_open()) {
            auto now = std::chrono::system_clock::now();
            auto time = std::chrono::system_clock::to_time_t(now);
            log_stream << "[" << std::ctime(&time) << "] GPU " << device_id << " status: "
                << "Total: " << (info.total_memory / 1024 / 1024) << " MB, "
                << "Used: " << (info.occupied_memory / 1024 / 1024) << " MB, "
                << "Utilization: " << (info.utilization_rate * 100) << "%" << std::endl;
            log_stream.close();
        }

        std::this_thread::sleep_for(std::chrono::seconds(5));
    }
}

// 打印 GPU 信息
void print_gpu_info() {
    int device_count;
    cudaError_t err = cudaGetDeviceCount(&device_count);

    if (err != cudaSuccess) {
        std::cerr << "CUDA Error: " << cudaGetErrorString(err) << std::endl;
        return;
    }

    if (device_count == 0) {
        std::cout << "No CUDA-capable devices found." << std::endl;
        return;
    }

    std::cout << "Found " << device_count << " CUDA device(s):" << std::endl;
    std::cout << "==================================================" << std::endl;

    for (int i = 0; i < device_count; ++i) {
        cudaDeviceProp prop;
        err = cudaGetDeviceProperties(&prop, i);

        if (err == cudaSuccess) {
            std::cout << "Device [" << i << "]: " << prop.name << std::endl;
            std::cout << "  Memory: " << prop.totalGlobalMem / 1024 / 1024 << " MB" << std::endl;
            std::cout << "  Compute Capability: " << prop.major << "." << prop.minor << std::endl;
            std::cout << "  Max Threads Per Block: " << prop.maxThreadsPerBlock << std::endl;
        } else {
            std::cerr << "Error getting device properties for device " << i << ": "
                      << cudaGetErrorString(err) << std::endl;
        }
        std::cout << std::endl;
    }
}

int main(int argc, char* argv[]) {
    // 设置信号处理
    signal(SIGTERM, signal_handler);
    signal(SIGINT, signal_handler);

    int gpu_id = -1;  // -1 表示占用所有 GPU
    size_t memory_mb = 0;  // 0 表示占用全部可用内存
    bool monitor_only = false;
    std::string log_file = "/var/run/tokenmachine/occupy_gpu.log";

    // 解析命令行参数
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--gpu" && i + 1 < argc) {
            gpu_id = std::stoi(argv[++i]);
        } else if (arg == "--memory" && i + 1 < argc) {
            memory_mb = std::stoull(argv[++i]) * 1024 * 1024;  // 转换为字节
        } else if (arg == "--log" && i + 1 < argc) {
            log_file = argv[++i];
        } else if (arg == "--monitor") {
            monitor_only = true;
        } else if (arg == "--help") {
            std::cout << "Usage: " << argv[0] << " [OPTIONS]" << std::endl;
            std::cout << "Options:" << std::endl;
            std::cout << "  --gpu N          Specify GPU ID to occupy (default: all GPUs)" << std::endl;
            std::cout << "  --memory MB      Memory size in MB to occupy (default: 90% of available)" << std::endl;
            std::cout << "  --log FILE       Log file path (default: /var/run/tokenmachine/occupy_gpu.log)" << std::endl;
            std::cout << "  --monitor        Only monitor GPU status without occupying memory" << std::endl;
            std::cout << "  --help           Show this help message" << std::endl;
            return 0;
        }
    }

    // 检查 CUDA 是否可用
    cudaError_t err = cudaSetDevice(0);
    if (err != cudaSuccess) {
        std::cerr << "CUDA not available or no devices found." << std::endl;
        std::cerr << "Error: " << cudaGetErrorString(err) << std::endl;
        return 1;
    }

    // 获取 GPU 数量
    int device_count;
    err = cudaGetDeviceCount(&device_count);
    if (err != cudaSuccess) {
        std::cerr << "Failed to get device count: " << cudaGetErrorString(err) << std::endl;
        return 1;
    }

    if (device_count == 0) {
        std::cerr << "No CUDA devices found." << std::endl;
        return 1;
    }

    std::cout << "TokenMachine GPU Occupancy Program" << std::endl;
    std::cout << "==================================" << std::endl;
    print_gpu_info();

    // 创建日志目录
    std::string log_dir = log_file.substr(0, log_file.find_last_of('/'));
    std::string mkdir_cmd = "mkdir -p " + log_dir;
    int mkdir_result = system(mkdir_cmd.c_str());
    (void)mkdir_result;  // 避免未使用变量的警告

    if (monitor_only) {
        std::cout << "Starting GPU monitoring mode..." << std::endl;

        if (gpu_id >= 0) {
            std::cout << "Monitoring GPU " << gpu_id << std::endl;
            monitor_gpu_status(gpu_id, log_file);
        } else {
            // 监控所有 GPU
            while (keep_running) {
                for (int i = 0; i < device_count; ++i) {
                    monitor_gpu_status(i, log_file);
                }
                std::this_thread::sleep_for(std::chrono::seconds(1));
            }
        }
    } else {
        std::cout << "Starting GPU memory occupation..." << std::endl;

        if (gpu_id >= 0) {
            std::cout << "Occupying GPU " << gpu_id << std::endl;
            if (memory_mb > 0) {
                std::cout << "Memory size: " << (memory_mb / 1024 / 1024) << " MB" << std::endl;
            } else {
                std::cout << "Memory size: 90% of available memory" << std::endl;
            }
            occupy_gpu_memory(gpu_id, memory_mb, log_file);
        } else {
            std::cout << "Occupying all GPUs..." << std::endl;
            if (memory_mb > 0) {
                std::cout << "Memory size per GPU: " << (memory_mb / 1024 / 1024) << " MB" << std::endl;
            } else {
                std::cout << "Memory size per GPU: 90% of available memory" << std::endl;
            }

            // 为每个 GPU 创建线程
            std::vector<std::thread> threads;
            for (int i = 0; i < device_count; ++i) {
                threads.emplace_back(occupy_gpu_memory, i, memory_mb, log_file);
            }

            // 等待所有线程结束
            for (auto& thread : threads) {
                thread.join();
            }
        }
    }

    std::cout << "GPU occupancy program stopped." << std::endl;
    return 0;
}
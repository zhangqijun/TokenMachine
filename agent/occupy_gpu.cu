/**
 * occupy_gpu.cu - GPU Memory Occupation Program
 *
 * This program occupies a specified percentage of GPU memory to prevent
 * other processes from using the GPU. It's part of the TokenMachine
 * GPU agent system.
 *
 * Usage:
 *   ./occupy_gpu <gpu_id> [occupy_ratio=0.95]
 *
 * Arguments:
 *   gpu_id: GPU device ID (0-based index)
 *   occupy_ratio: Fraction of GPU memory to occupy (default: 0.95 = 95%)
 *
 * Example:
 *   ./occupy_gpu 0 0.95  # Occupy 95% of GPU 0's memory
 *
 * Compilation:
 *   nvcc -O3 -o occupy_gpu occupy_gpu.cu
 *   strip occupy_gpu  # Reduce binary size
 */

#include <cuda_runtime.h>
#include <signal.h>
#include <unistd.h>
#include <iostream>
#include <iomanip>
#include <cstdio>

// Global pointer for cleanup
void* g_gpu_ptr = nullptr;
int g_gpu_id = 0;
float g_occupy_ratio = 0.95f;

/**
 * Signal handler for graceful cleanup
 */
void cleanup(int signum) {
    std::cout << "Cleaning up GPU " << g_gpu_id << std::endl;

    if (g_gpu_ptr) {
        cudaError_t err = cudaFree(g_gpu_ptr);
        if (err == cudaSuccess) {
            std::cout << "GPU memory freed successfully" << std::endl;
        } else {
            std::cerr << "cudaFree failed: " << cudaGetErrorString(err) << std::endl;
        }
    }

    exit(0);
}

/**
 * Convert bytes to human-readable format
 */
std::string bytes_to_gb(size_t bytes) {
    double gb = static_cast<double>(bytes) / (1024.0 * 1024.0 * 1024.0);
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2) << gb << " GB";
    return oss.str();
}

/**
 * Main function
 */
int main(int argc, char** argv) {
    // Parse arguments
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <gpu_id> [occupy_ratio=0.95]" << std::endl;
        std::cerr << std::endl;
        std::cerr << "Arguments:" << std::endl;
        std::cerr << "  gpu_id:        GPU device ID (0-based index)" << std::endl;
        std::cerr << "  occupy_ratio:  Fraction of memory to occupy (0.0-1.0, default: 0.95)" << std::endl;
        std::cerr << std::endl;
        std::cerr << "Example:" << std::endl;
        std::cerr << "  " << argv[0] << " 0 0.95  # Occupy 95% of GPU 0's memory" << std::endl;
        return 1;
    }

    g_gpu_id = atoi(argv[1]);
    if (g_gpu_id < 0) {
        std::cerr << "Error: Invalid GPU ID " << g_gpu_id << std::endl;
        return 1;
    }

    g_occupy_ratio = argc > 2 ? atof(argv[2]) : 0.95f;

    if (g_occupy_ratio <= 0.0f || g_occupy_ratio > 1.0f) {
        std::cerr << "Error: occupy_ratio must be between 0.0 and 1.0, got " << g_occupy_ratio << std::endl;
        return 1;
    }

    // Set up signal handlers for graceful shutdown
    signal(SIGTERM, cleanup);
    signal(SIGINT, cleanup);

    // Set GPU device
    cudaError_t err = cudaSetDevice(g_gpu_id);
    if (err != cudaSuccess) {
        std::cerr << "Error: Failed to set GPU " << g_gpu_id << ": " << cudaGetErrorString(err) << std::endl;
        return 1;
    }

    // Get GPU memory information
    size_t free_mem = 0;
    size_t total_mem = 0;
    err = cudaMemGetInfo(&free_mem, &total_mem);
    if (err != cudaSuccess) {
        std::cerr << "Error: Failed to get memory info: " << cudaGetErrorString(err) << std::endl;
        return 1;
    }

    // Calculate memory to occupy
    size_t occupy_size = static_cast<size_t>(total_mem * g_occupy_ratio);

    // Print GPU information
    std::cout << "==================================================" << std::endl;
    std::cout << "GPU Memory Occupation Program" << std::endl;
    std::cout << "==================================================" << std::endl;
    std::cout << "GPU ID:        " << g_gpu_id << std::endl;
    std::cout << "Total Memory:  " << bytes_to_gb(total_mem) << std::endl;
    std::cout << "Free Memory:   " << bytes_to_gb(free_mem) << std::endl;
    std::cout << "Occupy Ratio:  " << std::fixed << std::setprecision(2) << (g_occupy_ratio * 100.0f) << "%" << std::endl;
    std::cout << "Occupy Size:   " << bytes_to_gb(occupy_size) << std::endl;
    std::cout << "PID:           " << getpid() << std::endl;
    std::cout << "==================================================" << std::endl;

    // Allocate GPU memory
    std::cout << "Allocating GPU memory..." << std::endl;
    err = cudaMalloc(&g_gpu_ptr, occupy_size);
    if (err != cudaSuccess) {
        std::cerr << "Error: cudaMalloc failed: " << cudaGetErrorString(err) << std::endl;
        std::cerr << "Note: This may be caused by:" << std::endl;
        std::cerr << "  1. Another process is using the GPU" << std::endl;
        std::cerr << "  2. Not enough free memory" << std::endl;
        std::cerr << "  3. GPU is in exclusive mode" << std::endl;
        return 1;
    }

    // Initialize memory (ensures physical allocation)
    std::cout << "Initializing memory..." << std::endl;
    err = cudaMemset(g_gpu_ptr, 0, occupy_size);
    if (err != cudaSuccess) {
        std::cerr << "Error: cudaMemset failed: " << cudaGetErrorString(err) << std::endl;
        cudaFree(g_gpu_ptr);
        return 1;
    }

    std::cout << "GPU " << g_gpu_id << " occupied successfully!" << std::endl;
    std::cout << "Status: Running (Press Ctrl+C to exit)" << std::endl;
    std::cout.flush();

    // Main loop - keep running and periodically refresh memory
    // This prevents the OS from reclaiming the memory
    int counter = 0;
    while (true) {
        sleep(30);  // Wait 30 seconds

        // Refresh a small portion of memory to maintain allocation
        if (g_gpu_ptr) {
            cudaMemset(g_gpu_ptr, counter % 256, 1024);  // Refresh first 1KB
            counter++;
        }
    }

    // Cleanup (unreachable, but kept for completeness)
    if (g_gpu_ptr) {
        cudaFree(g_gpu_ptr);
    }

    return 0;
}

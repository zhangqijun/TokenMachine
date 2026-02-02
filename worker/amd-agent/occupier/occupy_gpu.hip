/**
 * AMD GPU Memory Occupier
 *
 * This program occupies a specified percentage of AMD GPU memory using HIP
 * (Heterogeneous-Compute Interface for Portability) to prevent dynamic
 * memory allocation during inference.
 *
 * Compile with: hipcc -O3 -o occupy_gpu occupy_gpu.hip
 *
 * Usage: ./occupy_gpu --gpu <gpu_id> --percent <percent> [--mock]
 *   --gpu <gpu_id>     : GPU index to occupy (default: 0)
 *   --percent <percent>: Memory percentage to occupy (default: 90)
 *   --mock            : Run in mock/simulation mode (no real GPU required)
 *   --help            : Show this help message
 */

#include <hip/hip_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <time.h>
#include <signal.h>

#define CHECK_HIP(call)                                                         \
    do {                                                                        \
        hipError_t err = call;                                                  \
        if (err != hipSuccess) {                                                \
            fprintf(stderr, "HIP error at %s:%d: %s\n", __FILE__, __LINE__,      \
                    hipGetErrorString(err));                                     \
            exit(EXIT_FAILURE);                                                 \
        }                                                                       \
    } while (0)

// Structure to hold occupy configuration
typedef struct {
    int gpu_id;
    float occupy_percent;
    int mock_mode;
    char *log_file;
} OccupyConfig;

// Structure to hold mock GPU info (for testing without real AMD hardware)
typedef struct {
    int gpu_id;
    size_t total_memory;
    size_t used_memory;
    float temperature;
    float utilization;
} MockGpuInfo;

// Global flag for cleanup on signal
static volatile int keep_running = 1;

// Signal handler for graceful shutdown
void signal_handler(int sig) {
    (void)sig;
    keep_running = 0;
}

// Parse command line arguments
void parse_args(int argc, char *argv[], OccupyConfig *config) {
    static struct option long_options[] = {
        {"gpu", required_argument, 0, 'g'},
        {"percent", required_argument, 0, 'p'},
        {"mock", no_argument, 0, 'm'},
        {"simulate", no_argument, 0, 's'},
        {"log", required_argument, 0, 'l'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0}
    };

    int opt;
    int option_index = 0;

    config->gpu_id = 0;
    config->occupy_percent = 90.0f;
    config->mock_mode = 0;
    config->log_file = NULL;

    while ((opt = getopt_long(argc, argv, "g:p:msl:h", long_options, &option_index)) != -1) {
        switch (opt) {
            case 'g':
                config->gpu_id = atoi(optarg);
                if (config->gpu_id < 0) {
                    fprintf(stderr, "Error: Invalid GPU ID: %s\n", optarg);
                    exit(EXIT_FAILURE);
                }
                break;
            case 'p':
                config->occupy_percent = atof(optarg);
                if (config->occupy_percent < 0.0f || config->occupy_percent > 100.0f) {
                    fprintf(stderr, "Error: Invalid occupy percentage: %s (must be 0-100)\n", optarg);
                    exit(EXIT_FAILURE);
                }
                break;
            case 'm':
            case 's':
                config->mock_mode = 1;
                break;
            case 'l':
                config->log_file = strdup(optarg);
                break;
            case 'h':
                print_help(argv[0]);
                exit(EXIT_SUCCESS);
            default:
                print_help(argv[0]);
                exit(EXIT_FAILURE);
        }
    }
}

// Print help message
void print_help(const char *program_name) {
    printf("AMD GPU Memory Occupier\n");
    printf("========================\n\n");
    printf("Usage: %s [options]\n\n", program_name);
    printf("Options:\n");
    printf("  -g, --gpu <id>        GPU index to occupy (default: 0)\n");
    printf("  -p, --percent <%%>      Memory percentage to occupy (default: 90)\n");
    printf("  -m, --mock            Run in mock/simulation mode (no real GPU required)\n");
    printf("  -l, --log <file>      Log file path\n");
    printf("  -h, --help            Show this help message\n\n");
    printf("Example:\n");
    printf("  %s --gpu 0 --percent 90    # Occupy 90%% of GPU 0 memory\n", program_name);
    printf("  %s --mock                 # Run in simulation mode\n", program_name);
}

// Log message to file and stdout
void log_message(const char *log_file, const char *format, ...) {
    va_list args;
    char timestamp[64];
    time_t now;
    struct tm *tm_info;

    // Get current timestamp
    time(&now);
    tm_info = localtime(&now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm_info);

    // Print to stdout
    va_start(args, format);
    printf("[%s] ", timestamp);
    vprintf(format, args);
    printf("\n");
    va_end(args);

    // Write to log file if specified
    if (log_file) {
        FILE *fp = fopen(log_file, "a");
        if (fp) {
            va_start(args, format);
            fprintf(fp, "[%s] ", timestamp);
            vfprintf(fp, format, args);
            fprintf(fp, "\n");
            va_end(args);
            fclose(fp);
        }
    }
}

// Get mock GPU info for simulation
void get_mock_gpu_info(MockGpuInfo *info, int gpu_id, float occupy_percent) {
    info->gpu_id = gpu_id;
    // Simulate 16GB total memory (typical high-end AMD GPU)
    info->total_memory = 16ULL * 1024 * 1024 * 1024;
    // Calculate used memory based on occupy percentage
    info->used_memory = (size_t)((info->total_memory * occupy_percent) / 100.0);
    // Simulated temperature (65-85 Celsius)
    info->temperature = 65.0f + (occupy_percent / 100.0f) * 20.0f;
    // Simulated utilization (varies with memory usage)
    info->utilization = occupy_percent * 0.5f + 20.0f;
}

// Occupy GPU memory (real mode)
void occupy_real_gpu(int gpu_id, float occupy_percent, const char *log_file) {
    int deviceCount;
    hipError_t err;

    // Check for HIP errors
    err = hipGetDeviceCount(&deviceCount);
    if (err != hipSuccess) {
        log_message(log_file, "Error: Failed to get device count: %s", hipGetErrorString(err));
        exit(EXIT_FAILURE);
    }

    if (deviceCount == 0) {
        log_message(log_file, "Error: No HIP-capable devices found");
        exit(EXIT_FAILURE);
    }

    if (gpu_id >= deviceCount) {
        log_message(log_file, "Error: GPU ID %d out of range (max: %d)", gpu_id, deviceCount - 1);
        exit(EXIT_FAILURE);
    }

    // Select the specified GPU
    err = hipSetDevice(gpu_id);
    if (err != hipSuccess) {
        log_message(log_file, "Error: Failed to set device to GPU %d: %s", gpu_id, hipGetErrorString(err));
        exit(EXIT_FAILURE);
    }

    // Get device properties
    hipDeviceProp_t props;
    err = hipGetDeviceProperties(&props, gpu_id);
    if (err != hipSuccess) {
        log_message(log_file, "Error: Failed to get properties for GPU %d: %s", gpu_id, hipGetErrorString(err));
        exit(EXIT_FAILURE);
    }

    log_message(log_file, "GPU %d: %s", gpu_id, props.name);
    log_message(log_file, "Total memory: %.2f GB", (float)props.totalGlobalMem / (1024.0f * 1024.0f * 1024.0f));

    // Calculate memory to occupy
    size_t total_mem = props.totalGlobalMem;
    size_t occupy_size = (size_t)((total_mem * occupy_percent) / 100.0f);

    // Round to page boundary for better performance
    const size_t page_size = 4096;
    occupy_size = (occupy_size / page_size) * page_size;

    log_message(log_file, "Attempting to occupy %.2f GB (%.1f%%)",
                (float)occupy_size / (1024.0f * 1024.0f * 1024.0f), occupy_percent);

    // Allocate memory to occupy
    void *d_ptr;
    err = hipMalloc(&d_ptr, occupy_size);
    if (err != hipSuccess) {
        log_message(log_file, "Error: Failed to allocate memory: %s", hipGetErrorString(err));
        exit(EXIT_FAILURE);
    }

    // Initialize memory with non-zero values to ensure allocation
    err = hipMemset(d_ptr, 0x42, occupy_size);
    if (err != hipSuccess) {
        log_message(log_file, "Error: Failed to initialize memory: %s", hipGetErrorString(err));
        hipFree(d_ptr);
        exit(EXIT_FAILURE);
    }

    log_message(log_file, "Successfully occupied %.2f GB on GPU %d",
                (float)occupy_size / (1024.0f * 1024.0f * 1024.0f), gpu_id);

    // Keep the memory allocated until signal
    log_message(log_file, "Holding memory allocation... (PID: %d)", getpid());

    while (keep_running) {
        sleep(1);
    }

    // Cleanup
    log_message(log_file, "Shutting down, freeing memory...");
    hipFree(d_ptr);
    hipDeviceReset();
    log_message(log_file, "Memory freed, shutdown complete");
}

// Occupy GPU memory (mock/simulation mode)
void occupy_mock_gpu(int gpu_id, float occupy_percent, const char *log_file) {
    MockGpuInfo info;

    get_mock_gpu_info(&info, gpu_id, occupy_percent);

    log_message(log_file, "=== MOCK MODE ===");
    log_message(log_file, "GPU %d: Mock AMD GPU (simulated)", gpu_id);
    log_message(log_file, "Total memory: %.2f GB", (float)info.total_memory / (1024.0f * 1024.0f * 1024.0f));
    log_message(log_file, "Occupying: %.2f GB (%.1f%%)",
                (float)info.used_memory / (1024.0f * 1024.0f * 1024.0f), occupy_percent);
    log_message(log_file, "Simulated temperature: %.1f°C", info.temperature);
    log_message(log_file, "Simulated utilization: %.1f%%", info.utilization);
    log_message(log_file, "Memory occupation successful");
    log_message(log_file, "Holding memory... (PID: %d)", getpid());

    // Simulate memory occupation
    size_t *mock_memory = malloc(info.used_memory);
    if (mock_memory) {
        // Initialize with pattern
        memset(mock_memory, 0x42, info.used_memory);
        log_message(log_file, "Mock memory allocated and initialized");

        while (keep_running) {
            sleep(1);
            // Periodically update simulated metrics
            log_message(log_file, "Status: Mock GPU %d - %.1f%% occupied, %.1f°C",
                        gpu_id, occupy_percent, info.temperature);
        }

        free(mock_memory);
        log_message(log_file, "Mock memory freed");
    } else {
        log_message(log_file, "Error: Failed to allocate mock memory");
        exit(EXIT_FAILURE);
    }

    log_message(log_file, "Shutdown complete");
}

#include <stdarg.h>

int main(int argc, char *argv[]) {
    OccupyConfig config;

    // Set up signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGHUP, signal_handler);

    // Parse command line arguments
    parse_args(argc, argv, &config);

    printf("=================================================\n");
    printf("  AMD GPU Memory Occupier v1.0.0\n");
    printf("=================================================\n");
    printf("GPU ID: %d\n", config.gpu_id);
    printf("Occupy: %.1f%%\n", config.occupy_percent);
    printf("Mode: %s\n", config.mock_mode ? "MOCK (simulation)" : "REAL (HIP)");
    if (config.log_file) {
        printf("Log file: %s\n", config.log_file);
    }
    printf("=================================================\n\n");

    if (config.mock_mode) {
        occupy_mock_gpu(config.gpu_id, config.occupy_percent, config.log_file);
    } else {
        occupy_real_gpu(config.gpu_id, config.occupy_percent, config.log_file);
    }

    // Free log file path if allocated
    if (config.log_file) {
        free(config.log_file);
    }

    return 0;
}

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/spf13/cobra"
)

var (
	port      int
	debug     bool
	logFile   string
	jsonLogs  bool
	host      string
	interactive bool
	checkGPU  bool
	serviceName string
	user      string
	workingDir string
	envVars   []string
	gpuCount  int
	gpuIds    string // comma-separated GPU IDs to monitor (e.g., "0,1,2")
)

func main() {
	cmd := &cobra.Command{
		Use:   "gpu_exporter",
		Short: "TokenMachine GPU metrics exporter",
		Version: "0.1.0",
		Run: func(cmd *cobra.Command, args []string) {
			// Default command is serve
			if err := runServer(port, host, interactive, checkGPU); err != nil {
				fmt.Printf("Error: %v\n", err)
				os.Exit(1)
			}
		},
	}

	cmd.PersistentFlags().IntVarP(&port, "port", "p", 9090, "Port to listen on")
	cmd.PersistentFlags().BoolVar(&debug, "debug", false, "Enable debug logging")
	cmd.PersistentFlags().StringVar(&logFile, "log-file", "", "Log file path")
	cmd.PersistentFlags().BoolVar(&jsonLogs, "json", false, "Enable JSON structured logging")

	// Add subcommands
	cmd.AddCommand(&cobra.Command{
		Use:   "serve",
		Short: "Run the GPU exporter HTTP server",
		Run: func(cmd *cobra.Command, args []string) {
			if err := runServer(port, host, interactive, checkGPU); err != nil {
				fmt.Printf("Error: %v\n", err)
				os.Exit(1)
			}
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "check",
		Short: "Check GPU availability",
		Run: func(cmd *cobra.Command, args []string) {
			if err := checkGPUAvailability(); err != nil {
				fmt.Printf("Error: %v\n", err)
				os.Exit(1)
			}
			fmt.Println("GPU check passed")
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "dump",
		Short: "Show metrics once (dry run)",
		Run: func(cmd *cobra.Command, args []string) {
			if err := dumpMetrics(); err != nil {
				fmt.Printf("Error: %v\n", err)
				os.Exit(1)
			}
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "generate-systemd",
		Short: "Generate systemd service file",
		Run: func(cmd *cobra.Command, args []string) {
			if err := generateSystemdFile(serviceName, user, workingDir, envVars); err != nil {
				fmt.Printf("Error: %v\n", err)
				os.Exit(1)
			}
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "test",
		Short: "Test mode with mock GPU data",
		Run: func(cmd *cobra.Command, args []string) {
			if err := runTestMode(gpuCount); err != nil {
				fmt.Printf("Error: %v\n", err)
				os.Exit(1)
			}
		},
	})

	// Add serve flags
	cmd.PersistentFlags().StringVarP(&host, "host", "H", "0.0.0.0", "Bind address")
	cmd.PersistentFlags().BoolVar(&interactive, "interactive", false, "Enable interactive mode")
	cmd.PersistentFlags().BoolVar(&checkGPU, "check-gpu", false, "Verify GPU availability on startup")

	// Add systemd flags
	cmd.PersistentFlags().StringVarP(&serviceName, "service-name", "s", "tokenmachine-gpu-exporter", "Service name")
	cmd.PersistentFlags().StringVarP(&user, "user", "u", "root", "User to run as")
	cmd.PersistentFlags().StringVarP(&workingDir, "working-dir", "w", "/opt/tokenmachine", "Working directory")
	cmd.PersistentFlags().StringSliceVarP(&envVars, "env", "e", []string{}, "Environment variables")

	// Add test flags
	cmd.PersistentFlags().IntVarP(&gpuCount, "gpu-count", "n", 1, "Number of mock GPUs")

	// Add GPU filter flags
	cmd.PersistentFlags().StringVar(&gpuIds, "gpu-ids", "", "Comma-separated GPU IDs to monitor (e.g., \"0,1,2\"). Monitor all GPUs if not specified.")

	// Execute
	if err := cmd.Execute(); err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}
}

func runServer(port int, host string, interactive bool, checkGPU bool) error {
	if checkGPU {
		if err := checkGPUAvailability(); err != nil {
			return fmt.Errorf("GPU check failed: %w", err)
		}
	}

	if interactive {
		if err := interactiveSetup(); err != nil {
			return err
		}
	}

	// Parse GPU IDs if specified
	var targetGpuIds []int
	if gpuIds != "" {
		parsedIds, err := parseGPUIds(gpuIds)
		if err != nil {
			return fmt.Errorf("invalid --gpu-ids parameter: %w", err)
		}
		targetGpuIds = parsedIds
		fmt.Printf("Monitoring specific GPUs: %v\n", targetGpuIds)
	} else {
		fmt.Println("Monitoring all available GPUs")
	}

	server := NewExporterServer(port, targetGpuIds)
	bindAddr := fmt.Sprintf("%s:%d", host, port)
	fmt.Printf("Server will bind to %s\n", bindAddr)

	if err := server.StartWithTcpListener(); err != nil {
		return fmt.Errorf("server failed: %w", err)
	}

	return nil
}

func interactiveSetup() error {
	fmt.Println("\n=== TokenMachine GPU Exporter Setup ===")

	if err := checkGPUAvailability(); err != nil {
		return err
	}

	fmt.Println("Press Enter to continue or Ctrl+C to exit...")
	fmt.Scanln()
	return nil
}

func checkGPUAvailability() error {
	fmt.Println("Checking GPU availability...")

	collector := NewGpuCollector()
	if _, err := collector.Collect(); err != nil {
		return fmt.Errorf("failed to check GPU availability: %w", err)
	}

	fmt.Printf("Found %d GPU(s)\n", len(collector.GetGpus()))
	return nil
}

func dumpMetrics() error {
	fmt.Println("Dumping metrics...")

	collector := NewGpuCollector()
	gpus, err := collector.Collect()
	if err != nil {
		return fmt.Errorf("failed to collect metrics: %w", err)
	}

	metrics := NewGpuMetrics()
	metrics.UpdateMetrics(gpus)

	fmt.Println("Prometheus Metrics:")
	fmt.Println(metrics.ToPrometheusText())

	fmt.Println("\nJSON Metrics:")
	fmt.Println(metrics.GetJsonMetrics())

	return nil
}

func generateSystemdFile(serviceName, user, workingDir string, envVars []string) error {
	var serviceFile string

	if len(envVars) > 0 {
		envVarsStr := ""
		for i, env := range envVars {
			if i > 0 {
				envVarsStr += "\\n"
			}
			envVarsStr += fmt.Sprintf("Environment=\"%s\"", env)
		}

		serviceFile = fmt.Sprintf(`[Unit]
Description=%s
After=network.target

[Service]
Type=simple
User=%s
WorkingDirectory=%s
ExecStart=/usr/local/bin/gpu_exporter serve --port 9090
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

%s

[Install]
WantedBy=multi-user.target
`, serviceName, user, workingDir, envVarsStr)
	} else {
		serviceFile = fmt.Sprintf(`[Unit]
Description=%s
After=network.target

[Service]
Type=simple
User=%s
WorkingDirectory=%s
ExecStart=/usr/local/bin/gpu_exporter serve --port 9090
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
`, serviceName, user, workingDir)
	}

	filePath := filepath.Join("/etc/systemd/system", serviceName+".service")
	if err := os.WriteFile(filePath, []byte(serviceFile), 0644); err != nil {
		return fmt.Errorf("failed to write systemd file: %w", err)
	}

	fmt.Printf("Generated systemd service file: %s\n", filePath)
	fmt.Println("Usage:")
	fmt.Println("  sudo systemctl daemon-reload")
	fmt.Println("  sudo systemctl start", serviceName)
	fmt.Println("  sudo systemctl enable", serviceName)

	return nil
}

func runTestMode(gpuCount int) error {
	fmt.Printf("Running in test mode with %d mock GPU(s)\n", gpuCount)

	metrics := NewGpuMetrics()
	mockGpus := generateMockGpus(gpuCount)
	metrics.UpdateMetrics(mockGpus)

	fmt.Println("\nMock Metrics:")
	fmt.Println(metrics.ToPrometheusText())

	return nil
}

func generateMockGpus(count int) []*GpuInfo {
	var gpus []*GpuInfo

	for i := 0; i < count; i++ {
		gpus = append(gpus, &GpuInfo{
			Index:                 i,
			Name:                 fmt.Sprintf("Mock GPU %d", i),
			UUID:                 fmt.Sprintf("gpu-%d-mock-uuid", i),
			PciBusId:             fmt.Sprintf("0000:%02x:00.0", i+1),
			MemoryTotalMiB:      uint64(8192 + i*1024),
			MemoryUsedMiB:        uint64(4096 + i*512),
			UtilizationGpuPercent: 50.0 + float64(i)*10.0,
			UtilizationMemoryPercent: 50.0 + float64(i)*5.0,
			TemperatureGpuCelsius: 40.0 + float64(i)*5.0,
			Timestamp:            fmt.Sprintf("%d", getUnixTimestamp()),
		})
	}

	return gpus
}

func getUnixTimestamp() int64 {
	return time.Now().Unix()
}

// parseGPUIds parses a comma-separated string of GPU IDs
// e.g., "0,1,2" -> []int{0, 1, 2}
func parseGPUIds(gpuIdsStr string) ([]int, error) {
	var ids []int
	parts := strings.Split(gpuIdsStr, ",")

	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		id, err := strconv.Atoi(part)
		if err != nil {
			return nil, fmt.Errorf("invalid GPU ID '%s': %w", part, err)
		}

		if id < 0 {
			return nil, fmt.Errorf("GPU ID must be non-negative, got %d", id)
		}

		ids = append(ids, id)
	}

	if len(ids) == 0 {
		return nil, fmt.Errorf("no valid GPU IDs provided")
	}

	return ids, nil
}
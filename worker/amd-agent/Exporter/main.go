package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	// Define command line flags
	port := flag.Int("p", 9091, "Port to listen on")
	portStr := flag.String("port", "", "Port to listen on (alternative)")
	gpuIdsStr := flag.String("gpu-ids", "", "Comma-separated list of GPU IDs to monitor")
	gpuIdsStrAlt := flag.String("g", "", "Comma-separated list of GPU IDs to monitor (alternative)")
	mockMode := flag.Bool("mock", false, "Enable mock mode for testing without real AMD hardware")
	mockModeAlt := flag.Bool("simulate", false, "Enable simulation mode")
	help := flag.Bool("h", false, "Show help")
	helpLong := flag.Bool("help", false, "Show help")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, `AMD GPU Exporter - Prometheus metrics exporter for AMD GPUs

Usage: %s [options]

Options:
`, os.Args[0])
		flag.PrintDefaults()
		fmt.Fprintf(os.Stderr, `
Examples:
  %s -p 9091                           # Start on port 9091
  %s --port 9091 --gpu-ids 0,1         # Monitor GPUs 0 and 1
  %s --mock                            # Start in mock/simulation mode

Endpoints:
  /metrics     - Prometheus metrics in text format
  /json        - GPU information in JSON format
  /health      - Health check (returns {"status": "healthy"})
  /            - This help page

Mock Mode:
  When running with --mock, the exporter simulates AMD GPU metrics
  for testing purposes without requiring actual AMD hardware.
`, os.Args[0], os.Args[0], os.Args[0])
	}

	flag.Parse()

	if *help || *helpLong {
		flag.Usage()
		os.Exit(0)
	}

	// Determine port
	actualPort := *port
	if *portStr != "" {
		if p, err := parsePort(*portStr); err == nil {
			actualPort = p
		} else {
			log.Printf("Error: Invalid port '%s': %v", *portStr, err)
			os.Exit(1)
		}
	}

	// Determine GPU IDs
	gpuIds := parseGpuIds(*gpuIdsStr)
	if *gpuIdsStrAlt != "" {
		gpuIds = parseGpuIds(*gpuIdsStrAlt)
	}

	// Determine mock mode
	isMock := *mockMode || *mockModeAlt

	// Create and configure server
	server := NewExporterServer(actualPort, gpuIds)
	server.SetMockMode(isMock)

	log.Printf("Starting AMD GPU Exporter")
	log.Printf("Port: %d", actualPort)
	if len(gpuIds) > 0 {
		log.Printf("Monitoring GPU IDs: %v", gpuIds)
	} else {
		log.Printf("Monitoring all available AMD GPUs")
	}
	if isMock {
		log.Printf("Mock mode: enabled (simulation mode)")
	}

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start server in goroutine
	go func() {
		if err := server.Start(); err != nil {
			log.Printf("Server error: %v", err)
			os.Exit(1)
		}
	}()

	// Wait for shutdown signal
	sig := <-sigChan
	log.Printf("Received signal %v, shutting down...", sig)
	server.Stop()
	log.Println("Server stopped")
}

// parsePort parses port from string
func parsePort(s string) (int, error) {
	var port int
	_, err := fmt.Sscanf(s, "%d", &port)
	return port, err
}

// parseGpuIds parses comma-separated GPU IDs
func parseGpuIds(s string) []int {
	var gpuIds []int
	if s == "" {
		return gpuIds
	}

	for _, part := range splitComma(s) {
		if id, err := parsePort(part); err == nil {
			gpuIds = append(gpuIds, id)
		}
	}

	return gpuIds
}

// splitComma splits a string by comma
func splitComma(s string) []string {
	var parts []string
	current := ""
	for _, c := range s {
		if c == ',' {
			parts = append(parts, current)
			current = ""
		} else if c != ' ' {
			current += string(c)
		}
	}
	if current != "" {
		parts = append(parts, current)
	}
	return parts
}

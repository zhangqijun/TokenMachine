package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ExporterServer serves AMD GPU metrics
type ExporterServer struct {
	amdInfos     []*AmdInfo
	amdMetrics   *AmdMetrics
	port         int
	targetGpuIds []int // Specific GPU IDs to monitor (empty = monitor all)
	mockMode     bool  // Enable mock mode for testing
	ctx          context.Context
	cancel       context.CancelFunc
	wg           sync.WaitGroup
}

// NewExporterServer creates a new ExporterServer
func NewExporterServer(port int, targetGpuIds []int) *ExporterServer {
	ctx, cancel := context.WithCancel(context.Background())
	return &ExporterServer{
		amdInfos:    make([]*AmdInfo, 0),
		amdMetrics:  NewAmdMetrics(),
		port:        port,
		targetGpuIds: targetGpuIds,
		ctx:         ctx,
		cancel:      cancel,
	}
}

// SetMockMode enables or disables mock mode
func (s *ExporterServer) SetMockMode(enabled bool) {
	s.mockMode = enabled
}

// Start begins serving AMD GPU metrics
func (s *ExporterServer) Start() error {
	// Start collection task
	s.wg.Add(1)
	go s.collectionLoop()

	// Start HTTP server
	addr := fmt.Sprintf("127.0.0.1:%d", s.port)
	server := &http.Server{
		Addr:    addr,
		Handler: http.HandlerFunc(s.handleRequest),
	}

	log.Printf("AMD exporter HTTP server started on %s", addr)

	errChan := make(chan error, 1)
	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errChan <- err
		}
	}()

	// Wait for server to start or error
	select {
	case err := <-errChan:
		return fmt.Errorf("server failed to start: %w", err)
	default:
		// Server started successfully
	}

	// Wait for shutdown signal
	go func() {
		<-s.ctx.Done()
		server.Shutdown(context.Background())
	}()

	// Run forever (or until shutdown)
	select {}
}

// Stop gracefully stops the server
func (s *ExporterServer) Stop() {
	s.cancel()
	s.wg.Wait()
}

// collectionLoop continuously collects AMD GPU metrics
func (s *ExporterServer) collectionLoop() {
	defer s.wg.Done()

	// Initial collection immediately
	collector := NewAmdCollector()
	if len(s.targetGpuIds) > 0 {
		collector.SetTargetGpuIds(s.targetGpuIds)
	}

	// Set mock mode if enabled
	if s.mockMode {
		collector.SetMockMode(true)
	}

	if gpus, err := collector.Collect(); err == nil {
		s.amdInfos = gpus
		s.amdMetrics.UpdateMetrics(gpus)
		log.Printf("Initial AMD GPU metrics collected: %d GPU(s)", len(gpus))
	} else {
		log.Printf("Failed to collect initial AMD GPU metrics: %v", err)
	}

	// Loop with collection every 5 seconds
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if gpus, err := collector.Collect(); err == nil {
				s.amdInfos = gpus
				s.amdMetrics.UpdateMetrics(gpus)
				log.Printf("Collected %d AMD GPU metrics", len(gpus))
			} else {
				log.Printf("Failed to collect AMD GPU metrics: %v", err)
			}
		}
	}
}

// handleRequest routes HTTP requests to appropriate handlers
func (s *ExporterServer) handleRequest(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	switch {
	case path == "/metrics":
		s.handleMetrics(w, r)
	case path == "/health":
		s.handleHealth(w, r)
	case path == "/json":
		s.handleJson(w, r)
	case path == "/":
		s.handleRoot(w, r)
	default:
		s.handleNotFound(w, r)
	}
}

// handleMetrics serves Prometheus metrics
func (s *ExporterServer) handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	w.Header().Set("Connection", "close")

	metrics := s.amdMetrics.ToPrometheusText()
	fmt.Fprint(w, metrics)
}

// handleHealth serves health check endpoint
func (s *ExporterServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Connection", "close")

	response := map[string]string{"status": "healthy"}
	json.NewEncoder(w).Encode(response)
}

// handleJson serves JSON metrics
func (s *ExporterServer) handleJson(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Connection", "close")

	json.NewEncoder(w).Encode(s.amdInfos)
}

// handleRoot serves root help page
func (s *ExporterServer) handleRoot(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Header().Set("Connection", "close")

	response := fmt.Sprintf(`# AMD GPU Exporter
# Version: 1.0.0
# Documentation: https://github.com/tokenmachine/amd-exporter

Metrics endpoints:
  GET /metrics    - Prometheus metrics
  GET /json      - JSON metrics
  GET /health    - Health check
  GET /          - This help

Mock mode: %s
Server time: %s
`, mapBool(s.mockMode), time.Now().Format(time.RFC3339))

	fmt.Fprint(w, response)
}

// handleNotFound serves 404 response
func (s *ExporterServer) handleNotFound(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Header().Set("Connection", "close")

	w.WriteHeader(http.StatusNotFound)
	fmt.Fprint(w, "# Not Found")
}

// StartWithTcpListener starts server with custom TCP listener
func (s *ExporterServer) StartWithTcpListener() error {
	addr := fmt.Sprintf("127.0.0.1:%d", s.port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to create listener: %w", err)
	}

	log.Printf("AMD exporter HTTP server started on %s", addr)

	// Start collection task
	s.wg.Add(1)
	go s.collectionLoop()

	// Start server loop
	go func() {
		defer s.wg.Done()

		for {
			select {
			case <-s.ctx.Done():
				return
			default:
				conn, err := listener.Accept()
				if err != nil {
					if s.ctx.Err() != nil {
						return
					}
					log.Printf("Accept error: %v", err)
					continue
				}

				s.wg.Add(1)
				go s.handleConnection(conn)
			}
		}
	}()

	// Wait for shutdown
	<-s.ctx.Done()
	listener.Close()
	s.wg.Wait()

	return nil
}

// handleConnection handles a single TCP connection
func (s *ExporterServer) handleConnection(conn net.Conn) {
	defer s.wg.Done()
	defer conn.Close()

	// Set read/write deadlines
	conn.SetReadDeadline(time.Now().Add(10 * time.Second))
	defer conn.SetWriteDeadline(time.Now().Add(10 * time.Second))

	// Read request
	buf := make([]byte, 1024)
	n, err := conn.Read(buf)
	if err != nil {
		log.Printf("Read error: %v", err)
		return
	}

	request := string(buf[:n])
	response := s.generateResponse(request)

	_, err = conn.Write([]byte(response))
	if err != nil {
		log.Printf("Write error: %v", err)
	}
}

// generateResponse generates HTTP response for raw TCP requests
func (s *ExporterServer) generateResponse(request string) string {
	if strings.HasPrefix(request, "GET /metrics") {
		metrics := s.amdMetrics.ToPrometheusText()
		return fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Type: text/plain; version=0.0.4\r\nConnection: close\r\n\r\n%s", metrics)
	} else if strings.HasPrefix(request, "GET /health") {
		return "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"status\": \"healthy\"}"
	} else if strings.HasPrefix(request, "GET /json") {
		jsonData, err := json.Marshal(s.amdInfos)
		if err != nil {
			return "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"error\": \"internal server error\"}"
		}
		return fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n%s", string(jsonData))
	} else if strings.HasPrefix(request, "GET /") {
		response := fmt.Sprintf(`# AMD GPU Exporter
# Version: 1.0.0
# Documentation: https://github.com/tokenmachine/amd-exporter

Metrics endpoints:
  GET /metrics    - Prometheus metrics
  GET /json      - JSON metrics
  GET /health    - Health check
  GET /          - This help

Mock mode: %s
Server time: %s
`, mapBool(s.mockMode), time.Now().Format(time.RFC3339))
		return fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n%s", response)
	} else {
		return "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n# Not Found"
	}
}

// GetPort returns the server port
func (s *ExporterServer) GetPort() int {
	return s.port
}

// IsMockMode returns whether mock mode is enabled
func (s *ExporterServer) IsMockMode() bool {
	return s.mockMode
}

// GetMetricsSummary returns a summary of collected metrics
func (s *ExporterServer) GetMetricsSummary() map[string]interface{} {
	return s.amdMetrics.GetSummary()
}

// ParsePortFromArgs parses port from command line arguments
func ParsePortFromArgs(args []string) int {
	for i, arg := range args {
		if arg == "-p" || arg == "--port" {
			if i+1 < len(args) {
				if port, err := strconv.Atoi(args[i+1]); err == nil {
					return port
				}
			}
		}
		if strings.HasPrefix(arg, "--port=") {
			if port, err := strconv.Atoi(strings.TrimPrefix(arg, "--port=")); err == nil {
				return port
			}
		}
	}
	return 9091 // Default AMD exporter port
}

// ParseGpuIdsFromArgs parses GPU IDs from command line arguments
func ParseGpuIdsFromArgs(args []string) []int {
	var gpuIds []int

	for i, arg := range args {
		if arg == "--gpu-ids" || arg == "-g" {
			if i+1 < len(args) {
				for _, idStr := range strings.Split(args[i+1], ",") {
					if id, err := strconv.Atoi(strings.TrimSpace(idStr)); err == nil {
						gpuIds = append(gpuIds, id)
					}
				}
			}
		}
		if strings.HasPrefix(arg, "--gpu-ids=") {
			idStr := strings.TrimPrefix(arg, "--gpu-ids=")
			for _, id := range strings.Split(idStr, ",") {
				if id, err := strconv.Atoi(strings.TrimSpace(id)); err == nil {
					gpuIds = append(gpuIds, id)
				}
			}
		}
	}

	return gpuIds
}

// ParseMockModeFromArgs parses mock mode flag from command line arguments
func ParseMockModeFromArgs(args []string) bool {
	for _, arg := range args {
		if arg == "--mock" || arg == "-m" || arg == "--simulate" {
			return true
		}
		if strings.HasPrefix(arg, "--mock=") || strings.HasPrefix(arg, "--simulate=") {
			val := strings.TrimPrefix(arg, "--mock=")
			val = strings.TrimPrefix(val, "--simulate=")
			return val == "true" || val == "1" || val == "yes"
		}
	}
	return false
}

// Helper function to convert bool to string
func mapBool(b bool) string {
	if b {
		return "enabled"
	}
	return "disabled"
}

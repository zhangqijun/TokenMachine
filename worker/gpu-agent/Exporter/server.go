package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"sync"
	"time"
)

type ExporterServer struct {
	gpuInfos      []*GpuInfo
	gpuMetrics    *GpuMetrics
	port          int
	targetGpuIds  []int // Specific GPU IDs to monitor (empty = monitor all)
	ctx           context.Context
	cancel        context.CancelFunc
	wg            sync.WaitGroup
}

func NewExporterServer(port int, targetGpuIds []int) *ExporterServer {
	ctx, cancel := context.WithCancel(context.Background())
	return &ExporterServer{
		gpuInfos:     make([]*GpuInfo, 0),
		gpuMetrics:   NewGpuMetrics(),
		port:         port,
		targetGpuIds: targetGpuIds,
		ctx:          ctx,
		cancel:       cancel,
	}
}

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

	log.Printf("GPU exporter HTTP server started on %s", addr)

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

func (s *ExporterServer) Stop() {
	s.cancel()
	s.wg.Wait()
}

func (s *ExporterServer) collectionLoop() {
	defer s.wg.Done()

	// Initial collection immediately
	collector := NewGpuCollector()
	if len(s.targetGpuIds) > 0 {
		collector.SetTargetGpuIds(s.targetGpuIds)
	}

	if gpus, err := collector.Collect(); err == nil {
		s.gpuInfos = gpus
		s.gpuMetrics.UpdateMetrics(gpus)
		log.Printf("Initial GPU metrics collected: %d GPU(s)", len(gpus))
	} else {
		log.Printf("Failed to collect initial GPU metrics: %v", err)
	}

	// Loop with collection
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if gpus, err := collector.Collect(); err == nil {
				s.gpuInfos = gpus
				s.gpuMetrics.UpdateMetrics(gpus)
				log.Printf("Collected %d GPU metrics", len(gpus))
			} else {
				log.Printf("Failed to collect GPU metrics: %v", err)
			}
		}
	}
}

func (s *ExporterServer) handleRequest(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	switch {
	case path == "/metrics":
		s.handleMetrics(w, r)
	case path == "/health":
		s.handleHealth(w, r)
	case path == "/json":
		s.handleJson(w, r)
	case path == "/" || path == "/index":
		s.handleRoot(w, r)
	default:
		s.handleNotFound(w, r)
	}
}

func (s *ExporterServer) handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	w.Header().Set("Connection", "close")

	metrics := s.gpuMetrics.ToPrometheusText()
	fmt.Fprint(w, metrics)
}

func (s *ExporterServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Connection", "close")

	response := map[string]string{"status": "healthy"}
	json.NewEncoder(w).Encode(response)
}

func (s *ExporterServer) handleJson(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Connection", "close")

	json.NewEncoder(w).Encode(s.gpuInfos)
}

func (s *ExporterServer) handleRoot(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Header().Set("Connection", "close")

	response := fmt.Sprintf(`# GPU Exporter
# Version: 0.1.0
# Documentation: https://github.com/tokenmachine/gpu-exporter

Metrics endpoints:
  GET /metrics    - Prometheus metrics
  GET /json      - JSON metrics
  GET /health    - Health check
  GET /          - This help

# Server time: %s
`, time.Now().Format(time.RFC3339))

	fmt.Fprint(w, response)
}

func (s *ExporterServer) handleNotFound(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Header().Set("Connection", "close")

	w.WriteHeader(http.StatusNotFound)
	fmt.Fprint(w, "# Not Found")
}

// Alternative implementation using net.Listener for more control
func (s *ExporterServer) StartWithTcpListener() error {
	addr := fmt.Sprintf("127.0.0.1:%d", s.port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to create listener: %w", err)
	}

	log.Printf("GPU exporter HTTP server started on %s", addr)

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

func (s *ExporterServer) generateResponse(request string) string {
	if stringsContains(request, "GET /metrics") {
		metrics := s.gpuMetrics.ToPrometheusText()
		return fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Type: text/plain; version=0.0.4\r\nConnection: close\r\n\r\n%s", metrics)
	} else if stringsContains(request, "GET /health") {
		return "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"status\": \"healthy\"}"
	} else if stringsContains(request, "GET /json") {
		jsonData, err := json.Marshal(s.gpuInfos)
		if err != nil {
			return "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"error\": \"internal server error\"}"
		}
		return fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n%s", string(jsonData))
	} else if stringsContains(request, "GET /") {
		response := fmt.Sprintf(`# GPU Exporter
# Version: 0.1.0
# Documentation: https://github.com/tokenmachine/gpu-exporter

Metrics endpoints:
  GET /metrics    - Prometheus metrics
  GET /json      - JSON metrics
  GET /health    - Health check
  GET /          - This help

# Server time: %s
`, time.Now().Format(time.RFC3339))
		return fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n%s", response)
	} else {
		return "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n# Not Found"
	}
}

// Helper function to check if string contains substring
func stringsContains(s, substr string) bool {
	return len(s) >= len(substr) && s[:len(substr)] == substr || len(s) > len(substr) && s[len(s)-len(substr):] == substr
}
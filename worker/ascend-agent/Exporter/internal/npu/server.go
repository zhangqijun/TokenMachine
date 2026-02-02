package npu

import (
	"fmt"
	"log"
	"net/http"
	"strconv"
	"time"
)

// Exporter Prometheus 导出器
type Exporter struct {
	monitor *Monitor
}

// NewExporter 创建新的导出器
func NewExporter(monitor *Monitor) *Exporter {
	return &Exporter{monitor: monitor}
}

// StartServer 启动 HTTP 服务器
func (e *Exporter) StartServer(port int) {
	addr := fmt.Sprintf(":%d", port)

	http.HandleFunc("/metrics", e.handleMetrics)
	http.HandleFunc("/health", e.handleHealth)

	log.Printf("启动 Ascend NPU Exporter，监听端口 %d", port)
	log.Printf("指标端点: http://localhost:%d/metrics", port)
	log.Printf("健康检查: http://localhost:%d/health", port)

	// 启动指标收集定时器
	go e.collectMetricsPeriodically()

	// 启动 HTTP 服务器
	err := http.ListenAndServe(addr, nil)
	if err != nil {
		log.Fatalf("启动 HTTP 服务器失败: %v", err)
	}
}

// collectMetricsPeriodically 定期收集指标
func (e *Exporter) collectMetricsPeriodically() {
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		// 预热：确保能及时获取指标
		e.monitor.GetNPUInfo()
	}
}

// handleMetrics 处理 /metrics 端点
func (e *Exporter) handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Header().Set("Content-Length", strconv.Itoa(len(e.monitor.CollectMetrics())))

	metrics := e.monitor.CollectMetrics()
	w.Write([]byte(metrics))
}

// handleHealth 处理 /health 端点
func (e *Exporter) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// 检查 NPU 状态
	npus, err := e.monitor.GetNPUInfo()
	if err != nil {
		w.WriteHeader(http.StatusServiceUnavailable)
		w.Write([]byte(`{"status": "unhealthy", "error": "` + err.Error() + `"}`))
		return
	}

	// 检查是否有可用的 NPU
	available := 0
	for _, n := range npus {
		if n.Available {
			available++
		}
	}

	if available == 0 {
		w.WriteHeader(http.StatusServiceUnavailable)
		w.Write([]byte(`{"status": "unhealthy", "message": "no available npu"}`))
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Write([]byte(fmt.Sprintf(`{"status": "healthy", "npu_count": %d, "available_count": %d}`, len(npus), available)))
}

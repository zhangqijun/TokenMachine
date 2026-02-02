package main

import (
	"fmt"
	"strings"
	"time"
)

// AmdMetrics represents AMD GPU metrics for Prometheus
type AmdMetrics struct {
	metrics []string
}

// NewAmdMetrics creates a new AmdMetrics instance
func NewAmdMetrics() *AmdMetrics {
	return &AmdMetrics{
		metrics: make([]string, 0),
	}
}

// UpdateMetrics updates metrics from collected GPU info
func (m *AmdMetrics) UpdateMetrics(gpus []*AmdInfo) {
	m.metrics = make([]string, 0)

	// Add GPU count metric
	m.metrics = append(m.metrics, fmt.Sprintf("amd_gpu_count %d", len(gpus)))

	for _, gpu := range gpus {
		// Memory metrics (in bytes)
		m.metrics = append(m.metrics, fmt.Sprintf("amd_memory_used_bytes{gpu=\"%d\"} %d",
			gpu.Index, gpu.MemoryUsedMiB*1024*1024))
		m.metrics = append(m.metrics, fmt.Sprintf("amd_memory_total_bytes{gpu=\"%d\"} %d",
			gpu.Index, gpu.MemoryTotalMiB*1024*1024))

		// Utilization metrics (as ratio 0-1)
		m.metrics = append(m.metrics, fmt.Sprintf("amd_memory_utilization{gpu=\"%d\"} %.6f",
			gpu.Index, gpu.GetMemoryUtilization()))
		m.metrics = append(m.metrics, fmt.Sprintf("amd_utilization{gpu=\"%d\"} %.6f",
			gpu.Index, gpu.UtilizationGpuPercent/100.0))

		// Temperature (in Celsius)
		m.metrics = append(m.metrics, fmt.Sprintf("amd_temperature_celsius{gpu=\"%d\"} %.1f",
			gpu.Index, gpu.TemperatureGpuCelsius))

		// Memory utilization percentage
		m.metrics = append(m.metrics, fmt.Sprintf("amd_memory_utilization_percent{gpu=\"%d\"} %.1f",
			gpu.Index, gpu.UtilizationMemoryPercent))

		// GPU utilization percentage
		m.metrics = append(m.metrics, fmt.Sprintf("amd_utilization_percent{gpu=\"%d\"} %.1f",
			gpu.Index, gpu.UtilizationGpuPercent))
	}

	// Add timestamp
	m.metrics = append(m.metrics, fmt.Sprintf("amd_exporter_collected_timestamp_seconds %d",
		time.Now().Unix()))
}

// ToPrometheusText returns metrics in Prometheus text format
func (m *AmdMetrics) ToPrometheusText() string {
	var sb strings.Builder

	// Add help and type comments
	sb.WriteString("# HELP amd_gpu_count Number of AMD GPUs detected\n")
	sb.WriteString("# TYPE amd_gpu_count gauge\n")
	sb.WriteString("# HELP amd_memory_used_bytes AMD GPU memory used in bytes\n")
	sb.WriteString("# TYPE amd_memory_used_bytes gauge\n")
	sb.WriteString("# HELP amd_memory_total_bytes AMD GPU total memory in bytes\n")
	sb.WriteString("# TYPE amd_memory_total_bytes gauge\n")
	sb.WriteString("# HELP amd_memory_utilization AMD GPU memory utilization ratio (0-1)\n")
	sb.WriteString("# TYPE amd_memory_utilization gauge\n")
	sb.WriteString("# HELP amd_utilization AMD GPU utilization ratio (0-1)\n")
	sb.WriteString("# TYPE amd_utilization gauge\n")
	sb.WriteString("# HELP amd_temperature_celsius AMD GPU temperature in Celsius\n")
	sb.WriteString("# TYPE amd_temperature_celsius gauge\n")
	sb.WriteString("# HELP amd_memory_utilization_percent AMD GPU memory utilization percentage\n")
	sb.WriteString("# TYPE amd_memory_utilization_percent gauge\n")
	sb.WriteString("# HELP amd_utilization_percent AMD GPU utilization percentage\n")
	sb.WriteString("# TYPE amd_utilization_percent gauge\n")
	sb.WriteString("# HELP amd_exporter_collected_timestamp_seconds Timestamp of last collection\n")
	sb.WriteString("# TYPE amd_exporter_collected_timestamp_seconds gauge\n")

	// Add metric lines
	for _, metric := range m.metrics {
		sb.WriteString(metric + "\n")
	}

	return sb.String()
}

// GetSummary returns a summary of the metrics
func (m *AmdMetrics) GetSummary() map[string]interface{} {
	summary := make(map[string]interface{})
	summary["metric_count"] = len(m.metrics)

	// Extract key values
	totalMem := uint64(0)
	usedMem := uint64(0)
	maxTemp := 0.0
	maxUtil := 0.0

	for _, metric := range m.metrics {
		if strings.Contains(metric, "memory_total_bytes") {
			parts := strings.SplitN(metric, " ", 2)
			if len(parts) == 2 {
				if val, err := parseUint64(parts[1]); err == nil {
					totalMem += val
				}
			}
		}
		if strings.Contains(metric, "memory_used_bytes") {
			parts := strings.SplitN(metric, " ", 2)
			if len(parts) == 2 {
				if val, err := parseUint64(parts[1]); err == nil {
					usedMem += val
				}
			}
		}
		if strings.Contains(metric, "temperature_celsius") {
			parts := strings.SplitN(metric, " ", 2)
			if len(parts) == 2 {
				if val, err := parseFloat64(parts[1]); err == nil && val > maxTemp {
					maxTemp = val
				}
			}
		}
		if strings.Contains(metric, "utilization_percent") {
			parts := strings.SplitN(metric, " ", 2)
			if len(parts) == 2 {
				if val, err := parseFloat64(parts[1]); err == nil && val > maxUtil {
					maxUtil = val
				}
			}
		}
	}

	summary["total_memory_bytes"] = totalMem
	summary["used_memory_bytes"] = usedMem
	summary["max_temperature_celsius"] = maxTemp
	summary["max_utilization_percent"] = maxUtil

	if totalMem > 0 {
		summary["memory_utilization_percent"] = float64(usedMem) / float64(totalMem) * 100
	} else {
		summary["memory_utilization_percent"] = 0.0
	}

	return summary
}

// Helper functions

func parseUint64(s string) (uint64, error) {
	var val uint64
	_, err := fmt.Sscanf(s, "%d", &val)
	return val, err
}

func parseFloat64(s string) (float64, error) {
	var val float64
	_, err := fmt.Sscanf(s, "%f", &val)
	return val, err
}

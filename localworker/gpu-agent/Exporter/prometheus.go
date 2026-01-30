package main

import (
	"bytes"
	"encoding/json"
	"fmt"
)

type GpuMetrics struct {
	GpuMemoryUsed      float64
	GpuMemoryTotal     float64
	GpuMemoryUtilization float64
	GpuUtilization     float64
	GpuTemperature    float64
	GpuCount           float64
	GpuMemoryAllocated float64

	// Per-GPU metrics
	PerGpuMemoryUsed      map[int]float64
	PerGpuMemoryTotal     map[int]float64
	PerGpuMemoryUtilization map[int]float64
	PerGpuUtilization     map[int]float64
	PerGpuTemperature    map[int]float64
}

func NewGpuMetrics() *GpuMetrics {
	return &GpuMetrics{
		PerGpuMemoryUsed:         make(map[int]float64),
		PerGpuMemoryTotal:        make(map[int]float64),
		PerGpuMemoryUtilization: make(map[int]float64),
		PerGpuUtilization:        make(map[int]float64),
		PerGpuTemperature:        make(map[int]float64),
	}
}

func (m *GpuMetrics) UpdateMetrics(gpus []*GpuInfo) {
	// Reset per-GPU metrics
	m.PerGpuMemoryUsed = make(map[int]float64)
	m.PerGpuMemoryTotal = make(map[int]float64)
	m.PerGpuMemoryUtilization = make(map[int]float64)
	m.PerGpuUtilization = make(map[int]float64)
	m.PerGpuTemperature = make(map[int]float64)

	// Calculate global metrics
	var totalMemory, usedMemory uint64
	var totalUtilization float64
	var totalTemp float64
	var tempCount int

	for _, gpu := range gpus {
		totalMemory += gpu.MemoryTotalMiB
		usedMemory += gpu.MemoryUsedMiB
		totalUtilization += gpu.UtilizationGpuPercent

		if gpu.TemperatureGpuCelsius > 0 {
			totalTemp += gpu.TemperatureGpuCelsius
			tempCount++
		}
	}

	m.GpuMemoryTotal = float64(totalMemory * 1024 * 1024)
	m.GpuMemoryUsed = float64(usedMemory * 1024 * 1024)
	m.GpuCount = float64(len(gpus))
	m.GpuMemoryAllocated = float64(totalMemory * 1024 * 1024)

	// Calculate memory utilization
	if totalMemory > 0 {
		m.GpuMemoryUtilization = float64(usedMemory) / float64(totalMemory)
	} else {
		m.GpuMemoryUtilization = 0.0
	}

	// Calculate average utilization
	if len(gpus) > 0 {
		m.GpuUtilization = totalUtilization / float64(len(gpus))
	} else {
		m.GpuUtilization = 0.0
	}

	// Calculate average temperature
	if tempCount > 0 {
		m.GpuTemperature = totalTemp / float64(tempCount)
	} else {
		m.GpuTemperature = 0.0
	}

	// Update per-GPU metrics
	for _, gpu := range gpus {
		gpuId := gpu.Index

		m.PerGpuMemoryUsed[gpuId] = float64(gpu.MemoryUsedMiB * 1024 * 1024)
		m.PerGpuMemoryTotal[gpuId] = float64(gpu.MemoryTotalMiB * 1024 * 1024)
		m.PerGpuMemoryUtilization[gpuId] = gpu.GetMemoryUtilization()
		m.PerGpuUtilization[gpuId] = gpu.UtilizationGpuPercent

		if gpu.TemperatureGpuCelsius > 0 {
			m.PerGpuTemperature[gpuId] = gpu.TemperatureGpuCelsius
		}
	}
}

func (m *GpuMetrics) ToPrometheusText() string {
	var buffer bytes.Buffer

	// Global metrics
	buffer.WriteString(fmt.Sprintf("# HELP gpu_memory_used_bytes GPU memory used in bytes\n"))
	buffer.WriteString(fmt.Sprintf("# TYPE gpu_memory_used_bytes gauge\n"))
	buffer.WriteString(fmt.Sprintf("gpu_memory_used_bytes %.0f\n", m.GpuMemoryUsed))

	buffer.WriteString(fmt.Sprintf("# HELP gpu_memory_total_bytes GPU memory total in bytes\n"))
	buffer.WriteString(fmt.Sprintf("# TYPE gpu_memory_total_bytes gauge\n"))
	buffer.WriteString(fmt.Sprintf("gpu_memory_total_bytes %.0f\n", m.GpuMemoryTotal))

	buffer.WriteString(fmt.Sprintf("# HELP gpu_memory_utilization GPU memory utilization ratio\n"))
	buffer.WriteString(fmt.Sprintf("# TYPE gpu_memory_utilization gauge\n"))
	buffer.WriteString(fmt.Sprintf("gpu_memory_utilization %.6f\n", m.GpuMemoryUtilization))

	buffer.WriteString(fmt.Sprintf("# HELP gpu_utilization GPU utilization percentage\n"))
	buffer.WriteString(fmt.Sprintf("# TYPE gpu_utilization gauge\n"))
	buffer.WriteString(fmt.Sprintf("gpu_utilization %.6f\n", m.GpuUtilization))

	buffer.WriteString(fmt.Sprintf("# HELP gpu_temperature_celsius GPU temperature in Celsius\n"))
	buffer.WriteString(fmt.Sprintf("# TYPE gpu_temperature_celsius gauge\n"))
	buffer.WriteString(fmt.Sprintf("gpu_temperature_celsius %.6f\n", m.GpuTemperature))

	buffer.WriteString(fmt.Sprintf("# HELP gpu_count Number of GPUs\n"))
	buffer.WriteString(fmt.Sprintf("# TYPE gpu_count gauge\n"))
	buffer.WriteString(fmt.Sprintf("gpu_count %.0f\n", m.GpuCount))

	buffer.WriteString(fmt.Sprintf("# HELP gpu_memory_allocated_bytes GPU memory allocated in bytes\n"))
	buffer.WriteString(fmt.Sprintf("# TYPE gpu_memory_allocated_bytes gauge\n"))
	buffer.WriteString(fmt.Sprintf("gpu_memory_allocated_bytes %.0f\n", m.GpuMemoryAllocated))

	// Per-GPU metrics
	for gpuId := range m.PerGpuMemoryUsed {
		buffer.WriteString(fmt.Sprintf("# HELP gpu%d_memory_used_bytes GPU %d memory used in bytes\n", gpuId, gpuId))
		buffer.WriteString(fmt.Sprintf("# TYPE gpu%d_memory_used_bytes gauge\n", gpuId))
		buffer.WriteString(fmt.Sprintf("gpu%d_memory_used_bytes %.0f\n", gpuId, m.PerGpuMemoryUsed[gpuId]))

		buffer.WriteString(fmt.Sprintf("# HELP gpu%d_memory_total_bytes GPU %d memory total in bytes\n", gpuId, gpuId))
		buffer.WriteString(fmt.Sprintf("# TYPE gpu%d_memory_total_bytes gauge\n", gpuId))
		buffer.WriteString(fmt.Sprintf("gpu%d_memory_total_bytes %.0f\n", gpuId, m.PerGpuMemoryTotal[gpuId]))

		buffer.WriteString(fmt.Sprintf("# HELP gpu%d_memory_utilization GPU %d memory utilization ratio\n", gpuId, gpuId))
		buffer.WriteString(fmt.Sprintf("# TYPE gpu%d_memory_utilization gauge\n", gpuId))
		buffer.WriteString(fmt.Sprintf("gpu%d_memory_utilization %.6f\n", gpuId, m.PerGpuMemoryUtilization[gpuId]))

		buffer.WriteString(fmt.Sprintf("# HELP gpu%d_utilization GPU %d utilization percentage\n", gpuId, gpuId))
		buffer.WriteString(fmt.Sprintf("# TYPE gpu%d_utilization gauge\n", gpuId))
		buffer.WriteString(fmt.Sprintf("gpu%d_utilization %.6f\n", gpuId, m.PerGpuUtilization[gpuId]))

		buffer.WriteString(fmt.Sprintf("# HELP gpu%d_temperature_celsius GPU %d temperature in Celsius\n", gpuId, gpuId))
		buffer.WriteString(fmt.Sprintf("# TYPE gpu%d_temperature_celsius gauge\n", gpuId))
		if m.PerGpuTemperature[gpuId] > 0 {
			buffer.WriteString(fmt.Sprintf("gpu%d_temperature_celsius %.6f\n", gpuId, m.PerGpuTemperature[gpuId]))
		}
	}

	return buffer.String()
}

func (m *GpuMetrics) GetJsonMetrics() map[string]interface{} {
	perGpu := make(map[string]interface{})

	for gpuId := range m.PerGpuMemoryUsed {
		gpuObj := make(map[string]interface{})

		gpuObj[fmt.Sprintf("gpu%d_memory_used_bytes", gpuId)] = m.PerGpuMemoryUsed[gpuId]
		gpuObj[fmt.Sprintf("gpu%d_memory_total_bytes", gpuId)] = m.PerGpuMemoryTotal[gpuId]
		gpuObj[fmt.Sprintf("gpu%d_memory_utilization", gpuId)] = m.PerGpuMemoryUtilization[gpuId]
		gpuObj[fmt.Sprintf("gpu%d_utilization", gpuId)] = m.PerGpuUtilization[gpuId]
		gpuObj[fmt.Sprintf("gpu%d_temperature_celsius", gpuId)] = m.PerGpuTemperature[gpuId]

		perGpu[fmt.Sprintf("gpu%d", gpuId)] = gpuObj
	}

	return map[string]interface{}{
		"gpu_memory_used_bytes":     m.GpuMemoryUsed,
		"gpu_memory_total_bytes":    m.GpuMemoryTotal,
		"gpu_memory_utilization":   m.GpuMemoryUtilization,
		"gpu_utilization_percent":   m.GpuUtilization,
		"gpu_temperature_celsius":   m.GpuTemperature,
		"gpu_count":                 m.GpuCount,
		"gpu_memory_allocated_bytes": m.GpuMemoryAllocated,
		"per_gpu":                  perGpu,
	}
}

func (m *GpuMetrics) GetJsonString() string {
	data := m.GetJsonMetrics()
	jsonBytes, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return "{}"
	}
	return string(jsonBytes)
}
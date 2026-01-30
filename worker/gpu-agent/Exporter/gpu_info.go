package main

import (
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

type GpuError struct {
	Message string
}

func (e *GpuError) Error() string {
	return e.Message
}

type GpuInfo struct {
	Index                 int
	Name                 string
	UUID                 string
	PciBusId             string
	MemoryTotalMiB      uint64
	MemoryUsedMiB        uint64
	UtilizationGpuPercent float64
	UtilizationMemoryPercent float64
	TemperatureGpuCelsius float64
	Timestamp            string
}

func NewGpuInfo(index int) *GpuInfo {
	return &GpuInfo{
		Index:     index,
		Timestamp: time.Now().Format(time.RFC3339),
	}
}

func (g *GpuInfo) GetMemoryUtilization() float64 {
	if g.MemoryTotalMiB > 0 {
		return float64(g.MemoryUsedMiB) / float64(g.MemoryTotalMiB)
	}
	return 0.0
}

type GpuCollector struct {
	gpus         []*GpuInfo
	targetGpuIds []int // Specific GPU IDs to monitor (empty = monitor all)
}

func NewGpuCollector() *GpuCollector {
	return &GpuCollector{
		gpus: make([]*GpuInfo, 0),
	}
}

// SetTargetGpuIds sets the specific GPU IDs to monitor
func (c *GpuCollector) SetTargetGpuIds(ids []int) {
	c.targetGpuIds = ids
}

func (c *GpuCollector) Collect() ([]*GpuInfo, error) {
	var gpuIdsToCollect []int

	if len(c.targetGpuIds) > 0 {
		// Monitor specific GPUs
		gpuIdsToCollect = c.targetGpuIds
	} else {
		// Monitor all GPUs
		gpuCount, err := c.GetGpuCount()
		if err != nil {
			return nil, fmt.Errorf("failed to get GPU count: %w", err)
		}
		for i := 0; i < gpuCount; i++ {
			gpuIdsToCollect = append(gpuIdsToCollect, i)
		}
	}

	// Clear previous GPU data
	c.gpus = make([]*GpuInfo, 0)

	// Batch collect GPU info
	if err := c.CollectSpecificGpus(gpuIdsToCollect); err != nil {
		return nil, fmt.Errorf("failed to collect GPU info: %w", err)
	}

	return c.gpus, nil
}

func (c *GpuCollector) GetGpus() []*GpuInfo {
	return c.gpus
}

// CollectSpecificGpus collects info for specific GPU IDs only
func (c *GpuCollector) CollectSpecificGpus(gpuIds []int) error {
	for _, gpuId := range gpuIds {
		// Collect basic info
		output, err := exec.Command("nvidia-smi",
			"-i", strconv.Itoa(gpuId),
			"--query-gpu=name,uuid,memory.total,pci.bus_id",
			"--format=csv,noheader,nounits").Output()
		if err != nil {
			return &GpuError{
				Message: fmt.Sprintf("nvidia-smi info query failed for GPU %d: %v", gpuId, err),
			}
		}

		basicInfo := strings.TrimSpace(string(output))
		if basicInfo == "" {
			return &GpuError{
				Message: fmt.Sprintf("no info output for GPU %d", gpuId),
			}
		}

		// Collect status info
		output, err = exec.Command("nvidia-smi",
			"-i", strconv.Itoa(gpuId),
			"--query-gpu=utilization.gpu,memory.used,temperature.gpu",
			"--format=csv,noheader,nounits").Output()
		if err != nil {
			return &GpuError{
				Message: fmt.Sprintf("nvidia-smi status query failed for GPU %d: %v", gpuId, err),
			}
		}

		statusInfo := strings.TrimSpace(string(output))
		if statusInfo == "" {
			return &GpuError{
				Message: fmt.Sprintf("no status output for GPU %d", gpuId),
			}
		}

		// Parse and create GPU info
		gpuInfo := NewGpuInfo(gpuId)

		// Parse basic info
		parts := strings.Split(basicInfo, ",")
		if len(parts) >= 4 {
			gpuInfo.Name = strings.TrimSpace(parts[0])
			gpuInfo.UUID = strings.TrimSpace(parts[1])
			gpuInfo.PciBusId = strings.TrimSpace(parts[3])

			if memory, err := strconv.ParseUint(strings.TrimSpace(parts[2]), 10, 64); err == nil {
				gpuInfo.MemoryTotalMiB = memory
			}
		}

		// Parse status info
		parts = strings.Split(statusInfo, ",")
		if len(parts) >= 3 {
			// GPU utilization
			if util, err := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64); err == nil {
				gpuInfo.UtilizationGpuPercent = util
			}

			// Memory used
			if used, err := strconv.ParseUint(strings.TrimSpace(parts[1]), 10, 64); err == nil {
				gpuInfo.MemoryUsedMiB = used
			}

			// Temperature
			if temp, err := strconv.ParseFloat(strings.TrimSpace(parts[2]), 64); err == nil {
				gpuInfo.TemperatureGpuCelsius = temp
			}
		}

		c.gpus = append(c.gpus, gpuInfo)
	}

	return nil
}

func (c *GpuCollector) CollectAllGpusBatch(gpuCount int) error {
	basicInfo, err := c.GetAllGpuInfoBatch(gpuCount)
	if err != nil {
		return err
	}

	statusInfo, err := c.GetAllGpuStatusBatch(gpuCount)
	if err != nil {
		return err
	}

	// Combine the info
	for i := 0; i < gpuCount; i++ {
		gpuInfo := NewGpuInfo(i)

		// Parse basic info
		if i < len(basicInfo) {
			parts := strings.Split(basicInfo[i], ",")
			if len(parts) >= 4 {
				gpuInfo.Name = strings.TrimSpace(parts[0])
				gpuInfo.UUID = strings.TrimSpace(parts[1])
				gpuInfo.PciBusId = strings.TrimSpace(parts[3])

				if memory, err := strconv.ParseUint(strings.TrimSpace(parts[2]), 10, 64); err == nil {
					gpuInfo.MemoryTotalMiB = memory
				}
			}
		}

		// Parse status info
		if i < len(statusInfo) {
			parts := strings.Split(statusInfo[i], ",")
			if len(parts) >= 3 {
				// GPU utilization
				if util, err := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64); err == nil {
					gpuInfo.UtilizationGpuPercent = util
				}

				// Memory used
				if used, err := strconv.ParseUint(strings.TrimSpace(parts[1]), 10, 64); err == nil {
					gpuInfo.MemoryUsedMiB = used
				}

				// Temperature
				if temp, err := strconv.ParseFloat(strings.TrimSpace(parts[2]), 64); err == nil {
					gpuInfo.TemperatureGpuCelsius = temp
				}
			}
		}

		c.gpus = append(c.gpus, gpuInfo)
	}

	return nil
}

func (c *GpuCollector) GetAllGpuInfoBatch(gpuCount int) ([]string, error) {
	var results []string

	for i := 0; i < gpuCount; i++ {
		output, err := exec.Command("nvidia-smi",
			"-i", strconv.Itoa(i),
			"--query-gpu=name,uuid,memory.total,pci.bus_id",
			"--format=csv,noheader,nounits").Output()
		if err != nil {
			return nil, &GpuError{
				Message: fmt.Sprintf("nvidia-smi info query failed for GPU %d: %v", i, err),
			}
		}

		result := strings.TrimSpace(string(output))
		if result == "" {
			return nil, &GpuError{
				Message: fmt.Sprintf("no info output for GPU %d", i),
			}
		}

		results = append(results, result)
	}

	return results, nil
}

func (c *GpuCollector) GetAllGpuStatusBatch(gpuCount int) ([]string, error) {
	var results []string

	for i := 0; i < gpuCount; i++ {
		output, err := exec.Command("nvidia-smi",
			"-i", strconv.Itoa(i),
			"--query-gpu=utilization.gpu,memory.used,temperature.gpu",
			"--format=csv,noheader,nounits").Output()
		if err != nil {
			return nil, &GpuError{
				Message: fmt.Sprintf("nvidia-smi status query failed for GPU %d: %v", i, err),
			}
		}

		result := strings.TrimSpace(string(output))
		if result == "" {
			return nil, &GpuError{
				Message: fmt.Sprintf("no status output for GPU %d", i),
			}
		}

		results = append(results, result)
	}

	return results, nil
}

func (c *GpuCollector) GetGpuCount() (int, error) {
	output, err := exec.Command("nvidia-smi", "--list-gpus").Output()
	if err != nil {
		return 0, &GpuError{
			Message: fmt.Sprintf("nvidia-smi --list-gpus failed: %v", err),
		}
	}

	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	if len(lines) == 1 && lines[0] == "" {
		return 0, &GpuError{
			Message: "No GPUs found",
		}
	}

	return len(lines), nil
}

func (c *GpuCollector) GetMemoryUtilizationRates() []float64 {
	rates := make([]float64, len(c.gpus))
	for i, gpu := range c.gpus {
		rates[i] = gpu.GetMemoryUtilization()
	}
	return rates
}

func (c *GpuCollector) GetTotalMemory() uint64 {
	total := uint64(0)
	for _, gpu := range c.gpus {
		total += gpu.MemoryTotalMiB
	}
	return total
}

func (c *GpuCollector) GetUsedMemory() uint64 {
	used := uint64(0)
	for _, gpu := range c.gpus {
		used += gpu.MemoryUsedMiB
	}
	return used
}
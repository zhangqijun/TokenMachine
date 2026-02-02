package main

import (
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// AmdError represents an AMD GPU related error
type AmdError struct {
	Message string
}

func (e *AmdError) Error() string {
	return e.Message
}

// AmdInfo represents AMD GPU information
type AmdInfo struct {
	Index                     int
	Name                      string
	UUID                      string
	PciBusId                  string
	MemoryTotalMiB           uint64
	MemoryUsedMiB             uint64
	UtilizationGpuPercent    float64
	UtilizationMemoryPercent float64
	TemperatureGpuCelsius    float64
	Timestamp                 string
}

// NewAmdInfo creates a new AmdInfo instance
func NewAmdInfo(index int) *AmdInfo {
	return &AmdInfo{
		Index:     index,
		Timestamp: time.Now().Format(time.RFC3339),
	}
}

// GetMemoryUtilization returns the memory utilization percentage
func (a *AmdInfo) GetMemoryUtilization() float64 {
	if a.MemoryTotalMiB > 0 {
		return float64(a.MemoryUsedMiB) / float64(a.MemoryTotalMiB)
	}
	return 0.0
}

// AmdCollector collects AMD GPU information
type AmdCollector struct {
	gpus         []*AmdInfo
	targetGpuIds []int // Specific GPU IDs to monitor (empty = monitor all)
	mockMode     bool  // Enable mock mode for testing without real AMD hardware
	mockData     []*AmdInfo
}

// NewAmdCollector creates a new AmdCollector
func NewAmdCollector() *AmdCollector {
	return &AmdCollector{
		gpus:     make([]*AmdInfo, 0),
		mockMode: false,
	}
}

// SetMockMode enables mock mode for testing
func (c *AmdCollector) SetMockMode(enabled bool) {
	c.mockMode = enabled
}

// SetMockData sets mock data for testing
func (c *AmdCollector) SetMockData(data []*AmdInfo) {
	c.mockData = data
}

// SetTargetGpuIds sets the specific GPU IDs to monitor
func (c *AmdCollector) SetTargetGpuIds(ids []int) {
	c.targetGpuIds = ids
}

// Collect gathers AMD GPU information
func (c *AmdCollector) Collect() ([]*AmdInfo, error) {
	if c.mockMode {
		return c.collectMock()
	}
	return c.collectReal()
}

// collectMock collects mock AMD GPU information for testing
func (c *AmdCollector) collectMock() ([]*AmdInfo, error) {
	var gpuIdsToCollect []int

	if len(c.targetGpuIds) > 0 {
		gpuIdsToCollect = c.targetGpuIds
	} else {
		gpuCount := len(c.mockData)
		if gpuCount == 0 {
			gpuCount = 1 // Default mock: 1 GPU
		}
		for i := 0; i < gpuCount; i++ {
			gpuIdsToCollect = append(gpuIdsToCollect, i)
		}
	}

	c.gpus = make([]*AmdInfo, 0)

	for _, gpuId := range gpuIdsToCollect {
		var amdInfo *AmdInfo

		if gpuId < len(c.mockData) && c.mockData[gpuId] != nil {
			// Use provided mock data
			amdInfo = c.mockData[gpuId]
			amdInfo.Timestamp = time.Now().Format(time.RFC3339)
		} else {
			// Generate default mock data
			amdInfo = generateDefaultMockAmdInfo(gpuId)
		}

		c.gpus = append(c.gpus, amdInfo)
	}

	return c.gpus, nil
}

// generateDefaultMockAmdInfo generates default mock AMD GPU info
func generateDefaultMockAmdInfo(index int) *AmdInfo {
	info := NewAmdInfo(index)
	info.Name = fmt.Sprintf("AMD Radeon RX %d", 6000+index*1000)
	info.UUID = fmt.Sprintf("mock-amd-gpu-%d-uuid-12345678", index)
	info.PciBusId = fmt.Sprintf("0000:%02d:00.0", index+10)
	info.MemoryTotalMiB = 16 * 1024 // 16GB default
	info.MemoryUsedMiB = 12 * 1024  // 12GB used (75%)
	info.UtilizationGpuPercent = 45.0
	info.UtilizationMemoryPercent = 75.0
	info.TemperatureGpuCelsius = 65.0 + float64(index)*5
	return info
}

// collectReal collects real AMD GPU information using rocm-smi
func (c *AmdCollector) collectReal() ([]*AmdInfo, error) {
	var gpuIdsToCollect []int

	if len(c.targetGpuIds) > 0 {
		gpuIdsToCollect = c.targetGpuIds
	} else {
		gpuCount, err := c.GetGpuCount()
		if err != nil {
			return nil, fmt.Errorf("failed to get GPU count: %w", err)
		}
		for i := 0; i < gpuCount; i++ {
			gpuIdsToCollect = append(gpuIdsToCollect, i)
		}
	}

	c.gpus = make([]*AmdInfo, 0)

	if err := c.collectSpecificGpus(gpuIdsToCollect); err != nil {
		return nil, fmt.Errorf("failed to collect AMD GPU info: %w", err)
	}

	return c.gpus, nil
}

// GetGpus returns the collected GPU info
func (c *AmdCollector) GetGpus() []*AmdInfo {
	return c.gpus
}

// CollectSpecificGpus collects info for specific GPU IDs only
func (c *AmdCollector) CollectSpecificGpus(gpuIds []int) error {
	if c.mockMode {
		_, err := c.collectMock()
		return err
	}
	return c.collectSpecificGpus(gpuIds)
}

// collectSpecificGpus collects info for specific GPU IDs using rocm-smi
func (c *AmdCollector) collectSpecificGpus(gpuIds []int) error {
	for _, gpuId := range gpuIds {
		// Collect basic info using rocm-smi
		output, err := exec.Command("rocm-smi",
			"-i", strconv.Itoa(gpuId),
			"--showproductname",
			"--showid",
			"--showmeminfo",
			"--showtemp",
			"--showuse",
			"--parse").Output()
		if err != nil {
			return &AmdError{
				Message: fmt.Sprintf("rocm-smi info query failed for GPU %d: %v", gpuId, err),
			}
		}

		amdInfo := NewAmdInfo(gpuId)
		parseRocmSmiOutput(string(output), amdInfo)
		c.gpus = append(c.gpus, amdInfo)
	}

	return nil
}

// parseRocmSmiOutput parses rocm-smi output to AmdInfo
func parseRocmSmiOutput(output string, info *AmdInfo) {
	lines := strings.Split(output, "\n")

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// Parse GPU name
		if strings.Contains(line, "Card series:") || strings.Contains(line, "GPU") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				info.Name = strings.TrimSpace(parts[1])
			}
		}

		// Parse GPU ID/UUID
		if strings.Contains(line, "Device ID:") || strings.Contains(line, "UUID:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				info.UUID = strings.TrimSpace(parts[1])
			}
		}

		// Parse PCI Bus ID
		if strings.Contains(line, "PCI Bus:") || strings.Contains(line, "pci:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				info.PciBusId = strings.TrimSpace(parts[1])
			}
		}

		// Parse memory info (format: "vram: 16384MB total, 12288MB used")
		if strings.Contains(line, "vram:") {
			parts := strings.Split(line, ",")
			for _, part := range parts {
				part = strings.TrimSpace(part)
				if strings.Contains(part, "total") {
					memStr := strings.TrimSpace(strings.ReplaceAll(strings.ReplaceAll(part, "total", ""), "MB", ""))
					memStr = strings.TrimSpace(memStr)
					if mem, err := strconv.ParseUint(memStr, 10, 64); err == nil {
						info.MemoryTotalMiB = mem
					}
				}
				if strings.Contains(part, "used") {
					memStr := strings.TrimSpace(strings.ReplaceAll(strings.ReplaceAll(part, "used", ""), "MB", ""))
					memStr = strings.TrimSpace(memStr)
					if mem, err := strconv.ParseUint(memStr, 10, 64); err == nil {
						info.MemoryUsedMiB = mem
					}
				}
			}
		}

		// Parse temperature
		if strings.Contains(line, "Temperature:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				tempStr := strings.TrimSpace(strings.ReplaceAll(parts[1], "C", ""))
				if temp, err := strconv.ParseFloat(tempStr, 64); err == nil {
					info.TemperatureGpuCelsius = temp
				}
			}
		}

		// Parse GPU utilization
		if strings.Contains(line, "GPU use:") || strings.Contains(line, "GPU usage:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				utilStr := strings.TrimSpace(strings.ReplaceAll(parts[1], "%", ""))
				if util, err := strconv.ParseFloat(utilStr, 64); err == nil {
					info.UtilizationGpuPercent = util
				}
			}
		}
	}
}

// CollectAllGpusBatch collects all GPU info in batch mode
func (c *AmdCollector) CollectAllGpusBatch(gpuCount int) error {
	if c.mockMode {
		return nil
	}

	basicInfo, err := c.GetAllGpuInfoBatch(gpuCount)
	if err != nil {
		return err
	}

	statusInfo, err := c.GetAllGpuStatusBatch(gpuCount)
	if err != nil {
		return err
	}

	for i := 0; i < gpuCount; i++ {
		amdInfo := NewAmdInfo(i)
		parseRocmSmiOutput(basicInfo[i], amdInfo)
		parseRocmSmiOutput(statusInfo[i], amdInfo)
		c.gpus = append(c.gpus, amdInfo)
	}

	return nil
}

// GetAllGpuInfoBatch gets info for all GPUs in batch
func (c *AmdCollector) GetAllGpuInfoBatch(gpuCount int) ([]string, error) {
	var results []string

	for i := 0; i < gpuCount; i++ {
		output, err := exec.Command("rocm-smi",
			"-i", strconv.Itoa(i),
			"--showproductname",
			"--showid").Output()
		if err != nil {
			return nil, &AmdError{
				Message: fmt.Sprintf("rocm-smi info query failed for GPU %d: %v", i, err),
			}
		}

		result := strings.TrimSpace(string(output))
		if result == "" {
			return nil, &AmdError{
				Message: fmt.Sprintf("no info output for GPU %d", i),
			}
		}

		results = append(results, result)
	}

	return results, nil
}

// GetAllGpuStatusBatch gets status for all GPUs in batch
func (c *AmdCollector) GetAllGpuStatusBatch(gpuCount int) ([]string, error) {
	var results []string

	for i := 0; i < gpuCount; i++ {
		output, err := exec.Command("rocm-smi",
			"-i", strconv.Itoa(i),
			"--showmeminfo",
			"--showtemp",
			"--showuse").Output()
		if err != nil {
			return nil, &AmdError{
				Message: fmt.Sprintf("rocm-smi status query failed for GPU %d: %v", i, err),
			}
		}

		result := strings.TrimSpace(string(output))
		if result == "" {
			return nil, &AmdError{
				Message: fmt.Sprintf("no status output for GPU %d", i),
			}
		}

		results = append(results, result)
	}

	return results, nil
}

// GetGpuCount returns the number of AMD GPUs
func (c *AmdCollector) GetGpuCount() (int, error) {
	if c.mockMode {
		if len(c.mockData) > 0 {
			return len(c.mockData), nil
		}
		return 1, nil // Default mock: 1 GPU
	}

	output, err := exec.Command("rocm-smi", "--list").Output()
	if err != nil {
		return 0, &AmdError{
			Message: fmt.Sprintf("rocm-smi --list failed: %v", err),
		}
	}

	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	if len(lines) == 1 && lines[0] == "" {
		return 0, &AmdError{
			Message: "No AMD GPUs found",
		}
	}

	// Count non-empty lines
	count := 0
	for _, line := range lines {
		if strings.TrimSpace(line) != "" {
			count++
		}
	}

	return count, nil
}

// GetMemoryUtilizationRates returns memory utilization rates for all GPUs
func (c *AmdCollector) GetMemoryUtilizationRates() []float64 {
	rates := make([]float64, len(c.gpus))
	for i, gpu := range c.gpus {
		rates[i] = gpu.GetMemoryUtilization()
	}
	return rates
}

// GetTotalMemory returns total memory across all GPUs
func (c *AmdCollector) GetTotalMemory() uint64 {
	total := uint64(0)
	for _, gpu := range c.gpus {
		total += gpu.MemoryTotalMiB
	}
	return total
}

// GetUsedMemory returns used memory across all GPUs
func (c *AmdCollector) GetUsedMemory() uint64 {
	used := uint64(0)
	for _, gpu := range c.gpus {
		used += gpu.MemoryUsedMiB
	}
	return used
}

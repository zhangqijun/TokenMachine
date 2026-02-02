package npu

import (
	"fmt"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"sync"
)

// NPUInfo 存储 NPU 设备信息
type NPUInfo struct {
	ID            int     `json:"id"`
	Name          string  `json:"name"`
	MemoryTotal   int     `json:"memory_total_mb"`
	MemoryUsed    int     `json:"memory_used_mb"`
	MemoryPercent float64 `json:"memory_percent"`
	Utilization   float64 `json:"utilization_percent"`
	Temperature   float64 `json:"temperature_celsius"`
	Power         float64 `json:"power_watts"`
	Available     bool    `json:"available"`
}

// Monitor NPU 监控器
type Monitor struct {
	selectedIDs []int
	mu          sync.RWMutex
	lastInfo    []NPUInfo
}

// NewMonitor 创建新的 NPU 监控器
func NewMonitor(gpuIDs string) (*Monitor, error) {
	m := &Monitor{}

	// 解析 GPU ID 列表
	if gpuIDs != "" {
		for _, id := range strings.Split(gpuIDs, ",") {
			id = strings.TrimSpace(id)
			if id == "" {
				continue
			}
			n, err := strconv.Atoi(id)
			if err == nil {
				m.selectedIDs = append(m.selectedIDs, n)
			}
		}
	}

	return m, nil
}

// Close 关闭监控器
func (m *Monitor) Close() {
	// 清理资源
}

// GetNPUInfo 获取所有 NPU 信息
func (m *Monitor) GetNPUInfo() ([]NPUInfo, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	// 使用 npu-smi 获取信息
	info, err := m.getNPUInfoFromSMI()
	if err != nil {
		return nil, err
	}

	m.lastInfo = info
	return info, nil
}

// getNPUInfoFromSMI 使用 npu-smi 命令获取 NPU 信息
func (m *Monitor) getNPUInfoFromSMI() ([]NPUInfo, error) {
	// 尝试使用 npu-smi info 命令
	cmd := exec.Command("npu-smi", "info", "-f", "csv")
	output, err := cmd.Output()
	if err != nil {
		// 尝试备用方法
		return m.getNPUInfoFromList()
	}

	return m.parseNPUInfoCSV(string(output))
}

// getNPUInfoFromList 使用 npu-smi list 获取信息
func (m *Monitor) getNPUInfoFromList() ([]NPUInfo, error) {
	cmd := exec.Command("npu-smi", "list")
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("无法获取 NPU 信息: %v", err)
	}

	return m.parseNPUInfoList(string(output))
}

// parseNPUInfoCSV 解析 npu-smi info 的 CSV 输出
func (m *Monitor) parseNPUInfoCSV(output string) ([]NPUInfo, error) {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	npus := make([]NPUInfo, 0, len(lines))

	re := regexp.MustCompile(`(\d+)\s+(\w+)\s+(\w+)\s+(\d+)%\s+(\d+)\s*/\s*(\d+)\s*MB`)

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		matches := re.FindStringSubmatch(line)
		if len(matches) >= 7 {
			id, _ := strconv.Atoi(matches[1])
			name := matches[2]
			status := matches[3]
			util, _ := strconv.Atoi(matches[4])
			memUsed, _ := strconv.Atoi(matches[5])
			memTotal, _ := strconv.Atoi(matches[6])

			npu := NPUInfo{
				ID:            id,
				Name:          name,
				MemoryTotal:   memTotal,
				MemoryUsed:    memUsed,
				Utilization:   float64(util),
				Available:     status == "Normal",
			}

			if memTotal > 0 {
				npu.MemoryPercent = float64(memUsed) / float64(memTotal) * 100
			}

			// 检查是否在选择的列表中
			if len(m.selectedIDs) == 0 || containsInt(m.selectedIDs, id) {
				npus = append(npus, npu)
			}
		}
	}

	return npus, nil
}

// parseNPUInfoList 解析 npu-smi list 的输出
func (m *Monitor) parseNPUInfoList(output string) ([]NPUInfo, error) {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	npus := make([]NPUInfo, 0, len(lines))

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// 解析格式: "0  Ascend910  Normal  10%  16384MB / 32768MB"
		re := regexp.MustCompile(`^(\d+)\s+(\S+)\s+(\S+)\s+(\d+)%\s+(\d+)MB\s*/\s*(\d+)MB`)
		matches := re.FindStringSubmatch(line)

		if len(matches) >= 7 {
			id, _ := strconv.Atoi(matches[1])
			name := matches[2]
			status := matches[3]
			util, _ := strconv.Atoi(matches[4])
			memUsed, _ := strconv.Atoi(matches[5])
			memTotal, _ := strconv.Atoi(matches[6])

			npu := NPUInfo{
				ID:            id,
				Name:          name,
				MemoryTotal:   memTotal,
				MemoryUsed:    memUsed,
				Utilization:   float64(util),
				Available:     status == "Normal",
			}

			if memTotal > 0 {
				npu.MemoryPercent = float64(memUsed) / float64(memTotal) * 100
			}

			// 检查是否在选择的列表中
			if len(m.selectedIDs) == 0 || containsInt(m.selectedIDs, id) {
				npus = append(npus, npu)
			}
		}
	}

	return npus, nil
}

// containsInt 检查切片是否包含指定值
func containsInt(slice []int, val int) bool {
	for _, v := range slice {
		if v == val {
			return true
		}
	}
	return false
}

// GetSelectedIDs 返回选中的 NPU ID 列表
func (m *Monitor) GetSelectedIDs() []int {
	return m.selectedIDs
}

// NPUCollector 收集 NPU 指标数据
type NPUCollector struct {
	monitor *Monitor
}

// NewNPUCollector 创建新的 NPU 收集器
func NewNPUCollector(monitor *Monitor) *NPUCollector {
	return &NPUCollector{monitor: monitor}
}

// Collect 收集所有 NPU 指标
func (c *NPUCollector) Collect() ([]NPUInfo, error) {
	return c.monitor.GetNPUInfo()
}

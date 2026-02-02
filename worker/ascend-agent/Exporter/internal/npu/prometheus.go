package npu

import (
	"fmt"
	"strings"
)

// CollectMetrics 收集并格式化指标
func (m *Monitor) CollectMetrics() string {
	npus, err := m.GetNPUInfo()
	if err != nil {
		return fmt.Sprintf("# Error collecting NPU info: %v\n", err)
	}

	var sb strings.Builder

	// 设备数量
	sb.WriteString("# Ascend NPU Exporter Metrics\n")
	sb.WriteString("# Total NPU devices: " + fmt.Sprintf("%d\n", len(npus)))
	sb.WriteString("\n")

	// 帮助信息
	sb.WriteString("# HELP npu_count Number of NPU devices\n")
	sb.WriteString("# TYPE npu_count gauge\n")
	sb.WriteString(fmt.Sprintf("npu_count %d\n", len(npus)))
	sb.WriteString("\n")

	// 遍历每个 NPU 设备
	for _, n := range npus {
		labels := fmt.Sprintf(`npu="%d"`, n.ID)

		// 内存指标
		sb.WriteString(fmt.Sprintf("# HELP npu_memory_used_bytes NPU memory used in bytes (device %d)\n", n.ID))
		sb.WriteString(fmt.Sprintf("# TYPE npu_memory_used_bytes gauge\n"))
		sb.WriteString(fmt.Sprintf("npu_memory_used_bytes{%s} %d\n", labels, n.MemoryUsed*1024*1024))

		sb.WriteString(fmt.Sprintf("# HELP npu_memory_total_bytes NPU memory total in bytes (device %d)\n", n.ID))
		sb.WriteString(fmt.Sprintf("# TYPE npu_memory_total_bytes gauge\n"))
		sb.WriteString(fmt.Sprintf("npu_memory_total_bytes{%s} %d\n", labels, n.MemoryTotal*1024*1024))

		sb.WriteString(fmt.Sprintf("# HELP npu_memory_utilization NPU memory utilization ratio (device %d)\n", n.ID))
		sb.WriteString(fmt.Sprintf("# TYPE npu_memory_utilization gauge\n"))
		sb.WriteString(fmt.Sprintf("npu_memory_utilization{%s} %.4f\n", labels, n.MemoryPercent/100))

		// 计算利用率
		sb.WriteString(fmt.Sprintf("# HELP npu_utilization NPU computation utilization ratio (device %d)\n", n.ID))
		sb.WriteString(fmt.Sprintf("# TYPE npu_utilization gauge\n"))
		sb.WriteString(fmt.Sprintf("npu_utilization{%s} %.4f\n", labels, n.Utilization/100))

		// 温度
		sb.WriteString(fmt.Sprintf("# HELP npu_temperature_celsius NPU temperature in celsius (device %d)\n", n.ID))
		sb.WriteString(fmt.Sprintf("# TYPE npu_temperature_celsius gauge\n"))
		sb.WriteString(fmt.Sprintf("npu_temperature_celsius{%s} %.1f\n", labels, n.Temperature))

		// 功耗
		sb.WriteString(fmt.Sprintf("# HELP npu_power_watts NPU power consumption in watts (device %d)\n", n.ID))
		sb.WriteString(fmt.Sprintf("# TYPE npu_power_watts gauge\n"))
		sb.WriteString(fmt.Sprintf("npu_power_watts{%s} %.2f\n", labels, n.Power))

		// 可用性
		sb.WriteString(fmt.Sprintf("# HELP npu_available NPU availability status (device %d)\n", n.ID))
		sb.WriteString(fmt.Sprintf("# TYPE npu_available gauge\n"))
		if n.Available {
			sb.WriteString(fmt.Sprintf("npu_available{%s} 1\n", labels))
		} else {
			sb.WriteString(fmt.Sprintf("npu_available{%s} 0\n", labels))
		}

		sb.WriteString("\n")
	}

	return sb.String()
}

// GetMetricsText 返回指标文本格式
func (m *Monitor) GetMetricsText() string {
	return m.CollectMetrics()
}

package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"tokenmachine/worker/ascend-agent/Exporter/internal/npu"
)

func main() {
	// 命令行参数
	port := flag.Int("p", 9090, "Exporter 监听端口")
	gpuIDs := flag.String("gpu-ids", "", "要监控的 GPU ID 列表，用逗号分隔")
	serve := flag.Bool("serve", false, "启动 HTTP 服务模式")
	help := flag.Bool("help", false, "显示帮助信息")

	flag.Parse()

	if *help {
		fmt.Println("Ascend NPU Exporter - Prometheus 指标导出器")
		fmt.Println()
		fmt.Println("用法:")
		fmt.Println("  npu_exporter_main [选项]")
		fmt.Println()
		fmt.Println("选项:")
		flag.PrintDefaults()
		fmt.Println()
		fmt.Println("示例:")
		fmt.Println("  npu_exporter_main -serve -p 9090")
		fmt.Println("  npu_exporter_main -serve -p 9090 -gpu-ids 0,1")
		os.Exit(0)
	}

	// 初始化 NPU 监控器
	monitor, err := npu.NewMonitor(*gpuIDs)
	if err != nil {
		fmt.Fprintf(os.Stderr, "初始化 NPU 监控器失败: %v\n", err)
		os.Exit(1)
	}
	defer monitor.Close()

	if *serve {
		// 启动 HTTP 服务
		exporter := npu.NewExporter(monitor)
		exporter.StartServer(*port)
	} else {
		// 单次输出指标
		metrics := monitor.CollectMetrics()
		fmt.Println(metrics)
		fmt.Println("\nExporter 已停止")
		return
	}

	// 优雅退出
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	fmt.Println("\n正在停止 Exporter...")
}

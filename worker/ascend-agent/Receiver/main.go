package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

var (
	port     int
	serverURL string
	workDir   string
)

func init() {
	flag.IntVar(&port, "p", 9001, "Receiver 监听端口")
	flag.StringVar(&serverURL, "s", "http://localhost:8000", "后端服务器地址")
	flag.StringVar(&workDir, "w", "", "工作目录")
}

func main() {
	flag.Parse()

	// 设置工作目录
	if workDir == "" {
		workDir = os.Getenv("TM_WORK_DIR")
		if workDir == "" {
			workDir = "."
		}
	}

	// 设置服务器地址
	if serverURL == "" {
		serverURL = os.Getenv("TM_SERVER_URL")
		if serverURL == "" {
			log.Fatal("服务器地址未设置")
		}
	}

	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.Println("Ascend Agent Receiver 启动...")
	log.Printf("工作目录: %s", workDir)
	log.Printf("后端服务器: %s", serverURL)
	log.Printf("监听端口: %d", port)

	// 启动 HTTP 服务
	mux := http.NewServeMux()

	// 健康检查端点
	mux.HandleFunc("/health", handleHealth)

	// 任务 API
	mux.HandleFunc("/api/v1/tasks/list", handleListTasks)
	mux.HandleFunc("/api/v1/tasks/start", handleStartTask)
	mux.HandleFunc("/api/v1/tasks/stop", handleStopTask)

	// Ascend 特有 API
	mux.HandleFunc("/api/v1/npu/status", handleNPUStatus)

	server := &http.Server{
		Addr:         fmt.Sprintf(":%d", port),
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	// 优雅退出
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan

		log.Println("正在停止 Receiver...")
		server.Shutdown(nil)
	}()

	log.Printf("Receiver 启动成功，监听端口 %d", port)
	log.Fatal(server.ListenAndServe())
}

// handleHealth 健康检查
func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status": "ok", "agent": "ascend"}`))
}

// handleListTasks 列出任务
func handleListTasks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"tasks": [], "message": "task list placeholder for ascend agent"}`))
}

// handleStartTask 启动任务
func handleStartTask(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status": "started", "message": "task start placeholder for ascend agent"}`))
}

// handleStopTask 停止任务
func handleStopTask(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status": "stopped", "message": "task stop placeholder for ascend agent"}`))
}

// handleNPUStatus NPU 状态
func handleNPUStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"npu_count": 0, "message": "npu status placeholder for ascend agent"}`))
}

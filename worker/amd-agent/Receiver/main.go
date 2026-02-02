package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Task 定义任务结构
type Task struct {
	TaskID      string                 `json:"task_id"`
	Action      string                 `json:"action"`
	Config      map[string]interface{} `json:"config"`
	Status      string                 `json:"status"`
	CreatedAt   time.Time              `json:"created_at"`
	StartedAt   time.Time              `json:"started_at,omitempty"`
	CompletedAt time.Time              `json:"completed_at,omitempty"`
	Error       string                 `json:"error,omitempty"`
}

// TaskResponse API 响应结构
type TaskResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
	TaskID  string `json:"task_id,omitempty"`
}

// TaskListResponse 任务列表响应
type TaskListResponse struct {
	Status string  `json:"status"`
	Tasks  []Task  `json:"tasks"`
}

// Config 配置结构
type Config struct {
	ReceiverPort     int    `json:"receiver_port"`
	LogFile          string `json:"log_file"`
	WorkDir          string `json:"work_dir"`
	MaxConcurrent    int    `json:"max_concurrent"`
	DefaultVLLMImage string `json:"default_vllm_image"`
}

var (
	config      Config
	tasks       = make(map[string]Task)
	mu          sync.RWMutex
	activeJobs  = make(chan struct{}, 10) // 控制并发数
	agentType   = "amd"                   // Agent 类型
	agentPrefix = "amd"                   // Agent 前缀用于日志
)

func init() {
	// 默认配置
	config = Config{
		ReceiverPort:     9001,
		LogFile:          "/var/run/tokenmachine/amd-receiver.log",
		WorkDir:          "/var/run/tokenmachine",
		MaxConcurrent:    10,
		DefaultVLLMImage: "vllm/vllm:latest-rocm", // 使用 ROCm 版本的 vLLM 镜像
	}

	// 从环境变量读取配置
	if port := os.Getenv("TM_RECEIVER_PORT"); port != "" {
		if p, err := strconv.Atoi(port); err == nil {
			config.ReceiverPort = p
		}
	}
	if logFile := os.Getenv("TM_RECEIVER_LOG"); logFile != "" {
		config.LogFile = logFile
	}
	if workDir := os.Getenv("TM_WORK_DIR"); workDir != "" {
		config.WorkDir = workDir
	}
}

// log 日志函数
func logf(format string, args ...interface{}) {
	msg := fmt.Sprintf("[%s] [%s] %s", time.Now().Format("2006-01-02 15:04:05"), agentPrefix, fmt.Sprintf(format, args...))
	log.Printf(msg)

	// 写入日志文件
	if err := os.MkdirAll(filepath.Dir(config.LogFile), 0755); err == nil {
		f, err := os.OpenFile(config.LogFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err == nil {
			defer f.Close()
			f.WriteString(msg + "\n")
		}
	}
}

// handleTask 处理任务请求
func handleTask(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		TaskID string                 `json:"task_id"`
		Action string                 `json:"action"`
		Config map[string]interface{} `json:"config"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// 验证任务ID
	if req.TaskID == "" {
		http.Error(w, "task_id is required", http.StatusBadRequest)
		return
	}

	// 验证动作
	if req.Action != "start_vllm" && req.Action != "stop_vllm" {
		http.Error(w, "unsupported action", http.StatusBadRequest)
		return
	}

	// 检查任务是否已存在
	mu.Lock()
	if _, exists := tasks[req.TaskID]; exists {
		mu.Unlock()
		http.Error(w, "task_id already exists", http.StatusConflict)
		return
	}
	mu.Unlock()

	// 创建任务
	task := Task{
		TaskID:    req.TaskID,
		Action:    req.Action,
		Config:    req.Config,
		Status:    "pending",
		CreatedAt: time.Now(),
	}

	mu.Lock()
	tasks[req.TaskID] = task
	mu.Unlock()

	logf("Received task: %s, action: %s, config: %v", req.TaskID, req.Action, req.Config)

	// 异步执行任务
	go executeTask(req.TaskID, req.Action, req.Config)

	// 返回响应
	response := TaskResponse{
		Status:  "accepted",
		Message: "Task accepted",
		TaskID:  req.TaskID,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// executeTask 执行任务
func executeTask(taskID, action string, config map[string]interface{}) {
	// 限制并发数
	activeJobs <- struct{}{}
	defer func() { <-activeJobs }()

	mu.Lock()
	task, exists := tasks[taskID]
	if !exists {
		mu.Unlock()
		return
	}
	task.Status = "running"
	task.StartedAt = time.Now()
	tasks[taskID] = task
	mu.Unlock()

	logf("Executing task: %s", taskID)

	var err error

	switch action {
	case "start_vllm":
		err = startVLLM(taskID, config)
	case "stop_vllm":
		err = stopVLLM(taskID, config)
	}

	mu.Lock()
	task, exists = tasks[taskID]
	if !exists {
		mu.Unlock()
		return
	}

	if err != nil {
		task.Status = "failed"
		task.Error = err.Error()
		logf("Task %s failed: %v", taskID, err)
	} else {
		task.Status = "completed"
		logf("Task %s completed", taskID)
	}
	task.CompletedAt = time.Now()
	tasks[taskID] = task
	mu.Unlock()
}

// startVLLM 启动 vLLM 容器 (ROCm/HIP 版本)
func startVLLM(taskID string, config map[string]interface{}) error {
	// 获取配置参数
	modelName := getString(config, "model_name", "")
	modelPath := getString(config, "model_path", "")
	gpuIDs := getStringArray(config, "gpu_ids", []string{})
	port := getString(config, "port", "8000")
	apiKey := getString(config, "api_key", "")
	vllmImage := getString(config, "vllm_image", "vllm/vllm:latest-rocm") // 默认 ROCm 镜像
	vllmArgs := getStringArray(config, "vllm_args", []string{})

	if modelName == "" {
		return fmt.Errorf("model_name is required")
	}

	// 构建容器名称
	containerName := fmt.Sprintf("vllm-%s-%s", agentPrefix, taskID)

	// 构建 Docker 命令
	dockerArgs := []string{
		"run",
		"--rm",
		"--name", containerName,
	}

	// 添加 GPU 参数 (AMD ROCm 使用不同方式)
	if len(gpuIDs) > 0 {
		// AMD ROCm 使用 --device 参数
		for range gpuIDs {
			dockerArgs = append(dockerArgs, "--device", "/dev/dri:/dev/dri")
		}
	}

	// 添加端口映射
	dockerArgs = append(dockerArgs, "-p", fmt.Sprintf("%s:8000", port))

	// 添加环境变量
	if apiKey != "" {
		dockerArgs = append(dockerArgs, "-e", fmt.Sprintf("API_KEY=%s", apiKey))
	}

	// ROCm 特定的环境变量
	dockerArgs = append(dockerArgs, "-e", "HSA_OVERRIDE_GFX_VERSION=10.3.0")
	dockerArgs = append(dockerArgs, "-e", "ROCR_VISIBLE_DEVICES=0")
	dockerArgs = append(dockerArgs, "-e", "AMD_VISIBLE_DEVICES=all")

	// 添加 vLLM 参数
	dockerArgs = append(dockerArgs, vllmImage)
	dockerArgs = append(dockerArgs, "--model", modelName)
	dockerArgs = append(dockerArgs, "--port", "8000")

	// 添加额外的 vLLM 参数
	for _, arg := range vllmArgs {
		dockerArgs = append(dockerArgs, arg)
	}

	// 如果指定了模型路径，添加挂载点
	if modelPath != "" {
		dockerArgs = append(dockerArgs,
			"-v", fmt.Sprintf("%s:/models/%s", modelPath, modelName),
			"-e", fmt.Sprintf("MODEL_PATH=/models/%s", modelName))
	}

	logf("Starting ROCm container: %s, command: docker %s", containerName, strings.Join(dockerArgs, " "))

	// 执行 Docker 命令
	cmd := exec.Command("docker", dockerArgs...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("docker run failed: %v, output: %s", err, string(output))
	}

	logf("ROCm container started successfully: %s", containerName)
	return nil
}

// stopVLLM 停止 vLLM 容器
func stopVLLM(taskID string, config map[string]interface{}) error {
	containerName := fmt.Sprintf("vllm-%s-%s", agentPrefix, taskID)

	logf("Stopping container: %s", containerName)

	// 停止容器
	cmd := exec.Command("docker", "stop", containerName)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("docker stop failed: %v, output: %s", err, string(output))
	}

	logf("Container stopped successfully: %s", containerName)
	return nil
}

// handleGetTask 获取任务状态
func handleGetTask(w http.ResponseWriter, r *http.Request) {
	// 排除 action 路径
	if r.URL.Path == "/api/v1/tasks/start" || r.URL.Path == "/api/v1/tasks/stop" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	taskID := strings.TrimPrefix(r.URL.Path, "/api/v1/tasks/")
	if taskID == "" {
		http.Error(w, "task_id is required", http.StatusBadRequest)
		return
	}

	mu.RLock()
	task, exists := tasks[taskID]
	mu.RUnlock()

	if !exists {
		http.Error(w, "task not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(task)
}

// handleListTasks 列出所有任务
func handleListTasks(w http.ResponseWriter, r *http.Request) {
	mu.RLock()
	taskList := make([]Task, 0) // 初始化为空切片而非 nil
	for _, task := range tasks {
		taskList = append(taskList, task)
	}
	mu.RUnlock()

	response := TaskListResponse{
		Status: "success",
		Tasks:  taskList,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleDeleteTask 删除任务
func handleDeleteTask(w http.ResponseWriter, r *http.Request) {
	taskID := strings.TrimPrefix(r.URL.Path, "/api/v1/tasks/")
	if taskID == "" {
		http.Error(w, "task_id is required", http.StatusBadRequest)
		return
	}

	mu.Lock()
	delete(tasks, taskID)
	mu.Unlock()

	response := TaskResponse{
		Status:  "success",
		Message: "Task deleted",
		TaskID:  taskID,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleStatus 获取服务器状态
func handleStatus(w http.ResponseWriter, r *http.Request) {
	mu.RLock()
	taskCount := len(tasks)
	mu.RUnlock()

	status := map[string]interface{}{
		"status":         "running",
		"version":        "1.0.0",
		"agent_type":     agentType,
		"task_count":     taskCount,
		"max_concurrent": config.MaxConcurrent,
		"timestamp":      time.Now().Format(time.RFC3339),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// getString 从配置中获取字符串值
func getString(config map[string]interface{}, key, defaultValue string) string {
	if val, exists := config[key]; exists {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return defaultValue
}

// getStringArray 从配置中获取字符串数组
func getStringArray(config map[string]interface{}, key string, defaultValue []string) []string {
	if val, exists := config[key]; exists {
		if arr, ok := val.([]interface{}); ok {
			var result []string
			for _, item := range arr {
				if str, ok := item.(string); ok {
					result = append(result, str)
				}
			}
			return result
		}
	}
	return defaultValue
}

func main() {
	// 创建工作目录
	if err := os.MkdirAll(config.WorkDir, 0755); err != nil {
		logf("Failed to create work directory: %v", err)
		os.Exit(1)
	}

	// 设置日志
	log.SetOutput(os.Stdout)
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	logf("Starting AMD Agent Receiver")
	logf("Port: %d", config.ReceiverPort)
	logf("Work dir: %s", config.WorkDir)

	// 设置路由
	mux := http.NewServeMux()

	// API 路由 (注意顺序：更具体的路由在前)
	mux.HandleFunc("/api/v1/tasks/", handleGetTask)
	mux.HandleFunc("/api/v1/tasks", handleTask)
	mux.HandleFunc("/api/v1/tasks/list", handleListTasks)
	mux.HandleFunc("/api/v1/status", handleStatus)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	// 启动服务器
	addr := fmt.Sprintf(":%d", config.ReceiverPort)
	logf("Server listening on %s", addr)

	if err := http.ListenAndServe(addr, mux); err != nil {
		logf("Server failed: %v", err)
		os.Exit(1)
	}
}

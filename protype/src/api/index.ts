/**
 * API interface definitions for TokenMachine.
 *
 * This module provides typed interfaces for API requests and responses.
 */

/**
 * Worker interfaces
 */
export interface Worker {
  id: number;
  name: string;
  cluster_id: number;
  status: 'REGISTERING' | 'READY' | 'BUSY' | 'DRAINING' | 'UNHEALTHY' | 'OFFLINE';
  ip?: string;
  hostname?: string;
  gpu_count: number;
  expected_gpu_count: number;
  labels?: Record<string, string>;
  capabilities?: string[];
  agent_type?: string;
  agent_version?: string;
  last_heartbeat_at?: string;
  created_at: string;
  updated_at: string;
  gpu_devices?: GPU[];
}

export interface WorkerCreate {
  name: string;
  cluster_id?: number;
  expected_gpu_count?: number;
  labels?: Record<string, string>;
}

export interface WorkerCreateResponse {
  id: number;
  name: string;
  status: string;
  register_token: string;
  install_command: string;
  expected_gpu_count: number;
  current_gpu_count: number;
  created_at: string;
}

export interface WorkerListResponse {
  items: Worker[];
  total: number;
  page: number;
  page_size: number;
}

export interface WorkerStats {
  worker_id: number;
  worker_name: string;
  status: string;
  total_gpus: number;
  in_use_gpus: number;
  error_gpus: number;
  avg_memory_utilization: number;
  avg_core_utilization: number;
  avg_temperature: number;
  last_heartbeat_at: string;
}

/**
 * Model interfaces
 */
export interface Model {
  id: number;
  name: string;
  version: string;
  source: 'huggingface' | 'modelscope' | 'local';
  category: 'llm' | 'embedding' | 'reranker' | 'image' | 'tts' | 'stt';
  quantization: 'fp16' | 'int8' | 'fp4' | 'fp8';
  path?: string;
  size_gb?: number;
  status: 'downloading' | 'ready' | 'error';
  download_progress?: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Deployment interfaces
 */
export interface Deployment {
  id: number;
  model_id: number;
  model_name?: string;
  name: string;
  environment: 'dev' | 'test' | 'staging' | 'production';
  status: 'starting' | 'running' | 'stopping' | 'stopped' | 'error';
  replicas: number;
  traffic_weight: number;
  gpu_ids?: string[];
  backend: string;
  config?: Record<string, any>;
  health_status?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

/**
 * GPU interfaces
 */
export interface GPU {
  id: number;
  worker_id?: number;
  uuid: string;
  name: string;
  vendor?: string;
  index: number;
  ip?: string;
  port?: number;
  hostname?: string;
  pci_bus?: string;
  memory_total: number;
  memory_used?: number;
  memory_allocated?: number;
  memory_utilization_rate?: number;
  core_utilization_rate?: number;
  temperature?: number;
  state: 'AVAILABLE' | 'IN_USE' | 'ERROR';
  status_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

/**
 * API Key interfaces
 */
export interface ApiKey {
  id: number;
  key_prefix: string;
  user_id: number;
  organization_id: number;
  name: string;
  quota_tokens: number;
  tokens_used: number;
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  created_at: string;
}

/**
 * Usage Log interfaces
 */
export interface UsageLog {
  id: number;
  api_key_id: number;
  deployment_id: number;
  model_id: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  latency_ms?: number;
  status: 'success' | 'error';
  error_message?: string;
  created_at: string;
}

/**
 * Statistics interfaces
 */
export interface DashboardStats {
  total_models: number;
  running_models: number;
  total_deployments: number;
  running_deployments: number;
  total_gpus: number;
  used_gpus: number;
  available_gpus: number;
  total_api_calls_today: number;
  total_tokens_used: number;
}

/**
 * Worker GPU Metrics interfaces
 */
export interface GPUHistoryPoint {
  timestamp: number;
  datetime: string;
  utilization: number;
}

export interface WorkerGPUMetrics {
  gpu_index: number;
  name?: string;
  memory_total_mb?: number;
  memory_used_mb?: number;
  memory_utilization_percent?: number;
  gpu_utilization_percent?: number;
  temperature_celsius?: number;
}

export interface WorkerMetrics {
  worker_id: number;
  worker_name: string;
  worker_ip: string;
  timestamp: string;
  gpu_count: number;
  total_memory_gb: number;
  used_memory_gb: number;
  avg_utilization_percent: number;
  gpus: WorkerGPUMetrics[];
  history?: GPUHistoryPoint[];
}

export interface AllWorkersMetrics {
  timestamp: string;
  workers: WorkerMetrics[];
}

/**
 * API endpoints
 */
export const apiEndpoints = {
  // Workers
  listWorkers: '/workers',
  getWorker: (id: number) => `/workers/${id}`,
  createWorker: '/workers',
  updateWorker: (id: number) => `/workers/${id}`,
  deleteWorker: (id: number) => `/workers/${id}`,
  getWorkerStats: (id: number) => `/workers/${id}/stats`,
  setWorkerStatus: (id: number) => `/workers/${id}/set-status`,

  // Models
  listModels: '/models',
  getModel: (id: number) => `/models/${id}`,
  createModel: '/models',
  updateModel: (id: number) => `/models/${id}`,
  deleteModel: (id: number) => `/models/${id}`,

  // Deployments
  listDeployments: '/deployments',
  getDeployment: (id: number) => `/deployments/${id}`,
  createDeployment: '/deployments',
  updateDeployment: (id: number) => `/deployments/${id}`,
  deleteDeployment: (id: number) => `/deployments/${id}`,
  startDeployment: (id: number) => `/deployments/${id}/start`,
  stopDeployment: (id: number) => `/deployments/${id}/stop`,

  // GPUs
  listGpus: '/gpus',
  getGpu: (id: number) => `/gpus/${id}`,

  // API Keys
  listApiKeys: '/api-keys',
  createApiKey: '/api-keys',
  deleteApiKey: (id: number) => `/api-keys/${id}`,
  toggleApiKey: (id: number) => `/api-keys/${id}/toggle`,

  // Usage
  listUsageLogs: '/usage/logs',
  getStats: '/stats/dashboard',

  // Health
  health: '/health',
  metrics: '/metrics',

  // Worker GPU Metrics
  getWorkerMetrics: (id: number) => `/metrics/workers/${id}`,
  getWorkerMetricsHistory: (id: number, gpuIndex?: number) =>
    `/metrics/workers/${id}/history${gpuIndex !== undefined ? `?gpu_index=${gpuIndex}` : ''}`,
  getAllWorkersMetrics: '/metrics/workers',
  metricsHealth: '/metrics/health',
};

export default apiEndpoints;

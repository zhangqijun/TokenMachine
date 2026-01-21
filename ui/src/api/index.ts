/**
 * API interface definitions for TokenMachine.
 *
 * This module provides typed interfaces for API requests and responses.
 */

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
  gpu_id: string;
  name: string;
  memory_total_mb: number;
  memory_free_mb?: number;
  memory_used_mb?: number;
  utilization_percent?: number;
  temperature_celsius?: number;
  status: 'available' | 'in_use' | 'error';
  deployment_id?: number;
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
 * API endpoints
 */
export const apiEndpoints = {
  // Models
  listModels: '/api/v1/models',
  getModel: (id: number) => `/api/v1/models/${id}`,
  createModel: '/api/v1/models',
  updateModel: (id: number) => `/api/v1/models/${id}`,
  deleteModel: (id: number) => `/api/v1/models/${id}`,

  // Deployments
  listDeployments: '/api/v1/deployments',
  getDeployment: (id: number) => `/api/v1/deployments/${id}`,
  createDeployment: '/api/v1/deployments',
  updateDeployment: (id: number) => `/api/v1/deployments/${id}`,
  deleteDeployment: (id: number) => `/api/v1/deployments/${id}`,
  startDeployment: (id: number) => `/api/v1/deployments/${id}/start`,
  stopDeployment: (id: number) => `/api/v1/deployments/${id}/stop`,

  // GPUs
  listGpus: '/api/v1/gpus',
  getGpu: (id: number) => `/api/v1/gpus/${id}`,

  // API Keys
  listApiKeys: '/api/v1/api-keys',
  createApiKey: '/api/v1/api-keys',
  deleteApiKey: (id: number) => `/api/v1/api-keys/${id}`,
  toggleApiKey: (id: number) => `/api/v1/api-keys/${id}/toggle`,

  // Usage
  listUsageLogs: '/api/v1/usage/logs',
  getStats: '/api/v1/stats/dashboard',

  // Health
  health: '/health',
  metrics: '/metrics',
};

export default apiEndpoints;

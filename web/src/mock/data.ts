// Mock data for InferX platform

export interface Model {
  id: string;
  name: string;
  version: string;
  category: 'llm' | 'embedding' | 'reranker' | 'image';
  quantization: 'fp16' | 'int8' | 'fp4' | 'fp8';
  status: 'downloading' | 'ready' | 'error';
  size_gb: number;
  download_progress?: number;
  created_at: string;
}

export interface Deployment {
  id: string;
  model_id: string;
  model_name: string;
  name: string;
  environment: 'dev' | 'test' | 'staging' | 'prod';
  replicas: number;
  gpu_per_replica: number;
  backend: 'vllm' | 'sglang' | 'chitu';
  status: 'starting' | 'running' | 'stopping' | 'stopped' | 'error';
  qps: number;
  latency_ms: number;
  gpu_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface GPU {
  id: string;
  name: string;
  memory_total_mb: number;
  memory_free_mb: number;
  memory_used_mb: number;
  utilization_percent: number;
  temperature_celsius: number;
  status: 'available' | 'in_use' | 'error';
  deployment_id?: string;
}

export interface ApiKey {
  id: string;
  key_prefix: string;
  name: string;
  quota_tokens: number;
  tokens_used: number;
  is_active: boolean;
  expires_at: string;
  created_at: string;
  last_used_at: string;
}

export interface UsageLog {
  id: string;
  api_key_id: string;
  model_id: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  latency_ms: number;
  status: 'success' | 'error';
  created_at: string;
}

// Mock Models
export const mockModels: Model[] = [
  {
    id: 'model_1',
    name: 'Qwen2.5-7B-Instruct',
    version: 'v2.0',
    category: 'llm',
    quantization: 'fp8',
    status: 'ready',
    size_gb: 14.5,
    created_at: '2025-01-10T00:00:00Z',
  },
  {
    id: 'model_2',
    name: 'DeepSeek-R1-Distill-Qwen-32B',
    version: 'v1.0',
    category: 'llm',
    quantization: 'fp8',
    status: 'ready',
    size_gb: 32.0,
    created_at: '2025-01-08T00:00:00Z',
  },
  {
    id: 'model_3',
    name: 'GLM-4-9B-Chat',
    version: 'v3.0',
    category: 'llm',
    quantization: 'int8',
    status: 'ready',
    size_gb: 18.0,
    created_at: '2025-01-05T00:00:00Z',
  },
  {
    id: 'model_4',
    name: 'Llama-3-8B-Instruct',
    version: 'v1.0',
    category: 'llm',
    quantization: 'fp16',
    status: 'ready',
    size_gb: 16.0,
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'model_5',
    name: 'bge-large-zh-v1.5',
    version: 'v1.5',
    category: 'embedding',
    quantization: 'fp16',
    status: 'downloading',
    size_gb: 2.5,
    download_progress: 75,
    created_at: '2025-01-12T00:00:00Z',
  },
  {
    id: 'model_6',
    name: 'jina-reranker-v1-base',
    version: 'v1.0',
    category: 'reranker',
    quantization: 'fp16',
    status: 'ready',
    size_gb: 1.2,
    created_at: '2024-12-20T00:00:00Z',
  },
];

// Mock Deployments
export const mockDeployments: Deployment[] = [
  {
    id: 'deploy_1',
    model_id: 'model_1',
    model_name: 'Qwen2.5-7B-Instruct',
    name: 'qwen2.5-7b-prod',
    environment: 'prod',
    replicas: 2,
    gpu_per_replica: 1,
    backend: 'vllm',
    status: 'running',
    qps: 45,
    latency_ms: 250,
    gpu_ids: ['gpu:0', 'gpu:1'],
    created_at: '2025-01-10T10:00:00Z',
    updated_at: '2025-01-12T15:30:00Z',
  },
  {
    id: 'deploy_2',
    model_id: 'model_2',
    model_name: 'DeepSeek-R1-Distill-Qwen-32B',
    name: 'deepseek-r1-prod',
    environment: 'prod',
    replicas: 4,
    gpu_per_replica: 1,
    backend: 'vllm',
    status: 'running',
    qps: 12,
    latency_ms: 800,
    gpu_ids: ['gpu:2', 'gpu:3', 'gpu:4', 'gpu:5'],
    created_at: '2025-01-08T10:00:00Z',
    updated_at: '2025-01-12T15:30:00Z',
  },
  {
    id: 'deploy_3',
    model_id: 'model_3',
    model_name: 'GLM-4-9B-Chat',
    name: 'glm-4-staging',
    environment: 'staging',
    replicas: 1,
    gpu_per_replica: 1,
    backend: 'vllm',
    status: 'running',
    qps: 23,
    latency_ms: 420,
    gpu_ids: ['gpu:6'],
    created_at: '2025-01-05T10:00:00Z',
    updated_at: '2025-01-12T14:00:00Z',
  },
  {
    id: 'deploy_4',
    model_id: 'model_4',
    model_name: 'Llama-3-8B-Instruct',
    name: 'llama-3-dev',
    environment: 'dev',
    replicas: 1,
    gpu_per_replica: 1,
    backend: 'sglang',
    status: 'starting',
    qps: 0,
    latency_ms: 0,
    gpu_ids: ['gpu:7'],
    created_at: '2025-01-12T14:00:00Z',
    updated_at: '2025-01-12T14:00:00Z',
  },
];

// Mock GPUs
export const mockGPUs: GPU[] = [
  {
    id: 'gpu:0',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 8192,
    memory_used_mb: 16384,
    utilization_percent: 78.5,
    temperature_celsius: 68,
    status: 'in_use',
    deployment_id: 'deploy_1',
  },
  {
    id: 'gpu:1',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 7680,
    memory_used_mb: 16896,
    utilization_percent: 82.3,
    temperature_celsius: 71,
    status: 'in_use',
    deployment_id: 'deploy_1',
  },
  {
    id: 'gpu:2',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 2048,
    memory_used_mb: 22528,
    utilization_percent: 91.5,
    temperature_celsius: 79,
    status: 'in_use',
    deployment_id: 'deploy_2',
  },
  {
    id: 'gpu:3',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 1024,
    memory_used_mb: 23552,
    utilization_percent: 95.2,
    temperature_celsius: 82,
    status: 'in_use',
    deployment_id: 'deploy_2',
  },
  {
    id: 'gpu:4',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 3072,
    memory_used_mb: 21504,
    utilization_percent: 88.0,
    temperature_celsius: 76,
    status: 'in_use',
    deployment_id: 'deploy_2',
  },
  {
    id: 'gpu:5',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 2560,
    memory_used_mb: 22016,
    utilization_percent: 89.5,
    temperature_celsius: 77,
    status: 'in_use',
    deployment_id: 'deploy_2',
  },
  {
    id: 'gpu:6',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 15360,
    memory_used_mb: 9216,
    utilization_percent: 45.2,
    temperature_celsius: 55,
    status: 'in_use',
    deployment_id: 'deploy_3',
  },
  {
    id: 'gpu:7',
    name: 'NVIDIA RTX 4090',
    memory_total_mb: 24576,
    memory_free_mb: 24576,
    memory_used_mb: 0,
    utilization_percent: 0,
    temperature_celsius: 38,
    status: 'available',
  },
];

// Mock API Keys
export const mockApiKeys: ApiKey[] = [
  {
    id: 'key_1',
    key_prefix: 'inferx_sk_a7b3...',
    name: 'Production API Key',
    quota_tokens: 100000000,
    tokens_used: 12543000,
    is_active: true,
    expires_at: '2025-12-31T23:59:59Z',
    created_at: '2025-01-01T00:00:00Z',
    last_used_at: '2025-01-12T15:30:00Z',
  },
  {
    id: 'key_2',
    key_prefix: 'inferx_sk_c9d4...',
    name: 'Development Key',
    quota_tokens: 10000000,
    tokens_used: 2340000,
    is_active: true,
    expires_at: '2025-06-30T23:59:59Z',
    created_at: '2025-01-05T00:00:00Z',
    last_used_at: '2025-01-12T14:20:00Z',
  },
  {
    id: 'key_3',
    key_prefix: 'inferx_sk_e1f5...',
    name: 'Testing Key',
    quota_tokens: 5000000,
    tokens_used: 4875000,
    is_active: true,
    expires_at: '2025-03-31T23:59:59Z',
    created_at: '2024-12-01T00:00:00Z',
    last_used_at: '2025-01-12T15:00:00Z',
  },
];

// Mock Usage Logs
export const mockUsageLogs: UsageLog[] = [
  {
    id: 'log_1',
    api_key_id: 'key_1',
    model_id: 'model_1',
    model_name: 'Qwen2.5-7B-Instruct',
    input_tokens: 150,
    output_tokens: 300,
    total_tokens: 450,
    latency_ms: 250,
    status: 'success',
    created_at: '2025-01-12T15:30:00Z',
  },
  {
    id: 'log_2',
    api_key_id: 'key_1',
    model_id: 'model_2',
    model_name: 'DeepSeek-R1-Distill-Qwen-32B',
    input_tokens: 2000,
    output_tokens: 1500,
    total_tokens: 3500,
    latency_ms: 800,
    status: 'success',
    created_at: '2025-01-12T15:29:55Z',
  },
  {
    id: 'log_3',
    api_key_id: 'key_2',
    model_id: 'model_3',
    model_name: 'GLM-4-9B-Chat',
    input_tokens: 100,
    output_tokens: 200,
    total_tokens: 300,
    latency_ms: 420,
    status: 'success',
    created_at: '2025-01-12T15:29:50Z',
  },
  {
    id: 'log_4',
    api_key_id: 'key_1',
    model_id: 'model_1',
    model_name: 'Qwen2.5-7B-Instruct',
    input_tokens: 50,
    output_tokens: 0,
    total_tokens: 50,
    latency_ms: 0,
    status: 'error',
    created_at: '2025-01-12T15:29:45Z',
  },
];

// Dashboard stats
export const dashboardStats = {
  apiCallsToday: 125430,
  apiCallsMonth: 3250430,
  tokensUsed: 12500000,
  tokensQuota: 100000000,
  gpuUtilization: 78.5,
  runningModels: 3,
  totalModels: 10,
  totalGpus: 8,
  usedGpus: 7,
};

// Time series data for charts
export const generateTimeSeriesData = (hours: number = 24) => {
  const data = [];
  const now = Date.now();
  for (let i = hours; i >= 0; i--) {
    const timestamp = now - i * 3600 * 1000;
    data.push({
      timestamp: new Date(timestamp).toISOString(),
      qps: Math.floor(100 + Math.random() * 200),
      latency: Math.floor(200 + Math.random() * 600),
      tokens: Math.floor(50000 + Math.random() * 100000),
      gpuUtil: Math.floor(60 + Math.random() * 35),
    });
  }
  return data;
};

export const mockTimeSeriesData = generateTimeSeriesData(24);

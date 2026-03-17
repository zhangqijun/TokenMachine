// Mock data for TokenMachine platform

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
  backend: 'vllm' | 'sglang';
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
    key_prefix: 'tmachine_sk_a7b3...',
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
    key_prefix: 'tmachine_sk_c9d4...',
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
    key_prefix: 'tmachine_sk_e1f5...',
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

// Mock Workers (compatible with api/index.ts Worker interface)
export interface MockWorker {
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
  gpu_devices?: MockGPUDevice[];
}

export interface MockGPUDevice {
  id: number;
  worker_id: number;
  uuid: string;
  name: string;
  vendor: string;
  index: number;
  ip: string;
  memory_total: number;
  memory_used: number;
  memory_utilization_rate: number;
  core_utilization_rate: number;
  temperature: number;
  state: 'AVAILABLE' | 'IN_USE' | 'ERROR';
  created_at: string;
  updated_at: string;
}

export const mockWorkers: MockWorker[] = [
  {
    id: 1,
    name: 'worker-node-01',
    cluster_id: 1,
    status: 'READY',
    ip: '192.168.1.101',
    hostname: 'gpu-server-01',
    gpu_count: 4,
    expected_gpu_count: 4,
    labels: { region: 'cn-east', gpu_type: 'A100', env: 'prod' },
    capabilities: ['vllm', 'sglang'],
    agent_type: 'gpu-agent',
    agent_version: 'v1.2.0',
    last_heartbeat_at: new Date(Date.now() - 5000).toISOString(),
    created_at: '2025-01-05T08:00:00Z',
    updated_at: new Date().toISOString(),
    gpu_devices: [
      {
        id: 1, worker_id: 1, uuid: 'GPU-a1b2c3d4', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 0, ip: '192.168.1.101', memory_total: 85899345920, memory_used: 64424509440,
        memory_utilization_rate: 0.75, core_utilization_rate: 0.82, temperature: 68,
        state: 'IN_USE', created_at: '2025-01-05T08:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 2, worker_id: 1, uuid: 'GPU-e5f6g7h8', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 1, ip: '192.168.1.101', memory_total: 85899345920, memory_used: 68719476736,
        memory_utilization_rate: 0.80, core_utilization_rate: 0.88, temperature: 72,
        state: 'IN_USE', created_at: '2025-01-05T08:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 3, worker_id: 1, uuid: 'GPU-i9j0k1l2', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 2, ip: '192.168.1.101', memory_total: 85899345920, memory_used: 42949672960,
        memory_utilization_rate: 0.50, core_utilization_rate: 0.55, temperature: 58,
        state: 'IN_USE', created_at: '2025-01-05T08:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 4, worker_id: 1, uuid: 'GPU-m3n4o5p6', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 3, ip: '192.168.1.101', memory_total: 85899345920, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 35,
        state: 'AVAILABLE', created_at: '2025-01-05T08:00:00Z', updated_at: new Date().toISOString(),
      },
    ],
  },
  {
    id: 2,
    name: 'worker-node-02',
    cluster_id: 1,
    status: 'BUSY',
    ip: '192.168.1.102',
    hostname: 'gpu-server-02',
    gpu_count: 8,
    expected_gpu_count: 8,
    labels: { region: 'cn-east', gpu_type: 'H100', env: 'prod' },
    capabilities: ['vllm', 'sglang', 'mindie'],
    agent_type: 'gpu-agent',
    agent_version: 'v1.2.0',
    last_heartbeat_at: new Date(Date.now() - 3000).toISOString(),
    created_at: '2025-01-08T10:00:00Z',
    updated_at: new Date().toISOString(),
    gpu_devices: [
      {
        id: 5, worker_id: 2, uuid: 'GPU-h100-01', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 0, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 77309411328,
        memory_utilization_rate: 0.90, core_utilization_rate: 0.95, temperature: 78,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 6, worker_id: 2, uuid: 'GPU-h100-02', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 1, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 73014444032,
        memory_utilization_rate: 0.85, core_utilization_rate: 0.91, temperature: 75,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 7, worker_id: 2, uuid: 'GPU-h100-03', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 2, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 68719476736,
        memory_utilization_rate: 0.80, core_utilization_rate: 0.85, temperature: 71,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 8, worker_id: 2, uuid: 'GPU-h100-04', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 3, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 81604378624,
        memory_utilization_rate: 0.95, core_utilization_rate: 0.97, temperature: 82,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 9, worker_id: 2, uuid: 'GPU-h100-05', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 4, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 64424509440,
        memory_utilization_rate: 0.75, core_utilization_rate: 0.78, temperature: 66,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 10, worker_id: 2, uuid: 'GPU-h100-06', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 5, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 60129542144,
        memory_utilization_rate: 0.70, core_utilization_rate: 0.73, temperature: 63,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 11, worker_id: 2, uuid: 'GPU-h100-07', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 6, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 55834574848,
        memory_utilization_rate: 0.65, core_utilization_rate: 0.68, temperature: 60,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 12, worker_id: 2, uuid: 'GPU-h100-08', name: 'NVIDIA H100 80GB', vendor: 'NVIDIA',
        index: 7, ip: '192.168.1.102', memory_total: 85899345920, memory_used: 47244640256,
        memory_utilization_rate: 0.55, core_utilization_rate: 0.60, temperature: 56,
        state: 'IN_USE', created_at: '2025-01-08T10:00:00Z', updated_at: new Date().toISOString(),
      },
    ],
  },
  {
    id: 3,
    name: 'worker-node-03',
    cluster_id: 1,
    status: 'READY',
    ip: '192.168.1.103',
    hostname: 'gpu-server-03',
    gpu_count: 2,
    expected_gpu_count: 2,
    labels: { region: 'cn-north', gpu_type: 'RTX4090', env: 'staging' },
    capabilities: ['vllm'],
    agent_type: 'gpu-agent',
    agent_version: 'v1.1.5',
    last_heartbeat_at: new Date(Date.now() - 8000).toISOString(),
    created_at: '2025-01-10T14:00:00Z',
    updated_at: new Date().toISOString(),
    gpu_devices: [
      {
        id: 13, worker_id: 3, uuid: 'GPU-4090-01', name: 'NVIDIA RTX 4090', vendor: 'NVIDIA',
        index: 0, ip: '192.168.1.103', memory_total: 25769803776, memory_used: 18253611008,
        memory_utilization_rate: 0.71, core_utilization_rate: 0.65, temperature: 62,
        state: 'IN_USE', created_at: '2025-01-10T14:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 14, worker_id: 3, uuid: 'GPU-4090-02', name: 'NVIDIA RTX 4090', vendor: 'NVIDIA',
        index: 1, ip: '192.168.1.103', memory_total: 25769803776, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 38,
        state: 'AVAILABLE', created_at: '2025-01-10T14:00:00Z', updated_at: new Date().toISOString(),
      },
    ],
  },
  {
    id: 4,
    name: 'worker-ascend-01',
    cluster_id: 1,
    status: 'READY',
    ip: '192.168.2.201',
    hostname: 'ascend-server-01',
    gpu_count: 8,
    expected_gpu_count: 8,
    labels: { region: 'cn-east', gpu_type: '910B', env: 'prod', vendor: 'huawei' },
    capabilities: ['mindie'],
    agent_type: 'ascend-agent',
    agent_version: 'v0.5.0',
    last_heartbeat_at: new Date(Date.now() - 12000).toISOString(),
    created_at: '2025-01-12T09:00:00Z',
    updated_at: new Date().toISOString(),
    gpu_devices: [
      {
        id: 15, worker_id: 4, uuid: 'NPU-910B-01', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 0, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 51539607552,
        memory_utilization_rate: 0.75, core_utilization_rate: 0.80, temperature: 65,
        state: 'IN_USE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 16, worker_id: 4, uuid: 'NPU-910B-02', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 1, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 48318382080,
        memory_utilization_rate: 0.70, core_utilization_rate: 0.72, temperature: 62,
        state: 'IN_USE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 17, worker_id: 4, uuid: 'NPU-910B-03', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 2, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 34359738368,
        memory_utilization_rate: 0.50, core_utilization_rate: 0.55, temperature: 55,
        state: 'IN_USE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 18, worker_id: 4, uuid: 'NPU-910B-04', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 3, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 36,
        state: 'AVAILABLE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 19, worker_id: 4, uuid: 'NPU-910B-05', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 4, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 58583490560,
        memory_utilization_rate: 0.85, core_utilization_rate: 0.88, temperature: 70,
        state: 'IN_USE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 20, worker_id: 4, uuid: 'NPU-910B-06', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 5, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 41303859200,
        memory_utilization_rate: 0.60, core_utilization_rate: 0.62, temperature: 58,
        state: 'IN_USE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 21, worker_id: 4, uuid: 'NPU-910B-07', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 6, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 34,
        state: 'AVAILABLE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 22, worker_id: 4, uuid: 'NPU-910B-08', name: '华为昇腾 910B', vendor: 'Huawei',
        index: 7, ip: '192.168.2.201', memory_total: 68719476736, memory_used: 54878724096,
        memory_utilization_rate: 0.80, core_utilization_rate: 0.82, temperature: 67,
        state: 'IN_USE', created_at: '2025-01-12T09:00:00Z', updated_at: new Date().toISOString(),
      },
    ],
  },
  {
    id: 5,
    name: 'worker-node-05',
    cluster_id: 1,
    status: 'UNHEALTHY',
    ip: '192.168.1.105',
    hostname: 'gpu-server-05',
    gpu_count: 2,
    expected_gpu_count: 4,
    labels: { region: 'cn-east', gpu_type: 'A100', env: 'dev' },
    capabilities: ['vllm'],
    agent_type: 'gpu-agent',
    agent_version: 'v1.0.8',
    last_heartbeat_at: new Date(Date.now() - 300000).toISOString(),
    created_at: '2025-01-03T11:00:00Z',
    updated_at: new Date().toISOString(),
    gpu_devices: [
      {
        id: 23, worker_id: 5, uuid: 'GPU-a100-err-01', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 0, ip: '192.168.1.105', memory_total: 85899345920, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 92,
        state: 'ERROR', created_at: '2025-01-03T11:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 24, worker_id: 5, uuid: 'GPU-a100-err-02', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 1, ip: '192.168.1.105', memory_total: 85899345920, memory_used: 34359738368,
        memory_utilization_rate: 0.40, core_utilization_rate: 0.35, temperature: 55,
        state: 'IN_USE', created_at: '2025-01-03T11:00:00Z', updated_at: new Date().toISOString(),
      },
    ],
  },
  {
    id: 6,
    name: 'worker-node-06',
    cluster_id: 1,
    status: 'DRAINING',
    ip: '192.168.1.106',
    hostname: 'gpu-server-06',
    gpu_count: 4,
    expected_gpu_count: 4,
    labels: { region: 'cn-north', gpu_type: 'A100', env: 'prod' },
    capabilities: ['vllm', 'sglang'],
    agent_type: 'gpu-agent',
    agent_version: 'v1.2.0',
    last_heartbeat_at: new Date(Date.now() - 15000).toISOString(),
    created_at: '2025-01-06T16:00:00Z',
    updated_at: new Date().toISOString(),
    gpu_devices: [
      {
        id: 25, worker_id: 6, uuid: 'GPU-drain-01', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 0, ip: '192.168.1.106', memory_total: 85899345920, memory_used: 30064771072,
        memory_utilization_rate: 0.35, core_utilization_rate: 0.30, temperature: 48,
        state: 'IN_USE', created_at: '2025-01-06T16:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 26, worker_id: 6, uuid: 'GPU-drain-02', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 1, ip: '192.168.1.106', memory_total: 85899345920, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 35,
        state: 'AVAILABLE', created_at: '2025-01-06T16:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 27, worker_id: 6, uuid: 'GPU-drain-03', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 2, ip: '192.168.1.106', memory_total: 85899345920, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 34,
        state: 'AVAILABLE', created_at: '2025-01-06T16:00:00Z', updated_at: new Date().toISOString(),
      },
      {
        id: 28, worker_id: 6, uuid: 'GPU-drain-04', name: 'NVIDIA A100 80GB', vendor: 'NVIDIA',
        index: 3, ip: '192.168.1.106', memory_total: 85899345920, memory_used: 0,
        memory_utilization_rate: 0, core_utilization_rate: 0, temperature: 33,
        state: 'AVAILABLE', created_at: '2025-01-06T16:00:00Z', updated_at: new Date().toISOString(),
      },
    ],
  },
];

// Mock Worker Metrics
export const mockWorkerMetrics: Record<number, {
  worker_id: number;
  worker_name: string;
  worker_ip: string;
  timestamp: string;
  gpu_count: number;
  total_memory_gb: number;
  used_memory_gb: number;
  avg_utilization_percent: number;
  gpus: Array<{
    gpu_index: number;
    name: string;
    memory_total_mb: number;
    memory_used_mb: number;
    memory_utilization_percent: number;
    gpu_utilization_percent: number;
    temperature_celsius: number;
  }>;
}> = {
  1: {
    worker_id: 1, worker_name: 'worker-node-01', worker_ip: '192.168.1.101',
    timestamp: new Date().toISOString(), gpu_count: 4,
    total_memory_gb: 320, used_memory_gb: 195,
    avg_utilization_percent: 51.3,
    gpus: [
      { gpu_index: 0, name: 'NVIDIA A100 80GB', memory_total_mb: 81920, memory_used_mb: 61440, memory_utilization_percent: 75, gpu_utilization_percent: 82, temperature_celsius: 68 },
      { gpu_index: 1, name: 'NVIDIA A100 80GB', memory_total_mb: 81920, memory_used_mb: 65536, memory_utilization_percent: 80, gpu_utilization_percent: 88, temperature_celsius: 72 },
      { gpu_index: 2, name: 'NVIDIA A100 80GB', memory_total_mb: 81920, memory_used_mb: 40960, memory_utilization_percent: 50, gpu_utilization_percent: 55, temperature_celsius: 58 },
      { gpu_index: 3, name: 'NVIDIA A100 80GB', memory_total_mb: 81920, memory_used_mb: 0, memory_utilization_percent: 0, gpu_utilization_percent: 0, temperature_celsius: 35 },
    ],
  },
  2: {
    worker_id: 2, worker_name: 'worker-node-02', worker_ip: '192.168.1.102',
    timestamp: new Date().toISOString(), gpu_count: 8,
    total_memory_gb: 640, used_memory_gb: 510,
    avg_utilization_percent: 76.9,
    gpus: [
      { gpu_index: 0, name: 'NVIDIA H100 80GB', memory_total_mb: 81920, memory_used_mb: 73728, memory_utilization_percent: 90, gpu_utilization_percent: 95, temperature_celsius: 78 },
      { gpu_index: 1, name: 'NVIDIA H100 80GB', memory_total_mb: 81920, memory_used_mb: 69632, memory_utilization_percent: 85, gpu_utilization_percent: 91, temperature_celsius: 75 },
    ],
  },
  3: {
    worker_id: 3, worker_name: 'worker-node-03', worker_ip: '192.168.1.103',
    timestamp: new Date().toISOString(), gpu_count: 2,
    total_memory_gb: 48, used_memory_gb: 17,
    avg_utilization_percent: 35.5,
    gpus: [
      { gpu_index: 0, name: 'NVIDIA RTX 4090', memory_total_mb: 24576, memory_used_mb: 17408, memory_utilization_percent: 71, gpu_utilization_percent: 65, temperature_celsius: 62 },
      { gpu_index: 1, name: 'NVIDIA RTX 4090', memory_total_mb: 24576, memory_used_mb: 0, memory_utilization_percent: 0, gpu_utilization_percent: 0, temperature_celsius: 38 },
    ],
  },
  4: {
    worker_id: 4, worker_name: 'worker-ascend-01', worker_ip: '192.168.2.201',
    timestamp: new Date().toISOString(), gpu_count: 8,
    total_memory_gb: 512, used_memory_gb: 350,
    avg_utilization_percent: 52.5,
    gpus: [
      { gpu_index: 0, name: '华为昇腾 910B', memory_total_mb: 65536, memory_used_mb: 49152, memory_utilization_percent: 75, gpu_utilization_percent: 80, temperature_celsius: 65 },
      { gpu_index: 1, name: '华为昇腾 910B', memory_total_mb: 65536, memory_used_mb: 45875, memory_utilization_percent: 70, gpu_utilization_percent: 72, temperature_celsius: 62 },
    ],
  },
};

// Mock Worker Stats
export const mockWorkerStats: Record<number, {
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
}> = {
  1: { worker_id: 1, worker_name: 'worker-node-01', status: 'READY', total_gpus: 4, in_use_gpus: 3, error_gpus: 0, avg_memory_utilization: 51, avg_core_utilization: 56, avg_temperature: 58, last_heartbeat_at: new Date().toISOString() },
  2: { worker_id: 2, worker_name: 'worker-node-02', status: 'BUSY', total_gpus: 8, in_use_gpus: 8, error_gpus: 0, avg_memory_utilization: 77, avg_core_utilization: 81, avg_temperature: 69, last_heartbeat_at: new Date().toISOString() },
  3: { worker_id: 3, worker_name: 'worker-node-03', status: 'READY', total_gpus: 2, in_use_gpus: 1, error_gpus: 0, avg_memory_utilization: 36, avg_core_utilization: 33, avg_temperature: 50, last_heartbeat_at: new Date().toISOString() },
  4: { worker_id: 4, worker_name: 'worker-ascend-01', status: 'READY', total_gpus: 8, in_use_gpus: 6, error_gpus: 0, avg_memory_utilization: 53, avg_core_utilization: 55, avg_temperature: 56, last_heartbeat_at: new Date().toISOString() },
  5: { worker_id: 5, worker_name: 'worker-node-05', status: 'UNHEALTHY', total_gpus: 2, in_use_gpus: 1, error_gpus: 1, avg_memory_utilization: 20, avg_core_utilization: 18, avg_temperature: 74, last_heartbeat_at: new Date(Date.now() - 300000).toISOString() },
  6: { worker_id: 6, worker_name: 'worker-node-06', status: 'DRAINING', total_gpus: 4, in_use_gpus: 1, error_gpus: 0, avg_memory_utilization: 9, avg_core_utilization: 8, avg_temperature: 38, last_heartbeat_at: new Date().toISOString() },
};

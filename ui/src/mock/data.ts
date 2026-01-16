// Mock data for TokenMachine platform

export interface Model {
  id: string;
  name: string;
  version: string;
  path: string;              // 模型存储路径
  size_gb: number;
  status: 'running' | 'stopped' | 'loading' | 'error';
  backend: 'vllm' | 'sglang';
  created_at: string;
  updated_at: string;

  // 保留旧字段以兼容现有代码
  category?: 'llm' | 'embedding' | 'reranker' | 'image';
  quantization?: 'fp16' | 'int8' | 'fp4' | 'fp8';
  download_progress?: number;
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
    path: '/var/lib/backend/models/qwen2.5-7b-instruct',
    size_gb: 14.5,
    status: 'running',
    backend: 'vllm',
    created_at: '2025-01-10T00:00:00Z',
    updated_at: '2025-01-15T10:30:00Z',
    category: 'llm',
    quantization: 'fp8',
  },
  {
    id: 'model_2',
    name: 'DeepSeek-R1-Distill-Qwen-32B',
    version: 'v1.0',
    path: '/var/lib/backend/models/deepseek-r1-32b',
    size_gb: 32.0,
    status: 'running',
    backend: 'vllm',
    created_at: '2025-01-08T00:00:00Z',
    updated_at: '2025-01-15T11:00:00Z',
    category: 'llm',
    quantization: 'fp8',
  },
  {
    id: 'model_3',
    name: 'GLM-4-9B-Chat',
    version: 'v3.0',
    path: '/var/lib/backend/models/glm-4-9b-chat',
    size_gb: 18.0,
    status: 'stopped',
    backend: 'sglang',
    created_at: '2025-01-05T00:00:00Z',
    updated_at: '2025-01-14T16:00:00Z',
    category: 'llm',
    quantization: 'int8',
  },
  {
    id: 'model_4',
    name: 'Llama-3-8B-Instruct',
    version: 'v1.0',
    path: '/var/lib/backend/models/llama-3-8b-instruct',
    size_gb: 16.0,
    status: 'stopped',
    backend: 'vllm',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-13T09:00:00Z',
    category: 'llm',
    quantization: 'fp16',
  },
  {
    id: 'model_5',
    name: 'bge-large-zh-v1.5',
    version: 'v1.5',
    path: '/var/lib/backend/models/bge-large-zh-v1.5',
    size_gb: 2.5,
    status: 'loading',
    backend: 'vllm',
    created_at: '2025-01-12T00:00:00Z',
    updated_at: '2025-01-12T00:00:00Z',
    category: 'embedding',
    quantization: 'fp16',
    download_progress: 75,
  },
  {
    id: 'model_6',
    name: 'jina-reranker-v1-base',
    version: 'v1.0',
    path: '/var/lib/backend/models/jina-reranker-v1-base',
    size_gb: 1.2,
    status: 'stopped',
    backend: 'vllm',
    created_at: '2024-12-20T00:00:00Z',
    updated_at: '2025-01-10T14:00:00Z',
    category: 'reranker',
    quantization: 'fp16',
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

// Worker and Resource Management Types
export interface CPUInfo {
  total: number;
  allocated: number;
  utilization_rate: number;
}

export interface MemoryInfo {
  total: number;
  used: number;
  allocated: number;
  utilization_rate: number;
}

export interface GPUDevice {
  uuid: string;
  name: string;
  vendor: 'nvidia' | 'amd' | 'apple';
  index: number;
  core: {
    total: number;
    utilization_rate: number;
  };
  memory: {
    total: number;
    used: number;
    allocated: number;
    utilization_rate: number;
    is_unified_memory: boolean;
  };
  temperature: number;
  state: 'available' | 'in_use' | 'error';
}

export interface FileSystem {
  path: string;
  total: number;
  used: number;
  available: number;
}

export interface WorkerStatus {
  cpu: CPUInfo;
  memory: MemoryInfo;
  gpu_devices: GPUDevice[];
  filesystem: FileSystem[];
}

export interface Worker {
  name: string;
  state: 'running' | 'offline' | 'maintenance';
  ip: string;
  cluster_id: string;
  labels: Record<string, string>;
  status: WorkerStatus;
  last_heartbeat: string;
}

// Cluster Management Types
export interface Cluster {
  id: string;
  name: string;
  type: 'docker' | 'kubernetes' | 'digitalocean' | 'aws';
  is_default: boolean;
  status: 'running' | 'stopped' | 'error';
  worker_pools: WorkerPool[];
  created_at: string;
  updated_at: string;
}

export interface WorkerPool {
  id: string;
  cluster_id: string;
  name: string;
  worker_count: number;
  min_workers: number;
  max_workers: number;
  status: 'running' | 'scaling' | 'stopped';
  config: WorkerPoolConfig;
}

export interface WorkerPoolConfig {
  provider_specific: {
    docker?: {
      image: string;
      volumes: string[];
    };
    kubernetes?: {
      namespace: string;
      replicas: number;
    };
  };
}

// Mock Workers
export const mockWorkers: Worker[] = [
  {
    name: 'worker-1',
    state: 'running',
    ip: '192.168.1.10',
    cluster_id: 'cluster_default',
    labels: { env: 'production', zone: 'a' },
    status: {
      cpu: { total: 32, allocated: 16, utilization_rate: 65.5 },
      memory: {
        total: 128 * 1024 * 1024 * 1024, // 128GB in bytes
        used: 85 * 1024 * 1024 * 1024,
        allocated: 96 * 1024 * 1024 * 1024,
        utilization_rate: 66.4,
      },
      gpu_devices: [
        {
          uuid: 'gpu-0-0',
          name: 'NVIDIA RTX 4090',
          vendor: 'nvidia',
          index: 0,
          core: { total: 16384, utilization_rate: 78.5 },
          memory: {
            total: 24 * 1024 * 1024 * 1024,
            used: 18 * 1024 * 1024 * 1024,
            allocated: 20 * 1024 * 1024 * 1024,
            utilization_rate: 75.0,
            is_unified_memory: false,
          },
          temperature: 68,
          state: 'in_use',
        },
        {
          uuid: 'gpu-0-1',
          name: 'NVIDIA RTX 4090',
          vendor: 'nvidia',
          index: 1,
          core: { total: 16384, utilization_rate: 82.3 },
          memory: {
            total: 24 * 1024 * 1024 * 1024,
            used: 22 * 1024 * 1024 * 1024,
            allocated: 22 * 1024 * 1024 * 1024,
            utilization_rate: 91.7,
            is_unified_memory: false,
          },
          temperature: 74,
          state: 'in_use',
        },
      ],
      filesystem: [
        {
          path: '/var/lib/backend',
          total: 2 * 1024 * 1024 * 1024 * 1024, // 2TB
          used: 1.2 * 1024 * 1024 * 1024 * 1024,
          available: 0.8 * 1024 * 1024 * 1024 * 1024,
        },
      ],
    },
    last_heartbeat: new Date().toISOString(),
  },
  {
    name: 'worker-2',
    state: 'running',
    ip: '192.168.1.11',
    cluster_id: 'cluster_default',
    labels: { env: 'production', zone: 'b' },
    status: {
      cpu: { total: 32, allocated: 8, utilization_rate: 25.3 },
      memory: {
        total: 128 * 1024 * 1024 * 1024,
        used: 45 * 1024 * 1024 * 1024,
        allocated: 64 * 1024 * 1024 * 1024,
        utilization_rate: 35.2,
      },
      gpu_devices: [
        {
          uuid: 'gpu-1-0',
          name: 'NVIDIA RTX 4090',
          vendor: 'nvidia',
          index: 0,
          core: { total: 16384, utilization_rate: 0 },
          memory: {
            total: 24 * 1024 * 1024 * 1024,
            used: 0,
            allocated: 0,
            utilization_rate: 0,
            is_unified_memory: false,
          },
          temperature: 38,
          state: 'available',
        },
        {
          uuid: 'gpu-1-1',
          name: 'NVIDIA RTX 4090',
          vendor: 'nvidia',
          index: 1,
          core: { total: 16384, utilization_rate: 0 },
          memory: {
            total: 24 * 1024 * 1024 * 1024,
            used: 0,
            allocated: 0,
            utilization_rate: 0,
            is_unified_memory: false,
          },
          temperature: 38,
          state: 'available',
        },
      ],
      filesystem: [
        {
          path: '/var/lib/backend',
          total: 2 * 1024 * 1024 * 1024 * 1024,
          used: 0.8 * 1024 * 1024 * 1024 * 1024,
          available: 1.2 * 1024 * 1024 * 1024 * 1024,
        },
      ],
    },
    last_heartbeat: new Date().toISOString(),
  },
  {
    name: 'worker-3',
    state: 'maintenance',
    ip: '192.168.1.12',
    cluster_id: 'cluster_default',
    labels: { env: 'development' },
    status: {
      cpu: { total: 16, allocated: 0, utilization_rate: 0 },
      memory: {
        total: 64 * 1024 * 1024 * 1024,
        used: 8 * 1024 * 1024 * 1024,
        allocated: 0,
        utilization_rate: 12.5,
      },
      gpu_devices: [
        {
          uuid: 'gpu-2-0',
          name: 'NVIDIA RTX 3090',
          vendor: 'nvidia',
          index: 0,
          core: { total: 10496, utilization_rate: 0 },
          memory: {
            total: 24 * 1024 * 1024 * 1024,
            used: 0,
            allocated: 0,
            utilization_rate: 0,
            is_unified_memory: false,
          },
          temperature: 35,
          state: 'available',
        },
      ],
      filesystem: [
        {
          path: '/var/lib/backend',
          total: 1 * 1024 * 1024 * 1024 * 1024,
          used: 0.3 * 1024 * 1024 * 1024 * 1024,
          available: 0.7 * 1024 * 1024 * 1024 * 1024,
        },
      ],
    },
    last_heartbeat: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
];

// Mock Clusters
export const mockClusters: Cluster[] = [
  {
    id: 'cluster_default',
    name: 'default',
    type: 'docker',
    is_default: true,
    status: 'running',
    worker_pools: [
      {
        id: 'pool_default_1',
        cluster_id: 'cluster_default',
        name: 'pool-1',
        worker_count: 2,
        min_workers: 2,
        max_workers: 4,
        status: 'running',
        config: {
          provider_specific: {
            docker: {
              image: 'tokenmachine/worker:latest',
              volumes: ['/var/lib/backend/models:/models'],
            },
          },
        },
      },
    ],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-12T15:00:00Z',
  },
  {
    id: 'cluster_prod',
    name: 'production',
    type: 'kubernetes',
    is_default: false,
    status: 'running',
    worker_pools: [
      {
        id: 'pool_prod_1',
        cluster_id: 'cluster_prod',
        name: 'gpu-pool-a',
        worker_count: 4,
        min_workers: 4,
        max_workers: 8,
        status: 'running',
        config: {
          provider_specific: {
            kubernetes: {
              namespace: 'tokenmachine',
              replicas: 4,
            },
          },
        },
      },
      {
        id: 'pool_prod_2',
        cluster_id: 'cluster_prod',
        name: 'gpu-pool-b',
        worker_count: 4,
        min_workers: 2,
        max_workers: 6,
        status: 'scaling',
        config: {
          provider_specific: {
            kubernetes: {
              namespace: 'tokenmachine',
              replicas: 4,
            },
          },
        },
      },
    ],
    created_at: '2025-01-05T00:00:00Z',
    updated_at: '2025-01-12T14:00:00Z',
  },
];

export interface BackendInfo {
  id: string;
  name: string;
  displayName: string;
  version: string;
  status: 'installed' | 'not_installed' | 'outdated' | 'error';
  icon: string;
  description: string;
  homepage?: string;
  documentation?: string;
  // 支持的特性
  features: {
    tensorParallel: boolean;
    prefixCaching: boolean;
    multiLora: boolean;
    speculativeDecoding: boolean;
    quantization: string[]; // 支持的量化方式
    modelFormats: string[]; // 支持的模型格式
  };
  // 性能指标
  performance?: {
    avgTps: number;
    memoryEfficiency: number;
    startupTime: number; // 秒
  };
  // 兼容性
  compatibility: {
    gpuVendors: string[]; // 支持的GPU厂商
    minGpuMemory: number; // 最小显存要求（GB）
    supportedModels: string[]; // 支持的模型列表
  };
  // 配置
  config: {
    installedPath?: string;
    configPath?: string;
    port?: number;
    envVars?: Record<string, string>;
  };
  // 统计信息
  stats: {
    activeDeployments: number;
    totalRequests: number;
    lastHealthCheck: string;
  };
  updateAvailable?: string; // 可更新的版本
}

export interface BackendLog {
  id: string;
  backendId: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

// Re-export types from mock data
export * from '../mock/data';

// Additional types
export interface MenuItem {
  key: string;
  label: string;
  icon?: string;
  path?: string;
  children?: MenuItem[];
}

export interface ChartDataPoint {
  timestamp: string;
  value: number;
}

export interface GPUChartData {
  timestamp: string;
  qps: number;
  latency: number;
  tokens: number;
  gpuUtil: number;
}

import { create } from 'zustand';
import type {
  Model,
  Deployment,
  GPU,
  ApiKey,
  UsageLog,
} from '../mock/data';
import {
  mockModels,
  mockDeployments,
  mockGPUs,
  mockApiKeys,
  mockUsageLogs,
  dashboardStats,
} from '../mock/data';

interface AppState {
  // Data
  models: Model[];
  deployments: Deployment[];
  gpus: GPU[];
  apiKeys: ApiKey[];
  usageLogs: UsageLog[];
  stats: typeof dashboardStats;

  // Loading states
  isLoading: boolean;

  // Actions
  refreshData: () => Promise<void>;
  addModel: (model: Omit<Model, 'id' | 'created_at'>) => Promise<void>;
  deleteModel: (id: string) => Promise<void>;
  createDeployment: (deployment: Omit<Deployment, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  stopDeployment: (id: string) => Promise<void>;
  createApiKey: (key: Omit<ApiKey, 'id' | 'key_prefix' | 'created_at' | 'last_used_at'>) => Promise<void>;
  deleteApiKey: (id: string) => Promise<void>;
  toggleApiKey: (id: string) => Promise<void>;
}

export const useStore = create<AppState>((set) => ({
  // Initial data
  models: mockModels,
  deployments: mockDeployments,
  gpus: mockGPUs,
  apiKeys: mockApiKeys,
  usageLogs: mockUsageLogs,
  stats: dashboardStats,
  isLoading: false,

  // Actions
  refreshData: async () => {
    set({ isLoading: true });
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    set({ isLoading: false });
  },

  addModel: async (modelData) => {
    set({ isLoading: true });
    await new Promise(resolve => setTimeout(resolve, 800));
    const newModel: Model = {
      ...modelData,
      id: `model_${Date.now()}`,
      created_at: new Date().toISOString(),
    };
    set(state => ({ models: [...state.models, newModel], isLoading: false }));
  },

  deleteModel: async (id) => {
    set({ isLoading: true });
    await new Promise(resolve => setTimeout(resolve, 500));
    set(state => ({
      models: state.models.filter(m => m.id !== id),
      isLoading: false,
    }));
  },

  createDeployment: async (deploymentData) => {
    set({ isLoading: true });
    await new Promise(resolve => setTimeout(resolve, 1500));
    const now = new Date().toISOString();
    const newDeployment: Deployment = {
      ...deploymentData,
      id: `deploy_${Date.now()}`,
      created_at: now,
      updated_at: now,
      qps: 0,
      latency_ms: 0,
    };
    set(state => ({
      deployments: [...state.deployments, newDeployment],
      isLoading: false,
    }));
  },

  stopDeployment: async (id) => {
    set({ isLoading: true });
    await new Promise(resolve => setTimeout(resolve, 1000));
    set(state => ({
      deployments: state.deployments.map(d =>
        d.id === id ? { ...d, status: 'stopped' as const, qps: 0, latency_ms: 0 } : d
      ),
      isLoading: false,
    }));
  },

  createApiKey: async (keyData) => {
    set({ isLoading: true });
    await new Promise(resolve => setTimeout(resolve, 500));
    const randomPart = Math.random().toString(36).substring(2, 6);
    const newKey: ApiKey = {
      ...keyData,
      id: `key_${Date.now()}`,
      key_prefix: `tmachine_sk_${randomPart}...`,
      created_at: new Date().toISOString(),
      last_used_at: new Date().toISOString(),
    };
    set(state => ({ apiKeys: [...state.apiKeys, newKey], isLoading: false }));
  },

  deleteApiKey: async (id) => {
    set({ isLoading: true });
    await new Promise(resolve => setTimeout(resolve, 500));
    set(state => ({
      apiKeys: state.apiKeys.filter(k => k.id !== id),
      isLoading: false,
    }));
  },

  toggleApiKey: async (id) => {
    set({ isLoading: true });
    await new Promise(resolve => setTimeout(resolve, 300));
    set(state => ({
      apiKeys: state.apiKeys.map(k =>
        k.id === id ? { ...k, is_active: !k.is_active } : k
      ),
      isLoading: false,
    }));
  },
}));

import { create } from 'zustand';
import config from '../config/env';
import api from '../api/client';
import apiEndpoints, * as ApiTypes from '../api/index';
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
  error?: string;

  // Loading states
  isLoading: boolean;
  isRefreshing: boolean;

  // Actions
  refreshData: () => Promise<void>;
  fetchModels: () => Promise<void>;
  fetchDeployments: () => Promise<void>;
  fetchGpus: () => Promise<void>;
  fetchApiKeys: () => Promise<void>;
  fetchUsageLogs: () => Promise<void>;
  fetchStats: () => Promise<void>;
  addModel: (model: Omit<Model, 'id' | 'created_at'>) => Promise<void>;
  deleteModel: (id: string | number) => Promise<void>;
  createDeployment: (deployment: Omit<Deployment, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  stopDeployment: (id: string | number) => Promise<void>;
  createApiKey: (key: Omit<ApiKey, 'id' | 'key_prefix' | 'created_at' | 'last_used_at'>) => Promise<void>;
  deleteApiKey: (id: string | number) => Promise<void>;
  toggleApiKey: (id: string | number) => Promise<void>;
  clearError: () => void;
}

/**
 * Store with support for both mock data and real API
 */
export const useStore = create<AppState>((set, get) => ({
  // Initial data - use mock data if enabled, empty otherwise
  models: config.useMockData ? mockModels : [],
  deployments: config.useMockData ? mockDeployments : [],
  gpus: config.useMockData ? mockGPUs : [],
  apiKeys: config.useMockData ? mockApiKeys : [],
  usageLogs: config.useMockData ? mockUsageLogs : [],
  stats: dashboardStats,
  error: undefined,
  isLoading: false,
  isRefreshing: false,

  // Clear error
  clearError: () => set({ error: undefined }),

  // Refresh all data
  refreshData: async () => {
    const { isRefreshing } = get();
    if (isRefreshing) return;

    set({ isRefreshing: true, error: undefined });

    try {
      if (config.useMockData) {
        // Simulate API call with mock data
        await new Promise(resolve => setTimeout(resolve, 500));
        set({ isRefreshing: false });
        return;
      }

      // Fetch all data from API
      await Promise.all([
        get().fetchModels(),
        get().fetchDeployments(),
        get().fetchGpus(),
        get().fetchApiKeys(),
        get().fetchStats(),
      ]);

      set({ isRefreshing: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to refresh data',
        isRefreshing: false,
      });
    }
  },

  // Fetch models
  fetchModels: async () => {
    if (config.useMockData) {
      set({ models: mockModels });
      return;
    }

    try {
      const response = await api.get(apiEndpoints.listModels);
      set({ models: response.data || [] });
    } catch (error) {
      console.error('Failed to fetch models:', error);
      throw error;
    }
  },

  // Fetch deployments
  fetchDeployments: async () => {
    if (config.useMockData) {
      set({ deployments: mockDeployments });
      return;
    }

    try {
      const response = await api.get(apiEndpoints.listDeployments);
      set({ deployments: response.data || [] });
    } catch (error) {
      console.error('Failed to fetch deployments:', error);
      throw error;
    }
  },

  // Fetch GPUs
  fetchGpus: async () => {
    if (config.useMockData) {
      set({ gpus: mockGPUs });
      return;
    }

    try {
      const response = await api.get(apiEndpoints.listGpus);
      set({ gpus: response.data || [] });
    } catch (error) {
      console.error('Failed to fetch GPUs:', error);
      throw error;
    }
  },

  // Fetch API keys
  fetchApiKeys: async () => {
    if (config.useMockData) {
      set({ apiKeys: mockApiKeys });
      return;
    }

    try {
      const response = await api.get(apiEndpoints.listApiKeys);
      set({ apiKeys: response.data || [] });
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
      throw error;
    }
  },

  // Fetch usage logs
  fetchUsageLogs: async () => {
    if (config.useMockData) {
      set({ usageLogs: mockUsageLogs });
      return;
    }

    try {
      const response = await api.get(apiEndpoints.listUsageLogs);
      set({ usageLogs: response.data || [] });
    } catch (error) {
      console.error('Failed to fetch usage logs:', error);
      throw error;
    }
  },

  // Fetch statistics
  fetchStats: async () => {
    if (config.useMockData) {
      set({ stats: dashboardStats });
      return;
    }

    try {
      const response = await api.get(apiEndpoints.getStats);
      set({ stats: response.data || dashboardStats });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      throw error;
    }
  },

  // Add model
  addModel: async (modelData) => {
    set({ isLoading: true, error: undefined });

    try {
      if (config.useMockData) {
        await new Promise(resolve => setTimeout(resolve, 800));
        const newModel: Model = {
          ...modelData,
          id: `model_${Date.now()}`,
          created_at: new Date().toISOString(),
        };
        set(state => ({ models: [...state.models, newModel], isLoading: false }));
        return;
      }

      // Real API call
      const response = await api.post(apiEndpoints.createModel, modelData);
      set(state => ({
        models: [...state.models, response.data],
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to add model',
        isLoading: false,
      });
    }
  },

  // Delete model
  deleteModel: async (id) => {
    set({ isLoading: true, error: undefined });

    try {
      if (config.useMockData) {
        await new Promise(resolve => setTimeout(resolve, 500));
        set(state => ({
          models: state.models.filter(m => String(m.id) !== String(id)),
          isLoading: false,
        }));
        return;
      }

      // Real API call
      await api.delete(apiEndpoints.deleteModel(Number(id)));
      set(state => ({
        models: state.models.filter(m => String(m.id) !== String(id)),
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete model',
        isLoading: false,
      });
    }
  },

  // Create deployment
  createDeployment: async (deploymentData) => {
    set({ isLoading: true, error: undefined });

    try {
      if (config.useMockData) {
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
        return;
      }

      // Real API call
      const response = await api.post(apiEndpoints.createDeployment, deploymentData);
      set(state => ({
        deployments: [...state.deployments, response.data],
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create deployment',
        isLoading: false,
      });
    }
  },

  // Stop deployment
  stopDeployment: async (id) => {
    set({ isLoading: true, error: undefined });

    try {
      if (config.useMockData) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        set(state => ({
          deployments: state.deployments.map(d =>
            String(d.id) === String(id)
              ? { ...d, status: 'stopped' as const, qps: 0, latency_ms: 0 }
              : d
          ),
          isLoading: false,
        }));
        return;
      }

      // Real API call
      await api.post(apiEndpoints.stopDeployment(Number(id)));
      set(state => ({
        deployments: state.deployments.map(d =>
          String(d.id) === String(id) ? { ...d, status: 'stopped' as const } : d
        ),
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to stop deployment',
        isLoading: false,
      });
    }
  },

  // Create API key
  createApiKey: async (keyData) => {
    set({ isLoading: true, error: undefined });

    try {
      if (config.useMockData) {
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
        return;
      }

      // Real API call
      const response = await api.post(apiEndpoints.createApiKey, keyData);
      set(state => ({
        apiKeys: [...state.apiKeys, response.data],
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create API key',
        isLoading: false,
      });
    }
  },

  // Delete API key
  deleteApiKey: async (id) => {
    set({ isLoading: true, error: undefined });

    try {
      if (config.useMockData) {
        await new Promise(resolve => setTimeout(resolve, 500));
        set(state => ({
          apiKeys: state.apiKeys.filter(k => String(k.id) !== String(id)),
          isLoading: false,
        }));
        return;
      }

      // Real API call
      await api.delete(apiEndpoints.deleteApiKey(Number(id)));
      set(state => ({
        apiKeys: state.apiKeys.filter(k => String(k.id) !== String(id)),
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete API key',
        isLoading: false,
      });
    }
  },

  // Toggle API key
  toggleApiKey: async (id) => {
    set({ isLoading: true, error: undefined });

    try {
      if (config.useMockData) {
        await new Promise(resolve => setTimeout(resolve, 300));
        set(state => ({
          apiKeys: state.apiKeys.map(k =>
            String(k.id) === String(id) ? { ...k, is_active: !k.is_active } : k
          ),
          isLoading: false,
        }));
        return;
      }

      // Real API call
      await api.post(apiEndpoints.toggleApiKey(Number(id)));
      set(state => ({
        apiKeys: state.apiKeys.map(k =>
          String(k.id) === String(id) ? { ...k, is_active: !k.is_active } : k
        ),
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to toggle API key',
        isLoading: false,
      });
    }
  },
}));

export default useStore;

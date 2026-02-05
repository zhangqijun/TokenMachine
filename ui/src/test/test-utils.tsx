/**
 * Test utility functions and components.
 */
import type { ReactElement } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, theme, App } from 'antd'
import { vi } from 'vitest'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
})

// Mock store
const mockStore = {
  deployments: {
    items: [],
    loading: false,
    error: null,
  },
  models: {
    items: [],
    loading: false,
    error: null,
  },
  gpus: {
    items: [],
    loading: false,
    error: null,
  },
  apiKeys: {
    items: [],
    loading: false,
    error: null,
  },
}

interface AllTheProvidersProps {
  children: React.ReactNode
}

function AllTheProviders({ children }: AllTheProvidersProps) {
  return (
    <BrowserRouter>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: '#1677ff',
          },
        }}
      >
        <App>{children}</App>
      </ConfigProvider>
    </BrowserRouter>
  )
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  wrapper?: React.ComponentType
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <AllTheProviders>{children}</AllTheProviders>
  }

  return render(ui, { wrapper: Wrapper, ...options })
}

// Re-export everything from React Testing Library
export * from '@testing-library/react'
export { renderWithProviders as render }

// Mock data generators
export const mockDeployment = (overrides = {}) => ({
  id: 1,
  model_id: 1,
  name: 'llama-3-8b-deployment',
  status: 'running',
  replicas: 1,
  gpu_ids: ['gpu:0'],
  backend: 'vllm',
  config: {
    tensor_parallel_size: 1,
    max_model_len: 4096,
    gpu_memory_utilization: 0.9,
  },
  health_status: {
    '0': { healthy: true, endpoint: 'http://localhost:8001' },
  },
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  model: {
    id: 1,
    name: 'meta-llama/Llama-3-8B-Instruct',
    version: 'v1.0.0',
    category: 'llm',
    status: 'ready',
  },
  ...overrides,
})

export const mockModel = (overrides = {}) => ({
  id: 1,
  name: 'meta-llama/Llama-3-8B-Instruct',
  version: 'v1.0.0',
  source: 'huggingface',
  category: 'llm',
  path: '/var/lib/inferx/models/llama-3-8b',
  size_gb: 16.0,
  status: 'ready',
  download_progress: 100,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

export const mockGPU = (overrides = {}) => ({
  id: 'gpu:0',
  name: 'NVIDIA GeForce RTX 4090',
  memory_total_mb: 24576,
  memory_free_mb: 24576,
  memory_used_mb: 0,
  utilization_percent: 0,
  temperature_celsius: 30,
  status: 'available',
  deployment_id: null,
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

export const mockApiKey = (overrides = {}) => ({
  id: 1,
  key_prefix: 'inferx_sk_abc1',
  name: 'Test API Key',
  quota_tokens: 10000000,
  tokens_used: 0,
  is_active: true,
  expires_at: null,
  last_used_at: null,
  created_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

// Mock fetch wrapper
export function mockFetch(response: any, ok = true) {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok,
      json: () => Promise.resolve(response),
    } as Response)
  )
}

// Mock fetch error
export function mockFetchError(status = 500, message = 'Internal Server Error') {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({ error: message }),
    } as Response)
  )
}

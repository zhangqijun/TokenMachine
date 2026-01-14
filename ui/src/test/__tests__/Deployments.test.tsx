/**
 * Tests for Deployments page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { render } from '../test-utils'
import Deployments from '@/pages/Deployments'

const mockDeployments = [
  {
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
    },
    health_status: {
      '0': { healthy: true, endpoint: 'http://localhost:8001' },
    },
    created_at: '2024-01-01T00:00:00Z',
    model: {
      id: 1,
      name: 'meta-llama/Llama-3-8B-Instruct',
      version: 'v1.0.0',
    },
  },
  {
    id: 2,
    model_id: 2,
    name: 'mistral-7b-deployment',
    status: 'stopped',
    replicas: 1,
    gpu_ids: ['gpu:1'],
    backend: 'vllm',
    config: {},
    health_status: null,
    created_at: '2024-01-01T00:00:00Z',
    model: {
      id: 2,
      name: 'mistralai/Mistral-7B-Instruct',
      version: 'v0.2.0',
    },
  },
]

function mockDeploymentsApi() {
  global.fetch = vi.fn((url) => {
    const urlStr = typeof url === 'string' ? url : String(url)
    if (urlStr.includes('/deployments')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: mockDeployments }),
      } as Response)
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response)
  })
}

describe('Deployments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the deployments page', () => {
    mockDeploymentsApi()
    render(<Deployments />)

    expect(screen.getByText(/deployments/i)).toBeInTheDocument()
  })

  it('displays list of deployments', async () => {
    mockDeploymentsApi()
    render(<Deployments />)

    await waitFor(() => {
      expect(screen.getByText('llama-3-8b-deployment')).toBeInTheDocument()
      expect(screen.getByText('mistral-7b-deployment')).toBeInTheDocument()
    })
  })

  it('shows deployment status badges', async () => {
    mockDeploymentsApi()
    render(<Deployments />)

    await waitFor(() => {
      expect(screen.getByText(/running/i)).toBeInTheDocument()
      expect(screen.getByText(/stopped/i)).toBeInTheDocument()
    })
  })

  it('opens create deployment modal when button clicked', async () => {
    mockDeploymentsApi()
    render(<Deployments />)

    const createButton = screen.getByText(/create/i, { selector: 'button' })
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText(/new deployment/i)).toBeInTheDocument()
    })
  })

  it('displays deployment details', async () => {
    mockDeploymentsApi()
    render(<Deployments />)

    await waitFor(() => {
      expect(screen.getByText('meta-llama/Llama-3-8B-Instruct')).toBeInTheDocument()
      expect(screen.getByText('vllm')).toBeInTheDocument()
    })
  })

  it('handles empty deployment list', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: [] }),
      } as Response)
    )

    render(<Deployments />)

    expect(await screen.findByText(/no deployments/i)).toBeInTheDocument()
  })
})

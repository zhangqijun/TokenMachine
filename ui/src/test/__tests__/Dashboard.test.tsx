/**
 * Tests for Dashboard page.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '../test-utils'
import Dashboard from '@/pages/Dashboard'

// Mock API calls
const mockStatsResponse = {
  gpu_total: 4,
  gpu_used: 2,
  gpu_available: 2,
  models_total: 5,
  models_ready: 3,
  deployments_total: 2,
  deployments_running: 2,
  api_keys_total: 10,
  api_keys_active: 8,
}

function mockDashboardApi() {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockStatsResponse),
    } as Response)
  )
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the dashboard page', () => {
    mockDashboardApi()
    render(<Dashboard />)

    expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
  })

  it('displays system statistics', async () => {
    mockDashboardApi()
    render(<Dashboard />)

    // Wait for data to load
    expect(await screen.findByText(/4/)).toBeInTheDocument()
  })

  it('shows GPU statistics card', async () => {
    mockDashboardApi()
    render(<Dashboard />)

    expect(await screen.findByText(/gpu/i)).toBeInTheDocument()
  })

  it('shows models statistics card', async () => {
    mockDashboardApi()
    render(<Dashboard />)

    expect(await screen.findByText(/models/i)).toBeInTheDocument()
  })

  it('shows deployments statistics card', async () => {
    mockDashboardApi()
    render(<Dashboard />)

    expect(await screen.findByText(/deployments/i)).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ error: 'Server error' }),
      } as Response)
    )

    render(<Dashboard />)

    // Should show error state or empty state
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
  })
})

/**
 * Tests for MainLayout component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '../test-utils'
import MainLayout from '@/components/layout/MainLayout'

// Mock the router
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: '/' }),
    Outlet: () => <div data-testid="outlet-content">Outlet Content</div>,
  }
})

// Mock the logo
vi.mock('@/assets/react.svg', () => ({
  default: 'mock-logo.svg',
}))

describe('MainLayout', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
  })

  it('renders the layout', () => {
    render(<MainLayout />)

    expect(screen.getByTestId('outlet-content')).toBeInTheDocument()
  })

  it('renders the header with logo', () => {
    render(<MainLayout />)

    expect(screen.getByText(/TokenMachine/i)).toBeInTheDocument()
  })

  it('renders navigation menu items', () => {
    render(<MainLayout />)

    // Check for common navigation items
    expect(screen.getByText(/仪表盘/i)).toBeInTheDocument()
    expect(screen.getByText(/部署管理/i)).toBeInTheDocument()
    expect(screen.getByText(/模型管理/i)).toBeInTheDocument()
  })

  it('navigates when clicking menu items', () => {
    render(<MainLayout />)

    const deploymentsLink = screen.getByText(/部署管理/i)
    deploymentsLink.click()

    // Navigation should be triggered
    expect(mockNavigate).toHaveBeenCalled()
  })
})

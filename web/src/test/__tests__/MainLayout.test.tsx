/**
 * Tests for MainLayout component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '../test-utils'
import { MainLayout } from '@/components/layout/MainLayout'

// Mock the router
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: '/' }),
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

  it('renders the layout with children', () => {
    render(
      <MainLayout>
        <div data-testid="test-children">Test Content</div>
      </MainLayout>
    )

    expect(screen.getByTestId('test-children')).toBeInTheDocument()
  })

  it('renders the header with logo', () => {
    render(
      <MainLayout>
        <div>Content</div>
      </MainLayout>
    )

    const logo = screen.getByAltText(/logo/i) ?? screen.getByRole('img')
    expect(logo).toBeInTheDocument()
  })

  it('renders navigation menu items', () => {
    render(
      <MainLayout>
        <div>Content</div>
      </MainLayout>
    )

    // Check for common navigation items
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
    expect(screen.getByText(/deployments/i)).toBeInTheDocument()
    expect(screen.getByText(/models/i)).toBeInTheDocument()
  })

  it('navigates when clicking menu items', () => {
    render(
      <MainLayout>
        <div>Content</div>
      </MainLayout>
    )

    const deploymentsLink = screen.getByText(/deployments/i)
    deploymentsLink.click()

    // Navigation should be triggered
    expect(mockNavigate).toHaveBeenCalled()
  })
})

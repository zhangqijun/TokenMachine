/**
 * Isolated component tests to find the issue
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { screen, render } from '@testing-library/react'
import { render as testRender } from '../test-utils'
import ViewToggle from '@/pages/models/components/ViewToggle'
import SearchBar from '@/pages/models/components/SearchBar'
import SortDropdown from '@/pages/models/components/SortDropdown'

describe('Models Components - Isolated Tests', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
  })

  describe('ViewToggle', () => {
    it('renders correctly', () => {
      const handleChange = () => {}
      render(<ViewToggle value="card" onChange={handleChange} />)

      expect(screen.getByText('卡片视图')).toBeInTheDocument()
    })

    it('renders list view button', () => {
      const handleChange = () => {}
      render(<ViewToggle value="list" onChange={handleChange} />)

      expect(screen.getByText('列表视图')).toBeInTheDocument()
    })
  })

  describe('SearchBar', () => {
    it('renders correctly', () => {
      const handleChange = () => {}
      render(<SearchBar value="" onChange={handleChange} />)

      const input = screen.getByPlaceholderText('输入模型名称、ID或标签搜索...')
      expect(input).toBeInTheDocument()
    })

    it('renders with custom placeholder', () => {
      const handleChange = () => {}
      render(<SearchBar value="" onChange={handleChange} placeholder="Search..." />)

      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
    })
  })

  describe('SortDropdown', () => {
    it('renders correctly', () => {
      const handleChange = () => {}
      render(<SortDropdown field="name" order="asc" onChange={handleChange} />)

      expect(screen.getByText('名称')).toBeInTheDocument()
    })

    it('renders with default sort', () => {
      const handleChange = () => {}
      render(<SortDropdown field="default" order="asc" onChange={handleChange} />)

      expect(screen.getByText('默认排序')).toBeInTheDocument()
    })
  })
})

/**
 * Test hooks directly to see what they return
 */
import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useViewModel, useModelSearch, useModelFilter, useModelSort } from '@/pages/models/hooks'

describe('Models Hooks - Direct Tests', () => {
  describe('useViewModel', () => {
    it('returns correct values', () => {
      const { result } = renderHook(() => useViewModel())

      console.log('useViewModel result:', result.current)

      expect(result.current.viewMode).toBeDefined()
      expect(result.current.viewPreferences).toBeDefined()
      expect(result.current.setViewMode).toBeInstanceOf(Function)
    })
  })

  describe('useModelSearch', () => {
    it('returns correct values', () => {
      const { result } = renderHook(() => useModelSearch())

      console.log('useModelSearch result:', result.current)

      expect(result.current.keyword).toBeDefined()
      expect(result.current.setKeyword).toBeInstanceOf(Function)
      expect(result.current.filterModels).toBeInstanceOf(Function)
    })

    it('filterModels works correctly', () => {
      const { result } = renderHook(() => useModelSearch())

      const mockModels = [
        { name: 'Llama-2-7b', id: '1', tags: ['vision'] },
        { name: 'Qwen-14b', id: '2', tags: ['moe'] },
      ]

      const filtered = result.current.filterModels(mockModels)
      console.log('filterModels result (no keyword):', filtered)

      expect(filtered).toEqual(mockModels)
    })
  })

  describe('useModelFilter', () => {
    it('returns correct values', () => {
      const { result } = renderHook(() => useModelFilter())

      console.log('useModelFilter result:', result.current)

      expect(result.current.filters).toBeDefined()
      expect(result.current.setFilters).toBeInstanceOf(Function)
      expect(result.current.filterModels).toBeInstanceOf(Function)
    })
  })

  describe('useModelSort', () => {
    it('returns correct values', () => {
      const { result } = renderHook(() => useModelSort())

      console.log('useModelSort result:', result.current)

      expect(result.current.field).toBeDefined()
      expect(result.current.order).toBeDefined()
      expect(result.current.setSort).toBeInstanceOf(Function)
      expect(result.current.sortModels).toBeInstanceOf(Function)
    })

    it('sortModels works correctly', () => {
      const { result } = renderHook(() => useModelSort())

      const mockModels = [
        { name: 'Zebra', id: '3' },
        { name: 'Apple', id: '1' },
        { name: 'Mango', id: '2' },
      ]

      const sorted = result.current.sortModels(mockModels)
      console.log('sortModels result:', sorted)

      expect(sorted[0].name).toBe('Apple')
      expect(sorted[1].name).toBe('Mango')
      expect(sorted[2].name).toBe('Zebra')
    })
  })
})

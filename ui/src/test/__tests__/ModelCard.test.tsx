/**
 * Test ModelCard component directly
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { render as testRender } from '../test-utils'
import ModelCard from '@/pages/models/components/ModelCard'
import type { ModelData } from '@/pages/models/components'

describe('ModelCard Component', () => {
  const mockModel: ModelData = {
    id: '1',
    name: 'Llama-2-7b-chat-hf',
    type: 'chat',
    creator: 'Meta',
    size: '7B',
    quantization: 'fp16',
    tags: ['vision', 'inference'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'running',
    deploymentName: 'llama-2-7b-prod',
    instances: [
      {
        id: '1-1',
        name: 'llama-2-7b-prod',
        worker: 'worker-1',
        gpuMemory: 12.5,
        gpuMemoryTotal: 16,
        tps: 125,
      },
    ],
    createdAt: '2024-01-15T10:30:00Z',
  }

  it('renders model name', () => {
    const handleDeploy = () => {}
    const handleChat = () => {}
    const handleLogs = () => {}
    const handleDelete = () => {}
    const handleDownload = () => {}
    const handleScale = () => {}
    const handleStop = () => {}

    render(
      <ModelCard
        model={mockModel}
        onDeploy={handleDeploy}
        onChat={handleChat}
        onLogs={handleLogs}
        onDelete={handleDelete}
        onDownload={handleDownload}
        onScale={handleScale}
        onStop={handleStop}
      />
    )

    expect(screen.getByText('Llama-2-7b-chat-hf')).toBeInTheDocument()
  })

  it('renders model tags', () => {
    const handlers = {
      onDeploy: () => {},
      onChat: () => {},
      onLogs: () => {},
      onDelete: () => {},
      onDownload: () => {},
      onScale: () => {},
      onStop: () => {},
    }

    render(<ModelCard model={mockModel} {...handlers} />)

    expect(screen.getByText('vision')).toBeInTheDocument()
    expect(screen.getByText('inference')).toBeInTheDocument()
  })

  it('renders deployment status', () => {
    const handlers = {
      onDeploy: () => {},
      onChat: () => {},
      onLogs: () => {},
      onDelete: () => {},
      onDownload: () => {},
      onScale: () => {},
      onStop: () => {},
    }

    render(<ModelCard model={mockModel} {...handlers} />)

    // Check for running status
    const statusElements = screen.getAllByText('运行中')
    expect(statusElements.length).toBeGreaterThan(0)
  })

  it('renders action buttons', () => {
    const handlers = {
      onDeploy: () => {},
      onChat: () => {},
      onLogs: () => {},
      onDelete: () => {},
      onDownload: () => {},
      onScale: () => {},
      onStop: () => {},
    }

    render(<ModelCard model={mockModel} {...handlers} />)

    // Check for some action buttons
    expect(screen.getByText('聊天')).toBeInTheDocument()
  })
})

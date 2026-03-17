import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Row, Col, Button, message, Divider } from 'antd';
import {
  ReloadOutlined,
} from '@ant-design/icons';
import ModelCardSimple from './models/components/ModelCardSimple';
import type { ModelData } from './models/components';

// Mock data - TODO: 替换为真实 API 调用
// 保留 DeepSeek、GLM、Kimi、MiniMax 系列模型
const mockModelsData: ModelData[] = [
  // DeepSeek 系列
  {
    id: 'ds-v3',
    name: 'DeepSeek-V3',
    type: 'chat',
    creator: 'DeepSeek',
    size: '685B',
    quantization: 'fp16',
    tags: ['chat', 'reasoning', 'moe'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2025-01-10T00:00:00Z',
    description: 'DeepSeek 第三代大模型，强大的推理能力',
  },
  {
    id: 'ds-r1',
    name: 'DeepSeek-R1',
    type: 'chat',
    creator: 'DeepSeek',
    size: '671B',
    quantization: 'fp16',
    tags: ['chat', 'reasoning'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2025-02-01T00:00:00Z',
    description: 'DeepSeek 推理增强模型',
  },
  {
    id: 'ds-coder-33b',
    name: 'DeepSeek-Coder-33B',
    type: 'chat',
    creator: 'DeepSeek',
    size: '33B',
    quantization: 'int4',
    tags: ['coder', 'programming'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-20T14:20:00Z',
    description: '专为代码生成优化的模型',
  },
  {
    id: 'ds-v2-236b',
    name: 'DeepSeek-V2-236B',
    type: 'chat',
    creator: 'DeepSeek',
    size: '236B',
    quantization: 'int4',
    tags: ['moe', 'coder'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'running',
    deploymentName: 'deepseek-v2-prod',
    instances: [
      {
        id: 'ds-v2-1',
        name: 'deepseek-v2-prod',
        worker: 'worker-1',
        gpuMemory: 15.8,
        gpuMemoryTotal: 16,
        tps: 12,
      },
    ],
    createdAt: '2024-01-17T10:00:00Z',
    description: 'DeepSeek 第二代 MoE 架构模型',
  },

  // GLM 系列
  {
    id: 'glm-4-9b',
    name: 'GLM-4-9B',
    type: 'chat',
    creator: '智谱AI',
    size: '9B',
    quantization: 'fp16',
    tags: ['chat', 'chinese'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-06-01T00:00:00Z',
    description: '智谱 GLM-4 系列 9B 参数模型',
  },
  {
    id: 'chatglm-6b',
    name: 'ChatGLM-6B',
    type: 'chat',
    creator: '智谱AI',
    size: '6B',
    quantization: 'int8',
    tags: ['chinese', 'chat'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-08T11:30:00Z',
    description: '开源中英双语对话模型',
  },
  {
    id: 'glm-4-9b-chat',
    name: 'GLM-4-9B-Chat',
    type: 'chat',
    creator: '智谱AI',
    size: '9B',
    quantization: 'int4',
    tags: ['chat', 'chinese'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-06-01T00:00:00Z',
    description: 'GLM-4 对话优化版本',
  },

  // Kimi 系列 (Moonshot)
  {
    id: 'kimi-moonshot-v1-8b',
    name: 'Kimi-Moonshot-v1-8B',
    type: 'chat',
    creator: 'Moonshot AI',
    size: '8B',
    quantization: 'fp16',
    tags: ['chat', 'long-context'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-03-01T00:00:00Z',
    description: 'Moonshot Kimi 长上下文模型',
  },
  {
    id: 'kimi-moonshot-v1-32b',
    name: 'Kimi-Moonshot-v1-32B',
    type: 'chat',
    creator: 'Moonshot AI',
    size: '32B',
    quantization: 'int4',
    tags: ['chat', 'long-context'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-03-01T00:00:00Z',
    description: 'Kimi 32B 长上下文对话模型',
  },

  // MiniMax 系列
  {
    id: 'minimax-abab-6.5-chat',
    name: 'MiniMax-ABAB-6.5-Chat',
    type: 'chat',
    creator: 'MiniMax',
    size: '7B',
    quantization: 'fp16',
    tags: ['chat', 'multimodal'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-04-01T00:00:00Z',
    description: 'MiniMax ABAB 6.5 对话模型',
  },
  {
    id: 'minimax-abab-6.5s-chat',
    name: 'MiniMax-ABAB-6.5S-Chat',
    type: 'chat',
    creator: 'MiniMax',
    size: '13B',
    quantization: 'int8',
    tags: ['chat', 'multimodal'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'running',
    deploymentName: 'minimax-chat-prod',
    instances: [
      {
        id: 'mm-1',
        name: 'minimax-chat-prod',
        worker: 'worker-2',
        gpuMemory: 14.5,
        gpuMemoryTotal: 16,
        tps: 85,
      },
    ],
    createdAt: '2024-04-15T00:00:00Z',
    description: 'MiniMax ABAB 6.5S 高性能对话模型',
  },
];

const Models = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [allModels, setAllModels] = useState<ModelData[]>(mockModelsData);
  const [downloadModalVisible, setDownloadModalVisible] = useState(false);
  const [deployModalVisible, setDeployModalVisible] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelData | null>(null);
  const [selectedDeployType, setSelectedDeployType] = useState<'cpu' | 'gpu'>('gpu');

  // 按厂商分组
  const groupedModels = {
    'DeepSeek': allModels.filter(m => m.creator === 'DeepSeek'),
    '智谱AI': allModels.filter(m => m.creator === '智谱AI'),
    'Moonshot AI': allModels.filter(m => m.creator === 'Moonshot AI'),
    'MiniMax': allModels.filter(m => m.creator === 'MiniMax'),
  };

  const loadModels = async () => {
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
      message.success('刷新成功');
    } catch (error) {
      message.error('加载模型列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const handleDownload = (model: ModelData) => {
    setSelectedModel(model);
    setDownloadModalVisible(true);
  };

  const handleDeploy = (model: ModelData, deployType: 'cpu' | 'gpu') => {
    setSelectedModel(model);
    setSelectedDeployType(deployType);
    setDeployModalVisible(true);
  };

  const confirmDownload = async () => {
    if (!selectedModel) return;

    try {
      message.success(`开始下载模型 "${selectedModel.name}"`);
      setDownloadModalVisible(false);

      // 模拟下载
      setAllModels(prev =>
        prev.map(m =>
          m.id === selectedModel.id
            ? { ...m, downloadStatus: 'downloading' as const }
            : m
        )
      );

      setTimeout(() => {
        setAllModels(prev =>
          prev.map(m =>
            m.id === selectedModel.id
              ? { ...m, downloadStatus: 'downloaded' as const }
              : m
          )
        );
        message.success(`模型 "${selectedModel.name}" 下载完成`);
      }, 3000);
    } catch (error: any) {
      message.error(`下载失败: ${error.message || '未知错误'}`);
    } finally {
      setSelectedModel(null);
    }
  };

  const confirmDeploy = async () => {
    if (!selectedModel) return;

    try {
      const deploymentName = `${selectedModel.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}-prod`;
      message.success(
        `开始${selectedDeployType.toUpperCase()}部署模型 "${selectedModel.name}" (部署名称: ${deploymentName})`
      );
      setDeployModalVisible(false);

      // 模拟部署
      setAllModels(prev =>
        prev.map(m =>
          m.id === selectedModel.id
            ? {
                ...m,
                deploymentStatus: 'running' as const,
                deploymentName,
                instances: [
                  {
                    id: `${m.id}-inst-1`,
                    name: deploymentName,
                    worker: 'worker-1',
                    gpuMemory: selectedDeployType === 'gpu' ? 14.5 : 2.0,
                    gpuMemoryTotal: selectedDeployType === 'gpu' ? 16 : 4,
                    tps: selectedDeployType === 'gpu' ? 80 : 20,
                  },
                ],
              }
            : m
        )
      );
    } catch (error: any) {
      message.error(`部署失败: ${error.message || '未知错误'}`);
    } finally {
      setSelectedModel(null);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>模型中心</h1>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadModels}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      {/* Model Groups */}
      {Object.entries(groupedModels).map(([creator, models]) => (
        models.length > 0 && (
          <div key={creator} style={{ marginBottom: 32 }}>
            <Divider orientation="left" style={{ fontSize: 18, fontWeight: 600, margin: '24px 0 16px' }}>
              {creator} 系列
            </Divider>
            <Row gutter={[16, 16]}>
              {models.map((model) => (
                <Col xs={24} sm={12} md={8} lg={6} xl={6} key={model.id}>
                  <ModelCardSimple
                    model={model}
                    onDownload={handleDownload}
                    onDeploy={handleDeploy}
                  />
                </Col>
              ))}
            </Row>
          </div>
        )
      ))}

      {/* Download Modal - Simple confirm */}
      {downloadModalVisible && selectedModel && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setDownloadModalVisible(false)}
        >
          <div
            style={{
              background: '#fff',
              padding: 24,
              borderRadius: 8,
              minWidth: 400,
              maxWidth: 500,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>确认下载模型</h3>
            <p style={{ marginBottom: 24 }}>
              即将下载模型 <strong>{selectedModel.name}</strong> ({selectedModel.size})，确认继续吗？
            </p>
            <div style={{ textAlign: 'right' }}>
              <Button style={{ marginRight: 8 }} onClick={() => setDownloadModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" onClick={confirmDownload}>
                确认下载
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Deploy Modal - Simple confirm */}
      {deployModalVisible && selectedModel && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setDeployModalVisible(false)}
        >
          <div
            style={{
              background: '#fff',
              padding: 24,
              borderRadius: 8,
              minWidth: 400,
              maxWidth: 500,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>确认部署模型</h3>
            <p style={{ marginBottom: 24 }}>
              即将{selectedDeployType.toUpperCase()}部署模型 <strong>{selectedModel.name}</strong>，确认继续吗？
            </p>
            <div style={{ textAlign: 'right' }}>
              <Button style={{ marginRight: 8 }} onClick={() => setDeployModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" onClick={confirmDeploy}>
                确认部署
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Models;

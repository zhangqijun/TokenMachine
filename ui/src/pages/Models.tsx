import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Row, Col, Button, Space, Empty, message } from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import {
  ViewToggle,
  SearchBar,
  FilterPanel,
  SortDropdown,
  ModelCard,
  ModelList,
  DeployModal,
  AddNewModelModal,
  DownloadModal,
  ScaleModal,
  LogsModal,
  StopModal,
  DeleteConfirmDialog,
} from './models/components';
import type { ModelData } from './models/components';
import type { DownloadConfig } from './models/components';
import type { NewModelInfo } from './models/components';
import {
  useViewModel,
  useModelSearch,
  useModelFilter,
  useModelSort,
  useModelActions,
} from './models/hooks';

// Mock data - TODO: 替换为真实 API 调用
const mockModelsData: ModelData[] = [
  {
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
      {
        id: '1-2',
        name: 'llama-2-7b-prod-2',
        worker: 'worker-2',
        gpuMemory: 14.2,
        gpuMemoryTotal: 16,
        tps: 110,
      },
    ],
    createdAt: '2024-01-15T10:30:00Z',
  },
  {
    id: '2',
    name: 'Qwen-14b-chat',
    type: 'chat',
    creator: 'Alibaba',
    size: '14B',
    quantization: 'int8',
    tags: ['moe', 'tools'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-10T08:00:00Z',
  },
  {
    id: '3',
    name: 'DeepSeek-Coder-33b',
    type: 'chat',
    creator: 'DeepSeek',
    size: '33B',
    quantization: 'int4',
    tags: ['coder'],
    downloadStatus: 'downloading',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-20T14:20:00Z',
  },
  {
    id: '4',
    name: 'Qwen-72b-chat',
    type: 'chat',
    creator: 'Alibaba',
    size: '72B',
    quantization: 'int4',
    tags: ['moe', 'tools'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'running',
    deploymentName: 'qwen-72b-prod',
    instances: [
      {
        id: '4-1',
        name: 'qwen-72b-prod',
        worker: 'worker-2',
        gpuMemory: 15.2,
        gpuMemoryTotal: 16,
        tps: 45,
      },
    ],
    createdAt: '2024-01-12T09:15:00Z',
  },
  {
    id: '5',
    name: 'ChatGLM-6b',
    type: 'chat',
    creator: '智谱',
    size: '6B',
    quantization: 'int8',
    tags: ['chinese'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-08T11:30:00Z',
  },
  {
    id: '6',
    name: 'Llama-3-70b-instruct',
    type: 'chat',
    creator: 'Meta',
    size: '70B',
    quantization: 'fp16',
    tags: ['inference', 'tools'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'running',
    deploymentName: 'llama-3-70b-prod',
    instances: [
      {
        id: '6-1',
        name: 'llama-3-70b-prod',
        worker: 'worker-1',
        gpuMemory: 14.8,
        gpuMemoryTotal: 16,
        tps: 38,
      },
      {
        id: '6-2',
        name: 'llama-3-70b-prod-2',
        worker: 'worker-1',
        gpuMemory: 15.5,
        gpuMemoryTotal: 16,
        tps: 35,
      },
      {
        id: '6-3',
        name: 'llama-3-70b-prod-3',
        worker: 'worker-2',
        gpuMemory: 15.1,
        gpuMemoryTotal: 16,
        tps: 36,
      },
    ],
    createdAt: '2024-01-18T16:45:00Z',
  },
  {
    id: '7',
    name: 'Mistral-7b-instruct',
    type: 'chat',
    creator: 'Mistral AI',
    size: '7B',
    quantization: 'fp16',
    tags: ['inference'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-05T10:20:00Z',
  },
  {
    id: '8',
    name: 'Yi-34b-chat',
    type: 'chat',
    creator: '01.AI',
    size: '34B',
    quantization: 'int4',
    tags: ['chinese', 'coder'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'stopping',
    deploymentName: 'yi-34b-test',
    workerName: 'worker-2',
    createdAt: '2024-01-14T13:50:00Z',
  },
  {
    id: '9',
    name: 'Baichuan2-13b-chat',
    type: 'chat',
    creator: '百川',
    size: '13B',
    quantization: 'int8',
    tags: ['chinese'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-07T08:40:00Z',
  },
  {
    id: '10',
    name: 'Phi-3-mini-4k',
    type: 'chat',
    creator: 'Microsoft',
    size: '3.8B',
    quantization: 'fp16',
    tags: ['inference', 'coder'],
    downloadStatus: 'downloaded',
    deploymentStatus: 'error',
    deploymentName: 'phi-3-test',
    createdAt: '2024-01-19T15:10:00Z',
  },
  {
    id: '11',
    name: 'Gemma-7b-instruct',
    type: 'chat',
    creator: 'Google',
    size: '7B',
    quantization: 'fp16',
    tags: ['inference'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-11T12:00:00Z',
  },
  {
    id: '12',
    name: 'InternLM-20b',
    type: 'chat',
    creator: '上海AI实验室',
    size: '20B',
    quantization: 'int8',
    tags: ['chinese', 'tools'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-09T14:30:00Z',
  },
  {
    id: '13',
    name: 'DeepSeek-V2-236b',
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
        id: '13-1',
        name: 'deepseek-v2-prod',
        worker: 'worker-1',
        gpuMemory: 15.8,
        gpuMemoryTotal: 16,
        tps: 12,
      },
    ],
    createdAt: '2024-01-17T10:00:00Z',
  },
  {
    id: '14',
    name: 'Qwen1.5-110b-chat',
    type: 'chat',
    creator: 'Alibaba',
    size: '110B',
    quantization: 'int4',
    tags: ['moe', 'tools'],
    downloadStatus: 'not_downloaded',
    deploymentStatus: 'not_deployed',
    createdAt: '2024-01-16T11:20:00Z',
  },
  {
    id: '15',
    name: 'StableLM-2-12b',
    type: 'chat',
    creator: 'Stability AI',
    size: '12B',
    quantization: 'fp16',
    tags: ['inference'],
    deploymentStatus: 'not_deployed',
    downloadStatus: 'not_downloaded',
    createdAt: '2024-01-13T09:50:00Z',
  },
  {
    id: '16',
    name: 'Solar-10.7b-instruct',
    type: 'chat',
    creator: 'Upstage',
    size: '10.7B',
    quantization: 'fp16',
    tags: ['inference'],
    deploymentStatus: 'not_deployed',
    downloadStatus: 'not_downloaded',
    createdAt: '2024-01-06T13:15:00Z',
  },
  {
    id: '17',
    name: 'OpenChat-3.5-7b',
    type: 'chat',
    creator: 'OpenChat',
    size: '7B',
    quantization: 'fp16',
    tags: ['inference', 'tools'],
    deploymentStatus: 'not_deployed',
    downloadStatus: 'not_downloaded',
    createdAt: '2024-01-04T10:40:00Z',
  },
  {
    id: '18',
    name: 'WizardLM-2-8x22b',
    type: 'chat',
    creator: 'Microsoft',
    size: '141B',
    quantization: 'int4',
    tags: ['moe', 'coder'],
    deploymentStatus: 'not_deployed',
    downloadStatus: 'not_downloaded',
    createdAt: '2024-01-15T15:25:00Z',
  },
  {
    id: '19',
    name: 'Vicuna-13b-v1.5',
    type: 'chat',
    creator: 'LMSYS',
    size: '13B',
    quantization: 'fp16',
    tags: ['inference'],
    deploymentStatus: 'not_deployed',
    downloadStatus: 'not_downloaded',
    createdAt: '2024-01-03T08:55:00Z',
  },
  {
    id: '20',
    name: 'CodeQwen-7b-chat',
    type: 'chat',
    creator: 'Alibaba',
    size: '7B',
    quantization: 'int8',
    tags: ['coder'],
    deploymentStatus: 'not_deployed',
    downloadStatus: 'not_downloaded',
    createdAt: '2024-01-12T14:10:00Z',
  },
];

const Models = () => {
  const navigate = useNavigate();

  // 视图管理
  const { viewMode, viewPreferences, setViewMode } = useViewModel();

  // 搜索
  const { keyword, setKeyword, filterModels: filterBySearch } = useModelSearch();

  // 筛选
  const { filters, setFilters, resetFilters, filterModels: filterByFilters } = useModelFilter();

  // 排序
  const { field, order, setSort, sortModels } = useModelSort();

  // 模型操作
  const {
    deployingModelId,
    stoppingModelId,
    deployModalVisible,
    selectedModelForDeploy,
    handleDeploy,
    handleStop,
    handleConfigure,
    handleLogs,
    handleDelete,
    confirmDeploy,
    confirmStop,
    confirmDelete,
    saveConfig,
    closeDeployModal,
  } = useModelActions();

  // Modal states
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [deleteConfirmVisible, setDeleteConfirmVisible] = useState(false);
  const [downloadModalVisible, setDownloadModalVisible] = useState(false);
  const [scaleModalVisible, setScaleModalVisible] = useState(false);
  const [stopModalVisible, setStopModalVisible] = useState(false);
  const [deployNewModelModalVisible, setDeployNewModelModalVisible] = useState(false);
  const [selectedModelForAction, setSelectedModelForAction] = useState<ModelData | null>(null);

  // 数据加载
  const [loading, setLoading] = useState(false);
  const [allModels, setAllModels] = useState<ModelData[]>(mockModelsData);

  // 加载模型列表
  const loadModels = async () => {
    setLoading(true);
    try {
      // TODO: 调用后端 API
      // const response = await fetch('/api/v1/models');
      // const data = await response.json();
      // setAllModels(data.models);

      // 模拟网络请求
      await new Promise((resolve) => setTimeout(resolve, 500));
      message.success('刷新成功');
    } catch (error) {
      console.error('Failed to load models:', error);
      message.error('加载模型列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadModels();
  }, []);

  // 组合所有过滤和排序逻辑
  const processedModels = useMemo(() => {
    let models = [...allModels];

    // 应用搜索过滤
    models = filterBySearch(models);

    // 应用筛选条件
    models = filterByFilters(models);

    // 应用排序
    models = sortModels(models);

    return models;
  }, [allModels, filterBySearch, filterByFilters, sortModels]);

  // 处理刷新
  const handleRefresh = () => {
    loadModels();
  };

  // 处理部署配置保存
  const handleSaveDeployConfig = (config: any) => {
    message.success('配置已保存');
    closeDeployModal();
  };

  // 处理日志查看
  const handleLogsClick = (model: ModelData) => {
    setSelectedModelForAction(model);
    setLogsModalVisible(true);
  };

  // 处理删除确认
  const handleDeleteClick = (model: ModelData) => {
    setSelectedModelForAction(model);
    setDeleteConfirmVisible(true);
  };

  // 确认删除
  const handleConfirmDelete = async (deleteFiles: boolean) => {
    if (!selectedModelForAction) return;
    await confirmDelete(deleteFiles);
    setDeleteConfirmVisible(false);
    setSelectedModelForAction(null);
  };

  // 下载日志
  const handleDownloadLogs = () => {
    message.info('下载日志功能');
  };

  // 处理下载
  const handleDownloadClick = (model: ModelData) => {
    setSelectedModelForAction(model);
    setDownloadModalVisible(true);
  };

  // 确认下载
  const handleConfirmDownload = async (config: DownloadConfig) => {
    if (!selectedModelForAction) return;

    try {
      // TODO: 调用后端 API 开始下载
      // const response = await fetch(`/api/v1/models/${selectedModelForAction.id}/download`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(config),
      // });
      // if (!response.ok) throw new Error('下载失败');

      // 模拟下载请求
      message.success(`开始下载模型 "${selectedModelForAction.name}"`);
      setDownloadModalVisible(false);

      // 模拟下载状态变化
      setTimeout(() => {
        setAllModels((prev) =>
          prev.map((m) =>
            m.id === selectedModelForAction.id
              ? { ...m, downloadStatus: 'downloading' }
              : m
          )
        );
      }, 500);

      setTimeout(() => {
        setAllModels((prev) =>
          prev.map((m) =>
            m.id === selectedModelForAction.id
              ? { ...m, downloadStatus: 'downloaded' }
              : m
          )
        );
        message.success(`模型 "${selectedModelForAction.name}" 下载完成`);
      }, 5000);
    } catch (error: any) {
      console.error('Download failed:', error);
      message.error(`下载失败: ${error.message || '未知错误'}`);
    } finally {
      setSelectedModelForAction(null);
    }
  };

  // 处理添加新模型
  const handleDeployNewModelClick = () => {
    setDeployNewModelModalVisible(true);
  };

  // 确认添加新模型
  const handleConfirmAddModel = async (modelInfo: NewModelInfo) => {
    try {
      // TODO: 调用后端 API 添加新模型
      // const response = await fetch('/api/v1/models/add', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(modelInfo),
      // });
      // if (!response.ok) throw new Error('添加失败');

      message.success(`成功添加模型 "${modelInfo.name}"`);
      setDeployNewModelModalVisible(false);

      // 模拟添加新模型到列表
      const newModel: ModelData = {
        id: `${Date.now()}`,
        name: modelInfo.name,
        type: modelInfo.type,
        creator: modelInfo.creator,
        size: modelInfo.size,
        quantization: modelInfo.quantization,
        tags: modelInfo.tags,
        downloadStatus: 'not_downloaded',
        deploymentStatus: 'not_deployed',
        createdAt: new Date().toISOString(),
      };
      setAllModels((prev) => [...prev, newModel]);
    } catch (error: any) {
      console.error('Add model failed:', error);
      message.error(`添加失败: ${error.message || '未知错误'}`);
    }
  };

  // 处理扩容
  const handleScaleClick = (model: ModelData) => {
    setSelectedModelForAction(model);
    setScaleModalVisible(true);
  };

  // 确认扩容
  const handleConfirmScale = async (config: any) => {
    if (!selectedModelForAction) return;

    try {
      // TODO: 调用后端 API 进行扩容
      // const response = await fetch(`/api/v1/models/${selectedModelForAction.id}/scale`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(config),
      // });
      // if (!response.ok) throw new Error('扩容失败');

      message.success(`模型 "${selectedModelForAction.name}" 开始扩容`);
      setScaleModalVisible(false);
    } catch (error: any) {
      console.error('Scale failed:', error);
      message.error(`扩容失败: ${error.message || '未知错误'}`);
    } finally {
      setSelectedModelForAction(null);
    }
  };

  // 处理停止
  const handleStopClick = (model: ModelData) => {
    setSelectedModelForAction(model);
    setStopModalVisible(true);
  };

  // 确认停止实例
  const handleConfirmStop = async (instanceId: string) => {
    if (!selectedModelForAction) return;

    try {
      // TODO: 调用后端 API 停止实例
      // const response = await fetch(`/api/v1/models/${selectedModelForAction.id}/instances/${instanceId}`, {
      //   method: 'POST',
      // });
      // if (!response.ok) throw new Error('停止失败');

      message.success('实例已停止');
      setStopModalVisible(false);

      // 更新实例列表（移除已停止的实例）
      setAllModels((prev) =>
        prev.map((m) =>
          m.id === selectedModelForAction.id
            ? {
                ...m,
                instances: m.instances?.filter((inst) => inst.id !== instanceId),
              }
            : m
        )
      );
    } catch (error: any) {
      console.error('Stop failed:', error);
      message.error(`停止失败: ${error.message || '未知错误'}`);
    } finally {
      setSelectedModelForAction(null);
    }
  };

  // 处理聊天
  const handleChatClick = (model: ModelData) => {
    // 跳转到测试场页面
    navigate(`/playground?model=${model.id}`);
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>模型中心</h2>
      </div>

      {/* First Row: Search and Actions */}
      <div
        style={{
          marginBottom: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <Space size="middle">
          <SearchBar
            value={keyword}
            onChange={setKeyword}
            placeholder="搜索模型名称、ID或标签..."
            style={{ width: 300 }}
          />
          <SortDropdown
            field={field}
            order={order}
            onChange={setSort}
          />
        </Space>

        <Space size="middle">
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={loading}
          >
            刷新
          </Button>
          <ViewToggle
            value={viewMode}
            onChange={setViewMode}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleDeployNewModelClick}
          >
            添加新模型
          </Button>
        </Space>
      </div>

      {/* Second Row: Filter Panel */}
      <div style={{ marginBottom: 16 }}>
        <FilterPanel
          value={filters}
          onChange={setFilters}
        />
      </div>

      {/* Content */}
      {processedModels.length === 0 ? (
        <Empty
          description="未找到匹配的模型"
          style={{ marginTop: 64 }}
        />
      ) : viewMode === 'card' ? (
        <Row gutter={[16, 16]}>
          {processedModels.map((model) => (
            <Col
              xs={24}
              sm={12}
              md={8}
              lg={24 / viewPreferences.cardColumns!}
              xl={24 / viewPreferences.cardColumns!}
              key={model.id}
            >
              <ModelCard
                model={model}
                onDeploy={handleDeploy}
                onChat={handleChatClick}
                onLogs={handleLogsClick}
                onDelete={handleDeleteClick}
                onDownload={handleDownloadClick}
                onScale={handleScaleClick}
                onStop={handleStopClick}
              />
            </Col>
          ))}
        </Row>
      ) : (
        <ModelList
          models={processedModels}
          onDeploy={handleDeploy}
          onChat={handleChatClick}
          onLogs={handleLogsClick}
          onDelete={handleDeleteClick}
          onDownload={handleDownloadClick}
          onScale={handleScaleClick}
          onStop={handleStopClick}
        />
      )}

      {/* Deploy Modal */}
      <DeployModal
        visible={deployModalVisible}
        model={selectedModelForDeploy}
        onCancel={closeDeployModal}
        onDeploy={confirmDeploy}
        onSaveConfig={handleSaveDeployConfig}
      />

      {/* Add New Model Modal */}
      <AddNewModelModal
        visible={deployNewModelModalVisible}
        onCancel={() => setDeployNewModelModalVisible(false)}
        onAdd={handleConfirmAddModel}
      />

      {/* Logs Modal */}
      <LogsModal
        visible={logsModalVisible}
        model={selectedModelForAction}
        onClose={() => {
          setLogsModalVisible(false);
          setSelectedModelForAction(null);
        }}
        onDownload={handleDownloadLogs}
      />

      {/* Download Modal */}
      <DownloadModal
        visible={downloadModalVisible}
        model={selectedModelForAction}
        onCancel={() => {
          setDownloadModalVisible(false);
          setSelectedModelForAction(null);
        }}
        onDownload={handleConfirmDownload}
      />

      {/* Scale Modal */}
      <ScaleModal
        visible={scaleModalVisible}
        model={selectedModelForAction}
        onCancel={() => {
          setScaleModalVisible(false);
          setSelectedModelForAction(null);
        }}
        onScale={handleConfirmScale}
      />

      {/* Stop Modal */}
      <StopModal
        visible={stopModalVisible}
        model={selectedModelForAction}
        onCancel={() => {
          setStopModalVisible(false);
          setSelectedModelForAction(null);
        }}
        onConfirm={handleConfirmStop}
      />

      {/* Delete Confirm Dialog */}
      <DeleteConfirmDialog
        visible={deleteConfirmVisible}
        model={selectedModelForAction}
        onCancel={() => {
          setDeleteConfirmVisible(false);
          setSelectedModelForAction(null);
        }}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
};

export default Models;

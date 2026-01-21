import { useState, useMemo, useEffect } from 'react';
import {
  Row,
  Col,
  Input,
  Button,
  Space,
  Tag,
  Select,
  message,
  Segmented,
  Dropdown,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  AppstoreOutlined,
  BarsOutlined,
  PlusOutlined,
  FilterOutlined,
  FireOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import ModelCard from '../components/models/ModelCard';
import ModelList from '../components/models/ModelList';
import { mockModels } from '../mock/data';

type ViewMode = 'card' | 'list';
type SortBy = 'popularity' | 'calls' | 'name' | 'created';

const Models = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('card');
  const [searchText, setSearchText] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string[]>([]);
  const [selectedEngine, setSelectedEngine] = useState<string[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<string[]>([]);
  const [selectedGpuType, setSelectedGpuType] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<SortBy>('popularity');
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [loading, setLoading] = useState(false);

  // Get unique values for filters
  const uniqueTypes = useMemo(() => {
    const types = new Set(mockModels.map((m) => m.type));
    return Array.from(types);
  }, []);

  const uniqueTasks = useMemo(() => {
    const tasks = new Set(mockModels.flatMap((m) => m.taskTypes));
    return Array.from(tasks);
  }, []);

  const uniqueEngines = useMemo(() => {
    const engines = new Set(mockModels.map((m) => m.engine));
    return Array.from(engines);
  }, []);

  const uniqueClusters = useMemo(() => {
    const clusters = new Set(mockModels.map((m) => m.cluster));
    return Array.from(clusters);
  }, []);

  const uniqueGpuTypes = useMemo(() => {
    const gpus = new Set(mockModels.map((m) => m.gpuType));
    return Array.from(gpus);
  }, []);

  // Filter and sort models
  const filteredModels = useMemo(() => {
    let filtered = [...mockModels];

    // Search filter
    if (searchText) {
      filtered = filtered.filter(
        (m) =>
          m.name.toLowerCase().includes(searchText.toLowerCase()) ||
          m.creator.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    // Type filter
    if (selectedTypes.length > 0) {
      filtered = filtered.filter((m) => selectedTypes.includes(m.type));
    }

    // Task filter
    if (selectedTasks.length > 0) {
      filtered = filtered.filter((m) =>
        m.taskTypes.some((t) => selectedTasks.includes(t))
      );
    }

    // Status filter
    if (selectedStatus.length > 0) {
      filtered = filtered.filter((m) => selectedStatus.includes(m.status));
    }

    // Engine filter
    if (selectedEngine.length > 0) {
      filtered = filtered.filter((m) => selectedEngine.includes(m.engine));
    }

    // Cluster filter
    if (selectedCluster.length > 0) {
      filtered = filtered.filter((m) => selectedCluster.includes(m.cluster));
    }

    // GPU type filter
    if (selectedGpuType.length > 0) {
      filtered = filtered.filter((m) => selectedGpuType.includes(m.gpuType));
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'popularity':
          return b.popularity - a.popularity;
        case 'calls':
          return b.calls - a.calls;
        case 'name':
          return a.name.localeCompare(b.name);
        case 'created':
          return parseInt(b.id) - parseInt(a.id);
        default:
          return 0;
      }
    });

    return filtered;
  }, [
    searchText,
    selectedTypes,
    selectedTasks,
    selectedStatus,
    selectedEngine,
    selectedCluster,
    selectedGpuType,
    sortBy,
  ]);

  // Handle refresh
  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      message.success('刷新成功');
    }, 500);
  };

  // Handle model actions
  const handleChat = (modelId: string) => {
    message.info(`聊天: ${modelId}`);
  };

  const handleApiAccess = (modelId: string) => {
    message.info(`API 访问: ${modelId}`);
  };

  const handleConfig = (modelId: string) => {
    message.info(`配置: ${modelId}`);
  };

  const handleStart = (modelId: string) => {
    message.success(`启动模型: ${modelId}`);
  };

  const handleStop = (modelId: string) => {
    message.success(`停止模型: ${modelId}`);
  };

  const handleDownload = (modelId: string) => {
    message.info(`下载模型: ${modelId}`);
  };

  const handleDelete = (modelId: string) => {
    message.warning(`删除模型: ${modelId}`);
  };

  // Deploy model dropdown items
  const deployMenuItems = [
    {
      key: 'huggingface',
      label: '从 HuggingFace 部署',
      onClick: () => message.info('从 HuggingFace 部署'),
    },
    {
      key: 'modelscope',
      label: '从 ModelScope 部署',
      onClick: () => message.info('从 ModelScope 部署'),
    },
    {
      key: 'upload',
      label: '上传本地模型文件',
      onClick: () => message.info('上传本地模型'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'directory',
      label: '查看模型目录',
      onClick: () => message.info('查看模型目录'),
    },
  ];

  // Sort menu items
  const sortMenuItems = [
    {
      key: 'popularity',
      label: '热度',
      icon: <FireOutlined />,
      onClick: () => setSortBy('popularity'),
    },
    {
      key: 'calls',
      label: '调用次数',
      icon: <ThunderboltOutlined />,
      onClick: () => setSortBy('calls'),
    },
    {
      key: 'name',
      label: '名称',
      icon: <ClockCircleOutlined />,
      onClick: () => setSortBy('name'),
    },
    {
      key: 'created',
      label: '创建时间',
      onClick: () => setSortBy('created'),
    },
  ];

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>模型中心</h2>
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索模型名称..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ maxWidth: 400 }}
          allowClear
        />
        <Button
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
          loading={loading}
          style={{ marginLeft: 8 }}
        >
          刷新
        </Button>
      </div>

      {/* Filters */}
      <div
        style={{
          marginBottom: 16,
          padding: 16,
          backgroundColor: '#fafafa',
          borderRadius: 8,
        }}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 8, fontSize: 12, color: '#8c8c8c' }}>
            分类筛选:
          </div>
          <Space wrap size={8}>
            <Tag.CheckableTag
              checked={selectedTypes.length === 0}
              onChange={(checked) => {
                if (checked) setSelectedTypes([]);
              }}
            >
              全部
            </Tag.CheckableTag>
            {uniqueTypes.map((type) => (
              <Tag.CheckableTag
                key={type}
                checked={selectedTypes.includes(type)}
                onChange={(checked) => {
                  if (checked) {
                    setSelectedTypes([...selectedTypes, type]);
                  } else {
                    setSelectedTypes(selectedTypes.filter((t) => t !== type));
                  }
                }}
              >
                {type}
              </Tag.CheckableTag>
            ))}
          </Space>
        </div>

        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 8, fontSize: 12, color: '#8c8c8c' }}>
            任务类型:
          </div>
          <Space wrap size={8}>
            {uniqueTasks.map((task) => (
              <Tag.CheckableTag
                key={task}
                checked={selectedTasks.includes(task)}
                onChange={(checked) => {
                  if (checked) {
                    setSelectedTasks([...selectedTasks, task]);
                  } else {
                    setSelectedTasks(selectedTasks.filter((t) => t !== task));
                  }
                }}
              >
                {task}
              </Tag.CheckableTag>
            ))}
          </Space>
        </div>

        <div>
          <Space wrap size={8}>
            <Select
              placeholder="状态"
              style={{ minWidth: 120 }}
              allowClear
              mode="multiple"
              value={selectedStatus}
              onChange={setSelectedStatus}
              options={[
                { label: '运行中', value: 'running' },
                { label: '已停止', value: 'stopped' },
                { label: '异常', value: 'error' },
              ]}
            />
            <Select
              placeholder="引擎"
              style={{ minWidth: 120 }}
              allowClear
              mode="multiple"
              value={selectedEngine}
              onChange={setSelectedEngine}
              options={uniqueEngines.map((e) => ({ label: e, value: e }))}
            />
            <Select
              placeholder="集群"
              style={{ minWidth: 120 }}
              allowClear
              mode="multiple"
              value={selectedCluster}
              onChange={setSelectedCluster}
              options={uniqueClusters.map((c) => ({ label: c, value: c }))}
            />
            <Select
              placeholder="GPU 类型"
              style={{ minWidth: 120 }}
              allowClear
              mode="multiple"
              value={selectedGpuType}
              onChange={setSelectedGpuType}
              options={uniqueGpuTypes.map((g) => ({ label: g, value: g }))}
            />
          </Space>
        </div>
      </div>

      {/* View Toggle and Actions */}
      <div
        style={{
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Segmented
          value={viewMode}
          onChange={(value) => setViewMode(value as ViewMode)}
          options={[
            { label: '卡片视图', value: 'card', icon: <AppstoreOutlined /> },
            { label: '列表视图', value: 'list', icon: <BarsOutlined /> },
          ]}
        />
        <Space>
          <Dropdown menu={{ items: sortMenuItems }} trigger={['click']}>
            <Button>
              排序: {sortBy === 'popularity' ? '热度' : sortBy === 'calls' ? '调用' : sortBy}
            </Button>
          </Dropdown>
          <Dropdown menu={{ items: deployMenuItems }} trigger={['click']}>
            <Button type="primary" icon={<PlusOutlined />}>
              部署新模型
            </Button>
          </Dropdown>
        </Space>
      </div>

      {/* Content */}
      {viewMode === 'card' ? (
        <Row gutter={[16, 16]}>
          {filteredModels.map((model) => (
            <Col xs={24} sm={12} md={8} lg={6} xl={6} key={model.id}>
              <ModelCard
                model={model}
                onChat={handleChat}
                onApiAccess={handleApiAccess}
                onConfig={handleConfig}
                onStart={handleStart}
                onStop={handleStop}
                onDownload={handleDownload}
                onDelete={handleDelete}
              />
            </Col>
          ))}
        </Row>
      ) : (
        <ModelList
          models={filteredModels}
          selectedRowKeys={selectedRowKeys}
          onSelectionChange={setSelectedRowKeys}
          onChat={handleChat}
          onApiAccess={handleApiAccess}
          onConfig={handleConfig}
          onStart={handleStart}
          onStop={handleStop}
          onDelete={handleDelete}
        />
      )}

      {/* Empty State */}
      {filteredModels.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: 64,
            color: '#8c8c8c',
          }}
        >
          <FilterOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <div style={{ fontSize: 16, marginBottom: 8 }}>未找到匹配的模型</div>
          <div>请尝试调整筛选条件</div>
        </div>
      )}
    </div>
  );
};

export default Models;

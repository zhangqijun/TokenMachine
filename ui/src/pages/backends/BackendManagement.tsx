import { useState, useMemo } from 'react';
import { Row, Col, Button, Space, Select, message, Modal, Form, Input, Empty } from 'antd';
import {
  ReloadOutlined,
  FilterOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import BackendCard from './components/BackendCard';
import type { BackendInfo } from './types';

const BackendManagement = () => {
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedBackend, setSelectedBackend] = useState<BackendInfo | null>(null);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [form] = Form.useForm();

  // Mock data - 后端列表
  const [backends, setBackends] = useState<BackendInfo[]>([
    {
      id: 'vllm',
      name: 'vllm',
      displayName: 'vLLM',
      version: '0.6.3',
      status: 'installed',
      icon: 'thunderbolt',
      description: '高性能的LLM推理引擎，支持PagedAttention和连续批处理',
      homepage: 'https://github.com/vllm-project/vllm',
      documentation: 'https://docs.vllm.ai/',
      features: {
        tensorParallel: true,
        prefixCaching: true,
        multiLora: false,
        speculativeDecoding: true,
        quantization: ['fp16', 'int8', 'int4', 'awq', 'gptq'],
        modelFormats: ['hf', 'vllm'],
      },
      performance: {
        avgTps: 145,
        memoryEfficiency: 92,
        startupTime: 12,
      },
      compatibility: {
        gpuVendors: ['NVIDIA'],
        minGpuMemory: 16,
        supportedModels: ['Llama', 'Qwen', 'Mistral', 'ChatGLM'],
      },
      config: {
        installedPath: '/opt/vllm',
        configPath: '/etc/vllm/config.yaml',
        port: 8000,
      },
      stats: {
        activeDeployments: 5,
        totalRequests: 125430,
        lastHealthCheck: new Date(Date.now() - 300000).toISOString(),
      },
    },
    {
      id: 'sglang',
      name: 'sglang',
      displayName: 'SGLang',
      version: '0.3.2',
      status: 'outdated',
      updateAvailable: '0.4.0',
      icon: 'star',
      description: '优化的结构化语言生成推理引擎，提供高效的内存管理和调度',
      homepage: 'https://github.com/sgl-project/sglang',
      features: {
        tensorParallel: true,
        prefixCaching: true,
        multiLora: true,
        speculativeDecoding: false,
        quantization: ['fp16', 'int8', 'int4'],
        modelFormats: ['hf', 'sglang'],
      },
      compatibility: {
        gpuVendors: ['NVIDIA'],
        minGpuMemory: 24,
        supportedModels: ['Llama', 'Qwen', 'Yi'],
      },
      config: {
        installedPath: '/opt/sglang',
        port: 8001,
      },
      stats: {
        activeDeployments: 2,
        totalRequests: 45210,
        lastHealthCheck: new Date(Date.now() - 600000).toISOString(),
      },
    },
    {
      id: 'chitu',
      name: 'chitu',
      displayName: 'Chitu',
      version: '1.2.1',
      status: 'installed',
      icon: 'database',
      description: '国产AI芯片推理引擎，支持华为昇腾、沐曦等国产硬件',
      homepage: 'https://github.com/ChituEngine',
      features: {
        tensorParallel: true,
        prefixCaching: true,
        multiLora: false,
        speculativeDecoding: false,
        quantization: ['fp16', 'int8', 'int4'],
        modelFormats: ['hf', 'chitu'],
      },
      performance: {
        avgTps: 98,
        memoryEfficiency: 88,
        startupTime: 18,
      },
      compatibility: {
        gpuVendors: ['华为昇腾', '沐曦', '海光'],
        minGpuMemory: 32,
        supportedModels: ['ChatGLM', 'Qwen', 'Baichuan'],
      },
      config: {
        installedPath: '/opt/chitu',
        port: 8002,
      },
      stats: {
        activeDeployments: 3,
        totalRequests: 28950,
        lastHealthCheck: new Date(Date.now() - 180000).toISOString(),
      },
    },
    {
      id: 'llamacpp',
      name: 'llamacpp',
      displayName: 'llama.cpp',
      version: 'b3925',
      status: 'not_installed',
      icon: 'cloud',
      description: '轻量级C++推理引擎，支持在CPU和消费级GPU上运行大模型',
      homepage: 'https://github.com/ggerganov/llama.cpp',
      features: {
        tensorParallel: false,
        prefixCaching: false,
        multiLora: false,
        speculativeDecoding: true,
        quantization: ['q4_0', 'q4_k', 'q5_0', 'q5_k', 'q6_k', 'q8_0'],
        modelFormats: ['gguf'],
      },
      compatibility: {
        gpuVendors: ['NVIDIA', 'AMD', 'Apple', 'CPU'],
        minGpuMemory: 8,
        supportedModels: ['Llama', 'Mistral', 'Qwen'],
      },
      config: {},
      stats: {
        activeDeployments: 0,
        totalRequests: 0,
        lastHealthCheck: new Date().toISOString(),
      },
    },
    {
      id: 'mindie',
      name: 'mindie',
      displayName: 'MindIE',
      version: '2.1.0',
      status: 'error',
      icon: 'sync',
      description: '华为昇腾专用的推理引擎，提供最佳的性能优化',
      homepage: 'https://www.hiascend.com/software/mindie',
      features: {
        tensorParallel: true,
        prefixCaching: true,
        multiLora: true,
        speculativeDecoding: false,
        quantization: ['fp16', 'int8', 'int4'],
        modelFormats: ['hf', 'mindie'],
      },
      compatibility: {
        gpuVendors: ['华为昇腾'],
        minGpuMemory: 32,
        supportedModels: ['ChatGLM', 'Qwen', 'Baichuan', 'Llama'],
      },
      config: {
        installedPath: '/opt/mindie',
        port: 8003,
      },
      stats: {
        activeDeployments: 0,
        totalRequests: 0,
        lastHealthCheck: new Date(Date.now() - 3600000).toISOString(),
      },
    },
    {
      id: 'ktransformer',
      name: 'ktransformer',
      displayName: 'KTransformer',
      version: '0.8.5',
      status: 'not_installed',
      icon: 'setting',
      description: '高效的大模型推理服务框架，支持多种硬件和模型格式',
      homepage: 'https://github.com/Infini-Tensor/KTransformer',
      features: {
        tensorParallel: true,
        prefixCaching: true,
        multiLora: true,
        speculativeDecoding: false,
        quantization: ['fp16', 'int8', 'int4', 'gptq'],
        modelFormats: ['hf', 'awq', 'gptq'],
      },
      compatibility: {
        gpuVendors: ['NVIDIA', '华为昇腾'],
        minGpuMemory: 16,
        supportedModels: ['Llama', 'Qwen', 'ChatGLM', 'Yi'],
      },
      config: {},
      stats: {
        activeDeployments: 0,
        totalRequests: 0,
        lastHealthCheck: new Date().toISOString(),
      },
    },
  ]);

  // 过滤后端
  const filteredBackends = useMemo(() => {
    if (statusFilter === 'all') return backends;
    return backends.filter((b) => b.status === statusFilter);
  }, [backends, statusFilter]);

  const handleRefresh = async () => {
    setLoading(true);
    // TODO: 调用API刷新后端状态
    setTimeout(() => {
      setLoading(false);
      message.success('刷新成功');
    }, 1000);
  };

  const handleInstall = async (backendId: string) => {
    Modal.confirm({
      title: '确认安装',
      content: `确定要安装 ${backends.find(b => b.id === backendId)?.displayName} 吗？`,
      onOk: () => {
        message.success('开始安装');
        // TODO: 调用API安装
      },
    });
  };

  const handleUpgrade = async (backendId: string) => {
    const backend = backends.find(b => b.id === backendId);
    Modal.confirm({
      title: '确认升级',
      content: `确定要将 ${backend?.displayName} 从 ${backend?.version} 升级到 ${backend?.updateAvailable} 吗？`,
      onOk: () => {
        message.success('开始升级');
        // TODO: 调用API升级
      },
    });
  };

  const handleConfigure = (backendId: string) => {
    const backend = backends.find(b => b.id === backendId);
    setSelectedBackend(backend || null);
    form.setFieldsValue(backend?.config);
    setConfigModalVisible(true);
  };

  const handleUninstall = async (backendId: string) => {
    Modal.confirm({
      title: '确认卸载',
      content: '确定要卸载此后端吗？这将影响所有使用该后端的部署。',
      okText: '确认',
      okType: 'danger',
      onOk: () => {
        message.success('卸载成功');
        // TODO: 调用API卸载
      },
    });
  };

  const handleViewLogs = (backendId: string) => {
    setSelectedBackend(backends.find(b => b.id === backendId) || null);
    setLogsModalVisible(true);
  };

  const handleSaveConfig = async () => {
    try {
      const values = await form.validateFields();
      message.success('配置已保存');
      setConfigModalVisible(false);
      // TODO: 调用API保存配置
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const stats = useMemo(() => {
    return {
      total: backends.length,
      installed: backends.filter(b => b.status === 'installed').length,
      outdated: backends.filter(b => b.status === 'outdated').length,
      error: backends.filter(b => b.status === 'error').length,
    };
  }, [backends]);

  return (
    <div>
      {/* 头部 */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>后端管理</h2>
        <p style={{ margin: '8px 0 0 0', color: '#666' }}>
          管理推理引擎后端，包括安装、升级、配置和监控
        </p>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <div
            style={{
              padding: 16,
              background: '#f0f2f5',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 24, fontWeight: 600, color: '#1890ff' }}>
              {stats.total}
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>总后端数</div>
          </div>
        </Col>
        <Col span={6}>
          <div
            style={{
              padding: 16,
              background: '#f0f2f5',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 24, fontWeight: 600, color: '#52c41a' }}>
              {stats.installed}
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>已安装</div>
          </div>
        </Col>
        <Col span={6}>
          <div
            style={{
              padding: 16,
              background: '#f0f2f5',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 24, fontWeight: 600, color: '#faad14' }}>
              {stats.outdated}
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>待更新</div>
          </div>
        </Col>
        <Col span={6}>
          <div
            style={{
              padding: 16,
              background: '#f0f2f5',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 24, fontWeight: 600, color: '#f5222d' }}>
              {stats.error}
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>错误</div>
          </div>
        </Col>
      </Row>

      {/* 操作栏 */}
      <div
        style={{
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Space>
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 150 }}
            suffixIcon={<FilterOutlined />}
          >
            <Select.Option value="all">全部状态</Select.Option>
            <Select.Option value="installed">已安装</Select.Option>
            <Select.Option value="not_installed">未安装</Select.Option>
            <Select.Option value="outdated">待更新</Select.Option>
            <Select.Option value="error">错误</Select.Option>
          </Select>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 后端卡片网格 */}
      {filteredBackends.length === 0 ? (
        <Empty description="没有找到匹配的后端" style={{ marginTop: 64 }} />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredBackends.map((backend) => (
            <Col key={backend.id} xs={24} sm={12} lg={8} xl={6}>
              <BackendCard
                backend={backend}
                onInstall={handleInstall}
                onUpgrade={handleUpgrade}
                onConfigure={handleConfigure}
                onViewLogs={handleViewLogs}
              />
            </Col>
          ))}
        </Row>
      )}

      {/* 配置模态框 */}
      <Modal
        title={`配置 ${selectedBackend?.displayName}`}
        open={configModalVisible}
        onCancel={() => {
          setConfigModalVisible(false);
          setSelectedBackend(null);
        }}
        onOk={handleSaveConfig}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="安装路径" name="installedPath">
            <Input />
          </Form.Item>
          <Form.Item label="配置文件路径" name="configPath">
            <Input />
          </Form.Item>
          <Form.Item label="服务端口" name="port">
            <Input type="number" />
          </Form.Item>
          <Form.Item label="环境变量" name="envVars">
            <Input.TextArea rows={4} placeholder="KEY=VALUE，每行一个" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 日志模态框 */}
      <Modal
        title={`${selectedBackend?.displayName} 日志`}
        open={logsModalVisible}
        onCancel={() => {
          setLogsModalVisible(false);
          setSelectedBackend(null);
        }}
        footer={[
          <Button key="close" onClick={() => setLogsModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        <div
          style={{
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: 16,
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 12,
            maxHeight: 400,
            overflow: 'auto',
          }}
        >
          <div>2024-01-20 10:30:15 [INFO] 服务启动成功，监听端口 {selectedBackend?.config?.port}</div>
          <div>2024-01-20 10:30:16 [INFO] 加载模型配置</div>
          <div>2024-01-20 10:30:18 [INFO] 初始化GPU资源</div>
          <div>2024-01-20 10:30:20 [INFO] 模型加载完成，ready to serve</div>
          <div style={{ color: '#52c41a' }}>2024-01-20 10:35:22 [INFO] 健康检查通过</div>
          <div style={{ color: '#faad14' }}>2024-01-20 10:45:30 [WARN] GPU内存使用率达到85%</div>
          <div style={{ color: '#52c41a' }}>2024-01-20 10:50:45 [INFO] 请求处理成功，耗时125ms</div>
        </div>
      </Modal>
    </div>
  );
};

export default BackendManagement;

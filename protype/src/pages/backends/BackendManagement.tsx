import { useState } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Typography,
  Progress,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Divider,
  Tooltip,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  WarningOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface BackendVersion {
  id: string;
  version: string;
  status: 'installed' | 'installing' | 'failed';
  imageName: string;
  installPath: string;
  installedAt: string;
  size: string;
  runningInstances: number;
}

interface BackendInfo {
  type: 'vllm' | 'mindie' | 'llamacpp';
  name: string;
  displayName: string;
  description: string;
  icon: React.ReactNode;
  homepage: string;
  versions: BackendVersion[];
}

const BackendManagement = () => {
  const [activeTab, setActiveTab] = useState<'vllm' | 'mindie' | 'llamacpp'>('vllm');
  const [isInstallModalOpen, setIsInstallModalOpen] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [installProgress, setInstallProgress] = useState(0);
  const [currentInstallingVersion, setCurrentInstallingVersion] = useState('');
  const [form] = Form.useForm();

  // Mock data - 已安装的引擎版本
  const [backends, setBackends] = useState<Record<string, BackendInfo>>({
    vllm: {
      type: 'vllm',
      name: 'vllm',
      displayName: 'vLLM',
      description: '高性能推理引擎，支持 PagedAttention 和连续批处理',
      icon: <RocketOutlined />,
      homepage: 'https://github.com/vllm-project/vllm',
      versions: [
        {
          id: 'vllm-0.6.3',
          version: '0.6.3',
          status: 'installed',
          imageName: 'vllm/vllm-openapi:v0.6.3',
          installPath: '/opt/vllm/v0.6.3',
          installedAt: '2025-01-15 10:30:00',
          size: '2.3 GB',
          runningInstances: 5,
        },
        {
          id: 'vllm-0.6.0',
          version: '0.6.0',
          status: 'installed',
          imageName: 'vllm/vllm-openapi:v0.6.0',
          installPath: '/opt/vllm/v0.6.0',
          installedAt: '2025-01-10 14:20:00',
          size: '2.1 GB',
          runningInstances: 0,
        },
        {
          id: 'vllm-0.5.0',
          version: '0.5.0',
          status: 'installed',
          imageName: 'vllm/vllm-openapi:v0.5.0',
          installPath: '/opt/vllm/v0.5.0',
          installedAt: '2025-01-05 09:15:00',
          size: '2.0 GB',
          runningInstances: 0,
        },
      ],
    },
    mindie: {
      type: 'mindie',
      name: 'mindie',
      displayName: 'MindIE',
      description: '华为昇腾推理引擎，适配华为昇腾系列芯片',
      icon: <ThunderboltOutlined />,
      homepage: 'https://www.huawei.com/',
      versions: [
        {
          id: 'mindie-1.0.0',
          version: '1.0.0',
          status: 'installed',
          imageName: 'registry.tokenmachine.ai/mindie/mindie-serving:v1.0.0',
          installPath: '/opt/mindie/v1.0.0',
          installedAt: '2025-01-12 09:15:00',
          size: '3.2 GB',
          runningInstances: 2,
        },
        {
          id: 'mindie-0.9.5',
          version: '0.9.5',
          status: 'installed',
          imageName: 'registry.tokenmachine.ai/mindie/mindie-serving:v0.9.5',
          installPath: '/opt/mindie/v0.9.5',
          installedAt: '2025-01-08 16:30:00',
          size: '3.0 GB',
          runningInstances: 0,
        },
      ],
    },
    llamacpp: {
      type: 'llamacpp',
      name: 'llamacpp',
      displayName: 'llama.cpp',
      description: '轻量级推理引擎，支持 CPU 和 Apple Silicon',
      icon: <DatabaseOutlined />,
      homepage: 'https://github.com/ggerganov/llama.cpp',
      versions: [
        {
          id: 'llamacpp-b4380',
          version: 'b4380',
          status: 'installed',
          imageName: 'ghcr.io/ggerganov/llama.cpp:latest-b4380',
          installPath: '/opt/llamacpp/b4380',
          installedAt: '2025-01-18 11:20:00',
          size: '850 MB',
          runningInstances: 1,
        },
      ],
    },
  });

  // 可安装的版本列表（模拟）
  const availableVersions: Record<string, string[]> = {
    vllm: ['0.6.3', '0.6.2', '0.6.0', '0.5.0', '0.4.0'],
    mindie: ['1.0.0', '0.9.5', '0.9.0', '0.8.5'],
    llamacpp: ['b4380', 'b4025', 'b3956', 'b3856'],
  };

  const currentBackend = backends[activeTab];

  const getStatusConfig = (status: BackendVersion['status']) => {
    const configs = {
      installed: { color: 'success', icon: <CheckCircleOutlined />, text: '已安装' },
      installing: { color: 'processing', icon: <LoadingOutlined />, text: '安装中' },
      failed: { color: 'error', icon: <WarningOutlined />, text: '安装失败' },
    };
    return configs[status];
  };

  const handleDelete = (backendType: string, version: BackendVersion) => {
    if (version.runningInstances > 0) {
      message.error(`该版本有 ${version.runningInstances} 个正在运行的实例，请先停止实例后再删除`);
      return;
    }

    setBackends(prev => ({
      ...prev,
      [backendType]: {
        ...prev[backendType],
        versions: prev[backendType].versions.filter(v => v.id !== version.id),
      },
    }));
    message.success(`版本 ${version.version} 删除成功`);
  };

  const handleInstall = async (values: any) => {
    // 检查版本是否已存在
    const exists = backends[activeTab].versions.some(
      v => v.version === values.version && v.status !== 'failed'
    );

    if (exists) {
      message.error(`版本 ${values.version} 已安装`);
      return;
    }

    setInstalling(true);
    setInstallProgress(0);
    setCurrentInstallingVersion(values.version);

    // 模拟安装进度
    const progressInterval = setInterval(() => {
      setInstallProgress(prev => {
        if (prev >= 95) {
          clearInterval(progressInterval);
          return prev;
        }
        return prev + Math.random() * 15;
      });
    }, 500);

    // 模拟安装完成
    setTimeout(() => {
      clearInterval(progressInterval);
      setInstallProgress(100);

      const newVersion: BackendVersion = {
        id: `${activeTab}-${values.version}`,
        version: values.version,
        status: 'installed',
        imageName: values.imageName || `${activeTab}/${activeTab}:${values.version}`,
        installPath: values.installPath || `/opt/${activeTab}/v${values.version}`,
        installedAt: dayjs().format('YYYY-MM-DD HH:mm:ss'),
        size: '2.0 GB',
        runningInstances: 0,
      };

      setBackends(prev => ({
        ...prev,
        [activeTab]: {
          ...prev[activeTab],
          versions: [...prev[activeTab].versions, newVersion],
        },
      }));

      setInstalling(false);
      setIsInstallModalOpen(false);
      setCurrentInstallingVersion('');
      form.resetFields();
      message.success(`${currentBackend.displayName} ${values.version} 安装成功`);
    }, 4000);
  };

  const columns = [
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => (
        <Text strong style={{ fontSize: 15 }}>{version}</Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: BackendVersion['status']) => {
        const config = getStatusConfig(status);
        return (
          <Tag color={config.color} icon={config.icon} style={{ fontSize: 13 }}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '镜像名称',
      dataIndex: 'imageName',
      key: 'imageName',
      render: (imageName: string) => <Text code style={{ fontSize: 12 }}>{imageName}</Text>,
    },
    {
      title: '占用空间',
      dataIndex: 'size',
      key: 'size',
      render: (size: string) => <Text>{size}</Text>,
    },
    {
      title: '运行中实例',
      dataIndex: 'runningInstances',
      key: 'runningInstances',
      render: (count: number) => (
        <Tag color={count > 0 ? 'green' : 'default'}>{count} 个</Tag>
      ),
    },
    {
      title: '安装时间',
      dataIndex: 'installedAt',
      key: 'installedAt',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: BackendVersion) => (
        <Space size={4}>
          {record.status === 'installed' && record.runningInstances === 0 && (
            <Popconfirm
              title="确认删除"
              description={`确定要删除版本 ${record.version} 吗？`}
              onConfirm={() => handleDelete(activeTab, record)}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
              >
                删除
              </Button>
            </Popconfirm>
          )}
          {record.runningInstances > 0 && (
            <Tooltip title={`有 ${record.runningInstances} 个实例正在运行，请先停止`}>
              <Button type="link" size="small" disabled>
                删除
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // 计算统计数据
  const totalVersions = Object.values(backends).reduce(
    (sum, backend) => sum + backend.versions.filter(v => v.status === 'installed').length,
    0
  );
  const totalSize = Object.values(backends)
    .flatMap(backend => backend.versions)
    .reduce((sum, v) => {
      const sizeGB = parseFloat(v.size);
      return sum + sizeGB;
    }, 0);
  const activeInstances = Object.values(backends)
    .flatMap(backend => backend.versions)
    .reduce((sum, v) => sum + v.runningInstances, 0);

  const tabItems = [
    {
      key: 'vllm',
      label: (
        <Space>
          <RocketOutlined style={{ fontSize: 16 }} />
          <span style={{ fontWeight: 500 }}>vLLM</span>
          <Tag color={backends.vllm.versions.length > 0 ? 'blue' : 'default'}>
            {backends.vllm.versions.length}
          </Tag>
        </Space>
      ),
      children: null,
    },
    {
      key: 'mindie',
      label: (
        <Space>
          <ThunderboltOutlined style={{ fontSize: 16 }} />
          <span style={{ fontWeight: 500 }}>MindIE</span>
          <Tag color={backends.mindie?.versions.length > 0 ? 'blue' : 'default'}>
            {backends.mindie?.versions.length || 0}
          </Tag>
        </Space>
      ),
      children: null,
    },
    {
      key: 'llamacpp',
      label: (
        <Space>
          <DatabaseOutlined style={{ fontSize: 16 }} />
          <span style={{ fontWeight: 500 }}>llama.cpp</span>
          <Tag color={backends.llamacpp.versions.length > 0 ? 'blue' : 'default'}>
            {backends.llamacpp.versions.length}
          </Tag>
        </Space>
      ),
      children: null,
    },
  ];

  return (
    <div style={{ padding: '0 0 24px 0' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <div>
            <Title level={3} style={{ margin: 0 }}>
              引擎管理
            </Title>
            <Text type="secondary" style={{ fontSize: 14 }}>
              管理 vLLM、MindIE 和 llama.cpp 推理引擎的多个版本
            </Text>
          </div>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            size="large"
            onClick={() => setIsInstallModalOpen(true)}
          >
            安装新版本
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="已安装版本"
              value={totalVersions}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a', fontSize: 28 }}
              suffix="个"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="占用空间"
              value={totalSize.toFixed(1)}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff', fontSize: 28 }}
              suffix="GB"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中实例"
              value={activeInstances}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#722ed1', fontSize: 28 }}
              suffix="个"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="引擎类型"
              value={3}
              valueStyle={{ color: '#fa8c16', fontSize: 28 }}
              suffix="种"
            />
          </Card>
        </Col>
      </Row>

      <Card>
        {/* Tab 切换 */}
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as 'vllm' | 'mindie' | 'llamacpp')}
          items={tabItems}
          size="large"
        />

        <Divider />

        {/* 引擎信息 */}
        <div style={{ marginBottom: 24 }}>
          <Space direction="vertical" size={8}>
            <Space>
              <span style={{ fontSize: 20, fontWeight: 500 }}>
                {currentBackend.icon} {currentBackend.displayName}
              </span>
              <a href={currentBackend.homepage} target="_blank" rel="noopener noreferrer">
                <InfoCircleOutlined /> 文档
              </a>
            </Space>
            <Text type="secondary" style={{ fontSize: 14 }}>
              {currentBackend.description}
            </Text>
          </Space>
        </div>

        {/* 版本列表 */}
        <Table
          columns={columns}
          dataSource={currentBackend.versions}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      </Card>

      {/* 安装对话框 */}
      <Modal
        title={
          <Space>
            <DownloadOutlined />
            <span>安装 {currentBackend.displayName}</span>
          </Space>
        }
        open={isInstallModalOpen}
        onCancel={() => {
          if (!installing) {
            setIsInstallModalOpen(false);
            form.resetFields();
            setInstallProgress(0);
            setCurrentInstallingVersion('');
          }
        }}
        footer={installing ? null : [
          <Button key="cancel" onClick={() => setIsInstallModalOpen(false)}>
            取消
          </Button>,
          <Button
            key="install"
            type="primary"
            loading={installing}
            onClick={() => form.submit()}
            size="large"
          >
            开始安装
          </Button>,
        ]}
        width={600}
      >
        {installing ? (
          <div style={{ padding: '24px 0' }}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 15 }}>
                正在安装 {currentBackend.displayName} {currentInstallingVersion}...
              </Text>
              <Progress
                percent={Math.round(installProgress)}
                status="active"
                strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
                strokeWidth={10}
              />
              <Text type="secondary">
                安装过程可能需要几分钟，请耐心等待...
              </Text>
            </Space>
          </div>
        ) : (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleInstall}
            size="large"
          >
            <Form.Item label="引擎类型">
              <Input
                value={`${currentBackend.icon} ${currentBackend.displayName}`}
                disabled
                style={{ fontSize: 15 }}
              />
            </Form.Item>

            <Form.Item
              label="选择版本"
              name="version"
              rules={[{ required: true, message: '请选择版本' }]}
            >
              <Select
                placeholder="选择要安装的版本"
                size="large"
                showSearch
              >
                {availableVersions[activeTab].map(ver => (
                  <Select.Option key={ver} value={ver}>
                    <Space>
                      <Text strong>v{ver}</Text>
                      {ver === availableVersions[activeTab][0] && (
                        <Tag color="green">最新</Tag>
                      )}
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="镜像名称"
              name="imageName"
              initialValue={`${activeTab}/${activeTab}:latest`}
              rules={[{ required: true, message: '请输入镜像名称' }]}
            >
              <Input
                placeholder="vllm/vllm-openapi:latest"
                size="large"
              />
            </Form.Item>

            <Form.Item
              label="安装路径"
              name="installPath"
              initialValue={`/opt/${activeTab}`}
              rules={[{ required: true, message: '请输入安装路径' }]}
            >
              <Input
                placeholder="/opt/vllm"
                size="large"
                prefix={<InfoCircleOutlined />}
              />
            </Form.Item>

            <Divider />

            <Space direction="vertical" size={8}>
              <Text strong style={{ fontSize: 14 }}>安装说明：</Text>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li><Text type="secondary">安装过程可能需要几分钟时间</Text></li>
                <li><Text type="secondary">安装过程中请勿关闭页面或刷新浏览器</Text></li>
                <li><Text type="secondary">有运行实例的版本无法删除</Text></li>
              </ul>
            </Space>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default BackendManagement;

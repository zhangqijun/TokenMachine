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
  Tooltip,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Divider,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  WarningOutlined,
  RocketOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface BackendVersion {
  id: string;
  version: string;
  status: 'installed' | 'installing' | 'failed';
  installPath: string;
  installedAt: string;
  size: string;
  isDefault: boolean;
}

interface BackendInfo {
  type: 'vllm' | 'sglang';
  name: string;
  description: string;
  icon: React.ReactNode;
  versions: BackendVersion[];
}

const BackendManagement = () => {
  const [activeTab, setActiveTab] = useState<'vllm' | 'sglang'>('vllm');
  const [isInstallModalOpen, setIsInstallModalOpen] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [installProgress, setInstallProgress] = useState(0);
  const [form] = Form.useForm();

  // Mock data - 已安装的引擎版本
  const [backends, setBackends] = useState<Record<string, BackendInfo>>({
    vllm: {
      type: 'vllm',
      name: 'vLLM',
      description: '高性能推理引擎，支持 PagedAttention',
      icon: <RocketOutlined />,
      versions: [
        {
          id: 'vllm-0.6.0',
          version: '0.6.0',
          status: 'installed',
          installPath: '/opt/vllm/v0.6.0',
          installedAt: '2025-01-15 10:30:00',
          size: '2.3 GB',
          isDefault: true,
        },
        {
          id: 'vllm-0.5.0',
          version: '0.5.0',
          status: 'installed',
          installPath: '/opt/vllm/v0.5.0',
          installedAt: '2025-01-10 14:20:00',
          size: '2.1 GB',
          isDefault: false,
        },
      ],
    },
    sglang: {
      type: 'sglang',
      name: 'SGLang',
      description: '高吞吐量推理引擎，优化结构化生成',
      icon: <ThunderboltOutlined />,
      versions: [
        {
          id: 'sglang-0.3.0',
          version: '0.3.0',
          status: 'installed',
          installPath: '/opt/sglang/v0.3.0',
          installedAt: '2025-01-12 09:15:00',
          size: '1.8 GB',
          isDefault: true,
        },
      ],
    },
  });

  // 可安装的版本列表（模拟）
  const availableVersions: Record<string, string[]> = {
    vllm: ['0.6.1', '0.6.0', '0.5.0', '0.4.0'],
    sglang: ['0.3.1', '0.3.0', '0.2.0'],
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

  const handleSetDefault = (backendType: string, versionId: string) => {
    setBackends(prev => ({
      ...prev,
      [backendType]: {
        ...prev[backendType],
        versions: prev[backendType].versions.map(v => ({
          ...v,
          isDefault: v.id === versionId,
        })),
      },
    }));
    message.success(`已设置 ${backends[backendType].name} ${versionId.split('-')[1]} 为默认版本`);
  };

  const handleDelete = (backendType: string, version: BackendVersion) => {
    if (version.isDefault) {
      message.error('无法删除默认版本，请先设置其他版本为默认');
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
    setInstalling(true);
    setInstallProgress(0);

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
        installPath: values.installPath || `/opt/${activeTab}/v${values.version}`,
        installedAt: dayjs().format('YYYY-MM-DD HH:mm:ss'),
        size: '2.0 GB',
        isDefault: backends[activeTab].versions.length === 0,
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
      setInstallProgress(0);
      form.resetFields();
      message.success(`${currentBackend.name} ${values.version} 安装成功`);
    }, 4000);
  };

  const columns = [
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      render: (version: string, record: BackendVersion) => (
        <Space>
          <Text strong>{version}</Text>
          {record.isDefault && (
            <Tag color="blue">默认</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: BackendVersion['status']) => {
        const config = getStatusConfig(status);
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '安装路径',
      dataIndex: 'installPath',
      key: 'installPath',
      render: (path: string) => <Text code>{path}</Text>,
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
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
      width: 180,
      render: (_: any, record: BackendVersion) => (
        <Space>
          {!record.isDefault && record.status === 'installed' && (
            <Button
              type="link"
              size="small"
              onClick={() => handleSetDefault(activeTab, record.id)}
            >
              设为默认
            </Button>
          )}
          {record.status === 'installed' && (
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

  const tabItems = [
    {
      key: 'vllm',
      label: (
        <Space>
          <RocketOutlined />
          <span>vLLM</span>
          <Tag>{backends.vllm.versions.filter(v => v.status === 'installed').length}</Tag>
        </Space>
      ),
      children: null,
    },
    {
      key: 'sglang',
      label: (
        <Space>
          <ThunderboltOutlined />
          <span>SGLang</span>
          <Tag>{backends.sglang.versions.filter(v => v.status === 'installed').length}</Tag>
        </Space>
      ),
      children: null,
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Title level={3} style={{ margin: 0 }}>
            推理引擎管理
          </Title>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => setIsInstallModalOpen(true)}
          >
            安装新版本
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="已安装版本"
              value={totalVersions}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="占用空间"
              value={totalSize.toFixed(1)}
              suffix="GB"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="引擎类型"
              value={2}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as 'vllm' | 'sglang')}
          items={tabItems}
        />

        <Divider />

        <div style={{ marginBottom: 16 }}>
          <Space direction="vertical" size={4}>
            <Title level={5} style={{ margin: 0 }}>
              {currentBackend.icon} {currentBackend.name}
            </Title>
            <Text type="secondary">{currentBackend.description}</Text>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={currentBackend.versions}
          rowKey="id"
          pagination={false}
        />
      </Card>

      {/* 安装对话框 */}
      <Modal
        title={
          <Space>
            <DownloadOutlined />
            <span>安装 {currentBackend.name}</span>
          </Space>
        }
        open={isInstallModalOpen}
        onCancel={() => {
          if (!installing) {
            setIsInstallModalOpen(false);
            form.resetFields();
            setInstallProgress(0);
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
          >
            安装
          </Button>,
        ]}
        width={600}
      >
        {installing ? (
          <div style={{ padding: '24px 0' }}>
            <Text>正在安装 {currentBackend.name}，请稍候...</Text>
            <Progress
              percent={Math.round(installProgress)}
              status="active"
              style={{ marginTop: 16 }}
            />
          </div>
        ) : (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleInstall}
          >
            <Form.Item
              label="引擎类型"
              initialValue={activeTab}
            >
              <Input disabled value={currentBackend.name} />
            </Form.Item>

            <Form.Item
              label="版本"
              name="version"
              rules={[{ required: true, message: '请选择版本' }]}
            >
              <Select placeholder="选择要安装的版本">
                {availableVersions[activeTab].map(ver => (
                  <Select.Option key={ver} value={ver}>
                    v{ver}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="安装路径"
              name="installPath"
              initialValue={`/opt/${activeTab}`}
              rules={[{ required: true, message: '请输入安装路径' }]}
            >
              <Input placeholder="/opt/vllm" />
            </Form.Item>

            <Divider />

            <Space direction="vertical" size={8}>
              <Text strong>安装说明：</Text>
              <Text type="secondary">
                • 安装过程可能需要几分钟时间，请耐心等待
              </Text>
              <Text type="secondary">
                • 安装过程中请勿关闭页面或刷新浏览器
              </Text>
              <Text type="secondary">
                • 安装完成后可设为默认版本
              </Text>
            </Space>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default BackendManagement;

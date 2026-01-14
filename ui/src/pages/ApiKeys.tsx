import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Row,
  Col,
  Statistic,
  Progress,
  Switch,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  CopyOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  KeyOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useStore } from '../store';
import type { ApiKey } from '../mock/data';
import dayjs from 'dayjs';

const ApiKeys = () => {
  const { apiKeys, createApiKey, deleteApiKey, toggleApiKey, isLoading } = useStore();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [revealKeys, setRevealKeys] = useState<Record<string, boolean>>({});
  const [form] = Form.useForm();

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <KeyOutlined />
          <span style={{ fontWeight: 500 }}>{name}</span>
        </Space>
      ),
    },
    {
      title: 'API Key',
      dataIndex: 'key_prefix',
      key: 'key_prefix',
      render: (prefix: string, record: ApiKey) => {
        const isRevealed = revealKeys[record.id];
        const fullKey = `tmachine_sk_${record.id.substring(4)}_${Math.random().toString(36).substring(2, 10)}`;
        return (
          <Space>
            <code style={{ background: '#f5f5f5', padding: '4px 8px', borderRadius: 4 }}>
              {isRevealed ? fullKey : prefix}
            </code>
            <Button
              type="text"
              size="small"
              icon={isRevealed ? <EyeInvisibleOutlined /> : <EyeOutlined />}
              onClick={() => setRevealKeys({ ...revealKeys, [record.id]: !isRevealed })}
            />
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => {
                navigator.clipboard.writeText(fullKey);
                message.success('API Key 已复制到剪贴板');
              }}
            />
          </Space>
        );
      },
    },
    {
      title: '配额',
      key: 'quota',
      render: (_: unknown, record: ApiKey) => {
        const percent = (record.tokens_used / record.quota_tokens) * 100;
        const remaining = record.quota_tokens - record.tokens_used;
        return (
          <div style={{ width: 180 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 12, color: '#666' }}>
                已用: {(record.tokens_used / 1000000).toFixed(2)}M
              </span>
              <span style={{ fontSize: 12, color: '#666' }}>
                总计: {(record.quota_tokens / 1000000).toFixed(1)}M
              </span>
            </div>
            <Progress
              percent={percent}
              status={percent > 90 ? 'exception' : percent > 70 ? 'active' : 'normal'}
              size="small"
            />
            <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
              剩余: {(remaining / 1000000).toFixed(2)}M tokens
            </div>
          </div>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean, record: ApiKey) => (
        <Switch
          checked={isActive}
          onChange={() => handleToggle(record)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      render: (date: string) => {
        const days = dayjs(date).diff(dayjs(), 'day');
        let color = 'default';
        let text = dayjs(date).format('YYYY-MM-DD');
        if (days < 0) {
          color = 'error';
          text = '已过期';
        } else if (days < 7) {
          color = 'warning';
          text += ` (${days}天后过期)`;
        } else if (days < 30) {
          color = 'processing';
        }
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '最后使用',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      render: (date: string) => {
        const hours = dayjs().diff(dayjs(date), 'hour');
        if (hours < 1) return '刚刚';
        if (hours < 24) return `${hours} 小时前`;
        return dayjs(date).format('MM-DD HH:mm');
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: ApiKey) => (
        <Popconfirm
          title="确认删除"
          description="确定要删除这个 API Key 吗？此操作不可撤销。"
          onConfirm={() => handleDelete(record)}
          okText="删除"
          cancelText="取消"
          okType="danger"
        >
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const handleCreate = async (values: any) => {
    try {
      await createApiKey({
        name: values.name,
        quota_tokens: values.quota_tokens,
        tokens_used: 0,
        is_active: true,
        expires_at: dayjs().add(values.expires_in, 'day').toISOString(),
      });
      message.success('API Key 创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
    } catch (error) {
      message.error('创建 API Key 失败');
    }
  };

  const handleDelete = async (record: ApiKey) => {
    try {
      await deleteApiKey(record.id);
      message.success('API Key 已删除');
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleToggle = async (record: ApiKey) => {
    try {
      await toggleApiKey(record.id);
      message.success(`API Key 已${record.is_active ? '禁用' : '启用'}`);
    } catch (error) {
      message.error('操作失败');
    }
  };

  // Calculate stats
  const activeKeys = apiKeys.filter(k => k.is_active).length;
  const totalTokensUsed = apiKeys.reduce((sum, k) => sum + k.tokens_used, 0);
  const totalQuota = apiKeys.reduce((sum, k) => sum + k.quota_tokens, 0);

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总 API Keys"
              value={apiKeys.length}
              prefix={<KeyOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="启用中"
              value={activeKeys}
              suffix={`/ ${apiKeys.length}`}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>Token 使用情况</div>
            <Progress
              percent={(totalTokensUsed / totalQuota) * 100}
              status={(totalTokensUsed / totalQuota) > 0.9 ? 'exception' : 'normal'}
              format={() => `${(totalTokensUsed / 1000000).toFixed(2)}M / ${(totalQuota / 1000000).toFixed(1)}M`}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="API Keys 管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            创建 API Key
          </Button>
        }
      >
        <Table
          dataSource={apiKeys}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 API Keys`,
          }}
        />
      </Card>

      <Modal
        title="创建 API Key"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{
            quota_tokens: 10000000,
            expires_in: 365,
          }}
        >
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入 API Key 名称' }]}
            tooltip="用于标识此 Key 的用途"
          >
            <Input placeholder="例如: Production API Key" />
          </Form.Item>

          <Form.Item
            label="配额 (Tokens)"
            name="quota_tokens"
            rules={[{ required: true, message: '请输入配额' }]}
            tooltip="此 Key 可使用的最大 Token 数量"
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1000}
              max={1000000000}
              formatter={(value) => `${value?.toLocaleString()}`}
            />
          </Form.Item>

          <Form.Item
            label="有效期"
            name="expires_in"
            rules={[{ required: true, message: '请选择有效期' }]}
            tooltip="API Key 的过期时间"
          >
            <Select>
              <Select.Option value={30}>30 天</Select.Option>
              <Select.Option value={90}>90 天</Select.Option>
              <Select.Option value={180}>180 天</Select.Option>
              <Select.Option value={365}>1 年</Select.Option>
              <Select.Option value={730}>2 年</Select.Option>
              <Select.Option value={0}>永久</Select.Option>
            </Select>
          </Form.Item>

          <div style={{
            padding: 12,
            background: '#e6f7ff',
            border: '1px solid #91d5ff',
            borderRadius: 4,
            marginBottom: 16,
            fontSize: 13,
          }}>
            创建后，API Key 将只显示一次，请妥善保管。
          </div>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={isLoading}>
              创建
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApiKeys;

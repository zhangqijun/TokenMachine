import { useState } from 'react';
import {
  Card,
  Button,
  Tag,
  Space,
  Progress,
  Dropdown,
  Modal,
  message,
  Row,
  Col,
  Statistic,
  Select,
  Input,
} from 'antd';
import {
  PlusOutlined,
  CopyOutlined,
  EditOutlined,
  StopOutlined,
  CheckCircleOutlined,
  KeyOutlined,
  LinkOutlined,
  LockOutlined,
  BarChartOutlined,
  EllipsisOutlined,
} from '@ant-design/icons';
import { useStore } from '../../store';
import type { ApiKey } from '../../mock/data';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import CreateApiKeyModal from './CreateApiKeyModal';

dayjs.extend(relativeTime);

const ApiKeyManagement = () => {
  const { apiKeys, deleteApiKey, toggleApiKey, isLoading } = useStore();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchText, setSearchText] = useState('');

  const filteredKeys = apiKeys.filter((key) => {
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'active' && key.is_active) ||
      (statusFilter === 'disabled' && !key.is_active) ||
      (statusFilter === 'expired' && dayjs(key.expires_at).isBefore(dayjs()));

    const matchesSearch = key.name.toLowerCase().includes(searchText.toLowerCase()) ||
      key.key_prefix.toLowerCase().includes(searchText.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  const handleCopyKey = (fullKey: string) => {
    navigator.clipboard.writeText(fullKey);
    message.success('API Key 已复制到剪贴板');
  };

  const handleToggleStatus = async (record: ApiKey) => {
    try {
      await toggleApiKey(record.id);
      message.success(`API Key 已${record.is_active ? '禁用' : '启用'}`);
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDelete = async (record: ApiKey) => {
    Modal.confirm({
      title: '确认撤销',
      content: `确定要撤销 API Key "${record.name}" 吗？此操作不可撤销。`,
      okText: '撤销',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteApiKey(record.id);
          message.success('API Key 已撤销');
        } catch (error) {
          message.error('撤销失败');
        }
      },
    });
  };

  const getDropdownItems = (record: ApiKey) => [
    {
      key: 'detail',
      icon: <KeyOutlined />,
      label: '查看详情',
      onClick: () => message.info('查看详情功能开发中'),
    },
    {
      key: 'stats',
      icon: <BarChartOutlined />,
      label: '使用统计',
      onClick: () => message.info('使用统计功能开发中'),
    },
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: '编辑权限',
      onClick: () => message.info('编辑权限功能开发中'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'copy',
      icon: <CopyOutlined />,
      label: '复制密钥',
      onClick: () => {
        const fullKey = `tmachine_sk_${record.id.substring(4)}_${Math.random().toString(36).substring(2, 10)}`;
        handleCopyKey(fullKey);
      },
    },
    {
      key: 'toggle',
      icon: record.is_active ? <StopOutlined /> : <CheckCircleOutlined />,
      label: record.is_active ? '禁用' : '启用',
      onClick: () => handleToggleStatus(record),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'delete',
      icon: <EllipsisOutlined />,
      label: '撤销',
      danger: true,
      onClick: () => handleDelete(record),
    },
  ];

  const renderApiKeyCard = (record: ApiKey) => {
    const tokenPercent = (record.tokens_used / record.quota_tokens) * 100;
    const isExpired = dayjs(record.expires_at).isBefore(dayjs());

    return (
      <Card
        key={record.id}
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: 20 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <Space size="middle" align="center">
              <span style={{ fontSize: 16, fontWeight: 500 }}>{record.name}</span>
              <Tag color={isExpired ? 'error' : record.is_active ? 'success' : 'default'}>
                {isExpired ? '已过期' : record.is_active ? '活跃' : '已禁用'}
              </Tag>
              <Dropdown
                menu={{ items: getDropdownItems(record) }}
                trigger={['click']}
              >
                <Button type="text" size="small" icon={<EllipsisOutlined />} />
              </Dropdown>
            </Space>

            <div style={{ color: '#666', fontSize: 13, marginTop: 4 }}>
              {record.key_prefix} • 创建: {dayjs(record.created_at).format('YYYY-MM-DD')} •
              最后使用: {dayjs(record.last_used_at).fromNow()}
            </div>
          </div>
        </div>

        <Progress
          percent={tokenPercent}
          status={tokenPercent > 90 ? 'exception' : 'normal'}
          showInfo={false}
          style={{ marginBottom: 12 }}
        />

        <Row gutter={16} style={{ marginBottom: 12 }}>
          <Col span={12}>
            <div style={{ fontSize: 13, color: '#666' }}>
              Token: {(record.tokens_used / 1000000).toFixed(1)}M / {(record.quota_tokens / 1000000).toFixed(0)}M
              ({tokenPercent.toFixed(1)}%)
            </div>
          </Col>
          <Col span={12}>
            <div style={{ fontSize: 13, color: '#666' }}>
              请求: {(Math.floor(Math.random() * 200) + 50)}K 今日
            </div>
          </Col>
        </Row>

        <div style={{ display: 'flex', gap: 24, fontSize: 13, marginBottom: 12 }}>
          <div>
            <LinkOutlined style={{ marginRight: 4, color: '#1890ff' }} />
            <span style={{ color: '#666', marginRight: 4 }}>绑定路由:</span>
            <Tag color="blue">qwen-智能路由 (90%)</Tag>
            <Tag color="green">llama-灰度 (10%)</Tag>
          </div>
        </div>

        <div style={{ fontSize: 13 }}>
          <LockOutlined style={{ marginRight: 4, color: '#52c41a' }} />
          <span style={{ color: '#666', marginRight: 4 }}>权限:</span>
          <span style={{ color: '#333' }}>qwen/llama/glm • 并发: 10 • QPS: 100</span>
        </div>
      </Card>
    );
  };

  const activeKeys = apiKeys.filter((k) => k.is_active).length;
  const totalTokensUsed = apiKeys.reduce((sum, k) => sum + k.tokens_used, 0);
  const totalQuota = apiKeys.reduce((sum, k) => sum + k.quota_tokens, 0);

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总 API 密钥"
              value={apiKeys.length}
              prefix={<KeyOutlined />}
              valueStyle={{ color: '#1890ff', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃密钥"
              value={activeKeys}
              suffix={`/ ${apiKeys.length}`}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>总 Token 使用情况</div>
            <Progress
              percent={(totalTokensUsed / totalQuota) * 100}
              status={(totalTokensUsed / totalQuota) > 0.9 ? 'exception' : 'normal'}
              format={() => `${(totalTokensUsed / 1000000).toFixed(1)}M / ${(totalQuota / 1000000).toFixed(0)}M`}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="API 密钥管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            创建新密钥
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 120 }}
            options={[
              { label: '全部', value: 'all' },
              { label: '活跃', value: 'active' },
              { label: '已禁用', value: 'disabled' },
              { label: '已过期', value: 'expired' },
            ]}
          />
          <Input
            placeholder="搜索密钥名称或前缀"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 240 }}
            allowClear
          />
        </Space>

        <div style={{ maxHeight: 'calc(100vh - 420px)', overflowY: 'auto' }}>
          {filteredKeys.length > 0 ? (
            filteredKeys.map((key) => renderApiKeyCard(key))
          ) : (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              {searchText || statusFilter !== 'all' ? '没有找到匹配的 API 密钥' : '暂无 API 密钥'}
            </div>
          )}
        </div>
      </Card>

      <CreateApiKeyModal
        open={isCreateModalOpen}
        onCancel={() => setIsCreateModalOpen(false)}
      />
    </div>
  );
};

export default ApiKeyManagement;

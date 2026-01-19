import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Typography,
  message,
  Tabs,
  Row,
  Col,
  Statistic,
  Alert,
  Descriptions,
  Popconfirm,
  List,
} from 'antd';
import {
  ApiOutlined,
  PlusOutlined,
  CopyOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  KeyOutlined,
  LockOutlined,
  CheckCircleOutlined,
  SearchOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import ApiRouting from './ApiRouting';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface APIKey {
  id: string;
  name: string;
  key: string;
  prefix: string;
  created_at: string;
  last_used: string;
  status: 'active' | 'disabled' | 'expired';
  permissions: string[];
  rate_limit: number;
}

const ApiManagement = () => {
  const [apiKeyModalVisible, setApiKeyModalVisible] = useState(false);
  const [viewKeyModalVisible, setViewKeyModalVisible] = useState(false);
  const [selectedKey, setSelectedKey] = useState<APIKey | null>(null);
  const [showFullKey, setShowFullKey] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [form] = Form.useForm();

  const apiKeys: APIKey[] = [
    {
      id: '1',
      name: '生产环境主密钥',
      key: 'sk-1234567890abcdef1234567890abcdef',
      prefix: 'sk-1234****cdef',
      created_at: '2024-01-01 10:00:00',
      last_used: '2024-01-19 15:30:00',
      status: 'active',
      permissions: ['read', 'write', 'delete'],
      rate_limit: 10000,
    },
    {
      id: '2',
      name: '测试环境密钥',
      key: 'sk-abcdef1234567890abcdef1234567890',
      prefix: 'sk-abcd****7890',
      created_at: '2024-01-05 14:20:00',
      last_used: '2024-01-18 09:15:00',
      status: 'active',
      permissions: ['read', 'write'],
      rate_limit: 5000,
    },
    {
      id: '3',
      name: '只读访问密钥',
      key: 'sk-5678abcd90ef12345678abcd90ef1234',
      prefix: 'sk-5678****1234',
      created_at: '2024-01-10 08:00:00',
      last_used: '2024-01-17 16:45:00',
      status: 'active',
      permissions: ['read'],
      rate_limit: 1000,
    },
    {
      id: '4',
      name: '已废弃的密钥',
      key: 'sk-00001111222233334444555566667777',
      prefix: 'sk-0000****7777',
      created_at: '2023-12-01 10:00:00',
      last_used: '2024-01-01 12:00:00',
      status: 'disabled',
      permissions: ['read', 'write'],
      rate_limit: 5000,
    },
  ];

  const apiEndpoints = [
    {
      method: 'POST',
      path: '/v1/chat/completions',
      description: '聊天对话接口',
      auth: 'required',
    },
    {
      method: 'GET',
      path: '/v1/models',
      description: '获取模型列表',
      auth: 'required',
    },
    {
      method: 'POST',
      path: '/v1/completions',
      description: '文本补全接口',
      auth: 'required',
    },
    {
      method: 'GET',
      path: '/v1/deployments',
      description: '获取部署列表',
      auth: 'required',
    },
    {
      method: 'POST',
      path: '/v1/embeddings',
      description: '文本向量化接口',
      auth: 'required',
    },
  ];

  const handleCreateKey = () => {
    form.validateFields().then(() => {
      message.success('API Key创建成功，请妥善保管');
      setApiKeyModalVisible(false);
      form.resetFields();
    });
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    message.success('已复制到剪贴板');
  };

  const handleDeleteKey = (id: string) => {
    message.success('API Key已删除');
  };

  const handleDisableKey = (id: string) => {
    message.success('API Key已禁用');
  };

  const handleViewKey = (key: APIKey) => {
    setSelectedKey(key);
    setViewKeyModalVisible(true);
    setShowFullKey(false);
  };

  // 过滤API Keys
  const filteredApiKeys = apiKeys.filter((key) => {
    const matchesSearch =
      searchText === '' ||
      key.name.toLowerCase().includes(searchText.toLowerCase()) ||
      key.prefix.toLowerCase().includes(searchText.toLowerCase());

    const matchesStatus = statusFilter === undefined || key.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const getMethodTag = (method: string) => {
    const config: Record<string, { color: string; label: string }> = {
      GET: { color: 'green', label: 'GET' },
      POST: { color: 'blue', label: 'POST' },
      PUT: { color: 'orange', label: 'PUT' },
      DELETE: { color: 'red', label: 'DELETE' },
    };
    const { color, label } = config[method];
    return <Tag color={color}>{label}</Tag>;
  };

  const keyColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: 'API Key',
      dataIndex: 'prefix',
      key: 'prefix',
      render: (prefix: string, record: APIKey) => (
        <Space>
          <Tag color="blue" icon={<KeyOutlined />}>
            {prefix}
          </Tag>
          <Button
            type="link"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCopyKey(record.key)}
          >
            复制
          </Button>
        </Space>
      ),
    },
    {
      title: '权限',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: string[]) => (
        <Space>
          {permissions.map((perm) => (
            <Tag key={perm} color="purple">
              {perm}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '速率限制',
      dataIndex: 'rate_limit',
      key: 'rate_limit',
      render: (limit: number) => <Tag>{limit}/分钟</Tag>,
    },
    {
      title: '最后使用',
      dataIndex: 'last_used',
      key: 'last_used',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; label: string }> = {
          active: { color: 'success', label: '活跃' },
          disabled: { color: 'default', label: '已禁用' },
          expired: { color: 'error', label: '已过期' },
        };
        const { color, label } = config[status];
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: APIKey) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewKey(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            disabled={record.status !== 'active'}
          >
            编辑
          </Button>
          {record.status === 'active' ? (
            <Popconfirm
              title="确定禁用此API Key？"
              onConfirm={() => handleDisableKey(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<LockOutlined />}>
                禁用
              </Button>
            </Popconfirm>
          ) : (
            <Button type="link" size="small" icon={<CheckCircleOutlined />}>
              启用
            </Button>
          )}
          <Popconfirm
            title="确定删除此API Key？"
            onConfirm={() => handleDeleteKey(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const endpointColumns = [
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (method: string) => getMethodTag(method),
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      render: (path: string) => (
        <Tag color="blue" style={{ fontFamily: 'monospace' }}>
          {path}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '认证',
      dataIndex: 'auth',
      key: 'auth',
      width: 100,
      render: (auth: string) => (
        <Tag color={auth === 'required' ? 'green' : 'default'}>
          {auth === 'required' ? '需要' : '可选'}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <ApiOutlined />
            <span>API 管理</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="keys"
          items={[
            {
              key: 'keys',
              label: 'API Keys',
              children: (
                <div>
                  <Alert
                    message="API Key 安全提示"
                    description="API Key是访问系统的重要凭证，请妥善保管。建议为不同环境使用不同的Key，并定期轮换。"
                    type="warning"
                    showIcon
                    closable
                    style={{ marginBottom: 16 }}
                  />

                  <div
                    style={{
                      marginBottom: 16,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: 12,
                    }}
                  >
                    <Space>
                      <Input
                        placeholder="搜索API Key名称或前缀"
                        allowClear
                        style={{ width: 300 }}
                        prefix={<KeyOutlined style={{ color: 'rgba(0,0,0,0.25)' }} />}
                        suffix={<SearchOutlined style={{ color: 'rgba(0,0,0,0.25)' }} />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                      />
                      <Select
                        placeholder="筛选状态"
                        allowClear
                        style={{ width: 120 }}
                        value={statusFilter}
                        onChange={setStatusFilter}
                        suffixIcon={<FilterOutlined />}
                      >
                        <Select.Option value="active">活跃</Select.Option>
                        <Select.Option value="disabled">已禁用</Select.Option>
                        <Select.Option value="expired">已过期</Select.Option>
                      </Select>
                    </Space>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => setApiKeyModalVisible(true)}
                    >
                      创建 API Key
                    </Button>
                  </div>

                  <Table
                    columns={keyColumns}
                    dataSource={filteredApiKeys}
                    rowKey="id"
                    pagination={{
                      pageSize: 10,
                      showSizeChanger: true,
                      showTotal: (total) => `共 ${total} 个API Key`,
                    }}
                  />
                </div>
              ),
            },
            {
              key: 'endpoints',
              label: '接口文档',
              children: (
                <div>
                  <Alert
                    message="API 接口说明"
                    description="系统提供OpenAI兼容的API接口，支持标准HTTP请求。所有接口需要在Header中携带API Key进行身份验证。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <Card size="small" title="认证方式" style={{ marginBottom: 16 }}>
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="Header名称">
                        <Tag>Authorization</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="Header值格式">
                        <Text code>Bearer sk-your-api-key</Text>
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>

                  <Title level={5}>可用接口列表</Title>
                  <Table
                    columns={endpointColumns}
                    dataSource={apiEndpoints}
                    rowKey="path"
                    pagination={false}
                    size="small"
                  />

                  <Card
                    size="small"
                    title="请求示例"
                    style={{ marginTop: 16 }}
                  >
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        overflow: 'auto',
                      }}
                    >
{`curl -X POST https://api.tokenmachine.ai/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer sk-your-api-key" \\
  -d '{
    "model": "llama-3-8b-instruct",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'`}
                    </pre>
                  </Card>
                </div>
              ),
            },
            {
              key: 'usage',
              label: '使用统计',
              children: (
                <div>
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="总API调用"
                          value={1250000}
                          suffix="次"
                          prefix={<ApiOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="今日调用"
                          value={45678}
                          suffix="次"
                          styles={{ content: { color: '#3f8600' } }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="活跃Keys"
                          value={3}
                          suffix="个"
                          styles={{ content: { color: '#1890ff' } }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="平均响应时间"
                          value={245}
                          suffix="ms"
                          styles={{ content: { color: '#cf1322' } }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Card title="API Key使用排行" size="small">
                    <List
                      dataSource={apiKeys.filter((k) => k.status === 'active')}
                      renderItem={(key, index) => (
                        <List.Item>
                          <List.Item.Meta
                            avatar={
                              <Tag color={index < 3 ? 'gold' : 'default'}>
                                #{index + 1}
                              </Tag>
                            }
                            title={key.name}
                            description={
                              <Space>
                                <Text type="secondary">{key.prefix}</Text>
                                <Text type="secondary">
                                  最后使用: {key.last_used}
                                </Text>
                              </Space>
                            }
                          />
                          <Statistic
                            value={Math.floor(Math.random() * 100000)}
                            suffix="次"
                            styles={{ content: { fontSize: 16 } }}
                          />
                        </List.Item>
                      )}
                    />
                  </Card>
                </div>
              ),
            },
            {
              key: 'routing',
              label: '路由管理',
              children: <ApiRouting />,
            },
          ]}
        />
      </Card>

      {/* 创建API Key弹窗 */}
      <Modal
        title="创建 API Key"
        open={apiKeyModalVisible}
        onOk={handleCreateKey}
        onCancel={() => {
          setApiKeyModalVisible(false);
          form.resetFields();
        }}
        width={600}
      >
        <Alert
          message="重要提示"
          description="创建后请立即复制API Key，关闭此窗口后将无法再次查看完整密钥。"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={form} layout="vertical">
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入API Key名称' }]}
          >
            <Input placeholder="例如：生产环境主密钥" />
          </Form.Item>

          <Form.Item
            label="权限"
            name="permissions"
            initialValue={['read', 'write']}
            rules={[{ required: true, message: '请选择权限' }]}
          >
            <Select mode="multiple" placeholder="选择权限">
              <Select.Option value="read">读取 (Read)</Select.Option>
              <Select.Option value="write">写入 (Write)</Select.Option>
              <Select.Option value="delete">删除 (Delete)</Select.Option>
              <Select.Option value="admin">管理员 (Admin)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="速率限制 (请求/分钟)"
            name="rate_limit"
            initialValue={5000}
            rules={[{ required: true, message: '请输入速率限制' }]}
          >
            <Input placeholder="请输入速率限制" />
          </Form.Item>

          <Form.Item label="过期时间" name="expires_at">
            <Select placeholder="选择过期时间（可选）">
              <Select.Option value="">永不过期</Select.Option>
              <Select.Option value="30d">30天</Select.Option>
              <Select.Option value="90d">90天</Select.Option>
              <Select.Option value="180d">180天</Select.Option>
              <Select.Option value="365d">1年</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="备注" name="description">
            <TextArea rows={3} placeholder="可选的备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看API Key弹窗 */}
      <Modal
        title="查看 API Key"
        open={viewKeyModalVisible}
        onCancel={() => {
          setViewKeyModalVisible(false);
          setSelectedKey(null);
        }}
        footer={[
          <Button
            key="copy"
            type="primary"
            icon={<CopyOutlined />}
            onClick={() => selectedKey && handleCopyKey(selectedKey.key)}
          >
            复制完整密钥
          </Button>,
          <Button
            key="close"
            onClick={() => {
              setViewKeyModalVisible(false);
              setSelectedKey(null);
            }}
          >
            关闭
          </Button>,
        ]}
      >
        {selectedKey && (
          <div>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="名称">{selectedKey.name}</Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {selectedKey.created_at}
              </Descriptions.Item>
              <Descriptions.Item label="最后使用">
                {selectedKey.last_used}
              </Descriptions.Item>
              <Descriptions.Item label="权限">
                <Space>
                  {selectedKey.permissions.map((perm) => (
                    <Tag key={perm} color="purple">
                      {perm}
                    </Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="速率限制">
                {selectedKey.rate_limit}/分钟
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>完整API Key：</Text>
              <Input
                value={showFullKey ? selectedKey.key : '••••••••••••••••••••••••••••••••'}
                suffix={
                  <Button
                    type="text"
                    size="small"
                    icon={showFullKey ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                    onClick={() => setShowFullKey(!showFullKey)}
                  />
                }
                readOnly
              />
              <Alert
                message="请妥善保管此密钥，不要分享给他人"
                type="warning"
                showIcon
              />
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ApiManagement;

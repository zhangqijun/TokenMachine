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
  Switch,
  InputNumber,
  Alert,
  Divider,
  Popconfirm,
  Progress,
  Statistic,
  List,
} from 'antd';
import {
  ApiOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  BranchesOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ArrowRightOutlined,
  RocketOutlined,
  SafetyOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface RouteRule {
  id: string;
  name: string;
  path: string;
  type: 'semantic' | 'aggregate' | 'weighted';
  backends: Backend[];
  strategy: 'round-robin' | 'least-connections' | 'weighted' | 'random';
  enabled: boolean;
  status: 'active' | 'inactive' | 'error';
  totalRequests: number;
  avgLatency: number;
}

interface Backend {
  id: string;
  name: string;
  deploymentId: string;
  weight: number;
  health: 'healthy' | 'unhealthy' | 'unknown';
  url: string;
}

const ApiRouting = () => {
  const [routeModalVisible, setRouteModalVisible] = useState(false);
  const [backendModalVisible, setBackendModalVisible] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState<RouteRule | null>(null);
  const [form] = Form.useForm();
  const [backendForm] = Form.useForm();

  const [routes, setRoutes] = useState<RouteRule[]>([
    {
      id: '1',
      name: 'LLaMA-3 主路由',
      path: '/v1/chat/completions',
      type: 'weighted',
      backends: [
        {
          id: 'b1',
          name: 'llama-3-8b-prod-v1',
          deploymentId: 'dep-001',
          weight: 80,
          health: 'healthy',
          url: 'http://worker-01:8000',
        },
        {
          id: 'b2',
          name: 'llama-3-8b-prod-v2',
          deploymentId: 'dep-002',
          weight: 20,
          health: 'healthy',
          url: 'http://worker-02:8000',
        },
      ],
      strategy: 'weighted',
      enabled: true,
      status: 'active',
      totalRequests: 125000,
      avgLatency: 245,
    },
    {
      id: '2',
      name: 'Qwen-14B 路由',
      path: '/v1/chat/completions',
      type: 'semantic',
      backends: [
        {
          id: 'b3',
          name: 'qwen-14b-chat',
          deploymentId: 'dep-003',
          weight: 100,
          health: 'healthy',
          url: 'http://worker-03:8000',
        },
      ],
      strategy: 'round-robin',
      enabled: true,
      status: 'active',
      totalRequests: 45600,
      avgLatency: 520,
    },
    {
      id: '3',
      name: '聚合API路由',
      path: '/v1/models',
      type: 'aggregate',
      backends: [
        {
          id: 'b4',
          name: 'llama-3-8b',
          deploymentId: 'dep-001',
          weight: 50,
          health: 'healthy',
          url: 'http://worker-01:8000',
        },
        {
          id: 'b5',
          name: 'qwen-14b',
          deploymentId: 'dep-003',
          weight: 50,
          health: 'healthy',
          url: 'http://worker-03:8000',
        },
      ],
      strategy: 'round-robin',
      enabled: true,
      status: 'active',
      totalRequests: 8500,
      avgLatency: 120,
    },
    {
      id: '4',
      name: '测试路由',
      path: '/v1/chat/completions',
      type: 'weighted',
      backends: [
        {
          id: 'b6',
          name: 'test-model',
          deploymentId: 'dep-004',
          weight: 100,
          health: 'unhealthy',
          url: 'http://worker-04:8000',
        },
      ],
      strategy: 'weighted',
      enabled: false,
      status: 'error',
      totalRequests: 0,
      avgLatency: 0,
    },
  ]);

  const handleAddRoute = () => {
    setSelectedRoute(null);
    form.resetFields();
    setRouteModalVisible(true);
  };

  const handleEditRoute = (record: RouteRule) => {
    setSelectedRoute(record);
    form.setFieldsValue({
      name: record.name,
      path: record.path,
      type: record.type,
      strategy: record.strategy,
      enabled: record.enabled,
    });
    setRouteModalVisible(true);
  };

  const handleDeleteRoute = (id: string) => {
    setRoutes(routes.filter((r) => r.id !== id));
    message.success('路由规则已删除');
  };

  const handleToggleRoute = (id: string) => {
    setRoutes(
      routes.map((r) =>
        r.id === id ? { ...r, enabled: !r.enabled, status: !r.enabled ? 'active' : 'inactive' } : r
      )
    );
    message.success('路由状态已更新');
  };

  const handleSaveRoute = () => {
    form.validateFields().then((values) => {
      if (selectedRoute) {
        setRoutes(
          routes.map((r) =>
            r.id === selectedRoute.id ? { ...r, ...values } : r
          )
        );
        message.success('路由规则已更新');
      } else {
        const newRoute: RouteRule = {
          id: Date.now().toString(),
          ...values,
          backends: [],
          enabled: true,
          status: 'active',
          totalRequests: 0,
          avgLatency: 0,
        };
        setRoutes([...routes, newRoute]);
        message.success('路由规则已创建');
      }
      setRouteModalVisible(false);
      form.resetFields();
    });
  };

  const getTypeTag = (type: string) => {
    const config: Record<string, { color: string; label: string }> = {
      semantic: { color: 'blue', label: '语义路由' },
      aggregate: { color: 'green', label: 'API聚合' },
      weighted: { color: 'purple', label: '权重分配' },
    };
    const { color, label } = config[type];
    return <Tag color={color}>{label}</Tag>;
  };

  const getStrategyTag = (strategy: string) => {
    const config: Record<string, { label: string }> = {
      'round-robin': { label: '轮询' },
      'least-connections': { label: '最少连接' },
      weighted: { label: '加权' },
      random: { label: '随机' },
    };
    return <Tag>{config[strategy]?.label || strategy}</Tag>;
  };

  const getHealthStatus = (health: string) => {
    const config: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
      healthy: { color: 'success', icon: <CheckCircleOutlined />, label: '健康' },
      unhealthy: { color: 'error', icon: <CloseCircleOutlined />, label: '异常' },
      unknown: { color: 'default', icon: <SyncOutlined />, label: '未知' },
    };
    const { color, icon, label } = config[health];
    return (
      <Tag color={color} icon={icon}>
        {label}
      </Tag>
    );
  };

  const routeColumns = [
    {
      title: '路由名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      render: (path: string) => <Tag color="blue">{path}</Tag>,
    },
    {
      title: '路由类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => getTypeTag(type),
    },
    {
      title: '调度策略',
      dataIndex: 'strategy',
      key: 'strategy',
      render: (strategy: string) => getStrategyTag(strategy),
    },
    {
      title: '后端数',
      dataIndex: 'backends',
      key: 'backends',
      render: (backends: Backend[]) => (
        <Tag icon={<BranchesOutlined />}>{backends.length}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: RouteRule) => {
        const healthyCount = record.backends.filter((b) => b.health === 'healthy').length;
        return (
          <Space direction="vertical" size="small">
            <Tag color={status === 'active' ? 'success' : status === 'error' ? 'error' : 'default'}>
              {status === 'active' ? '活跃' : status === 'error' ? '异常' : '停用'}
            </Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {healthyCount}/{record.backends.length} 后端健康
            </Text>
          </Space>
        );
      },
    },
    {
      title: '请求数',
      dataIndex: 'totalRequests',
      key: 'totalRequests',
      render: (count: number) => count.toLocaleString(),
      sorter: (a: RouteRule, b: RouteRule) => a.totalRequests - b.totalRequests,
    },
    {
      title: '平均延迟',
      dataIndex: 'avgLatency',
      key: 'avgLatency',
      render: (latency: number) => `${latency}ms`,
      sorter: (a: RouteRule, b: RouteRule) => a.avgLatency - b.avgLatency,
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      width: 200,
      render: (_: any, record: RouteRule) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<BranchesOutlined />}
            onClick={() => setSelectedRoute(record)}
          >
            后端
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditRoute(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => handleToggleRoute(record.id)}
          >
            {record.enabled ? '禁用' : '启用'}
          </Button>
          <Popconfirm
            title="确定删除此路由？"
            onConfirm={() => handleDeleteRoute(record.id)}
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

  const backendColumns = [
    {
      title: '后端名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '部署ID',
      dataIndex: 'deploymentId',
      key: 'deploymentId',
      render: (id: string) => <Tag>{id}</Tag>,
    },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      render: (weight: number) => (
        <Space>
          <Progress
            type="circle"
            percent={weight}
            width={50}
            format={(percent) => `${percent}%`}
          />
        </Space>
      ),
    },
    {
      title: '健康状态',
      dataIndex: 'health',
      key: 'health',
      render: (health: string) => getHealthStatus(health),
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small">编辑</Button>
          <Button type="link" size="small" danger>
            移除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <BranchesOutlined />
            <span>API 路由管理</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddRoute}>
            添加路由
          </Button>
        }
      >
        <Alert
          message="API 路由说明"
          description="配置API请求路由规则，支持语义路由、API聚合、权重分配等策略。根据调度策略将请求分发到后端模型实例。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Tabs
          defaultActiveKey="routes"
          items={[
            {
              key: 'routes',
              label: '路由规则',
              children: (
                <Table
                  columns={routeColumns}
                  dataSource={routes}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 1400 }}
                />
              ),
            },
            {
              key: 'backends',
              label: '后端配置',
              children: selectedRoute ? (
                <div>
                  <Alert
                    message={`当前路由: ${selectedRoute.name}`}
                    description={selectedRoute.path}
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <Card
                    size="small"
                    title="后端实例"
                    extra={
                      <Button
                        type="primary"
                        size="small"
                        icon={<PlusOutlined />}
                        onClick={() => setBackendModalVisible(true)}
                      >
                        添加后端
                      </Button>
                    }
                  >
                    <Table
                      columns={backendColumns}
                      dataSource={selectedRoute.backends}
                      rowKey="id"
                      pagination={false}
                      size="small"
                    />
                  </Card>

                  <Card
                    size="small"
                    title="路由策略配置"
                    style={{ marginTop: 16 }}
                  >
                    <Form layout="vertical">
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item label="调度策略">
                            <Select defaultValue={selectedRoute.strategy}>
                              <Select.Option value="round-robin">轮询</Select.Option>
                              <Select.Option value="least-connections">最少连接</Select.Option>
                              <Select.Option value="weighted">加权轮询</Select.Option>
                              <Select.Option value="random">随机</Select.Option>
                            </Select>
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item label="健康检查间隔（秒）">
                            <InputNumber min={5} max={300} defaultValue={30} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item label="超时时间（毫秒）">
                            <InputNumber min={1000} max={60000} defaultValue={5000} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item label="最大重试次数">
                            <InputNumber min={0} max={5} defaultValue={3} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Form.Item
                        label="启用故障转移"
                        name="failover"
                        valuePropName="checked"
                        initialValue={true}
                      >
                        <Switch />
                      </Form.Item>

                      <Form.Item
                        label="启用断路器"
                        name="circuitBreaker"
                        valuePropName="checked"
                        initialValue={true}
                        extra="后端连续失败达到阈值时自动熔断"
                      >
                        <Switch />
                      </Form.Item>

                      <Form.Item label="熔断阈值（失败次数）">
                        <InputNumber min={3} max={50} defaultValue={10} style={{ width: '100%' }} />
                      </Form.Item>
                    </Form>
                  </Card>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <BranchesOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                  <div style={{ marginTop: 16 }}>
                    <Text type="secondary">请先选择一个路由规则</Text>
                  </div>
                </div>
              ),
            },
            {
              key: 'monitoring',
              label: '监控统计',
              children: (
                <div>
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="总请求数"
                          value={routes.reduce((sum, r) => sum + r.totalRequests, 0)}
                          suffix="次"
                          prefix={<ApiOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="活跃路由"
                          value={routes.filter((r) => r.enabled).length}
                          suffix="个"
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="健康后端"
                          value={routes.reduce(
                            (sum, r) => sum + r.backends.filter((b) => b.health === 'healthy').length,
                            0
                          )}
                          suffix="个"
                          valueStyle={{ color: '#1890ff' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card>
                        <Statistic
                          title="平均延迟"
                          value={Math.round(
                            routes.reduce((sum, r) => sum + r.avgLatency, 0) / routes.length
                          )}
                          suffix="ms"
                          valueStyle={{ color: '#cf1322' }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Card title="路由性能排行" size="small">
                    <List
                      dataSource={routes.filter((r) => r.enabled)}
                      renderItem={(route: RouteRule) => (
                        <List.Item>
                          <List.Item.Meta
                            avatar={
                              <Tag
                                color={route.avgLatency < 300 ? 'success' : route.avgLatency < 1000 ? 'warning' : 'error'}
                              >
                                {route.avgLatency}ms
                              </Tag>
                            }
                            title={route.name}
                            description={
                              <Space split={<Divider type="vertical" />}>
                                <Text type="secondary">{route.totalRequests.toLocaleString()} 次请求</Text>
                                <Text type="secondary">{route.backends.length} 个后端</Text>
                                <Text type="secondary">{route.path}</Text>
                              </Space>
                            }
                          />
                          <Progress
                            percent={Math.min(100, (route.avgLatency / 2000) * 100)}
                            status={route.avgLatency < 300 ? 'success' : route.avgLatency < 1000 ? 'normal' : 'exception'}
                            style={{ width: 150 }}
                          />
                        </List.Item>
                      )}
                    />
                  </Card>
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* 添加/编辑路由弹窗 */}
      <Modal
        title={selectedRoute ? '编辑路由规则' : '添加路由规则'}
        open={routeModalVisible}
        onOk={handleSaveRoute}
        onCancel={() => {
          setRouteModalVisible(false);
          form.resetFields();
        }}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="路由名称"
            name="name"
            rules={[{ required: true, message: '请输入路由名称' }]}
          >
            <Input placeholder="例如：LLaMA-3 主路由" />
          </Form.Item>

          <Form.Item
            label="API路径"
            name="path"
            rules={[{ required: true, message: '请输入API路径' }]}
          >
            <Select placeholder="选择API路径">
              <Select.Option value="/v1/chat/completions">/v1/chat/completions</Select.Option>
              <Select.Option value="/v1/completions">/v1/completions</Select.Option>
              <Select.Option value="/v1/embeddings">/v1/embeddings</Select.Option>
              <Select.Option value="/v1/models">/v1/models</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="路由类型"
            name="type"
            rules={[{ required: true, message: '请选择路由类型' }]}
            initialValue="weighted"
          >
            <Select>
              <Select.Option value="semantic">
                <Space>
                  <BranchesOutlined />
                  语义路由 - 根据请求内容智能路由
                </Space>
              </Select.Option>
              <Select.Option value="aggregate">
                <Space>
                  <ApiOutlined />
                  API聚合 - 聚合多个后端为单一接口
                </Space>
              </Select.Option>
              <Select.Option value="weighted">
                <Space>
                  <SettingOutlined />
                  权重分配 - 按权重分配流量
                </Space>
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="调度策略"
            name="strategy"
            rules={[{ required: true, message: '请选择调度策略' }]}
            initialValue="round-robin"
          >
            <Select>
              <Select.Option value="round-robin">轮询 (Round Robin)</Select.Option>
              <Select.Option value="least-connections">最少连接 (Least Connections)</Select.Option>
              <Select.Option value="weighted">加权轮询 (Weighted)</Select.Option>
              <Select.Option value="random">随机 (Random)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="启用路由" name="enabled" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加后端弹窗 */}
      <Modal
        title="添加后端实例"
        open={backendModalVisible}
        onOk={() => {
          message.success('后端实例已添加');
          setBackendModalVisible(false);
          backendForm.resetFields();
        }}
        onCancel={() => {
          setBackendModalVisible(false);
          backendForm.resetFields();
        }}
      >
        <Form form={backendForm} layout="vertical">
          <Form.Item label="后端名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="例如：llama-3-8b-prod-v1" />
          </Form.Item>

          <Form.Item label="选择部署" name="deploymentId" rules={[{ required: true }]}>
            <Select placeholder="选择一个部署">
              <Select.Option value="dep-001">llama-3-8b-prod-v1</Select.Option>
              <Select.Option value="dep-002">llama-3-8b-prod-v2</Select.Option>
              <Select.Option value="dep-003">qwen-14b-chat</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="后端URL" name="url" rules={[{ required: true }]}>
            <Input placeholder="http://worker-01:8000" />
          </Form.Item>

          <Form.Item label="权重" name="weight" initialValue={100}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApiRouting;

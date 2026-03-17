import { useState } from 'react';
import {
  Card,
  Button,
  Tag,
  Space,
  Progress,
  Dropdown,
  Modal,
  Form,
  Input,
  Select,
  Radio,
  InputNumber,
  Checkbox,
  message,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  EyeOutlined,
  SplitCellsOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

interface RoutingRule {
  pattern: string;
  target: string;
  weight: number;
  priority: number;
}

interface RoutingStrategy {
  id: string;
  name: string;
  description: string;
  mode: 'semantic' | 'weight' | 'round-robin' | 'least-conn';
  rules: RoutingRule[];
  isEnabled: boolean;
  boundKeys: number;
  todayRequests: number;
  p95Latency: number;
  createdAt: string;
}

const mockStrategies: RoutingStrategy[] = [
  {
    id: '1',
    name: 'qwen-智能路由',
    description: '根据模型名自动匹配到对应实例',
    mode: 'semantic',
    rules: [
      { pattern: 'qwen.*', target: 'qwen-2.5-7b (主实例)', weight: 90, priority: 1 },
      { pattern: 'qwen.*', target: 'qwen-2.5-7b (canary)', weight: 10, priority: 2 },
    ],
    isEnabled: true,
    boundKeys: 3,
    todayRequests: 125000,
    p95Latency: 450,
    createdAt: '2025-01-15',
  },
  {
    id: '2',
    name: 'llama-灰度发布',
    description: '新旧版本灰度发布',
    mode: 'weight',
    rules: [
      { pattern: 'llama.*', target: 'llama-3-8b-v2 (新版)', weight: 80, priority: 1 },
      { pattern: 'llama.*', target: 'llama-3-8b-v1 (旧版)', weight: 20, priority: 2 },
    ],
    isEnabled: true,
    boundKeys: 1,
    todayRequests: 45000,
    p95Latency: 320,
    createdAt: '2025-01-14',
  },
  {
    id: '3',
    name: '统一入口 (Round-Robin)',
    description: '平均分配到所有实例',
    mode: 'round-robin',
    rules: [
      { pattern: '*', target: 'llama-3-8b-1', weight: 25, priority: 1 },
      { pattern: '*', target: 'llama-3-8b-2', weight: 25, priority: 1 },
      { pattern: '*', target: 'qwen-2.5-7b', weight: 25, priority: 1 },
      { pattern: '*', target: 'glm-4-9b', weight: 25, priority: 1 },
    ],
    isEnabled: true,
    boundKeys: 5,
    todayRequests: 89000,
    p95Latency: 380,
    createdAt: '2025-01-13',
  },
];

const RoutingStrategy = () => {
  const [strategies, setStrategies] = useState<RoutingStrategy[]>(mockStrategies);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<RoutingStrategy | null>(null);
  const [form] = Form.useForm();

  const modeConfig = {
    semantic: { label: '语义路由', icon: '🧠', color: 'blue' },
    weight: { label: '权重路由', icon: '⚖️', color: 'green' },
    'round-robin': { label: '轮询路由', icon: '🔄', color: 'orange' },
    'least-conn': { label: '最少连接', icon: '📉', color: 'purple' },
  };

  const handleCreate = (values: any) => {
    const newStrategy: RoutingStrategy = {
      id: Date.now().toString(),
      name: values.name,
      description: values.description,
      mode: values.mode,
      rules: values.rules || [],
      isEnabled: true,
      boundKeys: 0,
      todayRequests: 0,
      p95Latency: 0,
      createdAt: dayjs().toISOString(),
    };
    setStrategies([...strategies, newStrategy]);
    setIsCreateModalOpen(false);
    form.resetFields();
    message.success('路由策略创建成功');
  };

  const handleEdit = (strategy: RoutingStrategy) => {
    setEditingStrategy(strategy);
    form.setFieldsValue(strategy);
    setIsCreateModalOpen(true);
  };

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个路由策略吗？',
      onOk: () => {
        setStrategies(strategies.filter((s) => s.id !== id));
        message.success('路由策略已删除');
      },
    });
  };

  const handleToggle = (id: string) => {
    setStrategies(
      strategies.map((s) =>
        s.id === id ? { ...s, isEnabled: !s.isEnabled } : s
      )
    );
  };

  const renderStrategyCard = (strategy: RoutingStrategy) => {
    const config = modeConfig[strategy.mode];

    return (
      <Card
        key={strategy.id}
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: 20 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <Space size="middle" align="center">
              <span style={{ fontSize: 16, fontWeight: 500 }}>{strategy.name}</span>
              <Tag color={strategy.isEnabled ? 'success' : 'default'}>
                {strategy.isEnabled ? '启用' : '禁用'} ●
              </Tag>
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'edit',
                      icon: <EditOutlined />,
                      label: '编辑',
                      onClick: () => handleEdit(strategy),
                    },
                    {
                      key: 'copy',
                      icon: <CopyOutlined />,
                      label: '复制配置',
                      onClick: () => {
                        navigator.clipboard.writeText(JSON.stringify(strategy, null, 2));
                        message.success('配置已复制到剪贴板');
                      },
                    },
                    {
                      key: 'toggle',
                      label: strategy.isEnabled ? '禁用' : '启用',
                      onClick: () => handleToggle(strategy.id),
                    },
                    {
                      type: 'divider' as const,
                    },
                    {
                      key: 'delete',
                      icon: <DeleteOutlined />,
                      label: '删除',
                      danger: true,
                      onClick: () => handleDelete(strategy.id),
                    },
                  ],
                }}
                trigger={['click']}
              >
                <Button type="text" size="small" icon={<EditOutlined />} />
              </Dropdown>
            </Space>

            <div style={{ color: '#666', fontSize: 13, marginTop: 4 }}>
              {config.icon} {config.label} • 实例数: {strategy.rules.length} • 创建: {dayjs(strategy.createdAt).format('YYYY-MM-DD')}
            </div>
          </div>
        </div>

        <div style={{ marginBottom: 12, fontSize: 13, fontWeight: 500, color: '#333' }}>
          路由规则:
        </div>

        {strategy.rules.map((rule, index) => (
          <div
            key={index}
            style={{
              background: index === 0 ? '#f0f5ff' : '#fafafa',
              padding: '8px 12px',
              borderRadius: 4,
              marginBottom: 6,
            }}
          >
            <Space size="large" style={{ width: '100%', justifyContent: 'space-between' }}>
              <span>
                <span style={{ fontWeight: 500 }}>{rule.target}</span>
                <Tag color={config.color} style={{ marginLeft: 8 }}>
                  P{rule.priority}
                </Tag>
              </span>
              <Progress
                percent={rule.weight}
                size="small"
                style={{ width: 120, margin: 0 }}
                format={(percent) => `${percent}%`}
              />
            </Space>
          </div>
        ))}

        <Divider style={{ margin: '12px 0' }} />

        <Row gutter={16}>
          <Col span={8}>
            <div style={{ fontSize: 13, color: '#666' }}>绑定密钥: {strategy.boundKeys} 个</div>
          </Col>
          <Col span={8}>
            <div style={{ fontSize: 13, color: '#666' }}>今日请求: {(strategy.todayRequests / 1000).toFixed(0)}K</div>
          </Col>
          <Col span={8}>
            <div style={{ fontSize: 13, color: '#666' }}>P95延迟: {strategy.p95Latency}ms</div>
          </Col>
        </Row>
      </Card>
    );
  };

  return (
    <div>
      <Card
        title="路由策略管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingStrategy(null);
              form.resetFields();
              setIsCreateModalOpen(true);
            }}
          >
            创建路由策略
          </Button>
        }
      >
        <div style={{ maxHeight: 'calc(100vh - 280px)', overflowY: 'auto' }}>
          {strategies.map((strategy) => renderStrategyCard(strategy))}
        </div>
      </Card>

      <Modal
        title={
          <Space>
            <SplitCellsOutlined />
            {editingStrategy ? '编辑路由策略' : '创建路由策略'}
          </Space>
        }
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          setEditingStrategy(null);
          form.resetFields();
        }}
        footer={null}
        width={640}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{
            mode: 'semantic',
            enableAggregation: true,
            responseMode: 'best',
          }}
        >
          <Card size="small" title="基本信息" style={{ marginBottom: 16 }}>
            <Form.Item
              label="策略名称"
              name="name"
              rules={[{ required: true, message: '请输入策略名称' }]}
            >
              <Input placeholder="qwen-智能路由" />
            </Form.Item>

            <Form.Item
              label="策略描述"
              name="description"
            >
              <Input.TextArea placeholder="根据模型名自动匹配到对应实例" rows={2} />
            </Form.Item>
          </Card>

          <Card size="small" title="路由模式" style={{ marginBottom: 16 }}>
            <Form.Item name="mode" rules={[{ required: true }]}>
              <Radio.Group>
                <Space direction="vertical">
                  <Radio value="semantic">⦿ 语义路由 (根据模型名称智能匹配)</Radio>
                  <Radio value="weight">○ 权重路由 (按指定比例分配流量)</Radio>
                  <Radio value="round-robin">○ 轮询路由 (平均分配到所有实例)</Radio>
                  <Radio value="least-conn">○ 最少连接 (路由到负载最低的实例)</Radio>
                </Space>
              </Radio.Group>
            </Form.Item>

            <Divider style={{ margin: '12px 0' }} />

            <div style={{ marginBottom: 12, fontWeight: 500 }}>路由规则配置:</div>

            <Form.List name="rules">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item
                        {...restField}
                        name={[name, 'pattern']}
                        rules={[{ required: true }]}
                      >
                        <Input placeholder="qwen.*" style={{ width: 140 }} />
                      </Form.Item>
                      <span>→</span>
                      <Form.Item
                        {...restField}
                        name={[name, 'target']}
                        rules={[{ required: true }]}
                      >
                        <Select placeholder="目标实例" style={{ width: 140 }} />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'weight']}
                        rules={[{ required: true }]}
                      >
                        <InputNumber min={0} max={100} formatter={(v) => `${v}%`} style={{ width: 80 }} />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'priority']}
                        rules={[{ required: true }]}
                      >
                        <InputNumber min={1} max={10} placeholder="P1" style={{ width: 60 }} />
                      </Form.Item>
                      <Button type="link" danger onClick={() => remove(name)}>
                        删除
                      </Button>
                    </Space>
                  ))}
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    添加规则
                  </Button>
                </>
              )}
            </Form.List>

            <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              💡 提示: 使用正则表达式匹配模型名，优先级越小越高
            </div>
          </Card>

          <Card size="small" title="API 端点聚合" style={{ marginBottom: 16 }}>
            <Form.Item name="enableAggregation" valuePropName="checked">
              <Checkbox>启用 API 聚合</Checkbox>
            </Form.Item>

            <Form.Item
              label="统一端点路径"
              name="unifiedEndpoint"
            >
              <Input placeholder="/v1/models/unified" />
            </Form.Item>

            <Form.Item label="统一端点响应模式">
              <Radio.Group>
                <Space direction="vertical">
                  <Radio value="best">⦿ 返回最佳结果</Radio>
                  <Radio value="all">○ 返回所有结果</Radio>
                  <Radio value="custom">○ 自定义</Radio>
                </Space>
              </Radio.Group>
            </Form.Item>
          </Card>

          <Card size="small" title="绑定 API 密钥" style={{ marginBottom: 16 }}>
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Checkbox value="prod">Production API Key</Checkbox>
                <Checkbox value="dev">Development Key</Checkbox>
                <Checkbox value="test">Testing Key</Checkbox>
              </Space>
            </Checkbox.Group>
          </Card>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setIsCreateModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                保存策略
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RoutingStrategy;

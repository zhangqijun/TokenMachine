import { useState } from 'react';
import {
  Card,
  Switch,
  Radio,
  InputNumber,
  Table,
  Button,
  Space,
  Tag,
  Checkbox,
  Timeline,
  Modal,
  message,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  HeartOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

interface HealthStatus {
  name: string;
  status: 'healthy' | 'warning' | 'failed';
  lastCheck: string;
  failCount: number;
}

interface FailoverEvent {
  time: string;
  sourceInstance: string;
  targetInstance: string;
  event: string;
}

const mockHealthStatus: HealthStatus[] = [
  { name: 'qwen-2.5-7b-1', status: 'healthy', lastCheck: '10秒前', failCount: 0 },
  { name: 'qwen-2.5-7b-2', status: 'healthy', lastCheck: '8秒前', failCount: 0 },
  { name: 'qwen-2.5-7b-3', status: 'warning', lastCheck: '5秒前', failCount: 1 },
  { name: 'llama-3-8b-1', status: 'healthy', lastCheck: '9秒前', failCount: 0 },
  { name: 'llama-3-8b-2', status: 'failed', lastCheck: '2分钟前', failCount: 5 },
  { name: 'glm-4-9b-1', status: 'healthy', lastCheck: '12秒前', failCount: 0 },
];

const mockFailoverEvents: FailoverEvent[] = [
  {
    time: '14:25:30',
    sourceInstance: 'llama-3-8b-2',
    targetInstance: 'qwen-2.5-7b-3',
    event: '标记为故障，自动转移',
  },
  {
    time: '14:23:15',
    sourceInstance: 'qwen-2.5-7b-1',
    targetInstance: 'qwen-2.5-7b-2',
    event: '响应超时，自动转移',
  },
];

const HealthCheck = () => {
  const [enableFailover, setEnableFailover] = useState(true);
  const [checkMethod, setCheckMethod] = useState<'active' | 'passive'>('active');
  const [checkInterval, setCheckInterval] = useState(10);
  const [timeout, setTimeout] = useState(5);
  const [failThreshold, setFailThreshold] = useState(3);
  const [responseTimeThreshold, setResponseTimeThreshold] = useState(5000);
  const [errorRateThreshold, setErrorRateThreshold] = useState(10);
  const [queueDepthThreshold, setQueueDepthThreshold] = useState(100);
  const [autoRecover, setAutoRecover] = useState(true);
  const [recoverThreshold, setRecoverThreshold] = useState(3);
  const [healthCheck, setHealthCheck] = useState(true);
  const [healthStatuses, setHealthStatuses] = useState<HealthStatus[]>(mockHealthStatus);
  const [failoverEvents, setFailoverEvents] = useState<FailoverEvent[]>(mockFailoverEvents);

  const handleManualFailover = () => {
    Modal.confirm({
      title: '手动触发故障转移',
      content: '确定要手动触发故障转移吗？这将把流量从故障实例转移到备用实例。',
      onOk: async () => {
        const delay = (ms: number): Promise<void> => {
          return new Promise<void>(resolve => {
            const timer = globalThis.setTimeout(() => resolve(), ms);
            void timer;
          });
        };
        await delay(1000);
        message.success('故障转移已触发');
      },
    });
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'healthy':
        return {
          icon: <CheckCircleOutlined />,
          color: 'success',
          text: '● 健康',
        };
      case 'warning':
        return {
          icon: <WarningOutlined />,
          color: 'warning',
          text: '⚠️ 警告',
        };
      case 'failed':
        return {
          icon: <CloseCircleOutlined />,
          color: 'error',
          text: '🔴 故障',
        };
      default:
        return {
          icon: <ClockCircleOutlined />,
          color: 'default',
          text: '○ 未知',
        };
    }
  };

  const columns = [
    {
      title: '实例名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <span style={{ fontWeight: 500 }}>{name}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = getStatusConfig(status);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
      filters: [
        { text: '健康', value: 'healthy' },
        { text: '警告', value: 'warning' },
        { text: '故障', value: 'failed' },
      ],
      onFilter: (value: boolean | React.Key, record: HealthStatus) => record.status === value,
    },
    {
      title: '最后检查',
      dataIndex: 'lastCheck',
      key: 'lastCheck',
      render: (time: string) => <span style={{ color: '#666' }}>{time}</span>,
    },
    {
      title: '失败次数',
      dataIndex: 'failCount',
      key: 'failCount',
      render: (count: number) => (
        <Tag color={count === 0 ? 'success' : count < 3 ? 'warning' : 'error'}>
          {count}
        </Tag>
      ),
      sorter: (a: HealthStatus, b: HealthStatus) => a.failCount - b.failCount,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: HealthStatus) => (
        <Button type="link" size="small" onClick={() => message.info(`查看 ${record.name} 详情`)}>
          详情
        </Button>
      ),
    },
  ];

  const healthyCount = healthStatuses.filter((s) => s.status === 'healthy').length;
  const warningCount = healthStatuses.filter((s) => s.status === 'warning').length;
  const failedCount = healthStatuses.filter((s) => s.status === 'failed').length;

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="健康实例"
              value={healthyCount}
              suffix={`/ ${healthStatuses.length}`}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="警告实例"
              value={warningCount}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="故障实例"
              value={failedCount}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="检查间隔"
              value={checkInterval}
              suffix="秒"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff', fontSize: 28 }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="全局健康检查配置"
        extra={
          <Space>
            <Button icon={<FileTextOutlined />} onClick={() => message.info('查看故障报告')}>
              查看故障报告
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => message.info('刷新中...')}>
              刷新
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={24}>
          <Col span={12}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>启用自动故障转移:</div>
              <Switch
                checked={enableFailover}
                onChange={setEnableFailover}
                checkedChildren="启用"
                unCheckedChildren="禁用"
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>健康检查配置:</div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ marginBottom: 8 }}>检查方式:</div>
                <Radio.Group
                  value={checkMethod}
                  onChange={(e) => setCheckMethod(e.target.value)}
                >
                  <Space direction="vertical">
                    <Radio value="active">⦿ 主动探测</Radio>
                    <Radio value="passive">○ 被动接收</Radio>
                  </Space>
                </Radio.Group>
              </div>

              <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                <div>
                  <div style={{ marginBottom: 4, fontSize: 13 }}>检查间隔</div>
                  <InputNumber
                    value={checkInterval}
                    onChange={(value) => setCheckInterval(value || 10)}
                    min={1}
                    max={300}
                    addonAfter="秒"
                  />
                </div>
                <div>
                  <div style={{ marginBottom: 4, fontSize: 13 }}>超时时间</div>
                  <InputNumber
                    value={timeout}
                    onChange={(value) => setTimeout(value || 5)}
                    min={1}
                    max={60}
                    addonAfter="秒"
                  />
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>故障判定条件:</div>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Checkbox checked={true}>
                  连续失败{' '}
                  <InputNumber
                    value={failThreshold}
                    onChange={(value) => setFailThreshold(value || 3)}
                    min={1}
                    max={10}
                    size="small"
                    style={{ width: 70, margin: '0 4px' }}
                  />{' '}
                  次标记为故障
                </Checkbox>
                <Checkbox checked={true}>
                  响应时间 &gt;{' '}
                  <InputNumber
                    value={responseTimeThreshold}
                    onChange={(value) => setResponseTimeThreshold(value || 5000)}
                    min={100}
                    max={30000}
                    size="small"
                    style={{ width: 90, margin: '0 4px' }}
                  />{' '}
                  ms 标记为故障
                </Checkbox>
                <Checkbox checked={true}>
                  错误率 &gt;{' '}
                  <InputNumber
                    value={errorRateThreshold}
                    onChange={(value) => setErrorRateThreshold(value || 10)}
                    min={1}
                    max={100}
                    size="small"
                    style={{ width: 70, margin: '0 4px' }}
                  />{' '}
                  % 标记为故障
                </Checkbox>
                <Checkbox checked={true}>
                  队列深度 &gt;{' '}
                  <InputNumber
                    value={queueDepthThreshold}
                    onChange={(value) => setQueueDepthThreshold(value || 100)}
                    min={10}
                    max={500}
                    size="small"
                    style={{ width: 80, margin: '0 4px' }}
                  />{' '}
                  标记为过载
                </Checkbox>
              </Space>
            </div>
          </Col>

          <Col span={12}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>恢复策略:</div>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Checkbox
                  checked={autoRecover}
                  onChange={(e) => setAutoRecover(e.target.checked)}
                >
                  连续成功{' '}
                  <InputNumber
                    value={recoverThreshold}
                    onChange={(value) => setRecoverThreshold(value || 3)}
                    min={1}
                    max={10}
                    size="small"
                    disabled={!autoRecover}
                    style={{ width: 70, margin: '0 4px' }}
                  />{' '}
                  次自动恢复
                </Checkbox>
                <Checkbox checked={true}>健康检查通过自动恢复</Checkbox>
              </Space>
            </div>

            <div style={{
              padding: 16,
              background: '#f0f5ff',
              border: '1px solid #adc6ff',
              borderRadius: 4,
            }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>
                <HeartOutlined /> 健康检查流程
              </div>
              <div style={{ fontSize: 12, color: '#666', lineHeight: 1.6 }}>
                <div style={{ marginBottom: 4 }}>1. 每隔 {checkInterval} 秒探测所有实例</div>
                <div style={{ marginBottom: 4 }}>2. 判定状态: 健康 / 警告 / 故障</div>
                <div style={{ marginBottom: 4 }}>3. 实例故障时自动转移到备用实例</div>
                <div>4. 持续检查并自动恢复健康实例</div>
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      <Card
        title="实例健康状态"
        style={{ marginBottom: 16 }}
      >
        <Table
          dataSource={healthStatuses}
          columns={columns}
          rowKey="name"
          pagination={false}
          size="middle"
        />
      </Card>

      <Card
        title="故障转移历史"
        extra={
          <Button type="link" onClick={() => message.info('查看完整历史')}>
            查看完整历史
          </Button>
        }
      >
        <Timeline
          items={failoverEvents.map((event, index) => ({
            dot: <ThunderboltOutlined style={{ fontSize: 16 }} />,
            color: index === 0 ? 'red' : 'blue',
            children: (
              <div>
                <div style={{ marginBottom: 4, fontWeight: 500 }}>{event.time}</div>
                <div style={{ fontSize: 13, color: '#666' }}>
                  <span style={{ fontWeight: 500 }}>{event.sourceInstance}</span>
                  <span style={{ margin: '0 8px' }}>→</span>
                  <span style={{ fontWeight: 500, color: '#52c41a' }}>{event.targetInstance}</span>
                </div>
                <div style={{ fontSize: 13, color: '#999' }}>{event.event}</div>
              </div>
            ),
          }))}
        />
      </Card>
    </div>
  );
};

export default HealthCheck;

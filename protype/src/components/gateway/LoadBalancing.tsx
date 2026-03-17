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
  Progress,
  message,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  ReloadOutlined,
  SettingOutlined,
  DownloadOutlined,
  UploadOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
} from '@ant-design/icons';

interface InstanceLoad {
  name: string;
  queueDepth: number;
  responseTime: number;
  gpuUtilization: number;
  status: 'healthy' | 'warning' | 'overload';
}

const mockInstances: InstanceLoad[] = [
  { name: 'qwen-2.5-7b-1', queueDepth: 23, responseTime: 250, gpuUtilization: 78, status: 'healthy' },
  { name: 'qwen-2.5-7b-2', queueDepth: 15, responseTime: 280, gpuUtilization: 82, status: 'healthy' },
  { name: 'qwen-2.5-7b-3', queueDepth: 5, responseTime: 310, gpuUtilization: 65, status: 'healthy' },
  { name: 'llama-3-8b-1', queueDepth: 45, responseTime: 420, gpuUtilization: 71, status: 'healthy' },
  { name: 'llama-3-8b-2', queueDepth: 38, responseTime: 390, gpuUtilization: 68, status: 'healthy' },
  { name: 'glm-4-9b-1', queueDepth: 12, responseTime: 380, gpuUtilization: 55, status: 'healthy' },
];

const LoadBalancing = () => {
  const [enableDynamicLB, setEnableDynamicLB] = useState(true);
  const [scheduleStrategy, setScheduleStrategy] = useState<'queue' | 'response' | 'resource' | 'combined'>('queue');
  const [queueThreshold, setQueueThreshold] = useState(50);
  const [responseThreshold, setResponseThreshold] = useState(5000);
  const [gpuThreshold, setGpuThreshold] = useState(95);
  const [instances, setInstances] = useState<InstanceLoad[]>(mockInstances);
  const [loading, setLoading] = useState(false);

  const handleRebalance = async () => {
    setLoading(true);
    // Simulate rebalancing
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(false);
    message.success('负载已重新平衡');
  };

  const handleExportConfig = () => {
    const config = {
      enableDynamicLB,
      scheduleStrategy,
      queueThreshold,
      responseThreshold,
      gpuThreshold,
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'load-balancing-config.json';
    a.click();
    URL.revokeObjectURL(url);
    message.success('配置已导出');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'overload':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy':
        return '●';
      case 'warning':
        return '⚠️';
      case 'overload':
        return '🔴';
      default:
        return '○';
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
      title: '队列深度',
      dataIndex: 'queueDepth',
      key: 'queueDepth',
      render: (depth: number) => (
        <div style={{ width: 100 }}>
          <Progress
            percent={(depth / 100) * 100}
            format={() => depth}
            status={depth > 80 ? 'exception' : 'normal'}
            size="small"
          />
        </div>
      ),
      sorter: (a: InstanceLoad, b: InstanceLoad) => a.queueDepth - b.queueDepth,
    },
    {
      title: '响应时间',
      dataIndex: 'responseTime',
      key: 'responseTime',
      render: (time: number) => (
        <Space>
          <span>{time}ms</span>
          <Progress
            percent={(time / 1000) * 100}
            showInfo={false}
            strokeColor={time > 500 ? '#ff4d4f' : time > 300 ? '#faad14' : '#52c41a'}
            size="small"
            style={{ width: 60 }}
          />
        </Space>
      ),
      sorter: (a: InstanceLoad, b: InstanceLoad) => a.responseTime - b.responseTime,
    },
    {
      title: 'GPU 利用率',
      dataIndex: 'gpuUtilization',
      key: 'gpuUtilization',
      render: (utilization: number) => (
        <div style={{ width: 100 }}>
          <Progress
            percent={utilization}
            status={utilization > 95 ? 'exception' : 'normal'}
            size="small"
            format={(percent) => `${percent}%`}
          />
        </div>
      ),
      sorter: (a: InstanceLoad, b: InstanceLoad) => a.gpuUtilization - b.gpuUtilization,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
  ];

  const strategyConfig = {
    queue: {
      title: '队列深度优先',
      description: '优先路由到队列最短的实例',
      advantage: '最大化吞吐量',
      disadvantage: '可能忽略响应时间',
      icon: <DashboardOutlined />,
    },
    response: {
      title: '响应时间优先',
      description: '优先路由到响应最快的实例',
      advantage: '优化用户体验',
      disadvantage: '可能导致负载不均',
      icon: <ThunderboltOutlined />,
    },
    resource: {
      title: '资源利用率优先',
      description: '优先路由到 GPU 利用率低的实例',
      advantage: '最大化资源利用',
      disadvantage: '可能影响性能',
      icon: <DashboardOutlined />,
    },
    combined: {
      title: '综合评分',
      description: '综合考虑多个指标的加权评分',
      advantage: '平衡多种因素',
      disadvantage: '配置复杂',
      icon: <SettingOutlined />,
    },
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总实例数"
              value={instances.length}
              prefix={<DashboardOutlined />}
              valueStyle={{ color: '#1890ff', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均队列深度"
              value={(instances.reduce((sum, i) => sum + i.queueDepth, 0) / instances.length).toFixed(1)}
              prefix={<DashboardOutlined />}
              valueStyle={{ color: '#52c41a', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均响应时间"
              value={(instances.reduce((sum, i) => sum + i.responseTime, 0) / instances.length).toFixed(0)}
              prefix={<ClockCircleOutlined />}
              suffix="ms"
              valueStyle={{ color: '#faad14', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均 GPU 利用率"
              value={(instances.reduce((sum, i) => sum + i.gpuUtilization, 0) / instances.length).toFixed(1)}
              prefix={<ThunderboltOutlined />}
              suffix="%"
              valueStyle={{ color: '#722ed1', fontSize: 28 }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="全局负载均衡策略"
        extra={
          <Space>
            <Button icon={<SettingOutlined />}>全局设置</Button>
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
              <div style={{ marginBottom: 8, fontWeight: 500 }}>启用动态负载均衡:</div>
              <Switch
                checked={enableDynamicLB}
                onChange={setEnableDynamicLB}
                checkedChildren="启用"
                unCheckedChildren="禁用"
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>调度策略:</div>
              <Radio.Group
                value={scheduleStrategy}
                onChange={(e) => setScheduleStrategy(e.target.value)}
                style={{ width: '100%' }}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  {Object.entries(strategyConfig).map(([key, config]) => (
                    <Radio key={key} value={key} style={{ display: 'flex', alignItems: 'flex-start' }}>
                      <span style={{ marginTop: 2 }}>
                        {config.icon} {config.title}
                      </span>
                    </Radio>
                  ))}
                </Space>
              </Radio.Group>
            </div>

            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4, fontSize: 13 }}>
              <div style={{ marginBottom: 8 }}>
                <strong>说明:</strong> {strategyConfig[scheduleStrategy].description}
              </div>
              <div style={{ color: '#52c41a' }}>
                优点: {strategyConfig[scheduleStrategy].advantage}
              </div>
              <div style={{ color: '#ff4d4f' }}>
                缺点: {strategyConfig[scheduleStrategy].disadvantage}
              </div>
            </div>
          </Col>

          <Col span={12}>
            <div style={{ marginBottom: 16, fontWeight: 500 }}>触发阈值:</div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span>队列深度阈值:</span>
                <InputNumber
                  value={queueThreshold}
                  onChange={(value) => setQueueThreshold(value || 50)}
                  min={1}
                  max={200}
                  addonAfter="请求"
                />
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>
                队列深度超过 {queueThreshold} 时自动切换到空闲实例
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span>响应时间阈值:</span>
                <InputNumber
                  value={responseThreshold}
                  onChange={(value) => setResponseThreshold(value || 5000)}
                  min={100}
                  max={30000}
                  addonAfter="ms"
                />
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>
                响应时间超过 {responseThreshold}ms 时切换到更快实例
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span>GPU 利用率阈值:</span>
                <InputNumber
                  value={gpuThreshold}
                  onChange={(value) => setGpuThreshold(value || 95)}
                  min={50}
                  max={100}
                  addonAfter="%"
                />
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>
                GPU 利用率超过 {gpuThreshold}% 时避免分配新请求
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      <Card
        title="实时负载监控"
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={handleExportConfig}>
              导出配置
            </Button>
            <Button icon={<UploadOutlined />}>
              导入配置
            </Button>
            <Button type="primary" icon={<ReloadOutlined />} loading={loading} onClick={handleRebalance}>
              手动重新平衡
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={instances}
          columns={columns}
          rowKey="name"
          pagination={false}
          size="middle"
        />
      </Card>
    </div>
  );
};

export default LoadBalancing;

import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Select,
  Button,
  Space,
  Progress,
  Table,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Radio,
  Checkbox,
  message,
} from 'antd';
import {
  ReloadOutlined,
  DownloadOutlined,
  BellOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

interface MonitoringData {
  qps: number;
  qpsChange: number;
  p95Latency: number;
  p95Change: number;
  availability: number;
  instanceCount: number;
}

const mockMonitoringData: MonitoringData = {
  qps: 125400,
  qpsChange: 12,
  p95Latency: 45,
  p95Change: -8,
  availability: 99.8,
  instanceCount: 6,
};

const topApiKeys = [
  { name: 'Production Key', requests: 85000, percent: 85 },
  { name: 'Development Key', requests: 12000, percent: 12 },
  { name: 'Testing Key', requests: 3000, percent: 3 },
];

const topStrategies = [
  { name: 'qwen-智能路由', requests: 98000, percent: 78 },
  { name: 'llama-灰度', requests: 15000, percent: 12 },
  { name: '统一入口', requests: 12000, percent: 10 },
];

const MonitoringStats = () => {
  const [timeRange, setTimeRange] = useState<'1h' | 'today' | 'week' | 'custom'>('1h');
  const [dimension, setDimension] = useState<'key' | 'strategy' | 'model'>('key');
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [form] = Form.useForm();

  const data = mockMonitoringData;

  const handleExportData = () => {
    const exportData = {
      timeRange,
      dimension,
      ...data,
      topApiKeys,
      topStrategies,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gateway-monitoring-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('数据已导出');
  };

  const handleCreateAlert = (values: any) => {
    message.success('告警规则已创建');
    setIsAlertModalOpen(false);
    form.resetFields();
  };

  return (
    <div>
      <Card
        title="网关监控仪表盘"
        extra={
          <Space>
            <Select
              value={timeRange}
              onChange={setTimeRange}
              style={{ width: 120 }}
              options={[
                { label: '最近1小时', value: '1h' },
                { label: '今天', value: 'today' },
                { label: '本周', value: 'week' },
                { label: '自定义', value: 'custom' },
              ]}
            />
            <Button icon={<ReloadOutlined />}>
              实时刷新: 5s
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="QPS"
                value={data.qps}
                valueStyle={{ color: '#1890ff', fontSize: 28 }}
                prefix={<DashboardOutlined />}
                suffix={
                  <span style={{ fontSize: 14, color: data.qpsChange >= 0 ? '#52c41a' : '#ff4d4f' }}>
                    {data.qpsChange >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                    {Math.abs(data.qpsChange)}%
                  </span>
                }
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="P95延迟"
                value={data.p95Latency}
                valueStyle={{ color: '#722ed1', fontSize: 28 }}
                prefix={
                  <>
                    <ThunderboltOutlined />
                    <span style={{ fontSize: 14, color: data.p95Change >= 0 ? '#ff4d4f' : '#52c41a', marginLeft: 8 }}>
                      {data.p95Change >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                      {Math.abs(data.p95Change)}ms
                    </span>
                  </>
                }
                suffix="ms"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="可用率"
                value={data.availability}
                valueStyle={{ color: '#52c41a', fontSize: 28 }}
                prefix={<CheckCircleOutlined />}
                suffix="%"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="实例数"
                value={data.instanceCount}
                valueStyle={{ color: '#faad14', fontSize: 28 }}
                suffix={`/ 8`}
                prefix={<DashboardOutlined />}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        <Col span={16}>
          <Card
            title="按维度分析"
            style={{ marginBottom: 16 }}
          >
            <Space direction="vertical" style={{ marginBottom: 16, width: '100%' }}>
              <Select
                value={dimension}
                onChange={setDimension}
                style={{ width: 200 }}
                options={[
                  { label: '按 API 密钥', value: 'key' },
                  { label: '按路由策略', value: 'strategy' },
                  { label: '按模型', value: 'model' },
                ]}
              />

              {dimension === 'key' && (
                <>
                  <div style={{ fontWeight: 500, marginBottom: 12 }}>Top 5 API 密钥 (按请求数)</div>
                  {topApiKeys.map((key) => (
                    <div key={key.name} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span>{key.name}</span>
                        <span style={{ color: '#666' }}>{key.requests.toLocaleString()}</span>
                      </div>
                      <Progress percent={key.percent} size="small" />
                    </div>
                  ))}
                </>
              )}

              {dimension === 'strategy' && (
                <>
                  <div style={{ fontWeight: 500, marginBottom: 12 }}>Top 5 路由策略 (按请求数)</div>
                  {topStrategies.map((strategy) => (
                    <div key={strategy.name} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span>{strategy.name}</span>
                        <span style={{ color: '#666' }}>{strategy.requests.toLocaleString()}</span>
                      </div>
                      <Progress percent={strategy.percent} size="small" />
                    </div>
                  ))}
                </>
              )}

              {dimension === 'model' && (
                <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>
                  按模型维度分析开发中...
                </div>
              )}
            </Space>
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title="告警配置"
            extra={
              <Button type="primary" icon={<BellOutlined />} onClick={() => setIsAlertModalOpen(true)}>
                添加告警
              </Button>
            }
          >
            <div style={{ marginBottom: 16 }}>
              <Table
                size="small"
                pagination={false}
                dataSource={[
                  {
                    key: '1',
                    name: 'QPS 异常告警',
                    metric: 'QPS',
                    condition: '高于阈值',
                    threshold: '15000',
                    triggered: 3,
                    lastTriggered: '5分钟前',
                  },
                  {
                    key: '2',
                    name: '延迟告警',
                    metric: 'P95延迟',
                    condition: '高于阈值',
                    threshold: '5000ms',
                    triggered: 1,
                    lastTriggered: '1小时前',
                  },
                ]}
                columns={[
                  { title: '规则名称', dataIndex: 'name', key: 'name' },
                  { title: '指标', dataIndex: 'metric', key: 'metric' },
                  { title: '触发', dataIndex: 'triggered', key: 'triggered', render: (v) => `${v} 次` },
                ]}
              />
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        title="操作"
        style={{ marginTop: 16 }}
      >
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExportData}>
            导出数据
          </Button>
          <Button icon={<BellOutlined />} onClick={() => setIsAlertModalOpen(true)}>
            配置告警
          </Button>
        </Space>
      </Card>

      <Modal
        title="配置告警规则"
        open={isAlertModalOpen}
        onCancel={() => {
          setIsAlertModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateAlert}
          initialValues={{
            condition: 'higher',
            duration: 5,
            enableEmail: true,
            enableWebhook: false,
            enableWechat: false,
            enableDingtalk: false,
          }}
        >
          <Form.Item
            label="告警规则名称"
            name="name"
            rules={[{ required: true, message: '请输入告警规则名称' }]}
          >
            <Input placeholder="QPS 异常告警" />
          </Form.Item>

          <Form.Item
            label="监控指标"
            name="metric"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { label: 'QPS', value: 'qps' },
                { label: 'P95延迟', value: 'p95_latency' },
                { label: '错误率', value: 'error_rate' },
                { label: '可用率', value: 'availability' },
              ]}
            />
          </Form.Item>

          <Form.Item
            label="触发条件"
            name="condition"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { label: '高于阈值', value: 'higher' },
                { label: '低于阈值', value: 'lower' },
              ]}
            />
          </Form.Item>

          <Form.Item
            label="阈值"
            name="threshold"
            rules={[{ required: true, message: '请输入阈值' }]}
          >
            <Input placeholder="15000" />
          </Form.Item>

          <Form.Item
            label="持续时间"
            name="duration"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={60} addonAfter="分钟" style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="通知方式">
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical">
                <Checkbox value="email" name="enableEmail">邮件</Checkbox>
                <Checkbox value="webhook" name="enableWebhook">Webhook</Checkbox>
                <Checkbox value="wechat" name="enableWechat">企业微信</Checkbox>
                <Checkbox value="dingtalk" name="enableDingtalk">钉钉</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Form.Item
            label="通知接收人"
            name="recipients"
            rules={[{ required: true, message: '请输入通知接收人' }]}
          >
            <Input placeholder="admin@tokenmachine.com" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setIsAlertModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                保存规则
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MonitoringStats;

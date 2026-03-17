import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Form,
  Input,
  Select,
  Switch,
  Button,
  Space,
  Typography,
  Divider,
  InputNumber,
  Tabs,
  Table,
  Tag,
  Alert,
  Slider,
  message,
} from 'antd';
import {
  MonitorOutlined,
  WarningOutlined,
  BellOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SaveOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface AlertRule {
  id: string;
  name: string;
  metric: string;
  condition: string;
  threshold: number;
  duration: string;
  severity: 'info' | 'warning' | 'critical';
  enabled: boolean;
}

const MonitoringSettings = () => {
  const [form] = Form.useForm();

  const alertRules: AlertRule[] = [
    {
      id: '1',
      name: 'GPU温度告警',
      metric: 'gpu.temperature',
      condition: '>',
      threshold: 80,
      duration: '5m',
      severity: 'warning',
      enabled: true,
    },
    {
      id: '2',
      name: 'GPU显存使用率',
      metric: 'gpu.memory_usage',
      condition: '>',
      threshold: 95,
      duration: '10m',
      severity: 'critical',
      enabled: true,
    },
    {
      id: '3',
      name: 'API响应时间',
      metric: 'api.response_time',
      condition: '>',
      threshold: 3000,
      duration: '5m',
      severity: 'warning',
      enabled: true,
    },
    {
      id: '4',
      name: '磁盘空间不足',
      metric: 'disk.usage_percent',
      condition: '>',
      threshold: 90,
      duration: '15m',
      severity: 'critical',
      enabled: true,
    },
    {
      id: '5',
      name: '服务可用性',
      metric: 'service.availability',
      condition: '<',
      threshold: 99,
      duration: '5m',
      severity: 'critical',
      enabled: false,
    },
  ];

  const metrics = [
    { key: 'gpu.temperature', name: 'GPU温度', unit: '°C' },
    { key: 'gpu.memory_usage', name: 'GPU显存使用率', unit: '%' },
    { key: 'gpu.utilization', name: 'GPU利用率', unit: '%' },
    { key: 'api.response_time', name: 'API响应时间', unit: 'ms' },
    { key: 'api.error_rate', name: 'API错误率', unit: '%' },
    { key: 'cpu.usage', name: 'CPU使用率', unit: '%' },
    { key: 'memory.usage', name: '内存使用率', unit: '%' },
    { key: 'disk.usage_percent', name: '磁盘使用率', unit: '%' },
    { key: 'disk.io_wait', name: '磁盘IO等待', unit: '%' },
    { key: 'network.bandwidth', name: '网络带宽使用', unit: 'Mbps' },
    { key: 'service.availability', name: '服务可用性', unit: '%' },
    { key: 'queue.pending_tasks', name: '队列待处理任务', unit: '个' },
  ];

  const conditions = [
    { label: '大于', value: '>' },
    { label: '小于', value: '<' },
    { label: '等于', value: '=' },
    { label: '大于等于', value: '>=' },
    { label: '小于等于', value: '<=' },
  ];

  const handleSave = () => {
    form.validateFields().then(() => {
      message.success('监控设置保存成功');
    });
  };

  const severityConfig = {
    info: { color: 'blue', label: '信息' },
    warning: { color: 'orange', label: '警告' },
    critical: { color: 'red', label: '严重' },
  };

  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '监控指标',
      dataIndex: 'metric',
      key: 'metric',
      render: (metric: string) => {
        const item = metrics.find((m) => m.key === metric);
        return <Tag color="blue">{item?.name || metric}</Tag>;
      },
    },
    {
      title: '触发条件',
      key: 'condition',
      render: (_: any, record: AlertRule) => (
        <Space>
          <Tag>{record.condition}</Tag>
          <Text strong>{record.threshold}</Text>
        </Space>
      ),
    },
    {
      title: '持续时间',
      dataIndex: 'duration',
      key: 'duration',
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const config = severityConfig[severity as keyof typeof severityConfig];
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />}>
            编辑
          </Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>
            删除
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
            <MonitorOutlined />
            <span>监控告警设置</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="rules"
          items={[
            {
              key: 'rules',
              label: '告警规则',
              children: (
                <div>
                  <Alert
                    message="告警规则说明"
                    description="当监控指标满足触发条件并持续指定时间后，系统将发送告警通知。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <div
                    style={{
                      marginBottom: 16,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <Text strong>告警规则列表 ({alertRules.length})</Text>
                    <Button type="primary" size="small" icon={<PlusOutlined />}>
                      添加规则
                    </Button>
                  </div>

                  <Table
                    columns={ruleColumns}
                    dataSource={alertRules}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                    size="small"
                  />
                </div>
              ),
            },
            {
              key: 'basic',
              label: '基础设置',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>监控基础配置</Text>
                    <Divider style={{ margin: '12px 0' }} />
                  </div>

                  <Form
                    form={form}
                    layout="vertical"
                    initialValues={{
                      scrape_interval: 15,
                      scrape_timeout: 10,
                      retention_period: 15,
                      enable_metrics: true,
                      enable_logs: true,
                      enable_traces: false,
                    }}
                  >
                    <Row gutter={16}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label="数据采集间隔"
                          name="scrape_interval"
                          tooltip="Prometheus采集指标数据的间隔时间"
                        >
                          <InputNumber
                            min={5}
                            max={300}
                            suffix="秒"
                            style={{ width: '100%' }}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label="采集超时时间"
                          name="scrape_timeout"
                          tooltip="单次采集任务的超时时间"
                        >
                          <InputNumber min={1} max={60} suffix="秒" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={16}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label="数据保留时间"
                          name="retention_period"
                          tooltip="监控数据的保留时间"
                        >
                          <InputNumber min={1} max={90} suffix="天" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={12}>
                        <Form.Item label="存储空间限制" name="storage_limit" initialValue={100}>
                          <InputNumber min={10} max={1000} suffix="GB" style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Divider>监控功能开关</Divider>

                    <Form.Item
                      label="启用指标采集"
                      name="enable_metrics"
                      valuePropName="checked"
                      extra="采集系统性能指标数据"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item
                      label="启用日志采集"
                      name="enable_logs"
                      valuePropName="checked"
                      extra="采集应用日志并索引"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item
                      label="启用链路追踪"
                      name="enable_traces"
                      valuePropName="checked"
                      extra="追踪请求调用链路"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item>
                      <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                        保存设置
                      </Button>
                    </Form.Item>
                  </Form>
                </div>
              ),
            },
            {
              key: 'thresholds',
              label: '阈值配置',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>默认告警阈值</Text>
                    <Divider style={{ margin: '12px 0' }} />
                  </div>

                  <Form layout="vertical">
                    <Card size="small" title="GPU 告警阈值" style={{ marginBottom: 16 }}>
                      <Form.Item
                        label={`温度告警: ${form.getFieldValue('gpu_temp') || 80}°C`}
                        name="gpu_temp"
                        initialValue={80}
                      >
                        <Slider min={50} max={100} marks={{ 60: '60°C', 80: '80°C', 90: '90°C' }} />
                      </Form.Item>

                      <Form.Item
                        label={`显存使用率: ${form.getFieldValue('gpu_memory') || 90}%`}
                        name="gpu_memory"
                        initialValue={90}
                      >
                        <Slider min={50} max={100} marks={{ 70: '70%', 85: '85%', 95: '95%' }} />
                      </Form.Item>

                      <Form.Item
                        label={`GPU利用率: ${form.getFieldValue('gpu_util') || 95}%`}
                        name="gpu_util"
                        initialValue={95}
                      >
                        <Slider min={50} max={100} marks={{ 75: '75%', 90: '90%', 98: '98%' }} />
                      </Form.Item>
                    </Card>

                    <Card size="small" title="系统资源告警阈值" style={{ marginBottom: 16 }}>
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item label="CPU使用率 (%)" name="cpu_usage" initialValue={85}>
                            <InputNumber min={50} max={100} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item label="内存使用率 (%)" name="memory_usage" initialValue={90}>
                            <InputNumber min={50} max={100} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item label="磁盘使用率 (%)" name="disk_usage" initialValue={85}>
                            <InputNumber min={50} max={100} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item label="磁盘IO等待 (%)" name="disk_io" initialValue={60}>
                            <InputNumber min={10} max={100} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>
                    </Card>

                    <Card size="small" title="API 服务告警阈值">
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item label="响应时间 (ms)" name="api_latency" initialValue={3000}>
                            <InputNumber min={100} max={10000} step={100} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item label="错误率 (%)" name="api_error_rate" initialValue={5}>
                            <InputNumber min={0.1} max={50} step={0.1} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item label="QPS阈值" name="api_qps" initialValue={10000}>
                            <InputNumber min={100} max={100000} step={100} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item label="可用性 (%)" name="api_availability" initialValue={99}>
                            <InputNumber min={90} max={100} step={0.1} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>
                    </Card>

                    <Form.Item style={{ marginTop: 24 }}>
                      <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                        保存阈值
                      </Button>
                    </Form.Item>
                  </Form>
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default MonitoringSettings;

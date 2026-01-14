import { Card, Row, Col, Table, Tag, Progress, Space, Select, DatePicker, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { useStore } from '../store';
import { mockTimeSeriesData } from '../mock/data';
import type { Deployment } from '../mock/data';

const { RangePicker } = DatePicker;

const Monitoring = () => {
  const { gpus, deployments } = useStore();

  // Prepare chart data
  const timestamps = mockTimeSeriesData.map(d => dayjs(d.timestamp).format('HH:mm'));
  const qpsData = mockTimeSeriesData.map(d => d.qps);
  const latencyData = mockTimeSeriesData.map(d => d.latency);
  const tokensData = mockTimeSeriesData.map(d => d.tokens / 1000);
  const gpuUtilData = mockTimeSeriesData.map(d => d.gpuUtil);

  // Combined metrics chart
  const metricsChartOption = {
    title: { text: 'API QPS & 延迟趋势', left: 'center' },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: { data: ['QPS', '延迟(ms)'], bottom: 10 },
    xAxis: { type: 'category', data: timestamps },
    yAxis: [
      { type: 'value', name: 'QPS', position: 'left' },
      { type: 'value', name: '延迟(ms)', position: 'right' },
    ],
    series: [
      {
        name: 'QPS',
        data: qpsData,
        type: 'line',
        smooth: true,
        itemStyle: { color: '#1890ff' },
        areaStyle: { opacity: 0.2 },
      },
      {
        name: '延迟(ms)',
        data: latencyData,
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        itemStyle: { color: '#52c41a' },
      },
    ],
    grid: { left: 50, right: 50, bottom: 50, top: 60 },
  };

  // Tokens chart
  const tokensChartOption = {
    title: { text: 'Token 消耗趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: timestamps },
    yAxis: { type: 'value', name: 'K Tokens' },
    series: [{
      data: tokensData,
      type: 'bar',
      itemStyle: { color: '#722ed1' },
    }],
    grid: { left: 50, right: 20, bottom: 30, top: 60 },
  };

  // GPU utilization chart
  const gpuUtilizationChartOption = {
    title: { text: 'GPU 利用率 (%)', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: timestamps },
    yAxis: { type: 'value', name: '%', min: 0, max: 100 },
    series: [{
      data: gpuUtilData,
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.3 },
      itemStyle: { color: '#faad14' },
    }],
    grid: { left: 50, right: 20, bottom: 30, top: 60 },
    markLine: {
      data: [{ yAxis: 80, label: { formatter: '警告线' } }],
      lineStyle: { color: '#ff4d4f', type: 'dashed' },
    },
  };

  // GPU details columns
  const gpuColumns = [
    {
      title: 'GPU',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '显存',
      key: 'memory',
      render: (_: unknown, record: { memory_used_mb: number; memory_total_mb: number }) => {
        const percent = (record.memory_used_mb / record.memory_total_mb) * 100;
        return (
          <div>
            <Progress
              percent={percent}
              size="small"
              status={percent > 90 ? 'exception' : percent > 70 ? 'active' : 'normal'}
              format={() => `${(record.memory_used_mb / 1024).toFixed(1)} / ${(record.memory_total_mb / 1024).toFixed(1)} GB`}
            />
          </div>
        );
      },
    },
    {
      title: '利用率',
      dataIndex: 'utilization_percent',
      key: 'utilization_percent',
      render: (percent: number) => (
        <Progress
          type="circle"
          percent={Math.round(percent)}
          width={50}
          status={percent > 90 ? 'exception' : 'normal'}
        />
      ),
    },
    {
      title: '温度',
      dataIndex: 'temperature_celsius',
      key: 'temperature_celsius',
      render: (temp: number) => {
        const color = temp > 80 ? '#ff4d4f' : temp > 70 ? '#faad14' : '#52c41a';
        return <span style={{ color, fontWeight: 500 }}>{temp}°C</span>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; text: string }> = {
          available: { color: 'success', text: '可用' },
          in_use: { color: 'processing', text: '使用中' },
          error: { color: 'error', text: '错误' },
        };
        return <Tag color={config[status].color}>{config[status].text}</Tag>;
      },
    },
  ];

  // Model performance columns
  const modelColumns = [
    {
      title: '部署名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: 'QPS',
      dataIndex: 'qps',
      key: 'qps',
      render: (qps: number) => qps > 0 ? qps.toFixed(0) : '-',
      sorter: (a: Deployment, b: Deployment) => a.qps - b.qps,
    },
    {
      title: 'P50 延迟',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      render: (latency: number) => latency > 0 ? `${latency}ms` : '-',
    },
    {
      title: '副本数',
      dataIndex: 'replicas',
      key: 'replicas',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; text: string }> = {
          running: { color: 'success', text: '运行中' },
          starting: { color: 'processing', text: '启动中' },
          stopped: { color: 'default', text: '已停止' },
          error: { color: 'error', text: '错误' },
        };
        return <Tag color={config[status].color}>{config[status].text}</Tag>;
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>监控面板</h2>
        <Space>
          <RangePicker
            defaultValue={[dayjs().subtract(24, 'hours'), dayjs()]}
            showTime
            format="YYYY-MM-DD HH:mm"
          />
          <Select defaultValue="24h" style={{ width: 100 }}>
            <Select.Option value="1h">1 小时</Select.Option>
            <Select.Option value="6h">6 小时</Select.Option>
            <Select.Option value="24h">24 小时</Select.Option>
            <Select.Option value="7d">7 天</Select.Option>
          </Select>
        </Space>
      </div>

      {/* Overview Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>平均 QPS</div>
            <div style={{ fontSize: 28, fontWeight: 'bold', color: '#1890ff' }}>
              {Math.round(qpsData.reduce((a, b) => a + b, 0) / qpsData.length)}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>平均延迟</div>
            <div style={{ fontSize: 28, fontWeight: 'bold', color: '#52c41a' }}>
              {Math.round(latencyData.reduce((a, b) => a + b, 0) / latencyData.length)} ms
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>GPU 平均利用率</div>
            <div style={{ fontSize: 28, fontWeight: 'bold', color: '#faad14' }}>
              {Math.round(gpuUtilData.reduce((a, b) => a + b, 0) / gpuUtilData.length)}%
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>Token 消耗</div>
            <div style={{ fontSize: 28, fontWeight: 'bold', color: '#722ed1' }}>
              {(tokensData.reduce((a, b) => a + b, 0) / 1000).toFixed(0)}K
            </div>
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card
            title="API 性能指标"
            extra={<Button icon={<ReloadOutlined />} size="small">刷新</Button>}
          >
            <ReactECharts option={metricsChartOption} style={{ height: 350 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="Token 消耗">
            <ReactECharts option={tokensChartOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="GPU 利用率">
            <ReactECharts option={gpuUtilizationChartOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>

      {/* Tables */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="模型性能排行" bordered={false}>
            <Table
              dataSource={deployments.filter(d => d.status === 'running')}
              columns={modelColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="GPU 详细状态" bordered={false}>
            <Table
              dataSource={gpus}
              columns={gpuColumns}
              rowKey="id"
              size="small"
              pagination={false}
              scroll={{ y: 300 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Monitoring;

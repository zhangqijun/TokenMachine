import { useState, useEffect } from 'react';
import { Card, Row, Col, Table, Tag, Progress, Space, Select, DatePicker, Button, Statistic } from 'antd';
import {
  ReloadOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { useStore } from '../store';
import { mockTimeSeriesData } from '../mock/data';
import type { Deployment } from '../mock/data';
import FuncTooltip from '../components/FuncTooltip';

const { RangePicker } = DatePicker;

const Monitoring = () => {
  const { gpus, deployments } = useStore();
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState<number>(5);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Auto refresh effect
  useEffect(() => {
    if (!autoRefresh) return;

    const timer = setInterval(() => {
      setLastRefresh(new Date());
      // 这里可以添加实际的数据刷新逻辑
    }, refreshInterval * 1000);

    return () => clearInterval(timer);
  }, [autoRefresh, refreshInterval]);

  // Prepare chart data
  const timestamps = mockTimeSeriesData.map(d => dayjs(d.timestamp).format('HH:mm'));
  const qpsData = mockTimeSeriesData.map(d => d.qps);
  const latencyData = mockTimeSeriesData.map(d => d.latency);
  const tokensData = mockTimeSeriesData.map(d => d.tokens / 1000);
  const gpuUtilData = mockTimeSeriesData.map(d => d.gpuUtil);

  // Calculate stats
  const avgQPS = Math.round(qpsData.reduce((a, b) => a + b, 0) / qpsData.length);
  const avgLatency = Math.round(latencyData.reduce((a, b) => a + b, 0) / latencyData.length);
  const avgGPU = Math.round(gpuUtilData.reduce((a, b) => a + b, 0) / gpuUtilData.length);
  const totalTokens = Math.round(tokensData.reduce((a, b) => a + b, 0));

  // Additional stats
  const maxQPS = Math.max(...qpsData);
  const minQPS = Math.min(...qpsData);
  const p95Latency = Math.round(latencyData.sort((a, b) => a - b)[Math.floor(latencyData.length * 0.95)]);
  const p99Latency = Math.round(latencyData.sort((a, b) => a - b)[Math.floor(latencyData.length * 0.99)]);
  const errorRate = 0.02; // 2% error rate
  const totalRequests = qpsData.reduce((a, b) => a + b, 0) * 60; // Total requests in time range

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
        <h2 style={{ margin: 0 }}>
          监控面板
          <FuncTooltip
            title="监控面板功能"
            description="实时监控系统运行状态和性能指标。\n\n• QPS/延迟趋势图\n• GPU利用率监控\n• Token消耗统计\n• 告警事件列表"
            placement="right"
          >
            <InfoCircleOutlined style={{ fontSize: 16, color: '#999', marginLeft: 8, cursor: 'help' }} />
          </FuncTooltip>
        </h2>
        <Space>
          <FuncTooltip
            title="刷新间隔"
            description="设置自动刷新数据的时间间隔。\n\n• 5秒：高频监控\n• 10秒：标准监控\n• 30秒：低频监控\n• 1分钟：概览模式"
          >
            <Select
              value={refreshInterval}
              onChange={setRefreshInterval}
              style={{ width: 120 }}
              disabled={!autoRefresh}
            >
              <Select.Option value={5}>5 秒</Select.Option>
              <Select.Option value={10}>10 秒</Select.Option>
              <Select.Option value={30}>30 秒</Select.Option>
              <Select.Option value={60}>1 分钟</Select.Option>
            </Select>
          </FuncTooltip>
          <FuncTooltip
            title="自动刷新开关"
            description="开启后系统将按设定间隔自动刷新监控数据。\n\n• 开启：实时监控\n• 关闭：手动刷新"
          >
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? '自动刷新开' : '自动刷新关'}
            </Button>
          </FuncTooltip>
          <FuncTooltip
            title="手动刷新"
            description="立即刷新监控数据，不受自动刷新间隔限制。"
          >
            <Button icon={<ReloadOutlined />}>
              手动刷新
            </Button>
          </FuncTooltip>
          <FuncTooltip
            title="时间范围选择"
            description="选择要查看的时间范围。\n\n• 自定义时间区间\n• 精确到分钟\n• 支持历史数据查看"
          >
            <RangePicker
              defaultValue={[dayjs().subtract(24, 'hours'), dayjs()]}
              showTime
              format="YYYY-MM-DD HH:mm"
            />
          </FuncTooltip>
          <FuncTooltip
            title="快捷时间选择"
            description="快速选择常用时间范围。\n\n• 1小时：实时监控\n• 6小时：短期趋势\n• 24小时：日监控\n• 7天：周统计"
          >
            <Select defaultValue="24h" style={{ width: 100 }}>
              <Select.Option value="1h">1 小时</Select.Option>
              <Select.Option value="6h">6 小时</Select.Option>
              <Select.Option value="24h">24 小时</Select.Option>
              <Select.Option value="7d">7 天</Select.Option>
            </Select>
          </FuncTooltip>
        </Space>
      </div>

      {/* Auto refresh indicator */}
      {autoRefresh && (
        <div style={{ marginBottom: 16, padding: '8px 16px', background: '#f0f5ff', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
          <span style={{ fontSize: 13, color: '#595959' }}>
            自动刷新已启用，每 {refreshInterval} 秒更新一次 • 上次更新：{dayjs(lastRefresh).format('HH:mm:ss')}
          </span>
        </div>
      )}

      {/* Overview Stats - 8 cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={3}>
          <Card>
            <Statistic
              title="平均 QPS"
              value={avgQPS}
              valueStyle={{ color: '#1890ff', fontSize: 24 }}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card>
            <Statistic
              title="峰值 QPS"
              value={maxQPS}
              valueStyle={{ color: '#722ed1', fontSize: 24 }}
              prefix={<ArrowUpOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card>
            <Statistic
              title="平均延迟"
              value={avgLatency}
              suffix="ms"
              valueStyle={{ color: '#52c41a', fontSize: 24 }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card>
            <Statistic
              title="P95 延迟"
              value={p95Latency}
              suffix="ms"
              valueStyle={{ color: '#faad14', fontSize: 24 }}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card>
            <Statistic
              title="P99 延迟"
              value={p99Latency}
              suffix="ms"
              valueStyle={{ color: '#ff4d4f', fontSize: 24 }}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card>
            <Statistic
              title="GPU 利用率"
              value={avgGPU}
              suffix="%"
              valueStyle={{ color: '#13c2c2', fontSize: 24 }}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card>
            <Statistic
              title="Token 消耗"
              value={totalTokens}
              valueStyle={{ color: '#eb2f96', fontSize: 24 }}
              formatter={(value) => `${Number(value).toLocaleString()}`}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card>
            <Statistic
              title="错误率"
              value={errorRate * 100}
              suffix="%"
              valueStyle={{ color: errorRate > 0.05 ? '#ff4d4f' : '#52c41a', fontSize: 24 }}
              prefix={<WarningOutlined />}
            />
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

      {/* Tables - Enhanced with more data */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card title="API 请求统计详情" bordered={false}>
            <Table
              dataSource={[
                { key: '1', endpoint: '/v1/chat/completions', requests: 125400, avgLatency: 45, p95: 78, p99: 120, errorRate: 0.01 },
                { key: '2', endpoint: '/v1/embeddings', requests: 45200, avgLatency: 23, p95: 45, p99: 67, errorRate: 0.02 },
                { key: '3', endpoint: '/v1/completions', requests: 32100, avgLatency: 38, p95: 72, p99: 105, errorRate: 0.03 },
                { key: '4', endpoint: '/v1/models', requests: 8900, avgLatency: 12, p95: 25, p99: 38, errorRate: 0.00 },
              ]}
              columns={[
                { title: 'API 端点', dataIndex: 'endpoint', key: 'endpoint', width: 250 },
                {
                  title: '请求数',
                  dataIndex: 'requests',
                  key: 'requests',
                  render: (v) => v.toLocaleString(),
                  sorter: (a: any, b: any) => a.requests - b.requests,
                },
                {
                  title: '平均延迟',
                  dataIndex: 'avgLatency',
                  key: 'avgLatency',
                  render: (v) => `${v}ms`,
                  sorter: (a: any, b: any) => a.avgLatency - b.avgLatency,
                },
                {
                  title: 'P95 延迟',
                  dataIndex: 'p95',
                  key: 'p95',
                  render: (v) => `${v}ms`,
                },
                {
                  title: 'P99 延迟',
                  dataIndex: 'p99',
                  key: 'p99',
                  render: (v) => `${v}ms`,
                },
                {
                  title: '错误率',
                  dataIndex: 'errorRate',
                  key: 'errorRate',
                  render: (v) => (
                    <span style={{ color: v > 0.02 ? '#ff4d4f' : '#52c41a' }}>
                      {(v * 100).toFixed(2)}%
                    </span>
                  ),
                  sorter: (a: any, b: any) => a.errorRate - b.errorRate,
                },
              ]}
              rowKey="key"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
      </Row>

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

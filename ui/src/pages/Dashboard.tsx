import { Card, Row, Col, Statistic, Progress, Table, Tag } from 'antd';
import {
  ArrowUpOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { useStore } from '../store';
import { mockTimeSeriesData } from '../mock/data';

const Dashboard = () => {
  const { stats, deployments, gpus } = useStore();

  // Prepare chart data
  const timestamps = mockTimeSeriesData.map(d => dayjs(d.timestamp).format('HH:mm'));
  const qpsData = mockTimeSeriesData.map(d => d.qps);
  const gpuUtilData = mockTimeSeriesData.map(d => d.gpuUtil);

  // QPS Chart option
  const qpsChartOption = {
    title: { text: 'API QPS (每秒请求数)', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: timestamps },
    yAxis: { type: 'value', name: 'QPS' },
    series: [{
      data: qpsData,
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.3 },
      itemStyle: { color: '#1890ff' },
    }],
    grid: { left: 50, right: 20, bottom: 30, top: 50 },
  };

  // GPU Utilization Chart option
  const gpuChartOption = {
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
    grid: { left: 50, right: 20, bottom: 30, top: 50 },
  };

  // Active deployments columns
  const deploymentColumns = [
    {
      title: '部署名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: '环境',
      dataIndex: 'environment',
      key: 'environment',
      render: (env: string) => {
        const colors: Record<string, string> = {
          prod: 'red',
          staging: 'orange',
          dev: 'blue',
          test: 'green',
        };
        return <Tag color={colors[env]}>{env.toUpperCase()}</Tag>;
      },
    },
    {
      title: '副本数',
      dataIndex: 'replicas',
      key: 'replicas',
    },
    {
      title: 'QPS',
      dataIndex: 'qps',
      key: 'qps',
      render: (qps: number) => qps > 0 ? qps : '-',
    },
    {
      title: '延迟',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      render: (latency: number) => latency > 0 ? `${latency}ms` : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusConfig: Record<string, { color: string; text: string }> = {
          running: { color: 'success', text: '运行中' },
          starting: { color: 'processing', text: '启动中' },
          stopping: { color: 'default', text: '停止中' },
          stopped: { color: 'default', text: '已停止' },
          error: { color: 'error', text: '错误' },
        };
        const config = statusConfig[status] || statusConfig.stopped;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
  ];

  // GPU status columns
  const gpuColumns = [
    {
      title: 'GPU ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '显存使用',
      key: 'memory',
      render: (_: unknown, record: { memory_used_mb: number; memory_total_mb: number }) => (
        <Progress
          percent={Math.round((record.memory_used_mb / record.memory_total_mb) * 100)}
          size="small"
          format={() => `${(record.memory_used_mb / 1024).toFixed(1)}GB / ${(record.memory_total_mb / 1024).toFixed(1)}GB`}
        />
      ),
    },
    {
      title: '利用率',
      dataIndex: 'utilization_percent',
      key: 'utilization_percent',
      render: (percent: number) => `${percent.toFixed(1)}%`,
    },
    {
      title: '温度',
      dataIndex: 'temperature_celsius',
      key: 'temperature_celsius',
      render: (temp: number) => (
        <span style={{ color: temp > 80 ? '#ff4d4f' : temp > 70 ? '#faad14' : 'inherit' }}>
          {temp}°C
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusConfig: Record<string, { color: string; text: string }> = {
          available: { color: 'success', text: '可用' },
          'in_use': { color: 'processing', text: '使用中' },
          error: { color: 'error', text: '错误' },
        };
        const config = statusConfig[status] || statusConfig.available;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>仪表盘</h2>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="API 调用 (今日)"
              value={stats.apiCallsToday}
              formatter={(value) => `${Number(value).toLocaleString()}`}
              prefix={<ApiOutlined />}
              suffix={<span style={{ fontSize: 14, color: '#52c41a' }}>
                <ArrowUpOutlined /> 12.5%
              </span>}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Token 消耗 (本月)"
              value={stats.tokensUsed}
              suffix={`/ ${(stats.tokensQuota / 1000000).toFixed(0)}M`}
              prefix={<ThunderboltOutlined />}
            />
            <Progress
              percent={(stats.tokensUsed / stats.tokensQuota) * 100}
              showInfo={false}
              strokeColor="#1890ff"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="GPU 利用率"
              value={stats.gpuUtilization}
              precision={1}
              suffix="%"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: stats.gpuUtilization > 80 ? '#ff4d4f' : '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行模型"
              value={stats.runningModels}
              suffix={`/ ${stats.totalModels}`}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={16}>
          <Card title="API QPS 趋势" bordered={false}>
            <ReactECharts option={qpsChartOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="GPU 利用率" bordered={false}>
            <ReactECharts option={gpuChartOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      {/* Tables */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="活跃部署" bordered={false}>
            <Table
              dataSource={deployments.filter(d => d.status === 'running' || d.status === 'starting')}
              columns={deploymentColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="GPU 状态" bordered={false}>
            <Table
              dataSource={gpus}
              columns={gpuColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;

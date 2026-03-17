import { Card, Row, Col, Table, Tag, Progress, Timeline, Space } from 'antd';
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  FireOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useStore } from '../store';
import FuncTooltip from '../components/FuncTooltip';

// ============================================
// 假数据区域 - 原型演示数据
// ============================================

// 实时指标假数据
const realtimeMetrics = {
  qps: 12540,
  tps: 2540000,
  ttft: 45,
  tpot: 12,
  activeDeployments: 8,
};

// GPU 集群状态假数据
const gpuClusterStatus = {
  available: 12,
  inUse: 18,
  error: 2,
  total: 32,
};

// 存储状态假数据
const storageStatus = {
  models: { used: 450, total: 1000, unit: 'GB' },
  logs: { used: 120, total: 500, unit: 'GB' },
};

// 热门模型假数据
const topModels = [
  { rank: 1, name: 'qwen-14b-chat', currentQps: 3240, todayCalls: 156000, status: 'running' },
  { rank: 2, name: 'llama-3-8b-instruct', currentQps: 2850, todayCalls: 142000, status: 'running' },
  { rank: 3, name: 'qwen-vl-plus', currentQps: 1980, todayCalls: 98000, status: 'running' },
  { rank: 4, name: 'deepseek-coder-33b', currentQps: 1560, todayCalls: 76000, status: 'running' },
  { rank: 5, name: 'chatglm3-6b', currentQps: 980, todayCalls: 45000, status: 'running' },
];

// 最近事件假数据
const recentEvents = [
  {
    time: '2分钟前',
    type: 'success',
    title: '部署完成',
    description: 'qwen-14b-chat 在 worker-01 上部署成功',
    icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  },
  {
    time: '15分钟前',
    type: 'warning',
    title: 'GPU 温度警告',
    description: 'worker-03: GPU:2 温度达到 82°C',
    icon: <WarningOutlined style={{ color: '#faad14' }} />,
  },
  {
    time: '32分钟前',
    type: 'error',
    title: 'API 错误率异常',
    description: 'deepseek-coder-33b 错误率超过 5%',
    icon: <WarningOutlined style={{ color: '#ff4d4f' }} />,
  },
  {
    time: '1小时前',
    type: 'info',
    title: '模型更新',
    description: 'llama-3-8b-instruct 更新到 v2.1',
    icon: <ClockCircleOutlined style={{ color: '#1890ff' }} />,
  },
  {
    time: '2小时前',
    type: 'success',
    title: '自动扩容',
    description: 'qwen-vl-plus 副本数自动扩容到 2',
    icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  },
];

// ============================================
// 功能描述配置
// ============================================
const funcDescriptions = {
  qps: {
    title: '实时 QPS（每秒查询数）',
    desc: '显示系统当前的每秒请求数量。\n\n• 反映系统实时吞吐量\n• 可点击查看历史趋势\n• 支持按模型维度筛选'
  },
  tps: {
    title: 'TPS（每秒Token数）',
    desc: '显示系统当前每秒处理的Token数量。\n\n• 包含输入和输出Token\n• 体现模型推理能力\n• 用于计算成本'
  },
  ttft: {
    title: 'TTFT（首Token延迟）',
    desc: 'Time To First Token，首次Token生成延迟。\n\n• 衡量响应速度\n• 影响用户体验\n• 值越低越好'
  },
  tpot: {
    title: 'TPOT（输出Token延迟）',
    desc: 'Time Per Output Token，每个输出Token的平均延迟。\n\n• 衡量生成速度\n• 影响长文本体验\n• 值越低越好'
  },
  vram: {
    title: '显存占用率',
    desc: 'GPU显存使用情况。\n\n• 监控显存瓶颈\n• 影响模型加载\n• 支持显存碎片整理'
  },
  gpuUtil: {
    title: 'GPU 利用率',
    desc: 'GPU计算资源使用情况。\n\n• 反映硬件利用效率\n• 过低表示资源浪费\n• 过高可能存在排队'
  },
  activeDeployments: {
    title: '活跃部署',
    desc: '当前正在运行的模型部署列表。\n\n• 显示部署基本信息\n• 可快速操作启停\n• 支持扩缩容'
  },
  gpuCluster: {
    title: 'GPU 集群状态',
    desc: '整体GPU资源分布情况。\n\n• 可用/使用中/故障统计\n• 支持按节点查看\n• 点击进入详情页'
  },
  storage: {
    title: '存储状态',
    desc: '模型和日志存储使用情况。\n\n• 模型文件占用空间\n• 运行日志占用空间\n• 支持清理策略配置'
  },
  topModels: {
    title: '热门模型 Top 5',
    desc: '按调用量排名的模型列表。\n\n• 实时QPS统计\n• 今日累计调用量\n• 可点击查看详情'
  },
  recentEvents: {
    title: '最近事件',
    desc: '系统重要事件时间线。\n\n• 部署状态变更\n• 资源告警信息\n• 自动扩缩容记录'
  }
};

const Dashboard = () => {
  const { deployments, gpus } = useStore();

  // 迷你图表配置
  const getSparklineOption = (data: number[], color: string) => ({
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { show: false, type: 'category' },
    yAxis: { show: false, type: 'value' },
    series: [{
      data,
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { color, width: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: color + '40' },
            { offset: 1, color: color + '00' },
          ],
        },
      },
    }],
  });

  // GPU饼图配置
  const gpuPieOption = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 10, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      data: [
        { value: gpuClusterStatus.available, name: '可用', itemStyle: { color: '#52c41a' } },
        { value: gpuClusterStatus.inUse, name: '使用中', itemStyle: { color: '#1890ff' } },
        { value: gpuClusterStatus.error, name: '故障', itemStyle: { color: '#ff4d4f' } },
      ],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)',
        },
      },
      label: {
        formatter: '{b}: {c} ({d}%)',
      },
    }],
  };

  // 部署表格列配置
  const deploymentColumns = [
    {
      title: <FuncTooltip title="部署名称" description="部署的唯一标识名称，点击可查看详情">部署名称 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: <FuncTooltip title="模型" description="部署所使用的模型名称和版本">模型 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: <FuncTooltip title="环境" description="部署环境：PROD(生产)、STAGING(预发布)、DEV(开发)、TEST(测试)">环境 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
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
      title: <FuncTooltip title="副本数" description="当前运行的副本实例数量，可手动扩缩容">副本数 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'replicas',
      key: 'replicas',
    },
    {
      title: <FuncTooltip title="QPS" description="当前实时每秒查询数">QPS <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'qps',
      key: 'qps',
      render: (qps: number) => qps > 0 ? qps : '-',
    },
    {
      title: <FuncTooltip title="延迟" description="平均请求响应延迟">延迟 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      render: (latency: number) => latency > 0 ? `${latency}ms` : '-',
    },
    {
      title: <FuncTooltip title="状态" description="运行状态：运行中/启动中/停止中/已停止/错误">状态 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
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

  // 热门模型表格列配置
  const topModelsColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank: number) => (
        <span style={{
          display: 'inline-block',
          width: 24,
          height: 24,
          lineHeight: '24px',
          textAlign: 'center',
          borderRadius: '50%',
          background: rank <= 3 ? '#1890ff' : '#f0f0f0',
          color: rank <= 3 ? '#fff' : '#666',
          fontWeight: rank <= 3 ? 'bold' : 'normal',
        }}>
          {rank}
        </span>
      ),
    },
    {
      title: <FuncTooltip title="模型名称" description="点击可查看模型详情和调用统计">模型名称 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <span style={{ fontWeight: 500, cursor: 'pointer', color: '#1890ff' }}>{text}</span>,
    },
    {
      title: <FuncTooltip title="当前 QPS" description="该模型的实时每秒查询数">当前 QPS <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'currentQps',
      key: 'currentQps',
      render: (qps: number) => (
        <span style={{ color: '#1890ff', fontWeight: 500 }}>
          {qps.toLocaleString()}
        </span>
      ),
    },
    {
      title: <FuncTooltip title="今日调用量" description="今日累计请求次数">今日调用量 <InfoCircleOutlined style={{fontSize: 12, color: '#999'}}/></FuncTooltip>,
      dataIndex: 'todayCalls',
      key: 'todayCalls',
      render: (calls: number) => calls.toLocaleString(),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; text: string }> = {
          running: { color: 'success', text: '运行中' },
        };
        const statusConfig = config[status] || { color: 'default', text: status };
        return <Tag color={statusConfig.color}>{statusConfig.text}</Tag>;
      },
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>仪表盘</h2>

      {/* 顶部 - 实时指标卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <FuncTooltip {...funcDescriptions.qps}>
            <Card
              style={{
                borderTop: '3px solid #1890ff',
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                cursor: 'help'
              }}
              bodyStyle={{ padding: '20px 24px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: 'linear-gradient(135deg, #1890ff20 0%, #1890ff10 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 12,
                  }}>
                    <ThunderboltOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 2 }}>实时 QPS</div>
                    <div style={{ fontSize: 28, fontWeight: 600, color: '#262626', lineHeight: 1 }}>
                      {realtimeMetrics.qps.toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Tag color="success" style={{ margin: 0, fontSize: 12 }}>
                  <ArrowUpOutlined /> +8.5%
                </Tag>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>较上小时</span>
              </div>
              <ReactECharts
                option={getSparklineOption([12000, 12300, 12100, 12540, 12400, 12600, 12540], '#1890ff')}
                style={{ height: 36, marginTop: 8 }}
              />
            </Card>
          </FuncTooltip>
        </Col>

        <Col span={4}>
          <FuncTooltip {...funcDescriptions.tps}>
            <Card
              style={{
                borderTop: '3px solid #722ed1',
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                cursor: 'help'
              }}
              bodyStyle={{ padding: '20px 24px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: 'linear-gradient(135deg, #722ed120 0%, #722ed110 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 12,
                  }}>
                    <FireOutlined style={{ fontSize: 24, color: '#722ed1' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 2 }}>TPS</div>
                    <div style={{ fontSize: 28, fontWeight: 600, color: '#262626', lineHeight: 1 }}>
                      {(realtimeMetrics.tps / 1000000).toFixed(1)}M
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>tokens/s</span>
              </div>
              <ReactECharts
                option={getSparklineOption([2400, 2480, 2520, 2490, 2540, 2530, 2540], '#722ed1')}
                style={{ height: 36, marginTop: 8 }}
              />
            </Card>
          </FuncTooltip>
        </Col>

        <Col span={4}>
          <FuncTooltip {...funcDescriptions.ttft}>
            <Card
              style={{
                borderTop: '3px solid #52c41a',
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                cursor: 'help'
              }}
              bodyStyle={{ padding: '20px 24px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: 'linear-gradient(135deg, #52c41a20 0%, #52c41a10 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 12,
                  }}>
                    <ClockCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 2 }}>TTFT</div>
                    <div style={{ fontSize: 28, fontWeight: 600, color: '#262626', lineHeight: 1 }}>
                      {realtimeMetrics.ttft}<span style={{ fontSize: 14, marginLeft: 2, color: '#8c8c8c' }}>ms</span>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>首token延迟</span>
              </div>
              <ReactECharts
                option={getSparklineOption([48, 46, 45, 47, 44, 45, 45], '#52c41a')}
                style={{ height: 36, marginTop: 8 }}
              />
            </Card>
          </FuncTooltip>
        </Col>

        <Col span={4}>
          <FuncTooltip {...funcDescriptions.tpot}>
            <Card
              style={{
                borderTop: '3px solid #faad14',
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                cursor: 'help'
              }}
              bodyStyle={{ padding: '20px 24px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: 'linear-gradient(135deg, #faad1420 0%, #faad1410 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 12,
                  }}>
                    <ArrowDownOutlined style={{ fontSize: 24, color: '#faad14' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 2 }}>TPOT</div>
                    <div style={{ fontSize: 28, fontWeight: 600, color: '#262626', lineHeight: 1 }}>
                      {realtimeMetrics.tpot}<span style={{ fontSize: 14, marginLeft: 2, color: '#8c8c8c' }}>ms</span>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>输出token延迟</span>
              </div>
              <ReactECharts
                option={getSparklineOption([13, 12, 12, 11, 12, 12, 12], '#faad14')}
                style={{ height: 36, marginTop: 8 }}
              />
            </Card>
          </FuncTooltip>
        </Col>

        <Col span={4}>
          <FuncTooltip {...funcDescriptions.vram}>
            <Card
              style={{
                borderTop: '3px solid #13c2c2',
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                cursor: 'help'
              }}
              bodyStyle={{ padding: '20px 24px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: 'linear-gradient(135deg, #13c2c220 0%, #13c2c210 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 12,
                  }}>
                    <DatabaseOutlined style={{ fontSize: 24, color: '#13c2c2' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 2 }}>显存占用率</div>
                    <div style={{ fontSize: 28, fontWeight: 600, color: '#262626', lineHeight: 1 }}>
                      68<span style={{ fontSize: 14, marginLeft: 2, color: '#8c8c8c' }}>%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>692 / 1024 GB</span>
              </div>
              <div style={{ marginTop: 12 }}>
                <Progress
                  percent={68}
                  strokeColor="#13c2c2"
                  showInfo={false}
                  strokeWidth={6}
                  style={{ marginBottom: 4 }}
                />
              </div>
            </Card>
          </FuncTooltip>
        </Col>

        <Col span={4}>
          <FuncTooltip {...funcDescriptions.gpuUtil}>
            <Card
              style={{
                borderTop: '3px solid #eb2f96',
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                cursor: 'help'
              }}
              bodyStyle={{ padding: '20px 24px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: 'linear-gradient(135deg, #eb2f9620 0%, #eb2f9610 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 12,
                  }}>
                    <DatabaseOutlined style={{ fontSize: 24, color: '#eb2f96' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 2 }}>GPU 利用率</div>
                    <div style={{ fontSize: 28, fontWeight: 600, color: '#262626', lineHeight: 1 }}>
                      73<span style={{ fontSize: 14, marginLeft: 2, color: '#8c8c8c' }}>%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>18 / 32 使用中</span>
              </div>
              <ReactECharts
                option={getSparklineOption([70, 72, 71, 73, 74, 72, 73], '#eb2f96')}
                style={{ height: 36, marginTop: 8 }}
              />
            </Card>
          </FuncTooltip>
        </Col>
      </Row>

      {/* 活跃部署表格 */}
      <Row style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card
            title={
              <FuncTooltip {...funcDescriptions.activeDeployments}>
                <span>活跃部署 <InfoCircleOutlined style={{fontSize: 12, color: '#999', marginLeft: 4}}/></span>
              </FuncTooltip>
            }
            bordered={false}
          >
            <Table
              dataSource={deployments.filter(d => d.status === 'running' || d.status === 'starting')}
              columns={deploymentColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
      </Row>

      {/* 中间区域 - 资源总览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card
            title={
              <FuncTooltip {...funcDescriptions.gpuCluster}>
                <span>GPU 集群状态 <InfoCircleOutlined style={{fontSize: 12, color: '#999', marginLeft: 4}}/></span>
              </FuncTooltip>
            }
            bordered={false}
            extra={<span style={{ fontSize: 14, color: '#666' }}>总计: {gpuClusterStatus.total} 个</span>}
          >
            <Row gutter={16}>
              <Col span={12}>
                <ReactECharts option={gpuPieOption} style={{ height: 200 }} />
              </Col>
              <Col span={12}>
                <Space direction="vertical" style={{ width: '100%', padding: '20px 0' }} size="large">
                  <div>
                    <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>可用</div>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                      {gpuClusterStatus.available}
                      <span style={{ fontSize: 14, color: '#999', fontWeight: 'normal', marginLeft: 8 }}>
                        ({Math.round(gpuClusterStatus.available / gpuClusterStatus.total * 100)}%)
                      </span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>使用中</div>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                      {gpuClusterStatus.inUse}
                      <span style={{ fontSize: 14, color: '#999', fontWeight: 'normal', marginLeft: 8 }}>
                        ({Math.round(gpuClusterStatus.inUse / gpuClusterStatus.total * 100)}%)
                      </span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>故障</div>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                      {gpuClusterStatus.error}
                      <span style={{ fontSize: 14, color: '#999', fontWeight: 'normal', marginLeft: 8 }}>
                        ({Math.round(gpuClusterStatus.error / gpuClusterStatus.total * 100)}%)
                      </span>
                    </div>
                  </div>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title={
              <FuncTooltip {...funcDescriptions.storage}>
                <span>存储状态 <InfoCircleOutlined style={{fontSize: 12, color: '#999', marginLeft: 4}}/></span>
              </FuncTooltip>
            }
            bordered={false}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center' }}>
                  <DatabaseOutlined style={{ fontSize: 18, color: '#1890ff', marginRight: 8 }} />
                  <span style={{ fontSize: 14, fontWeight: 500 }}>模型存储</span>
                </div>
                <Progress
                  percent={Math.round(storageStatus.models.used / storageStatus.models.total * 100)}
                  format={() => `${storageStatus.models.used} / ${storageStatus.models.total} GB`}
                  strokeColor="#1890ff"
                />
              </div>
              <div>
                <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center' }}>
                  <FileTextOutlined style={{ fontSize: 18, color: '#722ed1', marginRight: 8 }} />
                  <span style={{ fontSize: 14, fontWeight: 500 }}>日志存储</span>
                </div>
                <Progress
                  percent={Math.round(storageStatus.logs.used / storageStatus.logs.total * 100)}
                  format={() => `${storageStatus.logs.used} / ${storageStatus.logs.total} GB`}
                  strokeColor="#722ed1"
                />
              </div>
              <div style={{ marginTop: 16, padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <div style={{ fontSize: 12, color: '#666' }}>总使用空间</div>
                    <div style={{ fontSize: 20, fontWeight: 'bold', marginTop: 4 }}>
                      {storageStatus.models.used + storageStatus.logs.used} GB
                    </div>
                  </Col>
                  <Col span={12}>
                    <div style={{ fontSize: 12, color: '#666' }}>总可用空间</div>
                    <div style={{ fontSize: 20, fontWeight: 'bold', marginTop: 4 }}>
                      {storageStatus.models.total + storageStatus.logs.total} GB
                    </div>
                  </Col>
                </Row>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 下方区域 - 热门模型和最近事件 */}
      <Row gutter={16}>
        <Col span={12}>
          <Card
            title={
              <FuncTooltip {...funcDescriptions.topModels}>
                <span>热门模型 Top 5 <InfoCircleOutlined style={{fontSize: 12, color: '#999', marginLeft: 4}}/></span>
              </FuncTooltip>
            }
            bordered={false}
          >
            <Table
              dataSource={topModels}
              columns={topModelsColumns}
              rowKey="rank"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title={
              <FuncTooltip {...funcDescriptions.recentEvents}>
                <span>最近事件 <InfoCircleOutlined style={{fontSize: 12, color: '#999', marginLeft: 4}}/></span>
              </FuncTooltip>
            }
            bordered={false}
          >
            <Timeline
              items={recentEvents.map(event => ({
                color: event.type === 'success' ? 'green' : event.type === 'warning' ? 'orange' : event.type === 'error' ? 'red' : 'blue',
                dot: event.icon,
                children: (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontWeight: 500 }}>{event.title}</span>
                      <span style={{ fontSize: 12, color: '#999' }}>{event.time}</span>
                    </div>
                    <div style={{ fontSize: 13, color: '#666' }}>{event.description}</div>
                  </div>
                ),
              }))}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;

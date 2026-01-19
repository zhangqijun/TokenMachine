import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Form,
  Radio,
  Checkbox,
  Select,
  InputNumber,
  Button,
  Progress,
  Statistic,
  Typography,
  Space,
  Table,
  Tag,
  Divider,
  Rate,
  message,
  List,
} from 'antd';
import {
  PlayCircleOutlined,
  HistoryOutlined,
  DownloadOutlined,
  TrophyOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const { Title, Text } = Typography;

interface BenchmarkProgress {
  name: string;
  current: number;
  total: number;
  score: number;
  status: 'pending' | 'running' | 'completed' | 'error';
}

const BenchmarkTest = () => {
  const [testType, setTestType] = useState<'accuracy' | 'performance' | 'comprehensive'>('accuracy');
  const [testing, setTesting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [benchmarks, setBenchmarks] = useState<BenchmarkProgress[]>([
    { name: 'MMLU', current: 120, total: 150, score: 85.3, status: 'completed' },
    { name: 'GSM8K', current: 150, total: 150, score: 92.1, status: 'completed' },
    { name: 'HumanEval', current: 80, total: 164, score: 0, status: 'running' },
    { name: 'C-Eval', current: 180, total: 200, score: 78.5, status: 'completed' },
  ]);
  const [showResults, setShowResults] = useState(false);

  const radarOption = {
    title: { text: '模型能力雷达图', left: 'center' },
    tooltip: {},
    legend: { data: ['当前模型', '基线模型'], bottom: 10 },
    radar: {
      indicator: [
        { name: 'MMLU', max: 100 },
        { name: 'GSM8K', max: 100 },
        { name: 'HumanEval', max: 100 },
        { name: 'C-Eval', max: 100 },
        { name: 'TruthfulQA', max: 100 },
        { name: 'BBH', max: 100 },
      ],
    },
    series: [
      {
        name: '能力评分',
        type: 'radar',
        data: [
          {
            value: [85.3, 92.1, 78.5, 80.2, 75.6, 82.4],
            name: '当前模型',
            areaStyle: { color: 'rgba(24, 144, 255, 0.2)' },
          },
          {
            value: [75.0, 80.5, 70.2, 72.1, 68.3, 74.8],
            name: '基线模型',
            areaStyle: { color: 'rgba(150, 150, 150, 0.2)' },
          },
        ],
      },
    ],
  };

  const handleStartTest = () => {
    setTesting(true);
    setProgress(0);

    // 模拟测试进度
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setTesting(false);
          setShowResults(true);
          message.success('测试完成！');
          return 100;
        }
        return prev + 5;
      });
    }, 300);
  };

  const configPanel = (
    <Card title="测试配置" size="small">
      <Form layout="vertical" size="small">
        <Form.Item label="测试类型">
          <Radio.Group value={testType} onChange={(e) => setTestType(e.target.value)}>
            <Space direction="vertical">
              <Radio value="accuracy">精度测试</Radio>
              <Radio value="performance">性能测试</Radio>
              <Radio value="comprehensive">综合测试</Radio>
            </Space>
          </Radio.Group>
        </Form.Item>

        <Form.Item label="选择测试集">
          <Checkbox.Group style={{ width: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Checkbox defaultChecked>MMLU</Checkbox>
              <Checkbox defaultChecked>GSM8K</Checkbox>
              <Checkbox defaultChecked>HumanEval</Checkbox>
              <Checkbox defaultChecked>C-Eval</Checkbox>
              <Checkbox defaultChecked>TruthfulQA</Checkbox>
              <Checkbox defaultChecked>BBH</Checkbox>
              <Checkbox>自定义测试集...</Checkbox>
            </Space>
          </Checkbox.Group>
        </Form.Item>

        <Form.Item label="测试模型">
          <Select defaultValue="llama-3-8b">
            <Select.Option value="llama-3-8b">llama-3-8b-instruct</Select.Option>
            <Select.Option value="qwen-14b">qwen-14b-chat</Select.Option>
            <Select.Option value="gemma-7b">gemma-7b-it</Select.Option>
          </Select>
        </Form.Item>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="并发数">
              <InputNumber min={1} max={100} defaultValue={10} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="测试轮数">
              <InputNumber min={1} max={10} defaultValue={3} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="超时(s)">
              <InputNumber min={10} max={300} defaultValue={60} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>

        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleStartTest}
          loading={testing}
          block
        >
          开始测试
        </Button>
      </Form>
    </Card>
  );

  const progressPanel = (
    <Card title="测试进度" size="small" style={{ marginTop: 16 }}>
      <Progress percent={progress} status={testing ? 'active' : 'success'} />
      <div style={{ marginTop: 16 }}>
        {benchmarks.map((bm) => (
          <div key={bm.name} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>{bm.name}</Text>
              <Space>
                <Text type="secondary">
                  {bm.current}/{bm.total}
                </Text>
                {bm.status === 'completed' && (
                  <Tag color="success">✓ {bm.score}%</Tag>
                )}
                {bm.status === 'running' && <Tag color="processing">⏳ 进行中...</Tag>}
              </Space>
            </div>
            <Progress
              percent={Math.round((bm.current / bm.total) * 100)}
              size="small"
              status={bm.status === 'running' ? 'active' : bm.status === 'completed' ? 'success' : 'normal'}
            />
          </div>
        ))}
      </div>
    </Card>
  );

  const resultsPanel = (
    <Card title="实时结果" size="small" style={{ marginTop: 16 }}>
      <Row gutter={16}>
        <Col span={8}>
          <Statistic title="MMLU" value={85.3} suffix="%" />
        </Col>
        <Col span={8}>
          <Statistic title="GSM8K" value={92.1} suffix="%" />
        </Col>
        <Col span={8}>
          <Statistic title="C-Eval" value={78.5} suffix="%" />
        </Col>
      </Row>

      <Divider />

      <Row gutter={16}>
        <Col span={8}>
          <Card size="small" title="精度得分">
            <List
              size="small"
              dataSource={[
                { label: 'MMLU', value: 85.3 },
                { label: 'GSM8K', value: 92.1 },
                { label: 'C-Eval', value: 78.5 },
              ]}
              renderItem={(item) => (
                <List.Item>
                  <span style={{ flex: 1 }}>{item.label}</span>
                  <Text strong>{item.value}%</Text>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="性能指标">
            <List
              size="small"
              dataSource={[
                { label: 'TTFT', value: '120ms' },
                { label: 'TPS', value: '45.2' },
                { label: 'RPS', value: '12.5' },
                { label: 'P95', value: '180ms' },
              ]}
              renderItem={(item) => (
                <List.Item>
                  <span style={{ flex: 1 }}>{item.label}</span>
                  <Text strong>{item.value}</Text>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="综合评分">
            <div style={{ textAlign: 'center' }}>
              <Rate disabled defaultValue={4} style={{ fontSize: 24 }} />
              <Title level={2} style={{ margin: '8px 0' }}>
                8.2
                <Text type="secondary" style={{ fontSize: 16 }}>
                  /10
                </Text>
              </Title>
              <Text type="secondary">基于 6 个测试集综合评估</Text>
            </div>
          </Card>
        </Col>
      </Row>

      <Divider />

      <div style={{ marginBottom: 16 }}>
        <ReactECharts option={radarOption} style={{ height: 300 }} />
      </div>
    </Card>
  );

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={3} style={{ margin: 0 }}>
          Benchmark 测试
        </Title>
        <Space>
          <Button icon={<HistoryOutlined />}>查看历史记录</Button>
          <Button icon={<TrophyOutlined />}>排名榜单</Button>
        </Space>
      </div>

      <Row gutter={16}>
        <Col xs={24} lg={8}>
          {configPanel}
          {progressPanel}
        </Col>
        <Col xs={24} lg={16}>
          {showResults ? (
            resultsPanel
          ) : (
            <Card style={{ textAlign: 'center', padding: 64 }}>
              <RocketOutlined style={{ fontSize: 64, color: '#d9d9d9', marginBottom: 16 }} />
              <Title level={4} type="secondary">
                等待测试开始...
              </Title>
              <Text type="secondary">配置测试参数后点击"开始测试"</Text>
            </Card>
          )}
        </Col>
      </Row>

      {showResults && (
        <Card
          title="操作"
          style={{ marginTop: 16 }}
          extra={
            <Space>
              <Button icon={<HistoryOutlined />}>对比历史</Button>
              <Button icon={<DownloadOutlined />}>导出报告</Button>
              <Button type="primary">保存配置</Button>
            </Space>
          }
        >
          <Text type="secondary">
            测试已完成，您可以导出详细报告或与历史记录进行对比分析
          </Text>
        </Card>
      )}
    </div>
  );
};

export default BenchmarkTest;

import { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Form,
  Select,
  Input,
  Button,
  List,
  Steps,
  Tag,
  Typography,
  Checkbox,
  Radio,
  Slider,
  Progress,
  Space,
  message,
  Divider,
} from 'antd';
import {
  PlayCircleOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  ToolOutlined,
} from '@ant-design/icons';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface AgentStep {
  id: string;
  title: string;
  description: string;
  status: 'wait' | 'process' | 'finish' | 'error';
  time?: string;
}

interface ToolCall {
  id: number;
  name: string;
  params: string;
  status: 'pending' | 'running' | 'success' | 'error';
  result?: string;
}

const AgentTest = () => {
  const [executionMode, setExecutionMode] = useState<'auto' | 'step'>('auto');
  const [taskInput, setTaskInput] = useState('');
  const [running, setRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [finalAnswer, setFinalAnswer] = useState('');
  const [stats, setStats] = useState({ steps: 0, time: '0s', tokens: 0 });

  const handleRun = async () => {
    if (!taskInput.trim()) {
      message.warning('请输入任务描述');
      return;
    }

    setRunning(true);
    setCurrentStep(0);

    // 模拟 Agent 执行过程
    const agentSteps: AgentStep[] = [
      {
        id: '1',
        title: '理解问题',
        description: '分析用户任务，提取关键信息',
        status: 'process',
      },
      {
        id: '2',
        title: '检索知识库',
        description: '从知识库中搜索相关信息',
        status: 'wait',
      },
      {
        id: '3',
        title: '综合分析',
        description: '基于检索结果进行分析推理',
        status: 'wait',
      },
      {
        id: '4',
        title: '生成回答',
        description: '综合所有信息生成最终答案',
        status: 'wait',
      },
    ];

    setSteps(agentSteps);
    setToolCalls([
      {
        id: 1,
        name: 'knowledge_base.search',
        params: 'query: "AI 领域最新趋势"',
        status: 'running',
      },
    ]);

    // 模拟执行
    setTimeout(() => {
      setSteps((prev) =>
        prev.map((s, i) =>
          i === 0
            ? { ...s, status: 'finish', time: '2.3s' }
            : i === 1
            ? { ...s, status: 'process' }
            : s
        )
      );
      setCurrentStep(1);
      setToolCalls([
        {
          id: 1,
          name: 'knowledge_base.search',
          params: 'query: "AI 领域最新趋势"',
          status: 'success',
          result: '找到 15 篇相关文档',
        },
        {
          id: 2,
          name: 'web_search.google',
          params: 'query: "AI trends 2024"',
          status: 'running',
        },
      ]);
    }, 2000);

    setTimeout(() => {
      setSteps((prev) =>
        prev.map((s, i) =>
          i === 1
            ? { ...s, status: 'finish', time: '5.2s' }
            : i === 2
            ? { ...s, status: 'process' }
            : s
        )
      );
      setCurrentStep(2);
      setToolCalls((prev) =>
        prev.map((t) =>
          t.id === 2
            ? { ...t, status: 'success', result: '搜索完成，128 条结果' }
            : t
        )
      );
    }, 5000);

    setTimeout(() => {
      setSteps((prev) =>
        prev.map((s, i) =>
          i === 2
            ? { ...s, status: 'finish', time: '7.8s' }
            : i === 3
            ? { ...s, status: 'process' }
            : s
        )
      );
      setCurrentStep(3);
    }, 8000);

    setTimeout(() => {
      setSteps((prev) =>
        prev.map((s, i) => (i === 3 ? { ...s, status: 'finish', time: '10.2s' } : s))
      );
      setFinalAnswer(
        `根据知识库和网络搜索结果，2024 年 AI 领域的最新趋势包括：

1. **大语言模型**：多模态能力增强，上下文窗口持续扩大
2. **Agent 系统**：自主智能体成为热点，工具调用能力显著提升
3. **边缘计算**：模型轻量化，支持移动端部署
4. **开源生态**：Llama 3、Mistral 等开源模型性能追赶闭源
5. **行业应用**：AI 在医疗、教育、金融等领域深入应用

这些趋势表明 AI 正朝着更加实用化、普惠化的方向发展。`
      );
      setStats({ steps: 4, time: '10.2s', tokens: 846 });
      setRunning(false);
      message.success('Agent 执行完成');
    }, 10000);
  };

  const configPanel = (
    <div>
      <Title level={5}>Agent 配置</Title>

      <Form layout="vertical" size="small">
        <Form.Item label="Agent 模板">
          <Select defaultValue="ReAct">
            <Select.Option value="ReAct">ReAct (推理+行动)</Select.Option>
            <Select.Option value="Plan-and-Solve">Plan-and-Solve</Select.Option>
            <Select.Option value="CoT">Chain-of-Thought</Select.Option>
            <Select.Option value="ReWOO">ReWOO</Select.Option>
          </Select>
        </Form.Item>

        <Divider plain>知识库</Divider>

        <div style={{ marginBottom: 16 }}>
          <Button type="dashed" block icon={<PlusOutlined />}>
            添加文档
          </Button>
        </div>
        <List
          size="small"
          dataSource={[
            { name: '技术文档.pdf', size: '2.3 MB' },
            { name: '产品手册.pdf', size: '1.8 MB' },
            { name: 'API文档.md', size: '156 KB' },
          ]}
          renderItem={(item) => (
            <List.Item style={{ padding: '4px 0' }}>
              <FileTextOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              <span style={{ flex: 1 }}>{item.name}</span>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {item.size}
              </Text>
            </List.Item>
          )}
        />

        <Divider plain>工具链</Divider>

        <Checkbox.Group style={{ width: '100%' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Checkbox defaultChecked>Web Search</Checkbox>
            <Checkbox defaultChecked>Code Interpreter</Checkbox>
            <Checkbox defaultChecked>File System</Checkbox>
            <Checkbox>Database Query</Checkbox>
            <Checkbox>API Client</Checkbox>
          </Space>
        </Checkbox.Group>

        <Divider plain>执行模式</Divider>

        <Radio.Group value={executionMode} onChange={(e) => setExecutionMode(e.target.value)}>
          <Space direction="vertical">
            <Radio value="auto">自动执行</Radio>
            <Radio value="step">步骤确认</Radio>
          </Space>
        </Radio.Group>

        <Button type="primary" block style={{ marginTop: 16 }} onClick={() => message.success('配置已保存')}>
          保存配置
        </Button>
      </Form>
    </div>
  );

  const executionPanel = (
    <div>
      <Title level={5}>Agent 执行</Title>

      <div
        style={{
          marginBottom: 16,
          padding: 12,
          backgroundColor: '#f5f5f5',
          borderRadius: 4,
        }}
      >
        <Text type="secondary">用户任务：</Text>
        <div style={{ marginTop: 4 }}>{taskInput || '等待输入任务...'}</div>
      </div>

      <Title level={5}>思考链 (CoT)</Title>
      <Steps
        direction="vertical"
        current={currentStep}
        items={steps.map((step) => ({
          title: step.title,
          description: (
            <div>
              <div>{step.description}</div>
              {step.time && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  耗时: {step.time}
                </Text>
              )}
            </div>
          ),
          status: step.status,
          icon:
            step.status === 'process' ? (
              <LoadingOutlined />
            ) : step.status === 'finish' ? (
              <CheckCircleOutlined />
            ) : undefined,
        }))}
      />

      <Title level={5} style={{ marginTop: 24 }}>
        工具调用
      </Title>
      <List
        size="small"
        dataSource={toolCalls}
        renderItem={(tool) => (
          <List.Item>
            <List.Item.Meta
              avatar={
                tool.status === 'running' ? (
                  <LoadingOutlined />
                ) : tool.status === 'success' ? (
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <ThunderboltOutlined />
                )
              }
              title={<code>{tool.name}</code>}
              description={
                <div>
                  <div style={{ color: '#666', fontSize: 12 }}>{tool.params}</div>
                  {tool.result && (
                    <Tag color="success" style={{ marginTop: 4 }}>
                      {tool.result}
                    </Tag>
                  )}
                </div>
              }
            />
          </List.Item>
        )}
      />

      {finalAnswer && (
        <>
          <Title level={5} style={{ marginTop: 24 }}>
            最终回答
          </Title>
          <div
            style={{
              padding: 16,
              backgroundColor: '#f0f7ff',
              borderRadius: 8,
              border: '1px solid #91d5ff',
            }}
          >
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{finalAnswer}</pre>
          </div>
        </>
      )}

      {stats.steps > 0 && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            backgroundColor: '#fafafa',
            borderRadius: 4,
            textAlign: 'center',
          }}
        >
          <Space size={32}>
            <Text>
              步骤: <Text strong>{stats.steps}</Text>
            </Text>
            <Text>
              耗时: <Text strong>{stats.time}</Text>
            </Text>
            <Text>
              Tokens: <Text strong>{stats.tokens}</Text>
            </Text>
          </Space>
        </div>
      )}
    </div>
  );

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={3} style={{ margin: 0 }}>
          Agent 测试
        </Title>
        <Button icon={<PlusOutlined />}>新建 Agent</Button>
      </div>

      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card title={configPanel} style={{ height: '100%' }} />
        </Col>
        <Col xs={24} lg={16}>
          <Card
            title={executionPanel}
            extra={
              running && (
                <Button danger onClick={() => setRunning(false)}>
                  停止执行
                </Button>
              )
            }
            style={{ marginBottom: 16 }}
          />

          <Card title="任务输入" size="small">
            <TextArea
              rows={3}
              placeholder="输入 Agent 任务，例如：分析 AI 领域最新趋势..."
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
            />
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleRun}
              loading={running}
              style={{ marginTop: 12 }}
              block
            >
              开始执行
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AgentTest;

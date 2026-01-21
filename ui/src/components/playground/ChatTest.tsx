import { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Form,
  Select,
  Slider,
  Input,
  Button,
  Space,
  Divider,
  Typography,
  message,
  List,
  Avatar,
  Tag,
} from 'antd';
import {
  SendOutlined,
  ClearOutlined,
  ReloadOutlined,
  UserOutlined,
  RobotOutlined,
  CopyOutlined,
  DownloadOutlined,
} from '@ant-design/icons';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

const ChatTest = () => {
  const [form] = Form.useForm();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'user',
      content: '请介绍一下 TokenMachine',
      timestamp: '10:30:00',
    },
    {
      id: '2',
      role: 'assistant',
      content: `TokenMachine 是一个企业级的 AI 模型部署与管理平台，提供以下核心功能：

**核心特性：**
1. 模型管理 - 支持多种模型格式和推理引擎
2. 一键部署 - 快速部署和管理模型服务
3. 集群调度 - 智能 GPU 资源调度
4. 监控告警 - 实时性能监控和告警
5. API 服务 - OpenAI 兼容的 API 接口

**支持引擎：**
- vLLM (高性能推理)
- SGLang (结构化生成)

TokenMachine 让 AI 模型部署变得简单高效！`,
      timestamp: '10:30:02',
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [inputTokens, setInputTokens] = useState(0);
  const [outputTokens, setOutputTokens] = useState(124);
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSend = async () => {
    if (!inputText.trim()) {
      message.warning('请输入消息');
      return;
    }

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    };

    setMessages([...messages, newMessage]);
    setInputText('');
    setInputTokens(inputText.length / 2);
    setLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `这是对 "${inputText}" 的回复。TokenMachine 平台提供了完整的模型管理和部署能力...`,
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
      };
      setMessages((prev) => [...prev, response]);
      setOutputTokens(outputTokens + Math.floor(Math.random() * 100));
      setLoading(false);
    }, 1000);
  };

  const handleClear = () => {
    setMessages([]);
    setInputTokens(0);
    setOutputTokens(0);
    message.success('已清空对话');
  };

  const handleReset = () => {
    form.resetFields();
    message.success('已重置参数');
  };

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
    message.success('已复制到剪贴板');
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>
          对话测试
        </Title>
        <Button icon={<ClearOutlined />} onClick={handleClear}>
          清空对话
        </Button>
      </div>

      <Row gutter={16}>
        {/* 左侧配置面板 */}
        <Col xs={24} lg={8}>
          <Card title="模型配置" style={{ height: '100%' }}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                model: 'llama-3-8b',
                temperature: 0.7,
                topP: 0.9,
                maxTokens: 2047,
              }}
            >
              <Form.Item label="选择模型" name="model">
                <Select>
                  <Select.Option value="llama-3-8b">llama-3-8b-instruct</Select.Option>
                  <Select.Option value="qwen-14b">qwen-14b-chat</Select.Option>
                  <Select.Option value="gemma-7b">gemma-7b-it</Select.Option>
                  <Select.Option value="chatglm3-6b">chatglm3-6b</Select.Option>
                </Select>
              </Form.Item>

              <Divider plain>基础参数</Divider>

              <Form.Item label={`Temperature: ${form.getFieldValue('temperature') || 0.7}`} name="temperature">
                <Slider min={0} max={2} step={0.1} marks={{ 0: '0', 1: '1', 2: '2' }} />
              </Form.Item>

              <Form.Item label={`Top P: ${form.getFieldValue('topP') || 0.9}`} name="topP">
                <Slider min={0} max={1} step={0.05} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
              </Form.Item>

              <Form.Item label="Max Tokens" name="maxTokens">
                <Select>
                  <Select.Option value={512}>512</Select.Option>
                  <Select.Option value={1024}>1024</Select.Option>
                  <Select.Option value={2047}>2047</Select.Option>
                  <Select.Option value={4096}>4096</Select.Option>
                </Select>
              </Form.Item>

              <div style={{ margin: '16px 0 8px 0', cursor: 'pointer' }} onClick={() => setShowAdvanced(!showAdvanced)}>
                <Divider style={{ margin: 0 }}>
                  {showAdvanced ? '▼ 收起' : '▶ 高级设置'}
                </Divider>
              </div>

              {showAdvanced && (
                <>
                  <Form.Item label="Frequency Penalty" name="frequencyPenalty">
                    <Slider min={-2} max={2} step={0.1} marks={{ 0: '0' }} />
                  </Form.Item>

                  <Form.Item label="Presence Penalty" name="presencePenalty">
                    <Slider min={-2} max={2} step={0.1} marks={{ 0: '0' }} />
                  </Form.Item>

                  <Form.Item label="系统提示词" name="systemPrompt">
                    <TextArea rows={4} placeholder="You are a helpful assistant..." />
                  </Form.Item>
                </>
              )}

              <Space style={{ width: '100%', justifyContent: 'space-between', marginTop: 16 }}>
                <Button onClick={handleReset} icon={<ReloadOutlined />}>
                  重置为默认值
                </Button>
              </Space>
            </Form>
          </Card>
        </Col>

        {/* 右侧对话区域 */}
        <Col xs={24} lg={16}>
          <Card
            style={{ height: 'calc(100vh - 220px)', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
          >
            {/* 消息列表 */}
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: 24,
                backgroundColor: '#fafafa',
              }}
            >
              <List
                dataSource={messages}
                renderItem={(msg) => (
                  <List.Item
                    key={msg.id}
                    style={{
                      border: 'none',
                      padding: '12px 0',
                      backgroundColor: 'transparent',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        width: '100%',
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      {msg.role === 'assistant' && (
                        <Avatar
                          icon={<RobotOutlined />}
                          style={{ backgroundColor: '#1890ff', marginRight: 12 }}
                        />
                      )}
                      <div
                        style={{
                          maxWidth: '70%',
                          padding: '12px 16px',
                          borderRadius: 8,
                          backgroundColor: msg.role === 'user' ? '#1890ff' : '#fff',
                          color: msg.role === 'user' ? '#fff' : '#262626',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                        }}
                      >
                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                          {msg.content}
                        </div>
                        <div
                          style={{
                            marginTop: 8,
                            fontSize: 12,
                            opacity: 0.7,
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <span>{msg.timestamp}</span>
                          <Button
                            type="text"
                            size="small"
                            icon={<CopyOutlined />}
                            onClick={() => copyMessage(msg.content)}
                            style={{
                              color: msg.role === 'user' ? '#fff' : '#666',
                              padding: 0,
                              height: 'auto',
                            }}
                          />
                        </div>
                      </div>
                      {msg.role === 'user' && (
                        <Avatar
                          icon={<UserOutlined />}
                          style={{ backgroundColor: '#52c41a', marginLeft: 12 }}
                        />
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </div>

            {/* 输入区域 */}
            <div style={{ padding: 16, borderTop: '1px solid #f0f0f0', backgroundColor: '#fff' }}>
              <div style={{ marginBottom: 8 }}>
                <Space split={<Divider type="vertical" />}>
                  <Text type="secondary">
                    Input: <Text strong>{inputTokens}</Text>
                  </Text>
                  <Text type="secondary">
                    Output: <Text strong>{outputTokens}</Text>
                  </Text>
                  <Text type="secondary">
                    Total: <Text strong>{inputTokens + outputTokens}</Text>
                  </Text>
                  <Text type="secondary">
                    费用: <Text strong>¥{((inputTokens + outputTokens) * 0.0001).toFixed(4)}</Text>
                  </Text>
                </Space>
              </div>
              <Input
                placeholder="输入消息... (Shift + Enter 换行)"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                suffix={
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    loading={loading}
                  >
                    发送
                  </Button>
                }
              />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ChatTest;

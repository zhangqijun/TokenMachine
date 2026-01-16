import { useState, useRef, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Select,
  Space,
  Tag,
  message,
  Slider,
  Switch,
  Divider,
  Typography,
  Empty,
  InputNumber,
} from 'antd';
import {
  SendOutlined,
  StopOutlined,
  ClearOutlined,
  SettingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useStore } from '../store';
import type { Model } from '../mock/data';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Text } = Typography;

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

const Playground = () => {
  const { models } = useStore();
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Generation parameters
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(0.9);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [streamEnabled, setStreamEnabled] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const availableModels = models.filter(m => (m.status === 'running' || m.status === 'stopped' || m.status === 'error') && m.category === 'llm');

  useEffect(() => {
    if (availableModels.length > 0 && !selectedModel) {
      setSelectedModel(availableModels[0].id);
    }
  }, [availableModels, selectedModel]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedModel) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    if (streamEnabled) {
      setIsStreaming(true);
      // Create assistant message with empty content for streaming
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };
      setMessages(prev => [...prev, assistantMessage]);

      // Simulate streaming response
      await simulateStreamingResponse(assistantMessage);
    } else {
      // Non-streaming response
      await simulateNonStreamingResponse(userMessage);
    }
  };

  const simulateStreamingResponse = async (assistantMessage: ChatMessage) => {
    const responses = [
      '你好！我是',
      '一个 AI 助手',
      '，很高兴为你',
      '服务。请问有',
      '什么我可以',
      '帮助你的吗？',
    ];

    let fullContent = '';
    for (let i = 0; i < responses.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 100));
      fullContent += responses[i];
      setMessages(prev =>
        prev.map(msg =>
          msg === assistantMessage
            ? { ...msg, content: fullContent }
            : msg
        )
      );
    }

    setIsStreaming(false);
    setIsLoading(false);

    // Final message without streaming flag
    setMessages(prev =>
      prev.map(msg =>
        msg === assistantMessage
          ? { ...msg, isStreaming: false }
          : msg
      )
    );
  };

  const simulateNonStreamingResponse = async (userMessage: ChatMessage) => {
    await new Promise(resolve => setTimeout(resolve, 1500));

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '这是一个模拟的非流式响应。在实际应用中，这里会调用后端 API 获取模型的真实响应。',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, assistantMessage]);
    setIsLoading(false);
  };

  const handleStop = () => {
    setIsStreaming(false);
    setIsLoading(false);
    abortControllerRef.current?.abort();
  };

  const handleClear = () => {
    setMessages([]);
    message.info('对话已清空');
  };

  return (
    <div style={{ height: 'calc(100vh - 160px)' }}>
      <div style={{ display: 'flex', gap: 16, height: '100%' }}>
        {/* Left Panel - Chat */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Model Selection */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <Text strong>模型:</Text>
                <Select
                  style={{ width: 350 }}
                  value={selectedModel}
                  onChange={setSelectedModel}
                  placeholder="选择模型"
                  showSearch
                  optionFilterProp="children"
                >
                  {availableModels.map(model => (
                    <Select.Option key={model.id} value={model.id}>
                      <Space>
                        {model.name}
                        <Tag color="blue">{model.version}</Tag>
                        <Tag>{model.quantization?.toUpperCase() || 'FP16'}</Tag>
                      </Space>
                    </Select.Option>
                  ))}
                </Select>
              </Space>
              <Space>
                <Button
                  icon={<SettingOutlined />}
                  onClick={() => setShowSettings(!showSettings)}
                >
                  参数设置
                </Button>
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleClear}
                  disabled={messages.length === 0}
                >
                  清空
                </Button>
              </Space>
            </Space>
          </Card>

          {/* Messages */}
          <Card
            style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            bodyStyle={{ flex: 1, padding: 16, display: 'flex', flexDirection: 'column' }}
          >
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '0 8px',
              }}
            >
              {messages.length === 0 ? (
                <Empty
                  description="开始对话"
                  style={{ marginTop: 100 }}
                />
              ) : (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {messages.map((msg, index) => (
                    <div
                      key={index}
                      style={{
                        display: 'flex',
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <div
                        style={{
                          maxWidth: '70%',
                          padding: '12px 16px',
                          borderRadius: 8,
                          background: msg.role === 'user' ? '#1890ff' : '#f5f5f5',
                          color: msg.role === 'user' ? '#fff' : '#000',
                        }}
                      >
                        <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>
                          {msg.role === 'user' ? 'User' : 'Assistant'}
                          <span style={{ marginLeft: 8, fontSize: 11 }}>
                            {dayjs(msg.timestamp).format('HH:mm:ss')}
                          </span>
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {msg.content}
                          {msg.isStreaming && <span className="typing-cursor">|</span>}
                        </div>
                      </div>
                    </div>
                  ))}
                  {isLoading && isStreaming && (
                    <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                      <div
                        style={{
                          padding: '12px 16px',
                          borderRadius: 8,
                          background: '#f5f5f5',
                        }}
                      >
                        <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>
                          Assistant
                        </div>
                        <Space>
                          <div className="loading-dot" />
                          <div className="loading-dot" style={{ animationDelay: '0.2s' }} />
                          <div className="loading-dot" style={{ animationDelay: '0.4s' }} />
                        </Space>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </Space>
              )}
            </div>

            {/* Input */}
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
              <Space.Compact style={{ width: '100%' }}>
                <TextArea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onPressEnter={(e) => {
                    if (e.shiftKey) return;
                    e.preventDefault();
                    handleSend();
                  }}
                  placeholder="输入消息... (Shift+Enter 换行, Enter 发送)"
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  disabled={isLoading}
                />
                <Button
                  type="primary"
                  icon={isLoading ? <StopOutlined /> : <SendOutlined />}
                  onClick={isLoading ? handleStop : handleSend}
                  disabled={!input.trim() || !selectedModel}
                  style={{ height: 'auto' }}
                >
                  {isLoading ? '停止' : '发送'}
                </Button>
              </Space.Compact>
            </div>
          </Card>
        </div>

        {/* Right Panel - Settings */}
        {showSettings && (
          <Card
            title="生成参数"
            style={{ width: 320 }}
            bodyStyle={{ height: '100%', overflowY: 'auto' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* Temperature */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>Temperature</Text>
                  <Text strong>{temperature}</Text>
                </div>
                <Slider
                  min={0}
                  max={2}
                  step={0.1}
                  value={temperature}
                  onChange={setTemperature}
                  marks={{ 0: '0', 1: '1', 2: '2' }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  控制输出的随机性。值越高，输出越随机。
                </Text>
              </div>

              {/* Top P */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>Top P</Text>
                  <Text strong>{topP}</Text>
                </div>
                <Slider
                  min={0}
                  max={1}
                  step={0.05}
                  value={topP}
                  onChange={setTopP}
                  marks={{ 0: '0', 0.5: '0.5', 1: '1' }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  核采样参数，控制输出多样性。
                </Text>
              </div>

              {/* Max Tokens */}
              <div>
                <div style={{ marginBottom: 8 }}>
                  <Text>Max Tokens</Text>
                </div>
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber
                    min={1}
                    max={32768}
                    value={maxTokens}
                    onChange={(val: number | null) => setMaxTokens(val || 2048)}
                    style={{ width: '100%' }}
                  />
                </Space.Compact>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  最大生成 token 数量
                </Text>
              </div>

              {/* Stream */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text>流式输出</Text>
                  <Switch
                    checked={streamEnabled}
                    onChange={setStreamEnabled}
                    checkedChildren="开"
                    unCheckedChildren="关"
                  />
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  逐字显示生成的响应
                </Text>
              </div>

              <Divider />

              {/* Model Info */}
              <div>
                <Text strong>模型信息</Text>
                {selectedModel && (
                  <div style={{ marginTop: 8 }}>
                    {(() => {
                      const model = availableModels.find(m => m.id === selectedModel);
                      if (!model) return null;
                      return (
                        <Space direction="vertical" size="small" style={{ fontSize: 12 }}>
                          <div>
                            <Text type="secondary">名称: </Text>
                            {model.name}
                          </div>
                          <div>
                            <Text type="secondary">版本: </Text>
                            {model.version}
                          </div>
                          <div>
                            <Text type="secondary">量化: </Text>
                            {model.quantization?.toUpperCase() || 'FP16'}
                          </div>
                          <div>
                            <Text type="secondary">大小: </Text>
                            {model.size_gb} GB
                          </div>
                        </Space>
                      );
                    })()}
                  </div>
                )}
              </div>

              <Divider />

              {/* Quick Actions */}
              <div>
                <Text strong>快捷操作</Text>
                <div style={{ marginTop: 8 }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Button
                      block
                      size="small"
                      icon={<ThunderboltOutlined />}
                      onClick={() => {
                        setTemperature(0.7);
                        setTopP(0.9);
                        setMaxTokens(2048);
                        message.success('已恢复默认参数');
                      }}
                    >
                      恢复默认参数
                    </Button>
                  </Space>
                </div>
              </div>
            </Space>
          </Card>
        )}
      </div>

      <style>{`
        .typing-cursor {
          animation: blink 1s infinite;
        }
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
        .loading-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #1890ff;
          animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default Playground;

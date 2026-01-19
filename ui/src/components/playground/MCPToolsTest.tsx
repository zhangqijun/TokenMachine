import { useState } from 'react';
import {
  Row,
  Col,
  Card,
  List,
  Button,
  Input,
  Space,
  Tag,
  Typography,
  Modal,
  Form,
  message,
  Tabs,
  Descriptions,
  Steps,
} from 'antd';
import {
  PlusOutlined,
  ApiOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface MCPServer {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'error';
  tools: string[];
}

interface ToolCall {
  step: number;
  type: 'thought' | 'tool' | 'response';
  content: string;
  status?: 'pending' | 'running' | 'success' | 'error';
}

const MCPToolsTest = () => {
  const [servers, setServers] = useState<MCPServer[]>([
    {
      id: '1',
      name: 'server-weather',
      status: 'running',
      tools: ['weather', 'forecast'],
    },
    {
      id: '2',
      name: 'server-search',
      status: 'running',
      tools: ['search', 'web_search'],
    },
    {
      id: '3',
      name: 'server-files',
      status: 'running',
      tools: ['read', 'write', 'list'],
    },
  ]);
  const [selectedServer, setSelectedServer] = useState<string>('server-weather');
  const [selectedTool, setSelectedTool] = useState<string>('weather');
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [addModalVisible, setAddModalVisible] = useState(false);

  const tools = [
    { name: 'weather', server: 'server-weather', description: '查询天气信息' },
    { name: 'forecast', server: 'server-weather', description: '天气预报' },
    { name: 'search', server: 'server-search', description: '搜索功能' },
    { name: 'web_search', server: 'server-search', description: '网络搜索' },
    { name: 'read', server: 'server-files', description: '读取文件' },
    { name: 'write', server: 'server-files', description: '写入文件' },
    { name: 'list', server: 'server-files', description: '列出文件' },
  ];

  const selectedToolData = tools.find((t) => t.name === selectedTool);

  const handleTest = async () => {
    if (!inputText.trim()) {
      message.warning('请输入测试内容');
      return;
    }

    setLoading(true);

    // 模拟思考过程
    setToolCalls([
      { step: 1, type: 'thought', content: '用户请求查询天气信息' },
      { step: 2, type: 'thought', content: '需要调用 weather 工具，参数: location' },
      {
        step: 3,
        type: 'tool',
        content: `调用 ${selectedTool}("${inputText}")`,
        status: 'running',
      },
    ]);

    setTimeout(() => {
      setToolCalls((prev) => [
        ...prev,
        {
          step: 4,
          type: 'response',
          content: `${inputText}今日天气：晴，温度 18-25°C，空气质量良好`,
        },
      ]);
      setLoading(false);
    }, 1500);
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      running: 'success',
      stopped: 'default',
      error: 'error',
    };
    return colorMap[status] || 'default';
  };

  const getToolIcon = (type: string) => {
    switch (type) {
      case 'thought':
        return <SearchOutlined />;
      case 'tool':
        return <ApiOutlined />;
      case 'response':
        return <CheckCircleOutlined />;
      default:
        return null;
    }
  };

  const serverList = (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
        <Text strong>MCP Server</Text>
        <Button size="small" icon={<PlusOutlined />} onClick={() => setAddModalVisible(true)}>
          添加
        </Button>
      </div>
      <List
        size="small"
        dataSource={servers}
        renderItem={(server) => (
          <List.Item
            style={{
              cursor: 'pointer',
              backgroundColor: selectedServer === server.id ? '#e6f7ff' : 'transparent',
              padding: '8px 12px',
              borderRadius: 4,
            }}
            onClick={() => setSelectedServer(server.id)}
          >
            <div style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>{server.name}</Text>
                <Tag color={getStatusColor(server.status)} style={{ margin: 0 }}>
                  {server.status}
                </Tag>
              </div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {server.tools.length} tools
              </Text>
            </div>
          </List.Item>
        )}
      />
    </div>
  );

  const toolList = (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Input
          placeholder="搜索工具..."
          prefix={<SearchOutlined />}
          size="small"
        />
      </div>
      <List
        size="small"
        dataSource={tools.filter((t) => t.server === selectedServer)}
        renderItem={(tool) => (
          <List.Item
            style={{
              cursor: 'pointer',
              backgroundColor: selectedTool === tool.name ? '#e6f7ff' : 'transparent',
              padding: '8px 12px',
              borderRadius: 4,
            }}
            onClick={() => setSelectedTool(tool.name)}
          >
            <div style={{ width: '100%' }}>
              <Text strong>{tool.name}</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {tool.description}
              </Text>
            </div>
          </List.Item>
        )}
      />
    </div>
  );

  const testArea = (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          测试 {selectedTool}
        </Title>
        {selectedToolData && (
          <Text type="secondary">{selectedToolData.description}</Text>
        )}
      </div>

      <Tabs
        defaultActiveKey="chat"
        items={[
          {
            key: 'chat',
            label: '对话',
            children: (
              <div>
                <div
                  style={{
                    marginBottom: 16,
                    padding: 12,
                    backgroundColor: '#f5f5f5',
                    borderRadius: 4,
                  }}
                >
                  <Text type="secondary">用户任务：</Text>
                  <div>{inputText || '等待输入...'}</div>
                </div>

                <Steps
                  direction="vertical"
                  current={-1}
                  items={toolCalls.map((call) => ({
                    title: (
                      <span>
                        {getToolIcon(call.type)}
                        {call.type === 'thought' && ' 思考'}
                        {call.type === 'tool' && ' 工具调用'}
                        {call.type === 'response' && ' 响应'}
                      </span>
                    ),
                    description: (
                      <div>
                        <div style={{ marginTop: 8 }}>{call.content}</div>
                        {call.status === 'running' && (
                          <LoadingOutlined style={{ color: '#1890ff' }} />
                        )}
                      </div>
                    ),
                    status: call.status === 'success' ? 'finish' : call.status === 'error' ? 'error' : undefined,
                    icon: call.status === 'running' ? <LoadingOutlined /> : undefined,
                  }))}
                />
              </div>
            ),
          },
          {
            key: 'tool',
            label: '工具调用',
            children: (
              <div>
                <Descriptions column={1} bordered size="small">
                  <Descriptions.Item label="工具名称">{selectedTool}</Descriptions.Item>
                  <Descriptions.Item label="所属 Server">{selectedServer}</Descriptions.Item>
                  <Descriptions.Item label="参数">
                    <TextArea
                      rows={4}
                      placeholder='{"location": "北京"}'
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                    />
                  </Descriptions.Item>
                </Descriptions>
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={handleTest}
                  loading={loading}
                  style={{ marginTop: 16 }}
                  block
                >
                  执行工具调用
                </Button>
              </div>
            ),
          },
        ]}
      />
    </div>
  );

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={3} style={{ margin: 0 }}>
          MCP 工具调用测试
        </Title>
      </div>

      <Row gutter={16}>
        <Col xs={24} md={6}>
          <Card title={serverList} style={{ marginBottom: 16 }} />
        </Col>
        <Col xs={24} md={6}>
          <Card title={toolList} style={{ marginBottom: 16 }} />
        </Col>
        <Col xs={24} md={12}>
          <Card title={testArea} style={{ marginBottom: 16, height: '100%' }} />
        </Col>
      </Row>

      <Modal
        title="添加 MCP Server"
        open={addModalVisible}
        onCancel={() => setAddModalVisible(false)}
        onOk={() => {
          message.success('Server 添加成功');
          setAddModalVisible(false);
        }}
      >
        <Form layout="vertical">
          <Form.Item label="Server 名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="my-server" />
          </Form.Item>
          <Form.Item label="连接地址" name="url" rules={[{ required: true }]}>
            <Input placeholder="http://localhost:3000" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="Server 描述..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MCPToolsTest;

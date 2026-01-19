import { Tabs } from 'antd';
import {
  MessageOutlined,
  ApiOutlined,
  RobotOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import ChatTest from '../components/playground/ChatTest';
import MCPToolsTest from '../components/playground/MCPToolsTest';
import AgentTest from '../components/playground/AgentTest';
import BenchmarkTest from '../components/playground/BenchmarkTest';

const Playground = () => {
  const tabItems = [
    {
      key: 'chat',
      label: (
        <span>
          <MessageOutlined />
          对话测试
        </span>
      ),
      children: <ChatTest />,
    },
    {
      key: 'mcp',
      label: (
        <span>
          <ApiOutlined />
          MCP 工具
        </span>
      ),
      children: <MCPToolsTest />,
    },
    {
      key: 'agent',
      label: (
        <span>
          <RobotOutlined />
          Agent 测试
        </span>
      ),
      children: <AgentTest />,
    },
    {
      key: 'benchmark',
      label: (
        <span>
          <TrophyOutlined />
          Benchmark 测试
        </span>
      ),
      children: <BenchmarkTest />,
    },
  ];

  return (
    <div>
      <Tabs
        defaultActiveKey="chat"
        tabPosition="top"
        size="large"
        items={tabItems}
        style={{ marginBottom: 0 }}
      />
    </div>
  );
};

export default Playground;

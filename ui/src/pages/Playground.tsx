import { Tabs } from 'antd';
import {
  MessageOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import ChatTest from '../components/playground/ChatTest';
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
      key: 'benchmark',
      label: (
        <span>
          <ExperimentOutlined />
          批量测试
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

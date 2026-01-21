import { Tabs } from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import NodeManagement from './nodes/NodeManagement';
import BackendManagement from './backends/BackendManagement';

const NodesDeployments = () => {
  const tabItems = [
    {
      key: 'nodes',
      label: (
        <span>
          <CloudServerOutlined />
          节点管理
        </span>
      ),
      children: <NodeManagement />,
    },
    {
      key: 'backends',
      label: (
        <span>
          <ApiOutlined />
          后端管理
        </span>
      ),
      children: <BackendManagement />,
    },
  ];

  return (
    <div>
      <Tabs
        defaultActiveKey="nodes"
        items={tabItems}
        size="large"
        style={{ marginTop: 16 }}
      />
    </div>
  );
};

export default NodesDeployments;

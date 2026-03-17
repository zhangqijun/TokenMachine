import { Tabs, Typography } from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import NodeManagement from './nodes/NodeManagement';
import BackendManagement from './backends/BackendManagement';

const { Title } = Typography;

const NodesDeployments = () => {
  const tabItems = [
    {
      key: 'nodes',
      label: (
        <span>
          <CloudServerOutlined /> 节点管理
        </span>
      ),
      children: <NodeManagement />,
    },
    {
      key: 'backends',
      label: (
        <span>
          <ApiOutlined /> 引擎管理
        </span>
      ),
      children: <BackendManagement />,
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        节点与引擎
      </Title>
      <Tabs
        defaultActiveKey="nodes"
        items={tabItems}
        size="large"
      />
    </div>
  );
};

export default NodesDeployments;

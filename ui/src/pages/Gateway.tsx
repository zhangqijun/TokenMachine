import { Tabs } from 'antd';
import {
  KeyOutlined,
  SplitCellsOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import ApiKeyManagement from '../components/gateway/ApiKeyManagement';
import RoutingStrategy from '../components/gateway/RoutingStrategy';
import LoadBalancing from '../components/gateway/LoadBalancing';
import HealthCheck from '../components/gateway/HealthCheck';
import MonitoringStats from '../components/gateway/MonitoringStats';

const Gateway = () => {
  const tabItems = [
    {
      key: 'api-keys',
      label: (
        <span>
          <KeyOutlined />
          API 密钥管理
        </span>
      ),
      children: <ApiKeyManagement />,
    },
    {
      key: 'routing',
      label: (
        <span>
          <SplitCellsOutlined />
          路由策略
        </span>
      ),
      children: <RoutingStrategy />,
    },
    {
      key: 'load-balancing',
      label: (
        <span>
          <ThunderboltOutlined />
          负载均衡
        </span>
      ),
      children: <LoadBalancing />,
    },
    {
      key: 'health-check',
      label: (
        <span>
          <HeartOutlined />
          故障转移
        </span>
      ),
      children: <HealthCheck />,
    },
    {
      key: 'monitoring',
      label: (
        <span>
          <DashboardOutlined />
          监控统计
        </span>
      ),
      children: <MonitoringStats />,
    },
  ];

  return (
    <div>
      <Tabs
        defaultActiveKey="api-keys"
        items={tabItems}
        size="large"
        style={{ marginTop: 16 }}
      />
    </div>
  );
};

export default Gateway;

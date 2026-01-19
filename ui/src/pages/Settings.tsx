import { useState } from 'react';
import { Card, Menu, Row, Col, Typography } from 'antd';
import {
  DashboardOutlined,
  TeamOutlined,
  SafetyOutlined,
  BellOutlined,
  MonitorOutlined,
  SettingOutlined,
  FileTextOutlined,
  BgColorsOutlined,
  DatabaseOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import SystemOverview from '../components/settings/SystemOverview';
import UserManagement from '../components/settings/UserManagement';
import PermissionManagement from '../components/settings/PermissionManagement';
import NotificationSettings from '../components/settings/NotificationSettings';
import MonitoringSettings from '../components/settings/MonitoringSettings';
import SystemConfig from '../components/settings/SystemConfig';
import OperationLogs from '../components/settings/OperationLogs';
import InterfaceSettings from '../components/settings/InterfaceSettings';
import DataManagement from '../components/settings/DataManagement';
import ApiManagement from '../components/settings/ApiManagement';
import ApiRouting from '../components/settings/ApiRouting';

const { Title } = Typography;

type SettingsKey =
  | 'overview'
  | 'users'
  | 'permissions'
  | 'notifications'
  | 'monitoring'
  | 'config'
  | 'logs'
  | 'interface'
  | 'data'
  | 'api';

const Settings = () => {
  const [selectedKey, setSelectedKey] = useState<SettingsKey>('overview');

  const menuItems = [
    {
      key: 'overview',
      icon: <DashboardOutlined />,
      label: '系统概览',
    },
    {
      type: 'divider',
    },
    {
      key: 'users',
      icon: <TeamOutlined />,
      label: '用户管理',
    },
    {
      key: 'permissions',
      icon: <SafetyOutlined />,
      label: '权限管理',
    },
    {
      key: 'notifications',
      icon: <BellOutlined />,
      label: '通知设置',
    },
    {
      key: 'monitoring',
      icon: <MonitorOutlined />,
      label: '监控告警',
    },
    {
      type: 'divider',
    },
    {
      key: 'config',
      icon: <SettingOutlined />,
      label: '系统配置',
    },
    {
      key: 'logs',
      icon: <FileTextOutlined />,
      label: '操作日志',
    },
    {
      key: 'interface',
      icon: <BgColorsOutlined />,
      label: '界面定制',
    },
    {
      key: 'data',
      icon: <DatabaseOutlined />,
      label: '数据管理',
    },
    {
      key: 'api',
      icon: <ApiOutlined />,
      label: 'API 管理',
    },
  ];

  const renderContent = () => {
    switch (selectedKey) {
      case 'overview':
        return <SystemOverview />;
      case 'users':
        return <UserManagement />;
      case 'permissions':
        return <PermissionManagement />;
      case 'notifications':
        return <NotificationSettings />;
      case 'monitoring':
        return <MonitoringSettings />;
      case 'config':
        return <SystemConfig />;
      case 'logs':
        return <OperationLogs />;
      case 'interface':
        return <InterfaceSettings />;
      case 'data':
        return <DataManagement />;
      case 'api':
        return <ApiManagement />;
      default:
        return <SystemOverview />;
    }
  };

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        系统设置
      </Title>

      <Row gutter={24}>
        <Col xs={24} lg={6}>
          <Card
            bodyStyle={{ padding: 0 }}
            style={{ position: 'sticky', top: 88 }}
          >
            <Menu
              mode="inline"
              selectedKeys={[selectedKey]}
              onClick={({ key }) => setSelectedKey(key as SettingsKey)}
              items={menuItems}
              style={{ borderRight: 0 }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={18}>{renderContent()}</Col>
      </Row>
    </div>
  );
};

export default Settings;

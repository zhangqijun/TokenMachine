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
  InfoCircleOutlined,
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
import FuncTooltip from '../components/FuncTooltip';

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
      type: 'divider' as const,
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
      type: 'divider' as const,
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
        <FuncTooltip
          title="系统设置功能"
          description="配置和管理系统各项参数。\n\n• 系统概览：查看系统状态\n• 用户管理：管理用户账户\n• 权限管理：配置访问权限\n• 通知设置：告警通知配置\n• 监控告警：监控阈值设置\n• 系统配置：核心参数配置\n• 操作日志：审计日志查看\n• 界面设置：个性化配置\n• 数据管理：数据备份恢复\n• API管理：密钥和路由配置"
          placement="right"
        >
          <InfoCircleOutlined style={{ fontSize: 16, color: '#999', marginLeft: 8, cursor: 'help' }} />
        </FuncTooltip>
      </Title>

      <Row gutter={24}>
        <Col xs={24} lg={6}>
          <FuncTooltip
            title="设置菜单"
            description="左侧导航菜单，点击切换不同的设置页面。\n\n• 系统管理：概览、用户、权限\n• 监控配置：通知、告警阈值\n• 高级设置：配置、日志、界面\n• 数据与API：数据管理、API配置"
            placement="right"
          >
            <Card
              bodyStyle={{ padding: 0 }}
              style={{ position: 'sticky', top: 88, cursor: 'help' }}
            >
              <Menu
                mode="inline"
                selectedKeys={[selectedKey]}
                onClick={({ key }) => setSelectedKey(key as SettingsKey)}
                items={menuItems}
                style={{ borderRight: 0 }}
              />
            </Card>
          </FuncTooltip>
        </Col>

        <Col xs={24} lg={18}>{renderContent()}</Col>
      </Row>
    </div>
  );
};

export default Settings;

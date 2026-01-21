import { Layout, Menu, Avatar, Dropdown, Space, Badge, message } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import Logo from '../common/Logo';
import {
  DashboardOutlined,
  DatabaseOutlined,
  RocketOutlined,
  BarChartOutlined,
  SafetyOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
  ExperimentOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header, Content } = Layout;

const MainLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
      onClick: () => navigate('/dashboard'),
    },
    {
      key: '/nodes-deployments',
      icon: <CloudServerOutlined />,
      label: '节点与引擎',
      onClick: () => navigate('/nodes-deployments'),
    },
    {
      key: '/models',
      icon: <DatabaseOutlined />,
      label: '模型与实例',
      onClick: () => navigate('/models'),
    },
    {
      key: '/playground',
      icon: <ExperimentOutlined />,
      label: '测试场',
      onClick: () => navigate('/playground'),
    },
    {
      key: '/monitoring',
      icon: <BarChartOutlined />,
      label: '监控面板',
      onClick: () => navigate('/monitoring'),
    },
    {
      key: '/gateway',
      icon: <SafetyOutlined />,
      label: '网关管理',
      onClick: () => navigate('/gateway'),
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      onClick: () => navigate('/settings'),
    },
  ];

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人设置',
      onClick: () => navigate('/settings'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: () => {
        // 清除token
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        message.success('已退出登录');
        // 跳转到登录页
        navigate('/login');
      },
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          padding: '0 24px',
          background: '#001529',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'fixed',
          zIndex: 1,
          width: '100%',
          top: 0,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div
            style={{
              marginRight: 48,
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
            }}
            onClick={() => navigate('/dashboard')}
          >
            <Logo
              size={40}
              variant="full"
              showText={true}
              textColor="#fff"
              backgroundColor="#1890ff"
            />
          </div>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={menuItems}
            style={{ flex: 1, border: 'none', background: 'transparent' }}
          />
        </div>
        <Space size={16}>
          <Badge count={3}>
            <BellOutlined style={{ fontSize: 18, color: '#fff', cursor: 'pointer' }} />
          </Badge>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar
                style={{ backgroundColor: '#1890ff' }}
                icon={<UserOutlined />}
              />
              <span style={{ color: '#fff' }}>管理员</span>
            </Space>
          </Dropdown>
        </Space>
      </Header>
      <Content
        style={{
          marginTop: 64,
          minHeight: 'calc(100vh - 64px)',
          background: '#f0f2f5',
        }}
      >
        <div style={{ padding: 24 }}>
          <Outlet />
        </div>
      </Content>
    </Layout>
  );
};

export default MainLayout;

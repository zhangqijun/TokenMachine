import { Layout, Menu, Avatar, Dropdown, Space, Badge, Input } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  RobotOutlined,
  ClusterOutlined,
  KeyOutlined,
  ExperimentOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
  SearchOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;
const { Search } = Input;

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
      key: '/models',
      icon: <RobotOutlined />,
      label: '模型管理',
      onClick: () => navigate('/models'),
    },
    {
      key: '/clusters',
      icon: <ClusterOutlined />,
      label: '集群管理',
      onClick: () => navigate('/clusters'),
    },
    {
      key: '/api-keys',
      icon: <KeyOutlined />,
      label: 'API 密钥',
      onClick: () => navigate('/api-keys'),
    },
    {
      key: '/playground',
      icon: <ExperimentOutlined />,
      label: '测试场',
      onClick: () => navigate('/playground'),
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
    },
    {
      key: 'divider',
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={240}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            fontWeight: 'bold',
            color: '#fff',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          TokenMachine
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout style={{ marginLeft: 240 }}>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 999,
            borderBottom: '1px solid #f0f0f0',
            boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 500 }}>
            AI 模型部署与管理平台
          </div>
          <Space size="middle">
            <Search
              placeholder="搜索..."
              allowClear
              style={{ width: 200 }}
              prefix={<SearchOutlined />}
            />
            <a href="#" style={{ color: '#666' }} title="帮助文档">
              <QuestionCircleOutlined style={{ fontSize: 18 }} />
            </a>
            <Badge count={5} size="small">
              <BellOutlined style={{ fontSize: 18, color: '#666' }} />
            </Badge>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>管理员</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: '#fff',
            borderRadius: 8,
            minHeight: 'calc(100vh - 112px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;

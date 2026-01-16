import { useState } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Switch,
  Divider,
  Descriptions,
  Avatar,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  LockOutlined,
  SettingOutlined,
  SafetyOutlined,
  KeyOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user' | 'readonly';
  status: 'active' | 'disabled';
  created_at: string;
  last_login: string;
}

interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  description: string;
}

const mockUsers: User[] = [
  {
    id: 'user_1',
    username: 'admin',
    email: 'admin@local',
    role: 'admin',
    status: 'active',
    created_at: '2025-01-01T00:00:00Z',
    last_login: '2025-01-16T10:00:00Z',
  },
  {
    id: 'user_2',
    username: 'developer',
    email: 'dev@company.com',
    role: 'user',
    status: 'active',
    created_at: '2025-01-05T00:00:00Z',
    last_login: '2025-01-15T15:30:00Z',
  },
  {
    id: 'user_3',
    username: 'tester',
    email: 'tester@company.com',
    role: 'readonly',
    status: 'active',
    created_at: '2025-01-10T00:00:00Z',
    last_login: '2025-01-14T09:00:00Z',
  },
];

const mockPermissions: Permission[] = [
  { id: 'perm_1', name: '模型部署', resource: 'models', action: 'deploy', description: '允许部署和管理模型' },
  { id: 'perm_2', name: '集群管理', resource: 'clusters', action: 'manage', description: '允许管理集群配置' },
  { id: 'perm_3', name: 'API Key创建', resource: 'apikeys', action: 'create', description: '允许创建API密钥' },
  { id: 'perm_4', name: '用户管理', resource: 'users', action: 'manage', description: '允许管理用户' },
];

const Settings = () => {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState<User[]>(mockUsers);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  // User management columns
  const userColumns = [
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      render: (username: string, record: User) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <span style={{ fontWeight: 500 }}>{username}</span>
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        const roleConfig = {
          admin: { color: 'red', text: '管理员' },
          user: { color: 'blue', text: '普通用户' },
          readonly: { color: 'default', text: '只读用户' },
        };
        const config = roleConfig[role as keyof typeof roleConfig];
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Badge
          status={status === 'active' ? 'success' : 'default'}
          text={status === 'active' ? '启用' : '禁用'}
        />
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: User) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditUser(record)}
          >
            编辑
          </Button>
          {record.username !== 'admin' && (
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteUser(record)}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // Permission columns
  const permColumns = [
    {
      title: '权限名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <span style={{ fontWeight: 500 }}>{name}</span>,
    },
    {
      title: '资源',
      dataIndex: 'resource',
      key: 'resource',
      render: (resource: string) => <Tag color="blue">{resource}</Tag>,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => <Tag>{action}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: () => (
        <Button type="link" size="small">
          配置
        </Button>
      ),
    },
  ];

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue(user);
    setIsUserModalOpen(true);
  };

  const handleDeleteUser = (user: User) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除用户 "${user.username}" 吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        setUsers(users.filter(u => u.id !== user.id));
        message.success('用户已删除');
      },
    });
  };

  const handleCreateUser = () => {
    setEditingUser(null);
    form.resetFields();
    setIsUserModalOpen(true);
  };

  const handleUserSubmit = (values: any) => {
    if (editingUser) {
      setUsers(users.map(u =>
        u.id === editingUser.id
          ? { ...u, ...values }
          : u
      ));
      message.success('用户更新成功');
    } else {
      const newUser: User = {
        id: `user_${Date.now()}`,
        ...values,
        status: 'active',
        created_at: new Date().toISOString(),
        last_login: new Date().toISOString(),
      };
      setUsers([...users, newUser]);
      message.success('用户创建成功');
    }
    setIsUserModalOpen(false);
    form.resetFields();
    setEditingUser(null);
  };

  const tabItems = [
    {
      key: 'users',
      label: (
        <span>
          <UserOutlined /> 用户管理
        </span>
      ),
      children: (
        <Card
          title="用户列表"
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateUser}
            >
              添加用户
            </Button>
          }
        >
          <Table
            dataSource={users}
            columns={userColumns}
            rowKey="id"
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 个用户`,
            }}
          />
        </Card>
      ),
    },
    {
      key: 'permissions',
      label: (
        <span>
          <SafetyOutlined /> 权限配置
        </span>
      ),
      children: (
        <Card title="权限列表">
          <Table
            dataSource={mockPermissions}
            columns={permColumns}
            rowKey="id"
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: 'system',
      label: (
        <span>
          <SettingOutlined /> 系统设置
        </span>
      ),
      children: (
        <Card title="系统配置">
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* 基本设置 */}
            <div>
              <h4>基本设置</h4>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="系统名称">TokenMachine</Descriptions.Item>
                <Descriptions.Item label="版本">v1.0.0</Descriptions.Item>
                <Descriptions.Item label="部署模式">Standalone</Descriptions.Item>
              </Descriptions>
            </div>

            <Divider />

            {/* 安全设置 */}
            <div>
              <h4>安全设置</h4>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>启用 API Key 认证</div>
                    <div style={{ fontSize: 12, color: '#666' }}>所有 API 请求必须使用有效的 API Key</div>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>启用速率限制</div>
                    <div style={{ fontSize: 12, color: '#666' }}>限制每个 API Key 的请求频率</div>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>启用审计日志</div>
                    <div style={{ fontSize: 12, color: '#666' }}>记录所有敏感操作</div>
                  </div>
                  <Switch defaultChecked />
                </div>
              </Space>
            </div>

            <Divider />

            {/* 存储设置 */}
            <div>
              <h4>存储设置</h4>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="模型存储路径">/var/lib/backend/models</Descriptions.Item>
                <Descriptions.Item label="日志存储路径">/var/log/backend</Descriptions.Item>
                <Descriptions.Item label="最大存储空间">2 TB</Descriptions.Item>
                <Descriptions.Item label="已用空间">1.2 TB</Descriptions.Item>
              </Descriptions>
            </div>

            <Divider />

            {/* 高级设置 */}
            <div>
              <h4>高级设置</h4>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button icon={<LockOutlined />}>修改管理员密码</Button>
                <Button icon={<KeyOutlined />}>重置系统密钥</Button>
                <Button danger>清空缓存</Button>
              </Space>
            </div>
          </Space>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>系统设置</h2>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
      />

      {/* User Form Modal */}
      <Modal
        title={editingUser ? '编辑用户' : '添加用户'}
        open={isUserModalOpen}
        onCancel={() => {
          setIsUserModalOpen(false);
          form.resetFields();
          setEditingUser(null);
        }}
        footer={null}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleUserSubmit}
          initialValues={{
            role: 'user',
            status: 'active',
          }}
        >
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="username" disabled={!!editingUser} />
          </Form.Item>

          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="user@example.com" />
          </Form.Item>

          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select>
              <Select.Option value="admin">管理员</Select.Option>
              <Select.Option value="user">普通用户</Select.Option>
              <Select.Option value="readonly">只读用户</Select.Option>
            </Select>
          </Form.Item>

          {!editingUser && (
            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password placeholder="••••••••" />
            </Form.Item>
          )}

          <Form.Item
            label="状态"
            name="status"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="active">启用</Select.Option>
              <Select.Option value="disabled">禁用</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block>
              {editingUser ? '更新' : '创建'}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Settings;

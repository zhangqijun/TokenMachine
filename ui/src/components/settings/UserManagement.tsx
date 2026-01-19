import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Row,
  Col,
  Typography,
  Modal,
  Form,
  message,
  Popconfirm,
  Avatar,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  LockOutlined,
  StopOutlined,
  CheckOutlined,
  DeleteOutlined,
  UserOutlined,
  TeamOutlined,
  SafetyOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Search } = Input;

interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  status: 'active' | 'inactive';
  lastLogin: string;
  createdAt: string;
}

interface Role {
  id: string;
  name: string;
  description: string;
  userCount: number;
  permissionCount: number;
}

const UserManagement = () => {
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  const users: User[] = [
    {
      id: '1',
      username: 'admin',
      email: 'admin@tokenmachine.ai',
      role: '超级管理员',
      status: 'active',
      lastLogin: '2024-01-19 10:30:00',
      createdAt: '2024-01-01 09:00:00',
    },
    {
      id: '2',
      username: 'developer',
      email: 'dev@tokenmachine.ai',
      role: '开发者',
      status: 'active',
      lastLogin: '2024-01-19 09:15:00',
      createdAt: '2024-01-05 14:20:00',
    },
    {
      id: '3',
      username: 'researcher',
      email: 'research@tokenmachine.ai',
      role: '研究员',
      status: 'active',
      lastLogin: '2024-01-18 16:45:00',
      createdAt: '2024-01-08 11:30:00',
    },
    {
      id: '4',
      username: 'guest_user',
      email: 'guest@example.com',
      role: '普通用户',
      status: 'inactive',
      lastLogin: '2024-01-10 08:20:00',
      createdAt: '2024-01-10 08:00:00',
    },
  ];

  const roles: Role[] = [
    { id: '1', name: '超级管理员', description: '拥有系统所有权限', userCount: 2, permissionCount: 50 },
    { id: '2', name: '管理员', description: '管理用户和配置', userCount: 5, permissionCount: 30 },
    { id: '3', name: '开发者', description: '模型开发和部署权限', userCount: 12, permissionCount: 20 },
    { id: '4', name: '研究员', description: '只读访问权限', userCount: 8, permissionCount: 10 },
    { id: '5', name: '普通用户', description: '基础使用权限', userCount: 101, permissionCount: 5 },
  ];

  const handleAdd = () => {
    setEditingUser(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      role: user.role,
      status: user.status,
    });
    setIsModalVisible(true);
  };

  const handleDelete = (id: string) => {
    message.success('用户已删除');
  };

  const handleToggleStatus = (user: User) => {
    const newStatus = user.status === 'active' ? 'inactive' : 'active';
    message.success(`用户已${newStatus === 'active' ? '启用' : '禁用'}`);
  };

  const handleResetPassword = (username: string) => {
    message.success(`已重置用户 ${username} 的密码，新密码已发送至邮箱`);
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      message.success(editingUser ? '用户更新成功' : '用户创建成功');
      setIsModalVisible(false);
      form.resetFields();
    });
  };

  const userColumns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (text: string, record: User) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          <Text strong>{text}</Text>
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
      filters: [
        { text: '超级管理员', value: '超级管理员' },
        { text: '管理员', value: '管理员' },
        { text: '开发者', value: '开发者' },
        { text: '研究员', value: '研究员' },
        { text: '普通用户', value: '普通用户' },
      ],
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '活跃' : '已禁用'}
        </Tag>
      ),
      filters: [
        { text: '活跃', value: 'active' },
        { text: '已禁用', value: 'inactive' },
      ],
    },
    {
      title: '最后登录',
      dataIndex: 'lastLogin',
      key: 'lastLogin',
      sorter: true,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      sorter: true,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<LockOutlined />}
            onClick={() => handleResetPassword(record.username)}
          >
            重置密码
          </Button>
          <Button
            type="link"
            size="small"
            icon={record.status === 'active' ? <StopOutlined /> : <CheckOutlined />}
            onClick={() => handleToggleStatus(record)}
          >
            {record.status === 'active' ? '禁用' : '启用'}
          </Button>
          <Popconfirm
            title="确定要删除此用户吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const roleColumns = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <SafetyOutlined style={{ color: '#1890ff' }} />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '用户数',
      dataIndex: 'userCount',
      key: 'userCount',
      render: (count: number) => (
        <Tag color="blue" icon={<TeamOutlined />}>
          {count} 人
        </Tag>
      ),
      sorter: true,
    },
    {
      title: '权限数',
      dataIndex: 'permissionCount',
      key: 'permissionCount',
      render: (count: number) => (
        <Tag color="green">{count} 项</Tag>
      ),
      sorter: true,
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small">
            编辑权限
          </Button>
          <Button type="link" size="small">
            查看用户
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <TeamOutlined />
            <span>用户管理</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加用户
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Search
            placeholder="搜索用户名或邮箱"
            allowClear
            style={{ width: 300 }}
            onSearch={(value) => setSearchText(value)}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="筛选角色"
            allowClear
            style={{ width: 150 }}
            value={roleFilter}
            onChange={setRoleFilter}
          >
            <Select.Option value="超级管理员">超级管理员</Select.Option>
            <Select.Option value="管理员">管理员</Select.Option>
            <Select.Option value="开发者">开发者</Select.Option>
            <Select.Option value="研究员">研究员</Select.Option>
            <Select.Option value="普通用户">普通用户</Select.Option>
          </Select>
          <Select
            placeholder="筛选状态"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={setStatusFilter}
          >
            <Select.Option value="active">活跃</Select.Option>
            <Select.Option value="inactive">已禁用</Select.Option>
          </Select>
        </Space>

        <Table
          columns={userColumns}
          dataSource={users}
          rowKey="id"
          pagination={{
            total: users.length,
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个用户`,
          }}
        />
      </Card>

      <Card
        title={
          <Space>
            <SafetyOutlined />
            <span>角色管理</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => message.success('功能开发中')}>
            添加角色
          </Button>
        }
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Statistic title="总角色数" value={5} prefix={<SafetyOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="总用户数" value={128} prefix={<TeamOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="活跃用户" value={120} styles={{ content: { color: '#3f8600' } }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="今日新增" value={3} />
          </Col>
        </Row>

        <Table
          columns={roleColumns}
          dataSource={roles}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>

      <Modal
        title={editingUser ? '编辑用户' : '添加用户'}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" prefix={<UserOutlined />} />
          </Form.Item>

          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          {!editingUser && (
            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password placeholder="请输入密码" />
            </Form.Item>
          )}

          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select placeholder="请选择角色">
              <Select.Option value="超级管理员">超级管理员</Select.Option>
              <Select.Option value="管理员">管理员</Select.Option>
              <Select.Option value="开发者">开发者</Select.Option>
              <Select.Option value="研究员">研究员</Select.Option>
              <Select.Option value="普通用户">普通用户</Select.Option>
            </Select>
          </Form.Item>

          {editingUser && (
            <Form.Item label="状态" name="status">
              <Select>
                <Select.Option value="active">活跃</Select.Option>
                <Select.Option value="inactive">已禁用</Select.Option>
              </Select>
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagement;

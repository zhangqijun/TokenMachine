import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Tree,
  Button,
  Space,
  Tag,
  Input,
  Modal,
  Form,
  message,
  Typography,
  Divider,
  Checkbox,
  Tabs,
  Table,
  Popconfirm,
  Select,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SafetyOutlined,
  FolderOutlined,
  FileTextOutlined,
  SaveOutlined,
  RollbackOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Search } = Input;

interface Permission {
  id: string;
  name: string;
  key: string;
  type: 'module' | 'action';
  children?: Permission[];
}

interface Role {
  id: string;
  name: string;
  description: string;
  userCount: number;
  permissions: string[];
}

const PermissionManagement = () => {
  const [selectedRole, setSelectedRole] = useState<string>('1');
  const [isRoleModalVisible, setIsRoleModalVisible] = useState(false);
  const [isPermissionModalVisible, setIsPermissionModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [permissionForm] = Form.useForm();
  const [checkedKeys, setCheckedKeys] = useState<string[]>(['model:read', 'model:write']);

  const permissions: Permission[] = [
    {
      id: '1',
      name: '模型与实例',
      key: 'model',
      type: 'module',
      children: [
        { id: '1-1', name: '查看模型', key: 'model:read', type: 'action' },
        { id: '1-2', name: '上传模型', key: 'model:upload', type: 'action' },
        { id: '1-3', name: '删除模型', key: 'model:delete', type: 'action' },
        { id: '1-4', name: '编辑模型', key: 'model:write', type: 'action' },
      ],
    },
    {
      id: '2',
      name: '节点与后端',
      key: 'deployment',
      type: 'module',
      children: [
        { id: '2-1', name: '查看部署', key: 'deployment:read', type: 'action' },
        { id: '2-2', name: '创建部署', key: 'deployment:create', type: 'action' },
        { id: '2-3', name: '停止部署', key: 'deployment:stop', type: 'action' },
        { id: '2-4', name: '删除部署', key: 'deployment:delete', type: 'action' },
      ],
    },
    {
      id: '3',
      name: '集群管理',
      key: 'cluster',
      type: 'module',
      children: [
        { id: '3-1', name: '查看集群', key: 'cluster:read', type: 'action' },
        { id: '3-2', name: '管理节点', key: 'cluster:manage', type: 'action' },
        { id: '3-3', name: 'GPU调度', key: 'cluster:schedule', type: 'action' },
      ],
    },
    {
      id: '4',
      name: '用户管理',
      key: 'user',
      type: 'module',
      children: [
        { id: '4-1', name: '查看用户', key: 'user:read', type: 'action' },
        { id: '4-2', name: '创建用户', key: 'user:create', type: 'action' },
        { id: '4-3', name: '编辑用户', key: 'user:write', type: 'action' },
        { id: '4-4', name: '删除用户', key: 'user:delete', type: 'action' },
      ],
    },
    {
      id: '5',
      name: '权限管理',
      key: 'permission',
      type: 'module',
      children: [
        { id: '5-1', name: '查看权限', key: 'permission:read', type: 'action' },
        { id: '5-2', name: '分配权限', key: 'permission:assign', type: 'action' },
      ],
    },
    {
      id: '6',
      name: '系统设置',
      key: 'system',
      type: 'module',
      children: [
        { id: '6-1', name: '查看配置', key: 'system:read', type: 'action' },
        { id: '6-2', name: '修改配置', key: 'system:write', type: 'action' },
        { id: '6-3', name: '系统监控', key: 'system:monitor', type: 'action' },
      ],
    },
  ];

  const roles: Role[] = [
    {
      id: '1',
      name: '超级管理员',
      description: '拥有系统所有权限',
      userCount: 2,
      permissions: ['all'],
    },
    {
      id: '2',
      name: '管理员',
      description: '管理用户和配置',
      userCount: 5,
      permissions: ['model:read', 'deployment:read', 'deployment:create', 'user:read', 'user:create'],
    },
    {
      id: '3',
      name: '开发者',
      description: '模型开发和部署权限',
      userCount: 12,
      permissions: ['model:read', 'model:upload', 'deployment:read', 'deployment:create'],
    },
    {
      id: '4',
      name: '研究员',
      description: '只读访问权限',
      userCount: 8,
      permissions: ['model:read', 'deployment:read', 'cluster:read'],
    },
  ];

  const onCheck = (checkedKeysValue: any) => {
    setCheckedKeys(checkedKeysValue);
  };

  const handleSavePermissions = () => {
    message.success('权限保存成功');
  };

  const handleResetPermissions = () => {
    setCheckedKeys(['model:read', 'model:write']);
    message.info('已重置为默认权限');
  };

  const handleAddRole = () => {
    form.resetFields();
    setIsRoleModalVisible(true);
  };

  const handleEditRole = (role: Role) => {
    form.setFieldsValue({
      name: role.name,
      description: role.description,
    });
    setIsRoleModalVisible(true);
  };

  const handleDeleteRole = (roleId: string) => {
    message.success('角色已删除');
  };

  const handleAddPermission = () => {
    permissionForm.resetFields();
    setIsPermissionModalVisible(true);
  };

  const treeData = permissions.map((perm) => ({
    title: perm.name,
    key: perm.key,
    children: perm.children?.map((child) => ({
      title: child.name,
      key: child.key,
    })),
  }));

  const permissionColumns = [
    {
      title: '权限名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Permission) => (
        <Space>
          {record.type === 'module' ? <FolderOutlined /> : <FileTextOutlined />}
          <Text strong={record.type === 'module'}>{text}</Text>
        </Space>
      ),
    },
    {
      title: '权限键',
      dataIndex: 'key',
      key: 'key',
      render: (key: string) => <Tag color="blue">{key}</Tag>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'module' ? 'purple' : 'green'}>
          {type === 'module' ? '模块' : '操作'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />}>
            编辑
          </Button>
          <Popconfirm title="确定删除此权限？" onConfirm={() => message.success('权限已删除')}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const flattenPermissions = (perms: Permission[]): Permission[] => {
    const result: Permission[] = [];
    perms.forEach((perm) => {
      result.push(perm);
      if (perm.children) {
        result.push(...flattenPermissions(perm.children));
      }
    });
    return result;
  };

  return (
    <div>
      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <SafetyOutlined />
                <span>角色列表</span>
              </Space>
            }
            extra={
              <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleAddRole}>
                添加角色
              </Button>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {roles.map((role) => (
                <Card
                  key={role.id}
                  size="small"
                  hoverable
                  style={{
                    border: selectedRole === role.id ? '2px solid #1890ff' : '1px solid #f0f0f0',
                    cursor: 'pointer',
                  }}
                  onClick={() => setSelectedRole(role.id)}
                >
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text strong>{role.name}</Text>
                      <Tag color="blue">{role.userCount} 人</Tag>
                    </div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {role.description}
                    </Text>
                    <Space>
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditRole(role);
                        }}
                      >
                        编辑
                      </Button>
                      {role.id !== '1' && (
                        <Popconfirm
                          title="确定删除此角色？"
                          onConfirm={(e) => {
                            e?.stopPropagation();
                            handleDeleteRole(role.id);
                          }}
                          onCancel={(e) => e?.stopPropagation()}
                        >
                          <Button
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={(e) => e.stopPropagation()}
                          >
                            删除
                          </Button>
                        </Popconfirm>
                      )}
                    </Space>
                  </Space>
                </Card>
              ))}
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <SafetyOutlined />
                <span>权限配置</span>
                <Text type="secondary">
                  ({roles.find((r) => r.id === selectedRole)?.name})
                </Text>
              </Space>
            }
            extra={
              <Space>
                <Button icon={<RollbackOutlined />} onClick={handleResetPermissions}>
                  重置
                </Button>
                <Button type="primary" icon={<SaveOutlined />} onClick={handleSavePermissions}>
                  保存
                </Button>
              </Space>
            }
          >
            <div style={{ marginBottom: 16 }}>
              <Text strong>权限树</Text>
              <Divider style={{ margin: '12px 0' }} />
            </div>

            <Tree
              checkable
              checkedKeys={checkedKeys}
              onCheck={onCheck}
              treeData={treeData}
              defaultExpandAll
              style={{ marginBottom: 24 }}
            />

            <Divider />

            <div style={{ marginTop: 16 }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Text strong>已选权限 ({checkedKeys.length} 项)</Text>
              </Space>
              <div style={{ marginTop: 12 }}>
                <Space wrap>
                  {checkedKeys.map((key) => (
                    <Tag key={key} color="blue" closable>
                      {key}
                    </Tag>
                  ))}
                </Space>
              </div>
            </div>
          </Card>

          <Card
            title="权限列表"
            style={{ marginTop: 16 }}
            extra={
              <Button icon={<PlusOutlined />} onClick={handleAddPermission}>
                添加权限
              </Button>
            }
          >
            <Table
              columns={permissionColumns}
              dataSource={flattenPermissions(permissions)}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title="添加角色"
        open={isRoleModalVisible}
        onOk={() => {
          form.validateFields().then(() => {
            message.success('角色创建成功');
            setIsRoleModalVisible(false);
            form.resetFields();
          });
        }}
        onCancel={() => {
          setIsRoleModalVisible(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="角色名称"
            name="name"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="请输入角色名称" />
          </Form.Item>

          <Form.Item
            label="角色描述"
            name="description"
            rules={[{ required: true, message: '请输入角色描述' }]}
          >
            <Input.TextArea rows={3} placeholder="请输入角色描述" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加权限"
        open={isPermissionModalVisible}
        onOk={() => {
          permissionForm.validateFields().then(() => {
            message.success('权限添加成功');
            setIsPermissionModalVisible(false);
            permissionForm.resetFields();
          });
        }}
        onCancel={() => {
          setIsPermissionModalVisible(false);
          permissionForm.resetFields();
        }}
      >
        <Form form={permissionForm} layout="vertical">
          <Form.Item
            label="权限名称"
            name="name"
            rules={[{ required: true, message: '请输入权限名称' }]}
          >
            <Input placeholder="例如：查看模型" />
          </Form.Item>

          <Form.Item
            label="权限键"
            name="key"
            rules={[{ required: true, message: '请输入权限键' }]}
          >
            <Input placeholder="例如：model:read" />
          </Form.Item>

          <Form.Item
            label="权限类型"
            name="type"
            rules={[{ required: true, message: '请选择权限类型' }]}
          >
            <Select>
              <Select.Option value="module">模块</Select.Option>
              <Select.Option value="action">操作</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PermissionManagement;

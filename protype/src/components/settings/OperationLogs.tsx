import { useState } from 'react';
import {
  Card,
  Table,
  Space,
  Tag,
  Input,
  Select,
  Button,
  DatePicker,
  Typography,
  Drawer,
  Descriptions,
  message,
} from 'antd';
import {
  SearchOutlined,
  EyeOutlined,
  DownloadOutlined,
  FilterOutlined,
  ReloadOutlined,
  UserOutlined,
  LoginOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  FileTextOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { RangePickerProps } from 'antd/es/date-picker';

const { Title, Text } = Typography;
const { Search } = Input;
const { RangePicker } = DatePicker;

interface OperationLog {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  details: string;
  ip: string;
  status: 'success' | 'failure' | 'warning';
  duration?: number;
}

const OperationLogs = () => {
  const [searchText, setSearchText] = useState('');
  const [actionFilter, setActionFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<any>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<OperationLog | null>(null);

  const logs: OperationLog[] = [
    {
      id: '1',
      timestamp: '2024-01-19 10:30:15',
      user: 'admin',
      action: '登录系统',
      resource: '系统',
      details: '用户登录成功',
      ip: '192.168.1.100',
      status: 'success',
    },
    {
      id: '2',
      timestamp: '2024-01-19 10:28:42',
      user: 'developer',
      action: '创建部署',
      resource: 'deployment',
      details: '创建部署 llama-3-8b-prod',
      ip: '192.168.1.105',
      status: 'success',
      duration: 2340,
    },
    {
      id: '3',
      timestamp: '2024-01-19 10:25:18',
      user: 'developer',
      action: '上传模型',
      resource: 'model',
      details: '上传模型 llama-3-8b-instruct (v2)',
      ip: '192.168.1.105',
      status: 'success',
      duration: 12500,
    },
    {
      id: '4',
      timestamp: '2024-01-19 10:20:05',
      user: 'researcher',
      action: '删除模型',
      resource: 'model',
      details: '删除模型 outdated-model-v1',
      ip: '192.168.1.110',
      status: 'warning',
      duration: 450,
    },
    {
      id: '5',
      timestamp: '2024-01-19 10:15:33',
      user: 'guest_user',
      action: '登录系统',
      resource: '系统',
      details: '登录失败：密码错误（尝试3/5）',
      ip: '192.168.1.200',
      status: 'failure',
    },
    {
      id: '6',
      timestamp: '2024-01-19 10:10:22',
      user: 'admin',
      action: '修改配置',
      resource: 'system',
      details: '修改系统配置：GPU显存利用率从90%调整到95%',
      ip: '192.168.1.100',
      status: 'success',
      duration: 120,
    },
    {
      id: '7',
      timestamp: '2024-01-19 10:05:45',
      user: 'developer',
      action: '停止部署',
      resource: 'deployment',
      details: '停止部署 qwen-14b-dev',
      ip: '192.168.1.105',
      status: 'success',
      duration: 890,
    },
    {
      id: '8',
      timestamp: '2024-01-19 09:58:12',
      user: 'researcher',
      action: '创建用户',
      resource: 'user',
      details: '创建用户 new_researcher',
      ip: '192.168.1.110',
      status: 'success',
      duration: 340,
    },
    {
      id: '9',
      timestamp: '2024-01-19 09:45:30',
      user: 'admin',
      action: '删除部署',
      resource: 'deployment',
      details: '删除部署 test-deployment-001',
      ip: '192.168.1.100',
      status: 'success',
      duration: 560,
    },
    {
      id: '10',
      timestamp: '2024-01-19 09:30:18',
      user: 'developer',
      action: '编辑角色',
      resource: 'role',
      details: '修改角色"开发者"的权限：添加模型删除权限',
      ip: '192.168.1.105',
      status: 'success',
      duration: 280,
    },
  ];

  const getActionIcon = (action: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      登录系统: <LoginOutlined />,
      创建部署: <PlusOutlined />,
      上传模型: <PlusOutlined />,
      删除模型: <DeleteOutlined />,
      修改配置: <EditOutlined />,
      停止部署: <StopOutlined />,
      创建用户: <PlusOutlined />,
      删除部署: <DeleteOutlined />,
      编辑角色: <EditOutlined />,
    };
    return iconMap[action] || <EditOutlined />;
  };

  const getStatusTag = (status: string) => {
    const config: Record<string, { color: string; label: string }> = {
      success: { color: 'success', label: '成功' },
      failure: { color: 'error', label: '失败' },
      warning: { color: 'warning', label: '警告' },
    };
    const { color, label } = config[status] || { color: 'default', label: status };
    return <Tag color={color}>{label}</Tag>;
  };

  const handleView = (record: OperationLog) => {
    setSelectedLog(record);
    setDrawerVisible(true);
  };

  const handleExport = () => {
    message.success('日志导出成功');
  };

  const handleRefresh = () => {
    message.success('日志已刷新');
  };

  const handleDateRangeChange: RangePickerProps['onChange'] = (dates) => {
    setDateRange(dates);
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      sorter: true,
    },
    {
      title: '用户',
      dataIndex: 'user',
      key: 'user',
      width: 120,
      render: (text: string) => (
        <Space>
          <UserOutlined style={{ color: '#1890ff' }} />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (action: string) => (
        <Space>
          {getActionIcon(action)}
          <span>{action}</span>
        </Space>
      ),
      filters: [
        { text: '登录系统', value: '登录系统' },
        { text: '创建部署', value: '创建部署' },
        { text: '上传模型', value: '上传模型' },
        { text: '删除模型', value: '删除模型' },
        { text: '修改配置', value: '修改配置' },
        { text: '停止部署', value: '停止部署' },
        { text: '创建用户', value: '创建用户' },
        { text: '删除部署', value: '删除部署' },
        { text: '编辑角色', value: '编辑角色' },
      ],
    },
    {
      title: '资源',
      dataIndex: 'resource',
      key: 'resource',
      width: 100,
      render: (resource: string) => <Tag>{resource}</Tag>,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
      width: 140,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => getStatusTag(status),
      filters: [
        { text: '成功', value: 'success' },
        { text: '失败', value: 'failure' },
        { text: '警告', value: 'warning' },
      ],
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (duration?: number) => (duration ? `${duration}ms` : '-'),
      sorter: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: OperationLog) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleView(record)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>操作日志</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出日志
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle" wrap>
          <Search
            placeholder="搜索用户、操作或资源"
            allowClear
            style={{ width: 300 }}
            onSearch={(value) => setSearchText(value)}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="筛选操作类型"
            allowClear
            style={{ width: 150 }}
            value={actionFilter}
            onChange={setActionFilter}
          >
            <Select.Option value="登录系统">登录系统</Select.Option>
            <Select.Option value="创建部署">创建部署</Select.Option>
            <Select.Option value="上传模型">上传模型</Select.Option>
            <Select.Option value="删除模型">删除模型</Select.Option>
            <Select.Option value="修改配置">修改配置</Select.Option>
          </Select>
          <Select
            placeholder="筛选状态"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={setStatusFilter}
          >
            <Select.Option value="success">成功</Select.Option>
            <Select.Option value="failure">失败</Select.Option>
            <Select.Option value="warning">警告</Select.Option>
          </Select>
          <RangePicker
            showTime
            placeholder={['开始时间', '结束时间']}
            onChange={handleDateRangeChange}
          />
          <Button icon={<FilterOutlined />}>更多筛选</Button>
        </Space>

        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          pagination={{
            total: logs.length,
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条日志`,
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      <Drawer
        title="日志详情"
        placement="right"
        width={600}
        open={drawerVisible}
        onClose={() => {
          setDrawerVisible(false);
          setSelectedLog(null);
        }}
      >
        {selectedLog && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="日志ID">{selectedLog.id}</Descriptions.Item>
            <Descriptions.Item label="时间">{selectedLog.timestamp}</Descriptions.Item>
            <Descriptions.Item label="用户">{selectedLog.user}</Descriptions.Item>
            <Descriptions.Item label="操作">{selectedLog.action}</Descriptions.Item>
            <Descriptions.Item label="资源">{selectedLog.resource}</Descriptions.Item>
            <Descriptions.Item label="详情">{selectedLog.details}</Descriptions.Item>
            <Descriptions.Item label="IP地址">{selectedLog.ip}</Descriptions.Item>
            <Descriptions.Item label="状态">
              {getStatusTag(selectedLog.status)}
            </Descriptions.Item>
            {selectedLog.duration && (
              <Descriptions.Item label="耗时">{selectedLog.duration}ms</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default OperationLogs;

import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Modal,
  Form,
  Input,
  message,
  Alert,
  Tabs,
  List,
  Popconfirm,
  Checkbox,
  Radio,
} from 'antd';
import {
  DatabaseOutlined,
  DeleteOutlined,
  DownloadOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  CloudDownloadOutlined,
  HistoryOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface BackupRecord {
  id: string;
  name: string;
  type: 'full' | 'incremental';
  size: string;
  created_at: string;
  status: 'success' | 'failed' | 'in_progress';
}

const DataManagement = () => {
  const [backupModalVisible, setBackupModalVisible] = useState(false);
  const [restoreModalVisible, setRestoreModalVisible] = useState(false);
  const [backupForm] = Form.useForm();

  const storageStats = [
    { label: '模型数据', used: 450, total: 1000, unit: 'GB', color: '#1890ff' },
    { label: '日志数据', used: 12, total: 100, unit: 'GB', color: '#52c41a' },
    { label: '备份数据', used: 80, total: 200, unit: 'GB', color: '#faad14' },
    { label: '缓存数据', used: 25, total: 50, unit: 'GB', color: '#722ed1' },
  ];

  const backupRecords: BackupRecord[] = [
    {
      id: '1',
      name: 'backup-2024-01-19-full',
      type: 'full',
      size: '125.5 GB',
      created_at: '2024-01-19 03:00:00',
      status: 'success',
    },
    {
      id: '2',
      name: 'backup-2024-01-18-full',
      type: 'full',
      size: '124.8 GB',
      created_at: '2024-01-18 03:00:00',
      status: 'success',
    },
    {
      id: '3',
      name: 'backup-2024-01-19-incremental',
      type: 'incremental',
      size: '2.3 GB',
      created_at: '2024-01-19 12:00:00',
      status: 'success',
    },
    {
      id: '4',
      name: 'backup-2024-01-17-full',
      type: 'full',
      size: '123.5 GB',
      created_at: '2024-01-17 03:00:00',
      status: 'failed',
    },
  ];

  const dataRetentionPolicy = [
    { name: '模型数据', retention: '永久保存', autoClean: false },
    { name: '日志数据', retention: '30天', autoClean: true },
    { name: '备份数据', retention: '90天', autoClean: true },
    { name: '缓存数据', retention: '7天', autoClean: true },
  ];

  const handleCreateBackup = () => {
    backupForm.validateFields().then(() => {
      message.success('备份任务已创建，正在后台执行');
      setBackupModalVisible(false);
      backupForm.resetFields();
    });
  };

  const handleRestore = (record: BackupRecord) => {
    message.info(`准备恢复备份: ${record.name}`);
    setRestoreModalVisible(true);
  };

  const handleDeleteBackup = (id: string) => {
    message.success('备份已删除');
  };

  const handleCleanup = (type: string) => {
    Modal.confirm({
      title: '确认清理数据',
      icon: <ExclamationCircleOutlined />,
      content: `确定要清理${type}吗？此操作不可撤销。`,
      okText: '确认',
      okType: 'danger',
      cancelText: '取消',
      onOk() {
        message.success(`${type}清理完成`);
      },
    });
  };

  const handleExportData = () => {
    message.success('数据导出任务已创建');
  };

  const backupColumns = [
    {
      title: '备份名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'full' ? 'blue' : 'green'}>
          {type === 'full' ? '全量备份' : '增量备份'}
        </Tag>
      ),
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; label: string }> = {
          success: { color: 'success', label: '成功' },
          failed: { color: 'error', label: '失败' },
          in_progress: { color: 'processing', label: '进行中' },
        };
        const { color, label } = config[status];
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: BackupRecord) => (
        <Space>
          {record.status === 'success' && (
            <Button
              type="link"
              size="small"
              icon={<CloudDownloadOutlined />}
              onClick={() => handleRestore(record)}
            >
              恢复
            </Button>
          )}
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            disabled={record.status !== 'success'}
          >
            下载
          </Button>
          <Popconfirm
            title="确定删除此备份？"
            onConfirm={() => handleDeleteBackup(record.id)}
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

  return (
    <div>
      <Card
        title={
          <Space>
            <DatabaseOutlined />
            <span>数据管理</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="overview"
          items={[
            {
              key: 'overview',
              label: '数据概览',
              children: (
                <div>
                  <Alert
                    message="数据存储建议"
                    description="建议定期清理日志和缓存数据，保持系统性能。模型数据和备份数据建议定期归档到外部存储。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />

                  <Title level={5}>存储空间统计</Title>
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    {storageStats.map((stat) => (
                      <Col xs={24} sm={12} lg={6} key={stat.label}>
                        <Card size="small">
                          <Statistic
                            title={stat.label}
                            value={stat.used}
                            suffix={`/ ${stat.total} ${stat.unit}`}
                            styles={{ content: { color: stat.color } }}
                          />
                          <Progress
                            percent={(stat.used / stat.total) * 100}
                            strokeColor={stat.color}
                            showInfo={false}
                            size="small"
                          />
                        </Card>
                      </Col>
                    ))}
                  </Row>

                  <Title level={5}>数据保留策略</Title>
                  <Card size="small">
                    <List
                      dataSource={dataRetentionPolicy}
                      renderItem={(item) => (
                        <List.Item
                          actions={[
                            <Tag color={item.autoClean ? 'green' : 'default'}>
                              {item.autoClean ? '自动清理' : '手动管理'}
                            </Tag>,
                          ]}
                        >
                          <List.Item.Meta
                            avatar={<DatabaseOutlined style={{ fontSize: 20 }} />}
                            title={item.name}
                            description={`保留时间: ${item.retention}`}
                          />
                        </List.Item>
                      )}
                    />
                  </Card>
                </div>
              ),
            },
            {
              key: 'backup',
              label: '备份管理',
              children: (
                <div>
                  <div
                    style={{
                      marginBottom: 16,
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <Space>
                      <Button
                        type="primary"
                        icon={<SyncOutlined />}
                        onClick={() => setBackupModalVisible(true)}
                      >
                        创建备份
                      </Button>
                      <Button icon={<HistoryOutlined />}>备份计划</Button>
                    </Space>
                  </div>

                  <Table
                    columns={backupColumns}
                    dataSource={backupRecords}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                  />
                </div>
              ),
            },
            {
              key: 'cleanup',
              label: '数据清理',
              children: (
                <div>
                  <Alert
                    message="清理警告"
                    description="数据清理操作不可撤销，请谨慎操作。建议在清理前先创建备份。"
                    type="warning"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Card
                        title="日志数据"
                        size="small"
                        extra={
                          <Tag color="green">12GB / 100GB</Tag>
                        }
                        style={{ marginBottom: 16 }}
                      >
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text>保留30天，每天自动清理过期数据</Text>
                          <Button
                            danger
                            block
                            icon={<DeleteOutlined />}
                            onClick={() => handleCleanup('日志数据')}
                          >
                            立即清理
                          </Button>
                        </Space>
                      </Card>
                    </Col>

                    <Col xs={24} md={12}>
                      <Card
                        title="缓存数据"
                        size="small"
                        extra={
                          <Tag color="purple">25GB / 50GB</Tag>
                        }
                        style={{ marginBottom: 16 }}
                      >
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text>保留7天，包括临时文件和会话缓存</Text>
                          <Button
                            danger
                            block
                            icon={<DeleteOutlined />}
                            onClick={() => handleCleanup('缓存数据')}
                          >
                            立即清理
                          </Button>
                        </Space>
                      </Card>
                    </Col>

                    <Col xs={24} md={12}>
                      <Card
                        title="临时文件"
                        size="small"
                        extra={
                          <Tag color="orange">8.5GB</Tag>
                        }
                        style={{ marginBottom: 16 }}
                      >
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text>上传和下载过程中的临时文件</Text>
                          <Button
                            danger
                            block
                            icon={<DeleteOutlined />}
                            onClick={() => handleCleanup('临时文件')}
                          >
                            立即清理
                          </Button>
                        </Space>
                      </Card>
                    </Col>

                    <Col xs={24} md={12}>
                      <Card
                        title="过期备份"
                        size="small"
                        extra={
                          <Tag color="blue">15.2GB</Tag>
                        }
                        style={{ marginBottom: 16 }}
                      >
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text>超过保留期限的备份文件</Text>
                          <Button
                            danger
                            block
                            icon={<DeleteOutlined />}
                            onClick={() => handleCleanup('过期备份')}
                          >
                            立即清理
                          </Button>
                        </Space>
                      </Card>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'export',
              label: '数据导出',
              children: (
                <div>
                  <Alert
                    message="数据导出"
                    description="可以导出系统配置、用户数据等用于迁移或分析。大型数据导出可能需要较长时间。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Card title="系统配置" size="small" style={{ marginBottom: 16 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text type="secondary">导出系统配置和设置参数</Text>
                          <Button
                            block
                            icon={<DownloadOutlined />}
                            onClick={handleExportData}
                          >
                            导出配置
                          </Button>
                        </Space>
                      </Card>
                    </Col>

                    <Col xs={24} md={12}>
                      <Card title="用户数据" size="small" style={{ marginBottom: 16 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text type="secondary">导出用户列表和权限数据</Text>
                          <Button
                            block
                            icon={<DownloadOutlined />}
                            onClick={handleExportData}
                          >
                            导出用户
                          </Button>
                        </Space>
                      </Card>
                    </Col>

                    <Col xs={24} md={12}>
                      <Card title="部署记录" size="small" style={{ marginBottom: 16 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text type="secondary">导出部署历史和运行记录</Text>
                          <Button
                            block
                            icon={<DownloadOutlined />}
                            onClick={handleExportData}
                          >
                            导出记录
                          </Button>
                        </Space>
                      </Card>
                    </Col>

                    <Col xs={24} md={12}>
                      <Card title="操作日志" size="small" style={{ marginBottom: 16 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text type="secondary">导出系统操作日志（CSV格式）</Text>
                          <Button
                            block
                            icon={<DownloadOutlined />}
                            onClick={handleExportData}
                          >
                            导出日志
                          </Button>
                        </Space>
                      </Card>
                    </Col>
                  </Row>
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* 创建备份弹窗 */}
      <Modal
        title="创建数据备份"
        open={backupModalVisible}
        onOk={handleCreateBackup}
        onCancel={() => {
          setBackupModalVisible(false);
          backupForm.resetFields();
        }}
      >
        <Form form={backupForm} layout="vertical">
          <Form.Item
            label="备份名称"
            name="name"
            initialValue={`backup-${new Date().toISOString().split('T')[0]}`}
            rules={[{ required: true, message: '请输入备份名称' }]}
          >
            <Input placeholder="请输入备份名称" />
          </Form.Item>

          <Form.Item label="备份类型" name="type" initialValue="full">
            <Radio.Group>
              <Radio value="full">全量备份</Radio>
              <Radio value="incremental">增量备份</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item label="备份内容" name="content" initialValue={['models', 'database']}>
            <Checkbox.Group>
              <Space direction="vertical">
                <Checkbox value="models">模型数据</Checkbox>
                <Checkbox value="database">数据库</Checkbox>
                <Checkbox value="configs">系统配置</Checkbox>
                <Checkbox value="logs">日志文件</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Form.Item label="备注" name="description">
            <TextArea rows={3} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 恢复备份弹窗 */}
      <Modal
        title="恢复数据备份"
        open={restoreModalVisible}
        onOk={() => {
          message.success('数据恢复任务已创建');
          setRestoreModalVisible(false);
        }}
        onCancel={() => setRestoreModalVisible(false)}
        okButtonProps={{ danger: true }}
        okText="确认恢复"
      >
        <Alert
          message="恢复警告"
          description="数据恢复将覆盖当前数据，请确保已创建当前状态的备份。恢复期间系统可能暂时不可用。"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form layout="vertical">
          <Form.Item label="确认操作" name="confirm" required>
            <Input placeholder="输入 'RESTORE' 确认恢复操作" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DataManagement;

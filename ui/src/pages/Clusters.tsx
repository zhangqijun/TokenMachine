import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Drawer,
  Descriptions,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ClusterOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useStore } from '../store';
import type { Cluster, WorkerPool } from '../mock/data';
import { StatusTag } from '../components/common';
import dayjs from 'dayjs';

const Clusters = () => {
  const { clusters } = useStore();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
  const [form] = Form.useForm();

  const clusterTypeColors: Record<string, string> = {
    docker: 'blue',
    kubernetes: 'purple',
    digitalocean: 'green',
    aws: 'orange',
  };

  const clusterTypeNames: Record<string, string> = {
    docker: 'Docker',
    kubernetes: 'Kubernetes',
    digitalocean: 'DigitalOcean',
    aws: 'AWS',
  };

  // Cluster columns
  const clusterColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Cluster) => (
        <Space>
          <ClusterOutlined />
          <span style={{ fontWeight: 500 }}>{name}</span>
          {record.is_default && (
            <Tag color="gold" icon={<CheckCircleOutlined />}>
              默认
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={clusterTypeColors[type]}>{clusterTypeNames[type]}</Tag>
      ),
    },
    {
      title: 'Worker Pools',
      key: 'worker_pools',
      render: (_: unknown, record: Cluster) => (
        <Space direction="vertical" size="small">
          {record.worker_pools.map(pool => (
            <div key={pool.id}>
              <Tag color="blue">{pool.name}</Tag>
              <span style={{ fontSize: 12, color: '#666' }}>
                {pool.worker_count} workers ({pool.min_workers}-{pool.max_workers})
              </span>
            </div>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <StatusTag status={status} />,
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
      width: 180,
      render: (_: unknown, record: Cluster) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => {
              setSelectedCluster(record);
              setDetailDrawerOpen(true);
            }}
          >
            详情
          </Button>
          {!record.is_default && (
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // Expanded rows for worker pools
  const expandedRowRender = (record: Cluster) => {
    const poolColumns = [
      {
        title: 'Pool 名称',
        dataIndex: 'name',
        key: 'name',
        render: (name: string) => <span style={{ fontWeight: 500 }}>{name}</span>,
      },
      {
        title: 'Worker 数量',
        key: 'workers',
        render: (_: unknown, pool: WorkerPool) => (
          <Space>
            <Badge count={pool.worker_count} showZero />
            <span style={{ fontSize: 12, color: '#666' }}>
              ({pool.min_workers}-{pool.max_workers})
            </span>
          </Space>
        ),
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => <StatusTag status={status} />,
      },
      {
        title: '配置',
        key: 'config',
        render: (_: unknown, pool: WorkerPool) => {
          const config = pool.config.provider_specific;
          if (config.docker) {
            return (
              <Space direction="vertical" size="small">
                <span style={{ fontSize: 12 }}>镜像: {config.docker.image}</span>
                <span style={{ fontSize: 12 }}>卷: {config.docker.volumes.length}</span>
              </Space>
            );
          }
          if (config.kubernetes) {
            return (
              <Space direction="vertical" size="small">
                <span style={{ fontSize: 12 }}>命名空间: {config.kubernetes.namespace}</span>
                <span style={{ fontSize: 12 }}>副本: {config.kubernetes.replicas}</span>
              </Space>
            );
          }
          return '-';
        },
      },
      {
        title: '操作',
        key: 'actions',
        render: () => (
          <Button type="link" size="small">
            配置
          </Button>
        ),
      },
    ];

    return (
      <Table
        columns={poolColumns}
        dataSource={record.worker_pools}
        pagination={false}
        rowKey="id"
        size="small"
      />
    );
  };

  const handleCreateCluster = async (values: any) => {
    try {
      message.success('集群创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
    } catch (error) {
      message.error('创建集群失败');
    }
  };

  const handleDelete = (record: Cluster) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除集群 "${record.name}" 吗？此操作不可撤销。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          message.success('集群已删除');
        } catch (error) {
          message.error('删除集群失败');
        }
      },
    });
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>集群管理</h2>
      </div>

      <Card
        title="集群列表"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            新建集群
          </Button>
        }
      >
        <Table
          dataSource={clusters}
          columns={clusterColumns}
          rowKey="id"
          expandable={{
            expandedRowRender,
            defaultExpandAllRows: false,
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个集群`,
          }}
        />
      </Card>

      {/* Create Cluster Modal */}
      <Modal
        title="新建集群"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateCluster}
          initialValues={{
            type: 'docker',
            min_workers: 2,
            max_workers: 4,
          }}
        >
          <Form.Item
            label="集群名称"
            name="name"
            rules={[{ required: true, message: '请输入集群名称' }]}
          >
            <Input placeholder="my-cluster" />
          </Form.Item>

          <Form.Item
            label="提供商"
            name="type"
            rules={[{ required: true, message: '请选择提供商' }]}
          >
            <Select>
              <Select.Option value="docker">Docker</Select.Option>
              <Select.Option value="kubernetes">Kubernetes</Select.Option>
              <Select.Option value="digitalocean">DigitalOcean</Select.Option>
              <Select.Option value="aws">AWS</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="Worker Pool 配置">
            <Form.Item
              name="pool_name"
              label="Pool 名称"
              rules={[{ required: true, message: '请输入 Pool 名称' }]}
              style={{ marginBottom: 16 }}
            >
              <Input placeholder="pool-1" />
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.type !== currentValues.type}
            >
              {({ getFieldValue }) => {
                const type = getFieldValue('type');
                if (type === 'docker') {
                  return (
                    <>
                      <Form.Item
                        name="docker_image"
                        label="Docker 镜像"
                        initialValue="tokenmachine/worker:latest"
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item
                        name="docker_volumes"
                        label="卷挂载"
                        initialValue="/var/lib/backend/models:/models"
                      >
                        <Input placeholder="host_path:container_path" />
                      </Form.Item>
                    </>
                  );
                }
                if (type === 'kubernetes') {
                  return (
                    <>
                      <Form.Item
                        name="k8s_namespace"
                        label="命名空间"
                        initialValue="tokenmachine"
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item
                        name="k8s_replicas"
                        label="副本数"
                        initialValue={2}
                        rules={[{ required: true }]}
                      >
                        <InputNumber min={1} max={10} style={{ width: '100%' }} />
                      </Form.Item>
                    </>
                  );
                }
                return null;
              }}
            </Form.Item>

            <Form.Item label="Worker 数量">
              <Space>
                <Form.Item name="min_workers" noStyle>
                  <InputNumber min={1} max={10} />
                </Form.Item>
                <span>-</span>
                <Form.Item name="max_workers" noStyle>
                  <InputNumber min={1} max={10} />
                </Form.Item>
              </Space>
            </Form.Item>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block>
              创建集群
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Cluster Detail Drawer */}
      <Drawer
        title="集群详情"
        placement="right"
        width={720}
        open={detailDrawerOpen}
        onClose={() => {
          setDetailDrawerOpen(false);
          setSelectedCluster(null);
        }}
      >
        {selectedCluster && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* Basic Info */}
            <div>
              <h4>基本信息</h4>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="名称">{selectedCluster.name}</Descriptions.Item>
                <Descriptions.Item label="类型">
                  <Tag color={clusterTypeColors[selectedCluster.type]}>
                    {clusterTypeNames[selectedCluster.type]}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <StatusTag status={selectedCluster.status} />
                </Descriptions.Item>
                <Descriptions.Item label="默认集群">
                  {selectedCluster.is_default ? '是' : '否'}
                </Descriptions.Item>
                <Descriptions.Item label="创建时间" span={2}>
                  {dayjs(selectedCluster.created_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
                <Descriptions.Item label="更新时间" span={2}>
                  {dayjs(selectedCluster.updated_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              </Descriptions>
            </div>

            {/* Worker Pools */}
            <div>
              <h4>Worker Pools</h4>
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {selectedCluster.worker_pools.map(pool => (
                  <Card key={pool.id} size="small" title={pool.name}>
                    <Descriptions column={2} size="small">
                      <Descriptions.Item label="Worker 数量">
                        {pool.worker_count} ({pool.min_workers}-{pool.max_workers})
                      </Descriptions.Item>
                      <Descriptions.Item label="状态">
                        <StatusTag status={pool.status} />
                      </Descriptions.Item>
                      <Descriptions.Item label="配置" span={2}>
                        {pool.config.provider_specific.docker && (
                          <Space direction="vertical" size="small" style={{ fontSize: 12 }}>
                            <div>Docker 镜像: {pool.config.provider_specific.docker.image}</div>
                            <div>卷: {pool.config.provider_specific.docker.volumes.join(', ')}</div>
                          </Space>
                        )}
                        {pool.config.provider_specific.kubernetes && (
                          <Space direction="vertical" size="small" style={{ fontSize: 12 }}>
                            <div>命名空间: {pool.config.provider_specific.kubernetes.namespace}</div>
                            <div>副本: {pool.config.provider_specific.kubernetes.replicas}</div>
                          </Space>
                        )}
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                ))}
              </Space>
            </div>
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default Clusters;

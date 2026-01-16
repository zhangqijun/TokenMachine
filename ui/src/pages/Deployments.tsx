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
  Row,
  Col,
  Statistic,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  StopOutlined,
  RocketOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import { useStore } from '../store';
import type { Deployment } from '../mock/data';
import dayjs from 'dayjs';

const Deployments = () => {
  const { deployments, models, gpus, createDeployment, stopDeployment, isLoading } = useStore();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null);
  const [form] = Form.useForm();

  const statusConfig: Record<string, { color: string; text: string; icon: string }> = {
    running: { color: 'success', text: '运行中', icon: '●' },
    starting: { color: 'processing', text: '启动中', icon: '○' },
    stopping: { color: 'default', text: '停止中', icon: '○' },
    stopped: { color: 'default', text: '已停止', icon: '○' },
    error: { color: 'error', text: '错误', icon: '✕' },
  };

  const envColors: Record<string, string> = {
    prod: 'red',
    staging: 'orange',
    dev: 'blue',
    test: 'green',
  };

  const availableModels = models.filter(m => m.status === 'running' || m.status === 'stopped' || m.status === 'error');
  const availableGpus = gpus.filter(g => g.status === 'available');

  const columns = [
    {
      title: '部署名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <RocketOutlined />
          <span style={{ fontWeight: 500 }}>{name}</span>
        </Space>
      ),
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: '环境',
      dataIndex: 'environment',
      key: 'environment',
      render: (env: string) => (
        <Tag color={envColors[env]}>{env.toUpperCase()}</Tag>
      ),
    },
    {
      title: '推理引擎',
      dataIndex: 'backend',
      key: 'backend',
      render: (backend: string) => backend.toUpperCase(),
    },
    {
      title: '副本',
      dataIndex: 'replicas',
      key: 'replicas',
      render: (replicas: number, record: Deployment) => `${replicas} × ${record.gpu_per_replica} GPU`,
    },
    {
      title: 'GPU',
      dataIndex: 'gpu_ids',
      key: 'gpu_ids',
      render: (gpuIds: string[]) => (
        <Space wrap>
          {gpuIds.map(id => (
            <Tag key={id} color="blue">{id}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'QPS / 延迟',
      key: 'metrics',
      render: (_: unknown, record: Deployment) => (
        <span>
          {record.status === 'running' ? (
            `${record.qps} QPS / ${record.latency_ms}ms`
          ) : (
            '-'
          )}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = statusConfig[status];
        return (
          <Tag color={config.color}>
            {config.icon} {config.text}
          </Tag>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: Deployment) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => {
              setSelectedDeployment(record);
              setDetailDrawerOpen(true);
            }}
          >
            详情
          </Button>
          {record.status === 'running' && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleStop(record)}
            >
              停止
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const handleCreateDeployment = async (values: any) => {
    try {
      const selectedModel = models.find(m => m.id === values.model_id);
      if (!selectedModel) {
        message.error('请选择有效的模型');
        return;
      }

      // Calculate GPU IDs
      const gpuIds: string[] = [];
      for (let i = 0; i < values.replicas; i++) {
        const gpuIndex = i % availableGpus.length;
        gpuIds.push(availableGpus[gpuIndex]?.id || `gpu:${i}`);
      }

      await createDeployment({
        model_id: values.model_id,
        model_name: selectedModel.name,
        name: values.name,
        environment: values.environment,
        replicas: values.replicas,
        gpu_per_replica: values.gpu_per_replica,
        backend: values.backend,
        status: 'starting',
        qps: 0,
        latency_ms: 0,
        gpu_ids: gpuIds,
      });
      message.success('部署创建成功，正在启动...');
      setIsCreateModalOpen(false);
      form.resetFields();
    } catch (error) {
      message.error('创建部署失败');
    }
  };

  const handleStop = (record: Deployment) => {
    Modal.confirm({
      title: '确认停止',
      content: `确定要停止部署 "${record.name}" 吗？`,
      okText: '停止',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await stopDeployment(record.id);
          message.success('部署已停止');
        } catch (error) {
          message.error('停止部署失败');
        }
      },
    });
  };

  // Calculate stats
  const runningDeployments = deployments.filter(d => d.status === 'running').length;
  const totalGpuUsed = deployments
    .filter(d => d.status === 'running')
    .reduce((sum, d) => sum + d.replicas * d.gpu_per_replica, 0);

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="运行中的部署"
              value={runningDeployments}
              suffix={`/ ${deployments.length}`}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="GPU 使用"
              value={totalGpuUsed}
              suffix={`/ ${gpus.length}`}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="总 QPS"
              value={deployments
                .filter(d => d.status === 'running')
                .reduce((sum, d) => sum + d.qps, 0)
              }
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="部署管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            创建部署
          </Button>
        }
      >
        <Table
          dataSource={deployments}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          expandable={{
            expandedRowRender: (record: Deployment) => (
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="部署ID">{record.id}</Descriptions.Item>
                <Descriptions.Item label="更新时间">
                  {dayjs(record.updated_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
                <Descriptions.Item label="模型ID">{record.model_id}</Descriptions.Item>
                <Descriptions.Item label="GPU 列表">
                  {record.gpu_ids.join(', ')}
                </Descriptions.Item>
              </Descriptions>
            ),
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个部署`,
          }}
        />
      </Card>

      {/* Create Deployment Modal */}
      <Modal
        title="创建新部署"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateDeployment}
          initialValues={{
            environment: 'prod',
            backend: 'vllm',
            replicas: 1,
            gpu_per_replica: 1,
          }}
        >
          <Form.Item
            label="部署名称"
            name="name"
            rules={[{ required: true, message: '请输入部署名称' }]}
          >
            <Input placeholder="my-production-model" />
          </Form.Item>

          <Form.Item
            label="模型"
            name="model_id"
            rules={[{ required: true, message: '请选择模型' }]}
          >
            <Select
              placeholder="选择要部署的模型"
              showSearch
              optionFilterProp="children"
            >
              {availableModels.map(model => (
                <Select.Option key={model.id} value={model.id}>
                  {model.name} ({model.version}, {model.quantization?.toUpperCase() || 'FP16'})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="环境"
                name="environment"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="prod">生产</Select.Option>
                  <Select.Option value="staging">预发</Select.Option>
                  <Select.Option value="test">测试</Select.Option>
                  <Select.Option value="dev">开发</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="推理引擎"
                name="backend"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="vllm">vLLM</Select.Option>
                  <Select.Option value="sglang">SGLang</Select.Option>
                  <Select.Option value="chitu">Chitu</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="副本数"
                name="replicas"
                rules={[{ required: true }]}
              >
                <InputNumber min={1} max={8} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="GPU/副本"
                name="gpu_per_replica"
                rules={[{ required: true }]}
              >
                <InputNumber min={1} max={8} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4, marginBottom: 16 }}>
            <Space>
              <EnvironmentOutlined />
              <span>可用 GPU: {availableGpus.length} 个</span>
            </Space>
          </div>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={isLoading}>
              创建部署
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Drawer */}
      <Modal
        title="部署详情"
        open={detailDrawerOpen}
        onCancel={() => {
          setDetailDrawerOpen(false);
          setSelectedDeployment(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailDrawerOpen(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {selectedDeployment && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="部署名称" span={2}>
              {selectedDeployment.name}
            </Descriptions.Item>
            <Descriptions.Item label="部署ID" span={2}>
              {selectedDeployment.id}
            </Descriptions.Item>
            <Descriptions.Item label="模型">
              {selectedDeployment.model_name}
            </Descriptions.Item>
            <Descriptions.Item label="环境">
              <Tag color={envColors[selectedDeployment.environment]}>
                {selectedDeployment.environment.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="推理引擎">
              {selectedDeployment.backend.toUpperCase()}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusConfig[selectedDeployment.status].color}>
                {statusConfig[selectedDeployment.status].text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="副本数">
              {selectedDeployment.replicas}
            </Descriptions.Item>
            <Descriptions.Item label="GPU/副本">
              {selectedDeployment.gpu_per_replica}
            </Descriptions.Item>
            <Descriptions.Item label="GPU 列表" span={2}>
              <Space wrap>
                {selectedDeployment.gpu_ids.map(id => (
                  <Tag key={id} color="blue">{id}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="QPS">
              {selectedDeployment.qps}
            </Descriptions.Item>
            <Descriptions.Item label="延迟">
              {selectedDeployment.latency_ms} ms
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {dayjs(selectedDeployment.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间" span={2}>
              {dayjs(selectedDeployment.updated_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Deployments;

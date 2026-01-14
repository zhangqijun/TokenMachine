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
  message,
  Progress,
  Tooltip,
  Row,
  Col,
  Statistic,
} from 'antd';
import { PlusOutlined, DeleteOutlined, DownloadOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import type { Model } from '../mock/data';
import dayjs from 'dayjs';

const Models = () => {
  const { models, addModel, deleteModel, isLoading } = useStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();

  const categoryColors: Record<string, string> = {
    llm: 'blue',
    embedding: 'green',
    reranker: 'orange',
    image: 'purple',
  };

  const categoryNames: Record<string, string> = {
    llm: '大语言模型',
    embedding: '向量模型',
    reranker: '重排序模型',
    image: '图像模型',
  };

  const statusConfig: Record<string, { color: string; text: string }> = {
    ready: { color: 'success', text: '就绪' },
    downloading: { color: 'processing', text: '下载中' },
    error: { color: 'error', text: '错误' },
  };

  const columns = [
    {
      title: '模型名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Tooltip title={name}>
          <span style={{ fontWeight: 500 }}>{name}</span>
        </Tooltip>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100,
    },
    {
      title: '类型',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => (
        <Tag color={categoryColors[category]}>{categoryNames[category]}</Tag>
      ),
    },
    {
      title: '量化',
      dataIndex: 'quantization',
      key: 'quantization',
      width: 80,
      render: (quant: string) => quant.toUpperCase(),
    },
    {
      title: '大小',
      dataIndex: 'size_gb',
      key: 'size_gb',
      width: 100,
      render: (size: number) => `${size} GB`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: string, record: Model) => {
        const config = statusConfig[status];
        if (status === 'downloading' && record.download_progress) {
          return (
            <div>
              <Progress
                type="circle"
                percent={record.download_progress}
                size={40}
                status="active"
              />
            </div>
          );
        }
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: Model) => (
        <Space>
          <Button
            type="link"
            size="small"
            disabled={record.status !== 'ready'}
            icon={<DownloadOutlined />}
            onClick={() => message.info('部署功能即将开放')}
          >
            部署
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const handleAddModel = async (values: any) => {
    try {
      await addModel({
        name: values.name,
        version: values.version,
        category: values.category,
        quantization: values.quantization,
        status: 'downloading',
        size_gb: 0,
        download_progress: 0,
      });
      message.success('模型添加成功，开始下载...');
      setIsModalOpen(false);
      form.resetFields();
    } catch (error) {
      message.error('添加模型失败');
    }
  };

  const handleDelete = (record: Model) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除模型 "${record.name}" 吗？此操作不可撤销。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteModel(record.id);
          message.success('模型删除成功');
        } catch (error) {
          message.error('删除模型失败');
        }
      },
    });
  };

  // Calculate stats
  const totalModels = models.length;
  const readyModels = models.filter(m => m.status === 'ready').length;
  const totalSize = models.reduce((sum, m) => sum + m.size_gb, 0);

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="总模型数"
              value={totalModels}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="就绪模型"
              value={readyModels}
              suffix={`/ ${totalModels}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="总存储"
              value={totalSize}
              suffix="GB"
              precision={1}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="模型管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsModalOpen(true)}
          >
            添加模型
          </Button>
        }
      >
        <Table
          dataSource={models}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个模型`,
          }}
        />
      </Card>

      <Modal
        title="添加模型"
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAddModel}
        >
          <Form.Item
            label="模型名称"
            name="name"
            rules={[{ required: true, message: '请输入模型名称' }]}
            tooltip="例如: meta-llama/Llama-3-8B-Instruct"
          >
            <Input placeholder="meta-llama/Llama-3-8B-Instruct" />
          </Form.Item>

          <Form.Item
            label="版本"
            name="version"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="v1.0" />
          </Form.Item>

          <Form.Item
            label="模型类型"
            name="category"
            rules={[{ required: true, message: '请选择模型类型' }]}
          >
            <Select placeholder="选择类型">
              <Select.Option value="llm">大语言模型</Select.Option>
              <Select.Option value="embedding">向量模型</Select.Option>
              <Select.Option value="reranker">重排序模型</Select.Option>
              <Select.Option value="image">图像模型</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="量化方式"
            name="quantization"
            initialValue="fp16"
            rules={[{ required: true, message: '请选择量化方式' }]}
          >
            <Select>
              <Select.Option value="fp16">FP16 (半精度)</Select.Option>
              <Select.Option value="fp8">FP8 (8位浮点)</Select.Option>
              <Select.Option value="int8">INT8 (8位整数)</Select.Option>
              <Select.Option value="fp4">FP4 (4位浮点)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={isLoading}>
              添加并下载
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Models;

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  Tag,
  Progress,
  Descriptions,
  Table,
  Typography,
  message,
  Modal,
  List,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface GPUInfo {
  id: number;
  utilization: number;
  memory_used: number;
  memory_total: number;
  temperature: number;
  status: 'Running' | 'Idle' | 'Error';
}

interface RunningModel {
  id: string;
  name: string;
  replicas: number;
  gpus: string[];
}

interface WorkerDetail {
  id: string;
  name: string;
  ip: string;
  status: 'Ready' | 'Busy' | 'Draining' | 'Unhealthy';
  gpu_count: number;
  gpu_type: string;
  labels: Record<string, string>;
  created_at: string;
  last_heartbeat: string;
  gpus: GPUInfo[];
  running_models: RunningModel[];
}

const WorkerDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [worker, setWorker] = useState<WorkerDetail | null>(null);

  useEffect(() => {
    // Simulate API call
    setLoading(true);
    setTimeout(() => {
      setWorker({
        id: id || '1',
        name: 'worker-01',
        ip: '192.168.1.101',
        status: 'Ready',
        gpu_count: 4,
        gpu_type: 'NVIDIA A100 80GB',
        labels: {
          'gpu-type': 'a100',
          'zone': 'prod',
        },
        created_at: '2025-01-15 10:30:00',
        last_heartbeat: '5 秒前',
        gpus: [
          { id: 0, utilization: 82, memory_used: 65.6, memory_total: 80, temperature: 75, status: 'Running' },
          { id: 1, utilization: 78, memory_used: 62.4, memory_total: 80, temperature: 71, status: 'Running' },
          { id: 2, utilization: 42, memory_used: 33.6, memory_total: 80, temperature: 56, status: 'Idle' },
          { id: 3, utilization: 45, memory_used: 36.0, memory_total: 80, temperature: 58, status: 'Idle' },
        ],
        running_models: [
          { id: '1', name: 'llama-3-8b', replicas: 2, gpus: ['gpu:0', 'gpu:1'] },
          { id: '2', name: 'qwen-14b', replicas: 1, gpus: ['gpu:2'] },
        ],
      });
      setLoading(false);
    }, 500);
  }, [id]);

  const getStatusColor = (status: WorkerDetail['status']) => {
    const colorMap: Record<WorkerDetail['status'], string> = {
      Ready: 'success',
      Busy: 'processing',
      Draining: 'warning',
      Unhealthy: 'error',
    };
    return colorMap[status];
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization < 50) return '#52c41a';
    if (utilization < 80) return '#1890ff';
    if (utilization < 95) return '#fa8c16';
    return '#f5222d';
  };

  const getGPUStatusColor = (status: GPUInfo['status']) => {
    const colorMap: Record<GPUInfo['status'], string> = {
      Running: 'processing',
      Idle: 'default',
      Error: 'error',
    };
    return colorMap[status];
  };

  const handleDelete = () => {
    Modal.confirm({
      title: '确认删除节点',
      content: `确定要删除节点 ${worker?.name} 吗？此操作不可恢复。`,
      onOk: () => {
        message.success('节点删除成功');
        navigate('/cluster');
      },
    });
  };

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      message.success('刷新成功');
    }, 500);
  };

  const gpuColumns = [
    {
      title: 'GPU ID',
      dataIndex: 'id',
      key: 'id',
      render: (id: number) => <Text code>gpu:{id}</Text>,
    },
    {
      title: '利用率',
      dataIndex: 'utilization',
      key: 'utilization',
      render: (utilization: number) => (
        <Progress
          percent={utilization}
          strokeColor={getUtilizationColor(utilization)}
          size="small"
          format={(percent) => `${percent}%`}
        />
      ),
    },
    {
      title: '显存使用',
      key: 'memory',
      render: (_: any, record: GPUInfo) => (
        <Text>{record.memory_used}GB / {record.memory_total}GB</Text>
      ),
    },
    {
      title: '温度',
      dataIndex: 'temperature',
      key: 'temperature',
      render: (temp: number) => (
        <Text type={temp > 80 ? 'danger' : 'secondary'}>{temp}°C</Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: GPUInfo['status']) => (
        <Tag color={getGPUStatusColor(status)}>{status}</Tag>
      ),
    },
  ];

  if (!worker) {
    return <div>加载中...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/cluster')}
            >
              返回
            </Button>
            <Title level={3} style={{ margin: 0 }}>
              Worker 详情: {worker.name}
            </Title>
          </Space>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              刷新
            </Button>
            <Button icon={<EditOutlined />}>编辑</Button>
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              删除
            </Button>
          </Space>
        </Space>
      </div>

      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="节点名称">{worker.name}</Descriptions.Item>
          <Descriptions.Item label="IP 地址">{worker.ip}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={getStatusColor(worker.status)}>{worker.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="GPU 类型">{worker.gpu_type}</Descriptions.Item>
          <Descriptions.Item label="GPU 数量">{worker.gpu_count}</Descriptions.Item>
          <Descriptions.Item label="注册时间">{worker.created_at}</Descriptions.Item>
          <Descriptions.Item label="最后心跳">{worker.last_heartbeat}</Descriptions.Item>
          <Descriptions.Item label="标签">
            <Space size={4}>
              {Object.entries(worker.labels).map(([key, value]) => (
                <Tag key={key}>{key}={value}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={`GPU 资源 (${worker.gpu_count} 张 ${worker.gpu_type})`} style={{ marginBottom: 16 }}>
        <Table
          columns={gpuColumns}
          dataSource={worker.gpus}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>

      <Card title="运行中的模型">
        <List
          dataSource={worker.running_models}
          renderItem={(model) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{model.name}</Text>
                    <Tag>{model.replicas} 副本</Tag>
                  </Space>
                }
                description={
                  <Space>
                    <Text type="secondary">GPU:</Text>
                    {model.gpus.map((gpu, index) => (
                      <Tag key={index} color="blue">{gpu}</Tag>
                    ))}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default WorkerDetail;

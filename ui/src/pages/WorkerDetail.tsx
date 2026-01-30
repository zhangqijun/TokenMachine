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
  Spin,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import type { Worker, GPU } from '../api';

const { Title } = Typography;

const WorkerDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [worker, setWorker] = useState<Worker | null>(null);
  const [gpus, setGpus] = useState<GPU[]>([]);
  const [stats, setStats] = useState<any>(null);

  const fetchWorkerDetail = async () => {
    if (!id) return;

    setLoading(true);
    try {
      // Fetch worker details (includes gpu_devices)
      const workerResponse = await axios.get(`/workers/${id}`);
      setWorker(workerResponse.data);

      // Extract GPU devices from worker response
      if (workerResponse.data.gpu_devices) {
        setGpus(workerResponse.data.gpu_devices);
      } else {
        setGpus([]);
      }

      // Fetch worker stats
      try {
        const statsResponse = await axios.get(`/workers/${id}/stats`);
        setStats(statsResponse.data);
      } catch (statsError) {
        console.warn('Could not fetch worker stats:', statsError);
      }
    } catch (error: any) {
      message.error(`Failed to load worker: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkerDetail();
  }, [id]);

  const getStatusColor = (status: Worker['status'] | undefined) => {
    const colorMap: Record<string, string> = {
      'READY': 'success',
      'BUSY': 'processing',
      'DRAINING': 'warning',
      'UNHEALTHY': 'error',
      'OFFLINE': 'default',
      'REGISTERING': 'processing',
    };
    return colorMap[status || ''] || 'default';
  };

  const getStatusText = (status: Worker['status'] | undefined) => {
    const textMap: Record<string, string> = {
      'READY': 'Ready',
      'BUSY': 'Busy',
      'DRAINING': 'Draining',
      'UNHEALTHY': 'Unhealthy',
      'OFFLINE': 'Offline',
      'REGISTERING': 'Registering',
    };
    return textMap[status || ''] || status || 'Unknown';
  };

  const getGPUStateColor = (state: GPU['state']) => {
    const colorMap: Record<string, string> = {
      'AVAILABLE': 'success',
      'IN_USE': 'processing',
      'ERROR': 'error',
    };
    return colorMap[state] || 'default';
  };

  const formatMemory = (bytes: number) => {
    if (!bytes) return 'N/A';
    const gb = bytes / (1024 * 1024 * 1024);
    return `${gb.toFixed(2)} GB`;
  };

  const handleDelete = () => {
    Modal.confirm({
      title: 'Delete Worker',
      content: `Are you sure you want to delete worker "${worker?.name}"? This action cannot be undone.`,
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await axios.delete(`/workers/${id}`);
          message.success('Worker deleted successfully');
          navigate('/cluster/workers');
        } catch (error: any) {
          message.error(`Failed to delete worker: ${error.response?.data?.detail || error.message}`);
        }
      },
    });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!worker) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Title level={4}>Worker not found</Title>
        <Button type="primary" onClick={() => navigate('/cluster/workers')}>
          Go Back
        </Button>
      </div>
    );
  }

  const gpuColumns = [
    {
      title: 'Index',
      dataIndex: 'index',
      key: 'index',
      width: 80,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'IP',
      dataIndex: 'ip',
      key: 'ip',
    },
    {
      title: 'Memory',
      dataIndex: 'memory_total',
      key: 'memory_total',
      render: (memory: number) => formatMemory(memory),
    },
    {
      title: 'Utilization',
      dataIndex: 'memory_utilization_rate',
      key: 'memory_utilization_rate',
      render: (utilization: number) => (
        <Progress
          percent={utilization ? utilization * 100 : 0}
          size="small"
          status={utilization && utilization > 0.9 ? 'exception' : 'normal'}
        />
      ),
    },
    {
      title: 'Temperature',
      dataIndex: 'temperature',
      key: 'temperature',
      render: (temp: number) => temp ? `${temp.toFixed(1)}°C` : 'N/A',
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      render: (state: GPU['state']) => (
        <Tag color={getGPUStateColor(state)}>{state}</Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/cluster/workers')}
        >
          Back to Workers
        </Button>
      </div>

      <Card
        title="Worker Details"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchWorkerDetail}
            >
              Refresh
            </Button>
            <Button
              icon={<EditOutlined />}
              onClick={() => message.info('Edit functionality coming soon')}
            >
              Edit
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDelete}
            >
              Delete
            </Button>
          </Space>
        }
      >
        <Descriptions column={2} bordered>
          <Descriptions.Item label="ID">{worker.id}</Descriptions.Item>
          <Descriptions.Item label="Name">{worker.name}</Descriptions.Item>
          <Descriptions.Item label="Status">
            <Tag color={getStatusColor(worker.status)}>
              {getStatusText(worker.status)}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="IP Address">
            {worker.ip || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Hostname">
            {worker.hostname || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="GPU Count">
            {worker.gpu_count} / {worker.expected_gpu_count || '?'}
          </Descriptions.Item>
          <Descriptions.Item label="Agent Type">
            {worker.agent_type || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Agent Version">
            {worker.agent_version || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Last Heartbeat" span={2}>
            {worker.last_heartbeat_at
              ? new Date(worker.last_heartbeat_at).toLocaleString()
              : 'Never'}
          </Descriptions.Item>
          <Descriptions.Item label="Created At" span={2}>
            {new Date(worker.created_at).toLocaleString()}
          </Descriptions.Item>
          {worker.labels && Object.keys(worker.labels).length > 0 && (
            <Descriptions.Item label="Labels" span={2}>
              <Space>
                {Object.entries(worker.labels).map(([key, value]) => (
                  <Tag key={key}>{key}: {value}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          )}
          {worker.capabilities && worker.capabilities.length > 0 && (
            <Descriptions.Item label="Capabilities" span={2}>
              <Space>
                {worker.capabilities.map((cap) => (
                  <Tag key={cap} color="blue">{cap}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          )}
        </Descriptions>

        {stats && (
          <div style={{ marginTop: '24px' }}>
            <Title level={5}>Statistics</Title>
            <Descriptions column={4} bordered size="small">
              <Descriptions.Item label="Total GPUs">
                {stats.total_gpus}
              </Descriptions.Item>
              <Descriptions.Item label="In Use">
                {stats.in_use_gpus}
              </Descriptions.Item>
              <Descriptions.Item label="Error">
                {stats.error_gpus}
              </Descriptions.Item>
              <Descriptions.Item label="Avg Memory Util">
                {stats.avg_memory_utilization}%
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}

        <div style={{ marginTop: '24px' }}>
          <Title level={5}>GPUs ({gpus.length})</Title>
          <Table
            dataSource={gpus}
            columns={gpuColumns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </div>
      </Card>
    </div>
  );
};

export default WorkerDetail;

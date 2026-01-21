import { useState, useMemo } from 'react';
import {
  Table,
  Button,
  Card,
  Space,
  Tag,
  Progress,
  message,
  Modal,
  Typography,
  Row,
  Col,
  Statistic,
  Select,
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  StopOutlined,
  DeleteOutlined,
  ReloadOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import AddWorkerModal from '../components/cluster/AddWorkerModal';

const { Title } = Typography;

interface Worker {
  id: string;
  name: string;
  ip: string;
  status: 'Ready' | 'Busy' | 'Draining' | 'Unhealthy';
  gpu_count: number;
  gpu_utilization: number;
  gpu_memory_used: number;
  gpu_memory_total: number;
  labels: Record<string, string>;
  created_at: string;
  last_heartbeat: string;
}

interface GPUInfo {
  id: number;
  utilization: number;
  memory_used: number;
  memory_total: number;
  temperature: number;
  status: 'Running' | 'Idle' | 'Error';
}

const ClusterOverview = () => {
  const navigate = useNavigate();
  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [filterKey, setFilterKey] = useState<string>('');
  const [filterValues, setFilterValues] = useState<string[]>([]);

  // Mock data
  const [workers, setWorkers] = useState<Worker[]>([
    {
      id: '1',
      name: 'worker-01',
      ip: '192.168.1.101',
      status: 'Ready',
      gpu_count: 4,
      gpu_utilization: 85,
      gpu_memory_used: 128,
      gpu_memory_total: 160,
      labels: { 'gpu-type': 'a100', 'zone': 'prod' },
      created_at: '2025-01-15 10:30:00',
      last_heartbeat: '5 秒前',
    },
    {
      id: '2',
      name: 'worker-02',
      ip: '192.168.1.102',
      status: 'Ready',
      gpu_count: 4,
      gpu_utilization: 72,
      gpu_memory_used: 115,
      gpu_memory_total: 160,
      labels: { 'gpu-type': 'a100', 'zone': 'prod' },
      created_at: '2025-01-15 10:35:00',
      last_heartbeat: '3 秒前',
    },
    {
      id: '3',
      name: 'worker-03',
      ip: '192.168.1.103',
      status: 'Busy',
      gpu_count: 4,
      gpu_utilization: 95,
      gpu_memory_used: 152,
      gpu_memory_total: 160,
      labels: { 'gpu-type': 'a100', 'zone': 'prod' },
      created_at: '2025-01-15 10:40:00',
      last_heartbeat: '2 秒前',
    },
  ]);

  const stats = {
    total_workers: workers.length,
    total_gpus: workers.reduce((sum, w) => sum + w.gpu_count, 0),
    running_gpus: workers.reduce((sum, w) => sum + w.gpu_count, 0),
    unhealthy: workers.filter(w => w.status === 'Unhealthy').length,
  };

  // 收集所有的 label keys 和对应的 values
  const labelKeyValues = useMemo(() => {
    const keyValueMap: Record<string, Set<string>> = {};

    workers.forEach(w => {
      Object.entries(w.labels).forEach(([key, value]) => {
        if (!keyValueMap[key]) {
          keyValueMap[key] = new Set<string>();
        }
        keyValueMap[key].add(value);
      });
    });

    // 转换为数组格式并排序
    return Object.entries(keyValueMap)
      .map(([key, values]) => ({
        key,
        values: Array.from(values).sort(),
      }))
      .sort((a, b) => a.key.localeCompare(b.key));
  }, [workers]);

  // 获取当前选中 key 的所有可选 values
  const currentKeyValues = useMemo(() => {
    if (!filterKey) return [];
    const keyData = labelKeyValues.find(item => item.key === filterKey);
    return keyData?.values || [];
  }, [filterKey, labelKeyValues]);

  // 根据筛选条件过滤workers
  const filteredWorkers = useMemo(() => {
    return workers.filter(worker => {
      if (!filterKey || filterValues.length === 0) return true;

      const workerValue = worker.labels[filterKey];
      return filterValues.includes(workerValue);
    });
  }, [workers, filterKey, filterValues]);

  const getStatusColor = (status: Worker['status']) => {
    const colorMap: Record<Worker['status'], string> = {
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

  const handleViewDetail = (worker: Worker) => {
    navigate(`/cluster/workers/${worker.id}`);
  };

  const handleDrain = (worker: Worker) => {
    Modal.confirm({
      title: '确认排空节点',
      content: `确定要排空节点 ${worker.name} 吗？排空后节点将不再接受新任务。`,
      onOk: () => {
        setWorkers(workers.map(w =>
          w.id === worker.id ? { ...w, status: 'Draining' } : w
        ));
        message.success('节点排空成功');
      },
    });
  };

  const handleDelete = (worker: Worker) => {
    Modal.confirm({
      title: '确认删除节点',
      content: `确定要删除节点 ${worker.name} 吗？此操作不可恢复。`,
      onOk: () => {
        setWorkers(workers.filter(w => w.id !== worker.id));
        message.success('节点删除成功');
      },
    });
  };

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      message.success('刷新成功');
    }, 1000);
  };

  const columns = [
    {
      title: '节点名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Worker) => (
        <a onClick={() => handleViewDetail(record)}>{name}</a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: Worker['status']) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip',
      key: 'ip',
    },
    {
      title: 'GPU 数量',
      dataIndex: 'gpu_count',
      key: 'gpu_count',
    },
    {
      title: 'GPU 利用率',
      dataIndex: 'gpu_utilization',
      key: 'gpu_utilization',
      render: (utilization: number) => (
        <Progress
          percent={utilization}
          strokeColor={getUtilizationColor(utilization)}
          size="small"
        />
      ),
    },
    {
      title: '显存使用',
      key: 'memory',
      render: (_: any, record: Worker) => (
        <span>
          {record.gpu_memory_used}GB / {record.gpu_memory_total}GB
        </span>
      ),
    },
    {
      title: '标签',
      dataIndex: 'labels',
      key: 'labels',
      render: (labels: Record<string, string>) => (
        <Space size={4}>
          {Object.entries(labels).map(([key, value]) => (
            <Tag key={key}>{key}={value}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Worker) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {record.status !== 'Draining' && record.status !== 'Unhealthy' && (
            <Button
              type="link"
              icon={<StopOutlined />}
              onClick={() => handleDrain(record)}
            >
              排空
            </Button>
          )}
          <Button
            type="link"
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

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Title level={3} style={{ margin: 0 }}>
            集群管理
          </Title>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsAddModalVisible(true)}
            >
              添加 Worker
            </Button>
          </Space>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Workers"
              value={stats.total_workers}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总 GPU"
              value={stats.total_gpus}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={stats.running_gpus}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="异常"
              value={stats.unhealthy}
              valueStyle={{ color: stats.unhealthy > 0 ? '#f5222d' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Worker 节点列表"
        extra={
          <Space>
            <FilterOutlined />
            <Select
              placeholder="选择标签键"
              style={{ width: 150 }}
              value={filterKey || undefined}
              onChange={(value) => {
                setFilterKey(value);
                setFilterValues([]); // 切换key时清空已选values
              }}
              allowClear
              onClear={() => {
                setFilterKey('');
                setFilterValues([]);
              }}
            >
              {labelKeyValues.map(item => (
                <Select.Option key={item.key} value={item.key}>{item.key}</Select.Option>
              ))}
            </Select>
            {filterKey && (
              <Space size={4} wrap>
                {currentKeyValues.map(value => {
                  const isSelected = filterValues.includes(value);
                  return (
                    <Tag
                      key={value}
                      color={isSelected ? 'blue' : 'default'}
                      style={{ cursor: 'pointer' }}
                      onClick={() => {
                        if (isSelected) {
                          setFilterValues(filterValues.filter(v => v !== value));
                        } else {
                          setFilterValues([...filterValues, value]);
                        }
                      }}
                    >
                      {value}
                    </Tag>
                  );
                })}
              </Space>
            )}
            {filterValues.length > 0 && (
              <Tag
                closable
                onClose={() => setFilterValues([])}
                color="blue"
              >
                已选 {filterValues.length} 项
              </Tag>
            )}
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredWorkers}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <AddWorkerModal
        visible={isAddModalVisible}
        onCancel={() => setIsAddModalVisible(false)}
        onOk={(worker) => {
          // 注意：这里不再直接关闭modal，而是等待worker注册完成
          setWorkers([
            ...workers,
            {
              ...worker,
              id: Date.now().toString(),
              status: 'Ready',
              gpu_utilization: 0,
              gpu_memory_used: 0,
              created_at: new Date().toLocaleString(),
              last_heartbeat: '刚刚',
            },
          ]);
        }}
        onWorkerRegistered={(workerName) => {
          // Worker注册成功后的回调
          message.success(`Worker ${workerName} 注册成功！`);
          setWorkers(prev => prev.map(w =>
            w.name === workerName ? { ...w, status: 'Ready' as const } : w
          ));
        }}
      />
    </div>
  );
};

export default ClusterOverview;

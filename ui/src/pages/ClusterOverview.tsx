import { useState, useMemo, useEffect } from 'react';
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
import axios from 'axios';
import AddWorkerModal from '../components/cluster/AddWorkerModal';
import type { Worker, WorkerMetrics } from '../api';

const { Title } = Typography;

const ClusterOverview = () => {
  const navigate = useNavigate();
  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [filterKey, setFilterKey] = useState<string>('');
  const [filterValues, setFilterValues] = useState<string[]>([]);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [workerMetrics, setWorkerMetrics] = useState<Record<number, WorkerMetrics>>({});

  // Fetch workers from backend
  const fetchWorkers = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/workers');
      // Handle both array and paginated response
      const workersData = Array.isArray(response.data)
        ? response.data
        : (response.data?.items || []);
      setWorkers(workersData);

      // Fetch GPU metrics for each worker
      await fetchWorkersMetrics(workersData);
    } catch (error: any) {
      message.error(`Failed to load workers: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch GPU metrics for workers
  const fetchWorkersMetrics = async (workersList: Worker[]) => {
    const metrics: Record<number, WorkerMetrics> = {};

    for (const worker of workersList) {
      if (worker.status !== 'READY' || !worker.ip) continue;

      try {
        const response = await axios.get(`/metrics/workers/${worker.id}`);
        metrics[worker.id] = response.data;
      } catch (error) {
        console.warn(`Failed to fetch metrics for worker ${worker.id}:`, error);
      }
    }

    setWorkerMetrics(metrics);
  };

  useEffect(() => {
    fetchWorkers();

    // Auto-refresh metrics every 10 seconds
    const interval = setInterval(() => {
      fetchWorkersMetrics(workers);
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const stats = {
    total_workers: workers.length,
    total_gpus: workers.reduce((sum, w) => sum + w.gpu_count, 0),
    running_gpus: workers.reduce((sum, w) => sum + w.gpu_count, 0),
    unhealthy: workers.filter(w => w.status === 'UNHEALTHY').length,
  };

  // 收集所有的 label keys 和对应的 values
  const labelKeyValues = useMemo(() => {
    const keyValueMap: Record<string, Set<string>> = {};

    workers.forEach(w => {
      if (!w.labels) return;
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
      if (!worker.labels) return false;

      const workerValue = worker.labels[filterKey];
      return filterValues.includes(workerValue);
    });
  }, [workers, filterKey, filterValues]);

  const getStatusColor = (status: Worker['status']) => {
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

  const getStatusText = (status: Worker['status']) => {
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

  const getUtilizationColor = (utilization: number) => {
    if (utilization < 50) return '#52c41a';
    if (utilization < 80) return '#1890ff';
    if (utilization < 95) return '#fa8c16';
    return '#f5222d';
  };

  const handleViewDetail = (worker: Worker) => {
    navigate(`/cluster/workers/${worker.id}`);
  };

  const handleDrain = async (worker: Worker) => {
    Modal.confirm({
      title: '确认排空节点',
      content: `确定要排空节点 ${worker.name} 吗？排空后节点将不再接受新任务。`,
      onOk: async () => {
        try {
          await axios.post(`/workers/${worker.id}/set-status`, 'DRAINING', {
            headers: { 'Content-Type': 'application/json' }
          });
          message.success('节点排空成功');
          fetchWorkers();
        } catch (error: any) {
          message.error(`排空失败: ${error.response?.data?.detail || error.message}`);
        }
      },
    });
  };

  const handleDelete = async (worker: Worker) => {
    Modal.confirm({
      title: '确认删除节点',
      content: `确定要删除节点 ${worker.name} 吗？此操作不可恢复。`,
      onOk: async () => {
        try {
          await axios.delete(`/workers/${worker.id}`);
          message.success('节点删除成功');
          fetchWorkers();
        } catch (error: any) {
          message.error(`删除失败: ${error.response?.data?.detail || error.message}`);
        }
      },
    });
  };

  const handleRefresh = () => {
    fetchWorkers();
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
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip',
      key: 'ip',
      render: (ip: string) => ip || 'N/A',
    },
    {
      title: 'GPU 数量',
      dataIndex: 'gpu_count',
      key: 'gpu_count',
    },
    {
      title: 'GPU 利用率',
      key: 'gpu_utilization',
      render: (_: any, record: Worker) => {
        // Get real-time GPU utilization from metrics API
        const metrics = workerMetrics[record.id];
        if (!metrics || !metrics.gpus || metrics.gpus.length === 0) {
          return <Progress percent={0} size="small" />;
        }
        const avgUtil = metrics.avg_utilization_percent || 0;
        return (
          <Progress
            percent={Math.round(avgUtil)}
            strokeColor={getUtilizationColor(avgUtil)}
            size="small"
          />
        );
      },
    },
    {
      title: '显存使用',
      key: 'memory',
      render: (_: any, record: Worker) => {
        // Get real-time memory usage from metrics API
        const metrics = workerMetrics[record.id];
        if (!metrics) {
          return <span>N/A</span>;
        }
        const usedGB = metrics.used_memory_gb?.toFixed(1) || '0';
        const totalGB = metrics.total_memory_gb?.toFixed(1) || '0';
        return <span>{usedGB}GB / {totalGB}GB</span>;
      },
    },
    {
      title: '标签',
      dataIndex: 'labels',
      key: 'labels',
      render: (labels: Record<string, string> | undefined) => {
        if (!labels || Object.keys(labels).length === 0) {
          return <span>-</span>;
        }
        return (
          <Space size={4}>
            {Object.entries(labels).map(([key, value]) => (
              <Tag key={key}>{key}={value}</Tag>
            ))}
          </Space>
        );
      },
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
          {record.status !== 'DRAINING' && record.status !== 'UNHEALTHY' && (
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
        onOk={() => {
          // Refresh worker list after adding
          fetchWorkers();
        }}
        onWorkerRegistered={(workerName) => {
          // Worker注册成功后的回调
          message.success(`Worker ${workerName} 注册成功！`);
          fetchWorkers();
        }}
      />
    </div>
  );
};

export default ClusterOverview;

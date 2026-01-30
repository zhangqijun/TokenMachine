import { useState, useMemo, useEffect } from 'react';
import { Table, Tag, Space, Button, Badge, Tooltip, Progress, message, Modal } from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  SettingOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  DesktopOutlined,
  DownOutlined,
  RightOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import AddWorkerModal from '../../components/cluster/AddWorkerModal';
import type { Worker, GPU } from '../../api';

const NodeManagement = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [addNodeModalVisible, setAddNodeModalVisible] = useState(false);
  const [expandedRowKeys, setExpandedRowKeys] = useState<React.Key[]>([]);
  const [workers, setWorkers] = useState<Worker[]>([]);

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
    } catch (error: any) {
      message.error(`Failed to load workers: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, []);

  const stats = useMemo(() => {
    return {
      totalWorkers: workers.length,
      online: workers.filter(w => w.status === 'READY' || w.status === 'BUSY').length,
      warning: workers.filter(w => w.status === 'UNHEALTHY').length,
      offline: workers.filter(w => w.status === 'OFFLINE').length,
      maintenance: workers.filter(w => w.status === 'DRAINING').length,
      totalMachines: workers.length, // Each worker is treated as one machine
      onlineMachines: workers.filter(w => w.status === 'READY' || w.status === 'BUSY').length,
      totalGpus: workers.reduce((sum, w) => sum + (w.gpu_count || 0), 0),
      avgGpuUsage: workers.length > 0
        ? Math.round(
            workers.reduce((sum, w) => {
              if (!w.gpu_devices || w.gpu_devices.length === 0) return sum;
              const workerAvg = w.gpu_devices.reduce((gpuSum, gpu) =>
                gpuSum + (gpu.memory_utilization_rate || 0), 0) / w.gpu_devices.length;
              return sum + workerAvg;
            }, 0) / workers.filter(w => w.status !== 'OFFLINE' && w.gpu_devices && w.gpu_devices.length > 0).length * 100
          )
        : 0,
    };
  }, [workers]);

  const handleRefresh = async () => {
    await fetchWorkers();
    message.success('刷新成功');
  };

  const handleAddNode = () => {
    setAddNodeModalVisible(true);
  };

  const handleAddNodeConfirm = () => {
    // Refresh worker list after adding
    fetchWorkers();
  };

  const handleWorkerRegistered = (workerName: string) => {
    message.success(`Worker "${workerName}" 注册成功！`);
    fetchWorkers();
  };

  const handleViewDetail = (worker: Worker) => {
    // Navigate to WorkerDetail page
    navigate(`/cluster/workers/${worker.id}`);
  };

  const handleMaintenance = async (workerId: number) => {
    Modal.confirm({
      title: '确认维护模式',
      content: '确定要将此Worker设置为维护模式吗？这将停止所有新的部署任务。',
      onOk: async () => {
        try {
          await axios.post(`/workers/${workerId}/set-status`, 'DRAINING', {
            headers: { 'Content-Type': 'application/json' }
          });
          message.success('已设置为维护模式');
          fetchWorkers();
        } catch (error: any) {
          message.error(`操作失败: ${error.response?.data?.detail || error.message}`);
        }
      },
    });
  };

  const handleActivate = async (workerId: number) => {
    try {
      await axios.post(`/workers/${workerId}/set-status`, 'READY', {
        headers: { 'Content-Type': 'application/json' }
      });
      message.success('Worker已激活');
      fetchWorkers();
    } catch (error: any) {
      message.error(`操作失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getStatusTag = (status: Worker['status']) => {
    const config: Record<string, { icon: React.ReactElement; color: string; text: string }> = {
      'READY': { icon: <CheckCircleOutlined />, color: 'success', text: '在线' },
      'BUSY': { icon: <CheckCircleOutlined />, color: 'processing', text: '忙碌' },
      'OFFLINE': { icon: <CloseCircleOutlined />, color: 'default', text: '离线' },
      'UNHEALTHY': { icon: <WarningOutlined />, color: 'error', text: '异常' },
      'DRAINING': { icon: <PauseCircleOutlined />, color: 'warning', text: '排空中' },
      'REGISTERING': { icon: <LoadingOutlined />, color: 'processing', text: '注册中' },
    };
    const c = config[status || ''] || { icon: <CloseCircleOutlined />, color: 'default', text: '未知' };
    return (
      <Tag icon={c.icon} color={c.color}>
        {c.text}
      </Tag>
    );
  };

  // Format memory from bytes to GB
  const formatMemory = (bytes: number) => {
    if (!bytes) return 0;
    return (bytes / (1024 ** 3)).toFixed(0);
  };

  // Worker列定义
  const workerColumns: ColumnsType<Worker> = [
    {
      title: 'Worker名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <Badge
            status={
              record.status === 'READY' || record.status === 'BUSY'
                ? 'success'
                : record.status === 'OFFLINE'
                ? 'default'
                : record.status === 'UNHEALTHY'
                ? 'error'
                : 'warning'
            }
          />
          <span>
            <strong>{name}</strong>
          </span>
          <Tag color="blue" style={{ fontSize: 11 }}>
            {record.gpu_count} GPU
          </Tag>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status),
      filters: [
        { text: '在线', value: 'READY' },
        { text: '忙碌', value: 'BUSY' },
        { text: '排空中', value: 'DRAINING' },
        { text: '异常', value: 'UNHEALTHY' },
        { text: '离线', value: 'OFFLINE' },
      ],
    },
    {
      title: 'GPU资源',
      key: 'gpu',
      render: (_, record) => {
        if (!record.gpu_devices || record.gpu_devices.length === 0) {
          return <span style={{ color: '#999' }}>{record.gpu_count} 卡</span>;
        }
        const totalMemory = record.gpu_devices.reduce((sum, gpu) => sum + gpu.memory_total, 0);
        const usedMemory = record.gpu_devices.reduce((sum, gpu) => sum + (gpu.memory_used || 0), 0);
        const totalMemoryGB = formatMemory(totalMemory);
        const avgUtilization = record.gpu_devices.reduce((sum, gpu) =>
          sum + (gpu.memory_utilization_rate || 0), 0) / record.gpu_devices.length * 100;

        return (
          <Space direction="vertical" size={0}>
            <span style={{ fontSize: 12, color: '#666' }}>
              总计: {record.gpu_count}卡 × {totalMemoryGB}GB
            </span>
            <Tooltip title={`平均利用率: ${avgUtilization.toFixed(1)}%`}>
              <Progress
                percent={Math.round(avgUtilization)}
                size="small"
              />
            </Tooltip>
          </Space>
        );
      },
      sorter: (a, b) => a.gpu_count - b.gpu_count,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
      render: (ip) => ip || 'N/A',
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
          <Space size={4} wrap>
            {Object.entries(labels).map(([key, value]) => (
              <Tag key={key} color="geekblue" style={{ fontSize: 11 }}>
                {key}={value}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {record.status === 'READY' || record.status === 'BUSY' ? (
            <Button
              type="link"
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handleMaintenance(record.id)}
            >
              排空
            </Button>
          ) : record.status === 'DRAINING' || record.status === 'OFFLINE' ? (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleActivate(record.id)}
            >
              激活
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

  // GPU列定义（展开行中使用）
  const gpuColumns: ColumnsType<GPU> = [
    {
      title: 'GPU索引',
      dataIndex: 'index',
      key: 'index',
      width: 100,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (state) => {
        const colorMap: Record<string, string> = {
          'AVAILABLE': 'success',
          'IN_USE': 'processing',
          'ERROR': 'error',
        };
        const textMap: Record<string, string> = {
          'AVAILABLE': '可用',
          'IN_USE': '使用中',
          'ERROR': '错误',
        };
        const color = colorMap[state] || 'default';
        const text = textMap[state] || state;
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '显存',
      key: 'memory',
      render: (_, record) => {
        const totalGB = formatMemory(record.memory_total);
        const usedGB = formatMemory(record.memory_used || 0);
        const utilization = record.memory_utilization_rate || 0;
        return (
          <Space direction="vertical" size={0}>
            <span style={{ fontSize: 12 }}>{usedGB}GB / {totalGB}GB</span>
            <Progress
              percent={Math.round(utilization * 100)}
              size="small"
              strokeColor={utilization > 0.9 ? '#f5222d' : utilization > 0.7 ? '#faad14' : '#52c41a'}
            />
          </Space>
        );
      },
    },
    {
      title: '温度',
      dataIndex: 'temperature',
      key: 'temperature',
      render: (temp) => temp ? `${temp.toFixed(1)}°C` : 'N/A',
    },
  ];

  return (
    <div>
      {/* 头部 */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>节点管理</h2>
        <p style={{ margin: '8px 0 0 0', color: '#666' }}>
          管理Worker节点和物理机器，监控资源使用情况
        </p>
      </div>

      {/* 统计卡片 */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
        <div
          style={{
            flex: 1,
            padding: 16,
            background: '#f0f2f5',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 600, color: '#1890ff' }}>
            {stats.totalWorkers}
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>Worker总数</div>
        </div>
        <div
          style={{
            flex: 1,
            padding: 16,
            background: '#f0f2f5',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 600, color: '#52c41a' }}>
            {stats.online}
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>在线Worker</div>
        </div>
        <div
          style={{
            flex: 1,
            padding: 16,
            background: '#f0f2f5',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 600, color: '#722ed1' }}>
            {stats.totalMachines}
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>
            物理机器 ({stats.onlineMachines} 在线)
          </div>
        </div>
        <div
          style={{
            flex: 1,
            padding: 16,
            background: '#f0f2f5',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 600, color: '#faad14' }}>{stats.warning}</div>
          <div style={{ fontSize: 12, color: '#666' }}>异常Worker</div>
        </div>
        <div
          style={{
            flex: 1,
            padding: 16,
            background: '#f0f2f5',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 600, color: '#8c8c8c' }}>
            {stats.offline + stats.maintenance}
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>离线/排空</div>
        </div>
        <div
          style={{
            flex: 1,
            padding: 16,
            background: '#f0f2f5',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 600, color: '#eb2f96' }}>{stats.totalGpus}</div>
          <div style={{ fontSize: 12, color: '#666' }}>GPU总数</div>
        </div>
        <div
          style={{
            flex: 1,
            padding: 16,
            background: '#f0f2f5',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 600, color: '#13c2c2' }}>
            {isNaN(stats.avgGpuUsage) ? 0 : stats.avgGpuUsage}%
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>平均显存使用</div>
        </div>
      </div>

      {/* 操作栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <div></div>
        <Space>
          <Button icon={<PlusOutlined />} type="primary" onClick={handleAddNode}>
            添加Worker
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      {/* Worker表格 */}
      <Table
        columns={workerColumns}
        dataSource={workers}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        scroll={{ x: 1400 }}
        expandable={{
          expandedRowRender: (record) => (
            <div style={{ margin: '16px 48px' }}>
              <h4 style={{ marginBottom: 12 }}>GPU 列表 ({record.gpu_devices?.length || 0} 个)</h4>
              {!record.gpu_devices || record.gpu_devices.length === 0 ? (
                <div
                  style={{
                    padding: 24,
                    textAlign: 'center',
                    background: '#fafafa',
                    borderRadius: 4,
                  }}
                >
                  <DesktopOutlined style={{ fontSize: 32, color: '#d9d9d9', marginBottom: 8 }} />
                  <div style={{ color: '#999' }}>暂无GPU注册到此Worker</div>
                </div>
              ) : (
                <Table
                  columns={gpuColumns}
                  dataSource={record.gpu_devices}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              )}
            </div>
          ),
          expandIcon: ({ expanded, onExpand, record }) =>
            record.gpu_devices && record.gpu_devices.length > 0 ? (
              <Tooltip
                title={expanded ? `收起GPU (${record.gpu_devices.length}个)` : `查看GPU (${record.gpu_devices.length}个)`}
              >
                <Button
                  type="text"
                  size="small"
                  icon={expanded ? <DownOutlined /> : <RightOutlined />}
                  onClick={(e) => onExpand(record, e)}
                  style={{ padding: '4px 8px' }}
                />
              </Tooltip>
            ) : null
          ,
        }}
      />

      {/* Worker详情模态框 */}
      <Modal
        title={`Worker详情 - ${selectedWorker?.name}`}
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false);
          setSelectedWorker(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={1000}
      >
        {selectedWorker && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Space size={32}>
                <div>
                  <div style={{ color: '#666', fontSize: 12 }}>Worker名称</div>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>{selectedWorker.name}</div>
                </div>
                <div>
                  <div style={{ color: '#666', fontSize: 12 }}>状态</div>
                  <div>{getStatusTag(selectedWorker.status)}</div>
                </div>
                <div>
                  <div style={{ color: '#666', fontSize: 12 }}>创建时间</div>
                  <div style={{ fontSize: 14 }}>
                    {new Date(selectedWorker.created_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div style={{ color: '#666', fontSize: 12 }}>最后心跳</div>
                  <div style={{ fontSize: 14 }}>
                    {selectedWorker.last_heartbeat_at
                      ? new Date(selectedWorker.last_heartbeat_at).toLocaleString()
                      : '从未'}
                  </div>
                </div>
              </Space>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>
                GPU 列表 ({selectedWorker.gpu_devices?.length || 0} 个)
              </div>
              {!selectedWorker.gpu_devices || selectedWorker.gpu_devices.length === 0 ? (
                <div
                  style={{
                    padding: 24,
                    textAlign: 'center',
                    background: '#fafafa',
                    borderRadius: 4,
                  }}
                >
                  <DesktopOutlined style={{ fontSize: 32, color: '#d9d9d9', marginBottom: 8 }} />
                  <div style={{ color: '#999' }}>暂无GPU</div>
                </div>
              ) : (
                <Table
                  columns={gpuColumns}
                  dataSource={selectedWorker.gpu_devices}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              )}
            </div>

            {selectedWorker.labels && Object.keys(selectedWorker.labels).length > 0 && (
              <div>
                <div style={{ marginBottom: 8, fontWeight: 500 }}>Worker标签</div>
                <Space size={4} wrap>
                  {Object.entries(selectedWorker.labels).map(([key, value]) => (
                    <Tag key={key} color="geekblue">
                      {key}={value}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 添加Worker模态框 */}
      <AddWorkerModal
        visible={addNodeModalVisible}
        onCancel={() => setAddNodeModalVisible(false)}
        onOk={handleAddNodeConfirm}
        onWorkerRegistered={handleWorkerRegistered}
      />
    </div>
  );
};

export default NodeManagement;

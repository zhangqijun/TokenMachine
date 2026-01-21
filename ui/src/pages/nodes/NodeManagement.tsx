import { useState, useMemo } from 'react';
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
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AddWorkerModal from '../../components/cluster/AddWorkerModal';

interface PhysicalMachine {
  id: string;
  ip: string;
  hostname: string;
  status: 'online' | 'offline' | 'warning';
  gpuVendor: 'NVIDIA' | 'AMD' | '华为昇腾' | '沐曦' | '海光';
  gpuModel: string;
  gpuCount: number;
  gpuMemory: number; // 每块GPU的显存（GB）
  gpuMemoryUsed: number; // 已使用显存（GB）
  cpuUsage: number; // CPU使用率（%）
  memoryUsage: number; // 内存使用率（%）
  uptime: number; // 运行时间（秒）
  lastHeartbeat: string;
}

interface WorkerInfo {
  id: string;
  name: string;
  registerToken: string;
  status: 'online' | 'offline' | 'warning' | 'maintenance';
  machines: PhysicalMachine[]; // 该Worker下的物理机器列表
  totalGpuCount: number; // 总GPU数（所有机器加总）
  totalGpuMemory: number; // 总显存（GB）
  usedGpuMemory: number; // 已使用显存（GB）
  avgCpuUsage: number; // 平均CPU使用率
  avgMemoryUsage: number; // 平均内存使用率
  activeDeployments: number;
  totalRequests: number;
  createdAt: string;
  location?: string;
  labels: string[];
}

const NodeManagement = () => {
  const [loading, setLoading] = useState(false);
  const [selectedWorker, setSelectedWorker] = useState<WorkerInfo | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [addNodeModalVisible, setAddNodeModalVisible] = useState(false);
  const [expandedRowKeys, setExpandedRowKeys] = useState<React.Key[]>([]);

  // Mock data - Worker列表（每个Worker包含多台物理机器）
  const [workers, setWorkers] = useState<WorkerInfo[]>([
    {
      id: 'worker-1',
      name: 'worker-1',
      registerToken: 'tm_worker_abc123def456',
      status: 'online',
      machines: [
        {
          id: 'machine-1-1',
          ip: '192.168.1.101',
          hostname: 'gpu-server-01',
          status: 'online',
          gpuVendor: 'NVIDIA',
          gpuModel: 'A100-SXM4-80GB',
          gpuCount: 8,
          gpuMemory: 80,
          gpuMemoryUsed: 65,
          cpuUsage: 45,
          memoryUsage: 72,
          uptime: 86400 * 15,
          lastHeartbeat: new Date(Date.now() - 5000).toISOString(),
        },
        {
          id: 'machine-1-2',
          ip: '192.168.1.102',
          hostname: 'gpu-server-02',
          status: 'online',
          gpuVendor: 'NVIDIA',
          gpuModel: 'A100-SXM4-80GB',
          gpuCount: 8,
          gpuMemory: 80,
          gpuMemoryUsed: 58,
          cpuUsage: 38,
          memoryUsage: 65,
          uptime: 86400 * 12,
          lastHeartbeat: new Date(Date.now() - 3000).toISOString(),
        },
      ],
      totalGpuCount: 16,
      totalGpuMemory: 1280,
      usedGpuMemory: 984,
      avgCpuUsage: 42,
      avgMemoryUsage: 69,
      activeDeployments: 5,
      totalRequests: 52340,
      createdAt: '2024-01-05T10:00:00Z',
      location: '机房A-机柜01-02',
      labels: ['gpu-high', 'production'],
    },
    {
      id: 'worker-2',
      name: 'worker-2',
      registerToken: 'tm_worker_xyz789abc456',
      status: 'online',
      machines: [
        {
          id: 'machine-2-1',
          ip: '192.168.1.103',
          hostname: 'rtx-server-01',
          status: 'warning',
          gpuVendor: 'NVIDIA',
          gpuModel: 'RTX 4090',
          gpuCount: 2,
          gpuMemory: 24,
          gpuMemoryUsed: 22,
          cpuUsage: 78,
          memoryUsage: 89,
          uptime: 86400 * 8,
          lastHeartbeat: new Date(Date.now() - 10000).toISOString(),
        },
      ],
      totalGpuCount: 2,
      totalGpuMemory: 48,
      usedGpuMemory: 44,
      avgCpuUsage: 78,
      avgMemoryUsage: 89,
      activeDeployments: 2,
      totalRequests: 15230,
      createdAt: '2024-01-08T14:00:00Z',
      location: '机房B-机柜01',
      labels: ['gpu-mid', 'development'],
    },
    {
      id: 'worker-3',
      name: 'ascend-worker-1',
      registerToken: 'tm_worker_asc123def456',
      status: 'online',
      machines: [
        {
          id: 'machine-3-1',
          ip: '192.168.1.201',
          hostname: 'ascend-server-01',
          status: 'online',
          gpuVendor: '华为昇腾',
          gpuModel: 'Ascend 910B',
          gpuCount: 8,
          gpuMemory: 64,
          gpuMemoryUsed: 48,
          cpuUsage: 52,
          memoryUsage: 68,
          uptime: 86400 * 10,
          lastHeartbeat: new Date(Date.now() - 4000).toISOString(),
        },
        {
          id: 'machine-3-2',
          ip: '192.168.1.202',
          hostname: 'ascend-server-02',
          status: 'online',
          gpuVendor: '华为昇腾',
          gpuModel: 'Ascend 910B',
          gpuCount: 8,
          gpuMemory: 64,
          gpuMemoryUsed: 52,
          cpuUsage: 48,
          memoryUsage: 70,
          uptime: 86400 * 9,
          lastHeartbeat: new Date(Date.now() - 5000).toISOString(),
        },
      ],
      totalGpuCount: 16,
      totalGpuMemory: 1024,
      usedGpuMemory: 800,
      avgCpuUsage: 50,
      avgMemoryUsage: 69,
      activeDeployments: 4,
      totalRequests: 28560,
      createdAt: '2024-01-10T09:00:00Z',
      location: '机房C-机柜01',
      labels: ['ascend', 'production'],
    },
    {
      id: 'worker-4',
      name: 'mx-worker-1',
      registerToken: 'tm_worker_mx123abc456',
      status: 'offline',
      machines: [],
      totalGpuCount: 0,
      totalGpuMemory: 0,
      usedGpuMemory: 0,
      avgCpuUsage: 0,
      avgMemoryUsage: 5,
      activeDeployments: 0,
      totalRequests: 0,
      createdAt: '2024-01-12T11:00:00Z',
      location: '机房C-机柜02',
      labels: ['muxi', 'staging'],
    },
    {
      id: 'worker-5',
      name: 'worker-h100',
      registerToken: 'tm_worker_h100xyz789',
      status: 'maintenance',
      machines: [
        {
          id: 'machine-5-1',
          ip: '192.168.1.105',
          hostname: 'h100-server-01',
          status: 'offline',
          gpuVendor: 'NVIDIA',
          gpuModel: 'H100-SXM4-80GB',
          gpuCount: 8,
          gpuMemory: 80,
          gpuMemoryUsed: 0,
          cpuUsage: 5,
          memoryUsage: 15,
          uptime: 86400 * 5,
          lastHeartbeat: new Date(Date.now() - 3600000).toISOString(),
        },
      ],
      totalGpuCount: 8,
      totalGpuMemory: 640,
      usedGpuMemory: 0,
      avgCpuUsage: 5,
      avgMemoryUsage: 15,
      activeDeployments: 0,
      totalRequests: 12560,
      createdAt: '2024-01-15T16:00:00Z',
      location: '机房A-机柜03',
      labels: ['gpu-high', 'maintenance'],
    },
  ]);

  const stats = useMemo(() => {
    return {
      totalWorkers: workers.length,
      online: workers.filter(w => w.status === 'online').length,
      warning: workers.filter(w => w.status === 'warning').length,
      offline: workers.filter(w => w.status === 'offline').length,
      maintenance: workers.filter(w => w.status === 'maintenance').length,
      totalMachines: workers.reduce((sum, w) => sum + w.machines.length, 0),
      onlineMachines: workers.reduce((sum, w) => sum + w.machines.filter(m => m.status === 'online').length, 0),
      totalGpus: workers.reduce((sum, w) => sum + w.totalGpuCount, 0),
      avgGpuUsage: workers.length > 0
        ? Math.round(
            workers.reduce((sum, w) => sum + (w.usedGpuMemory / w.totalGpuMemory) * 100, 0) /
              workers.filter(w => w.status !== 'offline' && w.totalGpuCount > 0).length
          )
        : 0,
    };
  }, [workers]);

  const handleRefresh = async () => {
    setLoading(true);
    // TODO: 调用API刷新节点状态
    setTimeout(() => {
      setLoading(false);
      message.success('刷新成功');
    }, 1000);
  };

  const handleAddNode = () => {
    setAddNodeModalVisible(true);
  };

  const handleAddNodeConfirm = (worker: any) => {
    // TODO: 调用API添加Worker
    message.success(`Worker "${worker.name}" 创建成功`);
    // 将新Worker添加到列表
    const newWorker: WorkerInfo = {
      id: worker.id || `worker-${Date.now()}`,
      name: worker.name,
      registerToken: worker.registerToken || '',
      status: 'online',
      machines: [],
      totalGpuCount: 0,
      totalGpuMemory: 0,
      usedGpuMemory: 0,
      avgCpuUsage: 0,
      avgMemoryUsage: 0,
      activeDeployments: 0,
      totalRequests: 0,
      createdAt: new Date().toISOString(),
      labels: Object.values(worker.labels || {}),
    };
    setWorkers([...workers, newWorker]);
  };

  const handleWorkerRegistered = (workerName: string) => {
    message.success(`Worker "${workerName}" 有机器注册成功！`);
    // 刷新Worker列表
    handleRefresh();
  };

  const handleViewDetail = (worker: WorkerInfo) => {
    setSelectedWorker(worker);
    setDetailModalVisible(true);
  };

  const handleMaintenance = (workerId: string) => {
    Modal.confirm({
      title: '确认维护模式',
      content: '确定要将此Worker设置为维护模式吗？这将停止所有新的部署任务。',
      onOk: () => {
        message.success('已设置为维护模式');
        // TODO: 调用API
      },
    });
  };

  const handleActivate = (workerId: string) => {
    message.success('Worker已激活');
    // TODO: 调用API
  };

  const getStatusTag = (status: WorkerInfo['status'] | PhysicalMachine['status']) => {
    const config = {
      online: { icon: <CheckCircleOutlined />, color: 'success', text: '在线' },
      offline: { icon: <CloseCircleOutlined />, color: 'default', text: '离线' },
      warning: { icon: <WarningOutlined />, color: 'warning', text: '警告' },
      maintenance: { icon: <PauseCircleOutlined />, color: 'processing', text: '维护中' },
    };
    const c = config[status];
    return (
      <Tag icon={c.icon} color={c.color}>
        {c.text}
      </Tag>
    );
  };

  const formatUptime = (seconds: number) => {
    if (seconds === 0) return '-';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return `${days}天 ${hours}小时`;
  };

  // Worker列定义
  const workerColumns: ColumnsType<WorkerInfo> = [
    {
      title: 'Worker名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <Badge
            status={
              record.status === 'online'
                ? 'success'
                : record.status === 'offline'
                ? 'default'
                : record.status === 'warning'
                ? 'warning'
                : 'processing'
            }
          />
          <span>
            <strong>{name}</strong>
          </span>
          <Tag color="blue" style={{ fontSize: 11 }}>
            {record.machines.length} 台机器
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
        { text: '在线', value: 'online' },
        { text: '离线', value: 'offline' },
        { text: '警告', value: 'warning' },
        { text: '维护中', value: 'maintenance' },
      ],
    },
    {
      title: 'GPU资源',
      key: 'gpu',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <span style={{ fontSize: 12, color: '#666' }}>
            总计: {record.totalGpuCount}卡 × {record.totalGpuMemory}GB
          </span>
          <Tooltip title={`已用: ${record.usedGpuMemory}GB / ${record.totalGpuMemory}GB`}>
            <Progress
              percent={Math.round((record.usedGpuMemory / record.totalGpuMemory) * 100)}
              size="small"
              format={(percent) => `${percent}% (${record.usedGpuMemory}GB)`}
            />
          </Tooltip>
        </Space>
      ),
      sorter: (a, b) => a.totalGpuCount - b.totalGpuCount,
    },
    {
      title: '部署数',
      dataIndex: 'activeDeployments',
      key: 'activeDeployments',
      render: (count) => <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />,
      sorter: (a, b) => a.activeDeployments - b.activeDeployments,
    },
    {
      title: '总请求数',
      dataIndex: 'totalRequests',
      key: 'totalRequests',
      render: (count) => count.toLocaleString(),
      sorter: (a, b) => a.totalRequests - b.totalRequests,
    },
    {
      title: '标签',
      dataIndex: 'labels',
      key: 'labels',
      render: (labels: string[]) => (
        <Space size={4} wrap>
          {labels.map((label) => (
            <Tag key={label} color="geekblue" style={{ fontSize: 11 }}>
              {label}
            </Tag>
          ))}
        </Space>
      ),
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
          {record.status === 'online' || record.status === 'warning' ? (
            <Button
              type="link"
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handleMaintenance(record.id)}
            >
              维护
            </Button>
          ) : record.status === 'maintenance' || record.status === 'offline' ? (
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

  // 物理机器列定义（详情模态框中使用）
  const machineColumns: ColumnsType<PhysicalMachine> = [
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
    },
    {
      title: '主机名',
      dataIndex: 'hostname',
      key: 'hostname',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status),
    },
    {
      title: 'GPU信息',
      key: 'gpu',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <span style={{ fontSize: 12 }}>
            <Tag color="blue">{record.gpuVendor}</Tag>
            <span>{record.gpuModel}</span>
          </span>
          <span style={{ fontSize: 12, color: '#666' }}>
            {record.gpuCount}卡 × {record.gpuMemory}GB
          </span>
        </Space>
      ),
    },
    {
      title: '显存使用',
      key: 'gpuMemory',
      render: (_, record) => {
        const percent = Math.round((record.gpuMemoryUsed / record.gpuMemory) * 100);
        const color = percent > 90 ? '#f5222d' : percent > 70 ? '#faad14' : '#52c41a';
        return (
          <Tooltip title={`${record.gpuMemoryUsed}GB / ${record.gpuMemory}GB`}>
            <Progress
              percent={percent}
              size="small"
              strokeColor={color}
              format={() => `${record.gpuMemoryUsed}/${record.gpuMemory}GB`}
            />
          </Tooltip>
        );
      },
    },
    {
      title: '运行时间',
      dataIndex: 'uptime',
      key: 'uptime',
      render: (uptime) => formatUptime(uptime),
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
          <div style={{ fontSize: 12, color: '#666' }}>警告Worker</div>
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
          <div style={{ fontSize: 12, color: '#666' }}>离线/维护</div>
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
            {stats.avgGpuUsage}%
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
              <h4 style={{ marginBottom: 12 }}>物理机器列表 ({record.machines.length} 台)</h4>
              {record.machines.length === 0 ? (
                <div
                  style={{
                    padding: 24,
                    textAlign: 'center',
                    background: '#fafafa',
                    borderRadius: 4,
                  }}
                >
                  <DesktopOutlined style={{ fontSize: 32, color: '#d9d9d9', marginBottom: 8 }} />
                  <div style={{ color: '#999' }}>暂无物理机器注册到此Worker</div>
                  <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                    使用注册Token在物理机器上运行agent即可自动注册
                  </div>
                </div>
              ) : (
                <Table
                  columns={machineColumns}
                  dataSource={record.machines}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  showHeader={false}
                />
              )}
            </div>
          ),
          expandIcon: ({ expanded, onExpand, record }) =>
            record.machines.length > 0 ? (
              <Tooltip
                title={expanded ? `收起机器 (${record.machines.length}台)` : `查看机器 (${record.machines.length}台)`}
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
                    {new Date(selectedWorker.createdAt).toLocaleString()}
                  </div>
                </div>
              </Space>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>注册Token</div>
              <div
                style={{
                  padding: 12,
                  background: '#f5f5f5',
                  borderRadius: 4,
                  fontFamily: 'monospace',
                  fontSize: 12,
                }}
              >
                {selectedWorker.registerToken}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>物理机器 ({selectedWorker.machines.length} 台)</div>
              {selectedWorker.machines.length === 0 ? (
                <div
                  style={{
                    padding: 24,
                    textAlign: 'center',
                    background: '#fafafa',
                    borderRadius: 4,
                  }}
                >
                  <DesktopOutlined style={{ fontSize: 32, color: '#d9d9d9', marginBottom: 8 }} />
                  <div style={{ color: '#999' }}>暂无物理机器注册</div>
                  <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                    使用注册Token在物理机器上运行agent即可自动注册
                  </div>
                </div>
              ) : (
                <Table
                  columns={machineColumns}
                  dataSource={selectedWorker.machines}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              )}
            </div>

            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>Worker标签</div>
              <Space size={4} wrap>
                {selectedWorker.labels.map((label: string) => (
                  <Tag key={label} color="geekblue">
                    {label}
                  </Tag>
                ))}
              </Space>
            </div>
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

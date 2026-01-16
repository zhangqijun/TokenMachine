import { useState } from 'react';
import { Card, Tabs, Table, Tag, Space, Button, Input, Select, Drawer, Descriptions, Badge, Typography, Progress } from 'antd';
import { SearchOutlined, ReloadOutlined, TagOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import type { Worker, GPUDevice } from '../mock/data';
import { StatusTag, ProgressBar } from '../components/common';
import dayjs from 'dayjs';

const { Search } = Input;
const { Text } = Typography;

const Resources = () => {
  const { workers } = useStore();
  const [activeTab, setActiveTab] = useState('workers');
  const [searchText, setSearchText] = useState('');
  const [clusterFilter, setClusterFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('all');
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Flatten all GPUs from all workers
  const allGPUs: (GPUDevice & { worker_name: string; worker_ip: string })[] = workers.flatMap(worker =>
    worker.status.gpu_devices.map(gpu => ({
      ...gpu,
      worker_name: worker.name,
      worker_ip: worker.ip,
    }))
  );

  // Filter data
  const filteredWorkers = workers.filter(worker => {
    const matchesSearch =
      worker.name.toLowerCase().includes(searchText.toLowerCase()) ||
      worker.ip.includes(searchText);
    const matchesCluster = clusterFilter === 'all' || worker.cluster_id === clusterFilter;
    const matchesState = stateFilter === 'all' || worker.state === stateFilter;
    return matchesSearch && matchesCluster && matchesState;
  });

  const filteredGPUs = allGPUs.filter(gpu => {
    const matchesSearch =
      gpu.name.toLowerCase().includes(searchText.toLowerCase()) ||
      gpu.worker_name.toLowerCase().includes(searchText.toLowerCase());
    return matchesSearch;
  });

  // Worker columns
  const workerColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Worker) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{name}</span>
          {Object.keys(record.labels).length > 0 && (
            <Tag icon={<TagOutlined />} color="blue" style={{ fontSize: 11 }}>
              {Object.keys(record.labels).length}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => <StatusTag status={state} />,
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip',
      key: 'ip',
      render: (ip: string) => <Text code>{ip}</Text>,
    },
    {
      title: 'CPU',
      key: 'cpu',
      render: (_: unknown, record: Worker) => (
        <div style={{ minWidth: 150 }}>
          <ProgressBar
            percent={record.status.cpu.utilization_rate}
            size="small"
            tooltip={`${record.status.cpu.allocated} / ${record.status.cpu.total} 核心`}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.status.cpu.allocated} / {record.status.cpu.total} 核心
          </Text>
        </div>
      ),
    },
    {
      title: '内存',
      key: 'memory',
      render: (_: unknown, record: Worker) => (
        <div style={{ minWidth: 150 }}>
          <ProgressBar
            percent={record.status.memory.utilization_rate}
            size="small"
            tooltip={`${formatBytes(record.status.memory.used)} / ${formatBytes(record.status.memory.total)}`}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatBytes(record.status.memory.used)} / {formatBytes(record.status.memory.total)}
          </Text>
        </div>
      ),
    },
    {
      title: 'GPU',
      key: 'gpu',
      render: (_: unknown, record: Worker) => (
        <Space direction="vertical" size="small" style={{ minWidth: 150 }}>
          {record.status.gpu_devices.map(gpu => (
            <div key={gpu.uuid}>
              <Text style={{ fontSize: 12 }}>
                GPU {gpu.index} ({gpu.vendor})
              </Text>
              <ProgressBar
                percent={gpu.core.utilization_rate}
                size="small"
                tooltip={`显存: ${formatBytes(gpu.memory.used)} / ${formatBytes(gpu.memory.total)}`}
              />
            </div>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Worker) => (
        <Button
          size="small"
          onClick={() => {
            setSelectedWorker(record);
            setDrawerOpen(true);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  // GPU columns
  const gpuColumns = [
    {
      title: 'GPU',
      dataIndex: 'index',
      key: 'index',
      render: (index: number, record: typeof filteredGPUs[0]) => (
        <Space>
          <Badge status={record.state === 'in_use' ? 'processing' : 'default'} />
          <span>GPU {index}</span>
        </Space>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <span style={{ fontWeight: 500 }}>{name}</span>,
    },
    {
      title: 'Worker',
      key: 'worker',
      render: (_: unknown, record: typeof filteredGPUs[0]) => (
        <Space direction="vertical" size="small">
          <Text>{record.worker_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.worker_ip}
          </Text>
        </Space>
      ),
    },
    {
      title: '核心利用率',
      dataIndex: 'core',
      key: 'core',
      render: (core: GPUDevice['core']) => (
        <div>
          <ProgressBar percent={core.utilization_rate} size="small" />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {core.total} CUDA 核心
          </Text>
        </div>
      ),
    },
    {
      title: '显存',
      key: 'memory',
      render: (_: unknown, record: typeof filteredGPUs[0]) => (
        <div style={{ minWidth: 150 }}>
          <ProgressBar
            percent={record.memory.utilization_rate}
            size="small"
            color={record.memory.utilization_rate > 90 ? 'error' : record.memory.utilization_rate > 70 ? 'warning' : 'success'}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatBytes(record.memory.used)} / {formatBytes(record.memory.total)}
          </Text>
        </div>
      ),
    },
    {
      title: '温度',
      dataIndex: 'temperature',
      key: 'temperature',
      render: (temp: number) => (
        <span style={{ color: temp > 80 ? '#ff4d4f' : temp > 70 ? '#faad14' : 'inherit' }}>
          {temp}°C
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => <StatusTag status={state} />,
    },
  ];

  const tabItems = [
    {
      key: 'workers',
      label: `Workers (${workers.length})`,
      children: (
        <Table
          dataSource={filteredWorkers}
          columns={workerColumns}
          rowKey="name"
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 Workers`,
          }}
        />
      ),
    },
    {
      key: 'gpus',
      label: `GPUs (${allGPUs.length})`,
      children: (
        <Table
          dataSource={filteredGPUs}
          columns={gpuColumns}
          rowKey="uuid"
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 GPU`,
          }}
        />
      ),
    },
    {
      key: 'models',
      label: `模型文件 (${workers.flatMap(w => w.status.gpu_devices).filter(g => g.state === 'in_use').length}/${workers.flatMap(w => w.status.gpu_devices).length} 加载)`,
      children: (
        <Table
          dataSource={allGPUs}
          columns={[
            {
              title: 'Worker',
              key: 'worker',
              render: (_: unknown, record: typeof allGPUs[0]) => (
                <Space>
                  <Badge status={record.state === 'in_use' ? 'processing' : 'default'} />
                  <span>{record.worker_name}</span>
                </Space>
              ),
            },
            {
              title: 'GPU',
              dataIndex: 'index',
              key: 'index',
              render: (index: number) => <span>GPU {index}</span>,
            },
            {
              title: '模型名称',
              key: 'model',
              render: (_: unknown, record: typeof allGPUs[0]) => (
                record.state === 'in_use' ? (
                  <Tag color="blue">模型加载中</Tag>
                ) : (
                  <Tag>空闲</Tag>
                )
              ),
            },
            {
              title: '显存使用',
              key: 'memory',
              render: (_: unknown, record: typeof allGPUs[0]) => (
                <div style={{ minWidth: 150 }}>
                  <ProgressBar
                    percent={record.memory.utilization_rate}
                    size="small"
                    color={record.memory.utilization_rate > 90 ? 'error' : 'success'}
                  />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatBytes(record.memory.used)} / {formatBytes(record.memory.total)}
                  </Text>
                </div>
              ),
            },
            {
              title: '温度',
              dataIndex: 'temperature',
              key: 'temperature',
              render: (temp: number) => (
                <span style={{ color: temp > 80 ? '#ff4d4f' : temp > 70 ? '#faad14' : 'inherit' }}>
                  {temp}°C
                </span>
              ),
            },
            {
              title: '状态',
              dataIndex: 'state',
              key: 'state',
              render: (state: string) => <StatusTag status={state} />,
            },
          ]}
          rowKey="uuid"
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 GPU 设备`,
          }}
        />
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>资源管理</h2>
      </div>

      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Search
            placeholder="搜索 Worker 或 GPU..."
            allowClear
            style={{ width: 250 }}
            prefix={<SearchOutlined />}
            onChange={(e) => setSearchText(e.target.value)}
          />
          {activeTab === 'workers' && (
            <>
              <Select
                placeholder="集群"
                style={{ width: 150 }}
                value={clusterFilter}
                onChange={setClusterFilter}
              >
                <Select.Option value="all">全部集群</Select.Option>
                <Select.Option value="cluster_default">default</Select.Option>
                <Select.Option value="cluster_prod">production</Select.Option>
              </Select>
              <Select
                placeholder="状态"
                style={{ width: 120 }}
                value={stateFilter}
                onChange={setStateFilter}
              >
                <Select.Option value="all">全部状态</Select.Option>
                <Select.Option value="running">运行中</Select.Option>
                <Select.Option value="offline">离线</Select.Option>
                <Select.Option value="maintenance">维护中</Select.Option>
              </Select>
            </>
          )}
          <Button icon={<ReloadOutlined />} loading={false}>
            刷新
          </Button>
        </Space>
      </Card>

      {/* Tabs */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      {/* Worker Detail Drawer */}
      <Drawer
        title="Worker 详情"
        placement="right"
        width={720}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedWorker(null);
        }}
      >
        {selectedWorker && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* Basic Info */}
            <div>
              <h4>基本信息</h4>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="名称">{selectedWorker.name}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <StatusTag status={selectedWorker.state} />
                </Descriptions.Item>
                <Descriptions.Item label="IP 地址">
                  <Text code>{selectedWorker.ip}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="集群">{selectedWorker.cluster_id}</Descriptions.Item>
                <Descriptions.Item label="最后心跳">
                  {dayjs(selectedWorker.last_heartbeat).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              </Descriptions>
            </div>

            {/* Labels */}
            {Object.keys(selectedWorker.labels).length > 0 && (
              <div>
                <h4>标签</h4>
                <Space wrap>
                  {Object.entries(selectedWorker.labels).map(([key, value]) => (
                    <Tag key={key} color="blue" icon={<TagOutlined />}>
                      {key}: {value}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}

            {/* CPU */}
            <div>
              <h4>CPU</h4>
              <Card size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary">利用率</Text>
                    <Progress
                      percent={selectedWorker.status.cpu.utilization_rate}
                      status={selectedWorker.status.cpu.utilization_rate > 80 ? 'exception' : 'normal'}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text>已分配: {selectedWorker.status.cpu.allocated} 核心</Text>
                    <Text>总计: {selectedWorker.status.cpu.total} 核心</Text>
                  </div>
                </Space>
              </Card>
            </div>

            {/* Memory */}
            <div>
              <h4>内存</h4>
              <Card size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary">利用率</Text>
                    <Progress
                      percent={selectedWorker.status.memory.utilization_rate}
                      status={selectedWorker.status.memory.utilization_rate > 80 ? 'exception' : 'normal'}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text>已用: {formatBytes(selectedWorker.status.memory.used)}</Text>
                    <Text>总计: {formatBytes(selectedWorker.status.memory.total)}</Text>
                  </div>
                </Space>
              </Card>
            </div>

            {/* GPUs */}
            <div>
              <h4>GPU 设备</h4>
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {selectedWorker.status.gpu_devices.map((gpu, index) => (
                  <Card key={gpu.uuid} size="small" title={`GPU ${index} - ${gpu.name}`}>
                    <Descriptions column={2} size="small">
                      <Descriptions.Item label="状态">
                        <StatusTag status={gpu.state} />
                      </Descriptions.Item>
                      <Descriptions.Item label="温度">{gpu.temperature}°C</Descriptions.Item>
                      <Descriptions.Item label="核心利用率" span={2}>
                        <ProgressBar percent={gpu.core.utilization_rate} />
                      </Descriptions.Item>
                      <Descriptions.Item label="显存" span={2}>
                        <ProgressBar
                          percent={gpu.memory.utilization_rate}
                          color={gpu.memory.utilization_rate > 90 ? 'error' : 'success'}
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {formatBytes(gpu.memory.used)} / {formatBytes(gpu.memory.total)}
                        </Text>
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                ))}
              </Space>
            </div>

            {/* Filesystem */}
            <div>
              <h4>文件系统</h4>
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {selectedWorker.status.filesystem.map((fs, index) => (
                  <Card key={index} size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text strong>{fs.path}</Text>
                      <Progress
                        percent={(fs.used / fs.total) * 100}
                        status={(fs.used / fs.total) > 0.9 ? 'exception' : 'normal'}
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {formatBytes(fs.used)} / {formatBytes(fs.total)} ({formatBytes(fs.available)} 可用)
                      </Text>
                    </Space>
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

// Helper function to format bytes
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

export default Resources;

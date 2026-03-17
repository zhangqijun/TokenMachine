import { Card, Tag, Space, Button, Typography, Divider, Progress, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  DownloadOutlined,
  SyncOutlined,
  SettingOutlined,
  FileTextOutlined,
  StarOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import type { BackendInfo } from '../types';

const { Text, Paragraph } = Typography;

interface BackendCardProps {
  backend: BackendInfo;
  onInstall?: (backendId: string) => void;
  onUpgrade?: (backendId: string) => void;
  onConfigure?: (backendId: string) => void;
  onUninstall?: (backendId: string) => void;
  onViewLogs?: (backendId: string) => void;
  className?: string;
  style?: React.CSSProperties;
}

const BackendCard: React.FC<BackendCardProps> = ({
  backend,
  onInstall,
  onUpgrade,
  onConfigure,
  onUninstall,
  onViewLogs,
  className,
  style,
}) => {
  const getStatusConfig = () => {
    switch (backend.status) {
      case 'installed':
        return {
          icon: <CheckCircleOutlined />,
          color: 'success',
          text: '已安装',
        };
      case 'not_installed':
        return {
          icon: <CloseCircleOutlined />,
          color: 'default',
          text: '未安装',
        };
      case 'outdated':
        return {
          icon: <ExclamationCircleOutlined />,
          color: 'warning',
          text: '版本过旧',
        };
      case 'error':
        return {
          icon: <CloseCircleOutlined />,
          color: 'error',
          text: '错误',
        };
      default:
        return {
          icon: <CloseCircleOutlined />,
          color: 'default',
          text: '未知',
        };
    }
  };

  const statusConfig = getStatusConfig();

  const renderActions = () => {
    if (backend.status === 'not_installed') {
      return (
        <Button type="primary" icon={<DownloadOutlined />} onClick={() => onInstall?.(backend.id)}>
          安装
        </Button>
      );
    }

    if (backend.status === 'outdated') {
      return (
        <Space>
          <Button icon={<SyncOutlined />} onClick={() => onUpgrade?.(backend.id)}>
            更新至 {backend.updateAvailable}
          </Button>
          <Button icon={<SettingOutlined />} onClick={() => onConfigure?.(backend.id)}>
            配置
          </Button>
        </Space>
      );
    }

    if (backend.status === 'installed') {
      return (
        <Space>
          <Button icon={<SettingOutlined />} onClick={() => onConfigure?.(backend.id)}>
            配置
          </Button>
          <Button icon={<FileTextOutlined />} onClick={() => onViewLogs?.(backend.id)}>
            日志
          </Button>
        </Space>
      );
    }

    return null;
  };

  const getBackendIcon = (name: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      vllm: <ThunderboltOutlined style={{ fontSize: 32, color: '#1890ff' }} />,
      sglang: <StarOutlined style={{ fontSize: 32, color: '#52c41a' }} />,
      chitu: <DatabaseOutlined style={{ fontSize: 32, color: '#faad14' }} />,
      llamacpp: <CloudServerOutlined style={{ fontSize: 32, color: '#13c2c2' }} />,
      mindie: <SyncOutlined spin style={{ fontSize: 32, color: '#722ed1' }} />,
      ktransformer: <SettingOutlined style={{ fontSize: 32, color: '#eb2f96' }} />,
    };
    return iconMap[name.toLowerCase()] || <ApiOutlined style={{ fontSize: 32 }} />;
  };

  return (
    <Card
      hoverable
      className={className}
      style={style}
      bodyStyle={{ height: '100%' }}
    >
      {/* 头部：图标、名称、状态 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Space size={12}>
            {getBackendIcon(backend.name)}
            <div>
              <Text strong style={{ fontSize: 16 }}>
                {backend.displayName}
              </Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {backend.name} {backend.version}
              </Text>
            </div>
          </Space>
          <Tag icon={statusConfig.icon} color={statusConfig.color}>
            {statusConfig.text}
          </Tag>
        </div>
      </div>

      {/* 描述 */}
      <Paragraph
        ellipsis={{ rows: 2 }}
        type="secondary"
        style={{ fontSize: 13, marginBottom: 16, minHeight: 40 }}
      >
        {backend.description}
      </Paragraph>

      <Divider style={{ margin: '12px 0' }} />

      {/* 特性标签 */}
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          特性:
        </Text>
        <div style={{ marginTop: 6 }}>
          <Space size={4} wrap>
            {backend.features.tensorParallel && (
              <Tag color="blue">Tensor并行</Tag>
            )}
            {backend.features.prefixCaching && (
              <Tag color="cyan">Prefix缓存</Tag>
            )}
            {backend.features.multiLora && (
              <Tag color="purple">多LoRA</Tag>
            )}
            {backend.features.speculativeDecoding && (
              <Tag color="orange">推测解码</Tag>
            )}
          </Space>
        </div>
      </div>

      {/* 支持的量化 */}
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          量化支持:
        </Text>
        <div style={{ marginTop: 4 }}>
          <Space size={4} wrap>
            {backend.features.quantization.map((q) => (
              <Tag key={q} color="geekblue">
                {q.toUpperCase()}
              </Tag>
            ))}
          </Space>
        </div>
      </div>

      {/* 兼容性信息 */}
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          兼容性:
        </Text>
        <div style={{ marginTop: 4 }}>
          <Space size={4} wrap>
            {backend.compatibility.gpuVendors.map((vendor) => (
              <Tag key={vendor} icon={<CloudServerOutlined />}>
                {vendor}
              </Tag>
            ))}
            <Tooltip title={`最小显存要求: ${backend.compatibility.minGpuMemory}GB`}>
              <Tag>≥{backend.compatibility.minGpuMemory}GB</Tag>
            </Tooltip>
          </Space>
        </div>
      </div>

      {/* 性能指标（仅已安装时显示） */}
      {backend.status === 'installed' && backend.performance && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              性能指标:
            </Text>
            <div style={{ marginTop: 6 }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <div>
                  <Text style={{ fontSize: 12 }}>平均TPS: {backend.performance.avgTps}</Text>
                  <Progress
                    percent={75}
                    size="small"
                    showInfo={false}
                    style={{ marginTop: 4 }}
                  />
                </div>
                <div>
                  <Text style={{ fontSize: 12 }}>
                    显存效率: {backend.performance.memoryEfficiency}%
                  </Text>
                  <Progress
                    percent={backend.performance.memoryEfficiency}
                    size="small"
                    showInfo={false}
                    strokeColor="#52c41a"
                    style={{ marginTop: 4 }}
                  />
                </div>
              </Space>
            </div>
          </div>
        </>
      )}

      {/* 统计信息 */}
      {backend.status === 'installed' && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ marginBottom: 12 }}>
            <Space size={16}>
              <div>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  活跃部署
                </Text>
                <br />
                <Text strong style={{ fontSize: 14 }}>
                  {backend.stats.activeDeployments}
                </Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  总请求数
                </Text>
                <br />
                <Text strong style={{ fontSize: 14 }}>
                  {backend.stats.totalRequests.toLocaleString()}
                </Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  健康检查
                </Text>
                <br />
                <Text style={{ fontSize: 12 }}>
                  {new Date(backend.stats.lastHealthCheck).toLocaleString()}
                </Text>
              </div>
            </Space>
          </div>
        </>
      )}

      <Divider style={{ margin: '12px 0' }} />

      {/* 操作按钮 */}
      <div>{renderActions()}</div>
    </Card>
  );
};

export default BackendCard;

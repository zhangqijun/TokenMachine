import { Tag } from 'antd';
import {
  CheckCircleOutlined,
  StopOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import type React from 'react';

interface StatusTagProps {
  status: string;
  text?: string;
  progress?: number;
}

const statusConfigMap: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  running: { color: 'success', icon: <CheckCircleOutlined />, text: '运行中' },
  stopped: { color: 'default', icon: <StopOutlined />, text: '已停止' },
  starting: { color: 'processing', icon: <LoadingOutlined />, text: '启动中' },
  stopping: { color: 'default', icon: <ClockCircleOutlined />, text: '停止中' },
  loading: { color: 'processing', icon: <LoadingOutlined />, text: '加载中' },
  error: { color: 'error', icon: <CloseCircleOutlined />, text: '错误' },
  available: { color: 'success', icon: null, text: '可用' },
  in_use: { color: 'processing', icon: null, text: '使用中' },
  offline: { color: 'default', icon: <StopOutlined />, text: '离线' },
  maintenance: { color: 'warning', icon: <ClockCircleOutlined />, text: '维护中' },
  ready: { color: 'success', icon: <CheckCircleOutlined />, text: '就绪' },
  downloading: { color: 'processing', icon: <LoadingOutlined />, text: '下载中' },
  scaling: { color: 'processing', icon: <LoadingOutlined />, text: '扩缩容中' },
};

export const StatusTag = ({ status, text, progress }: StatusTagProps) => {
  const config = statusConfigMap[status] || {
    color: 'default',
    icon: null,
    text: status,
  };

  const displayText = text || config.text;

  return (
    <Tag color={config.color} icon={config.icon}>
      {displayText}
      {progress !== undefined && ` (${progress}%)`}
    </Tag>
  );
};

export default StatusTag;

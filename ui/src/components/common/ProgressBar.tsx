import { Progress, Tooltip } from 'antd';
import type { ProgressProps } from 'antd';

interface ProgressBarProps extends Omit<ProgressProps, 'strokeColor'> {
  tooltip?: string;
  color?: 'success' | 'warning' | 'error' | 'normal';
}

export const ProgressBar = ({
  tooltip,
  color,
  percent,
  ...props
}: ProgressBarProps) => {
  const getColor = () => {
    if (color) {
      const colorMap = {
        success: '#52c41a',
        warning: '#faad14',
        error: '#ff4d4f',
        normal: '#1890ff',
      };
      return colorMap[color];
    }
    // Auto color based on percent
    if (percent !== undefined) {
      if (percent >= 90) return '#ff4d4f';
      if (percent >= 70) return '#faad14';
      return '#52c41a';
    }
    return '#1890ff';
  };

  const content = (
    <Progress
      percent={percent}
      strokeColor={getColor()}
      {...props}
    />
  );

  if (tooltip) {
    return <Tooltip title={tooltip}>{content}</Tooltip>;
  }

  return content;
};

export default ProgressBar;

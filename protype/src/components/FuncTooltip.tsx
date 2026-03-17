import { Tooltip } from 'antd';
import React from 'react';

interface FuncTooltipProps {
  /** 功能名称 */
  title: string;
  /** 功能描述 */
  description: string;
  /** 子元素 */
  children: React.ReactNode;
  /** 提示位置 */
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight';
}

/**
 * 功能描述提示组件
 * 用于原型页面，鼠标悬停时显示功能的详细描述
 *
 * 使用方式：
 * <FuncTooltip title="功能名称" description="功能详细描述">
 *   <Button>按钮</Button>
 * </FuncTooltip>
 */
const FuncTooltip: React.FC<FuncTooltipProps> = ({
  title,
  description,
  children,
  placement = 'top'
}) => {
  return (
    <Tooltip
      title={
        <div style={{ maxWidth: 320 }}>
          <div style={{
            fontWeight: 600,
            marginBottom: 6,
            fontSize: 14,
            borderBottom: '1px solid rgba(255,255,255,0.2)',
            paddingBottom: 6
          }}>
            {title}
          </div>
          <div style={{
            fontSize: 13,
            opacity: 0.9,
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap'
          }}>
            {description}
          </div>
        </div>
      }
      color="rgba(0, 0, 0, 0.85)"
      placement={placement}
      overlayStyle={{ maxWidth: 360 }}
    >
      <span style={{ display: 'inline-block' }}>{children}</span>
    </Tooltip>
  );
};

export default FuncTooltip;

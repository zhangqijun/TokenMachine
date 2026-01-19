interface LogoProps {
  size?: number;
  variant?: 'full' | 'icon' | 'text';
  showText?: boolean;
  textColor?: string;
  backgroundColor?: string;
}

const Logo = ({
  size = 40,
  variant = 'icon',
  showText = true,
  textColor = '#fff',
  backgroundColor = '#1890ff',
}: LogoProps) => {
  // 图标版本 - AI芯片+神经网络节点
  const IconLogo = () => (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* 背景圆形 */}
      <circle cx="50" cy="50" r="48" fill={backgroundColor} opacity="0.1"/>
      <circle cx="50" cy="50" r="42" fill={backgroundColor}/>

      {/* AI芯片图案 */}
      <g transform="translate(50, 50)">
        {/* 中心节点 */}
        <circle cx="0" cy="0" r="8" fill="white"/>

        {/* 内圈节点 */}
        <circle cx="0" cy="-18" r="5" fill="white" opacity="0.9"/>
        <circle cx="15.6" cy="-9" r="5" fill="white" opacity="0.9"/>
        <circle cx="15.6" cy="9" r="5" fill="white" opacity="0.9"/>
        <circle cx="0" cy="18" r="5" fill="white" opacity="0.9"/>
        <circle cx="-15.6" cy="9" r="5" fill="white" opacity="0.9"/>
        <circle cx="-15.6" cy="-9" r="5" fill="white" opacity="0.9"/>

        {/* 连接线 */}
        <g stroke="white" strokeWidth="2" opacity="0.6">
          <line x1="0" y1="-8" x2="0" y2="-13"/>
          <line x1="6.9" y1="-4" x2="10.7" y2="-6.3"/>
          <line x1="6.9" y1="4" x2="10.7" y2="6.3"/>
          <line x1="0" y1="8" x2="0" y2="13"/>
          <line x1="-6.9" y1="4" x2="-10.7" y2="6.3"/>
          <line x1="-6.9" y1="-4" x2="-10.7" y2="-6.3"/>
        </g>

        {/* 外圈装饰点 */}
        <circle cx="0" cy="-26" r="2.5" fill="white" opacity="0.7"/>
        <circle cx="22.5" cy="-13" r="2.5" fill="white" opacity="0.7"/>
        <circle cx="22.5" cy="13" r="2.5" fill="white" opacity="0.7"/>
        <circle cx="0" cy="26" r="2.5" fill="white" opacity="0.7"/>
        <circle cx="-22.5" cy="13" r="2.5" fill="white" opacity="0.7"/>
        <circle cx="-22.5" cy="-13" r="2.5" fill="white" opacity="0.7"/>
      </g>

      {/* 数据流动效果 - 动态圆点 */}
      <circle cx="50" cy="24" r="2" fill="white" opacity="0.8">
        <animate
          attributeName="cy"
          values="24;30;24"
          dur="2s"
          repeatCount="indefinite"
        />
        <animate
          attributeName="opacity"
          values="0.8;0.3;0.8"
          dur="2s"
          repeatCount="indefinite"
        />
      </circle>
      <circle cx="65.6" cy="41" r="2" fill="white" opacity="0.8">
        <animate
          attributeName="cx"
          values="65.6;67.6;65.6"
          dur="2s"
          begin="0.3s"
          repeatCount="indefinite"
        />
        <animate
          attributeName="opacity"
          values="0.8;0.3;0.8"
          dur="2s"
          begin="0.3s"
          repeatCount="indefinite"
        />
      </circle>
      <circle cx="65.6" cy="59" r="2" fill="white" opacity="0.8">
        <animate
          attributeName="cy"
          values="59;63;59"
          dur="2s"
          begin="0.6s"
          repeatCount="indefinite"
        />
        <animate
          attributeName="opacity"
          values="0.8;0.3;0.8"
          dur="2s"
          begin="0.6s"
          repeatCount="indefinite"
        />
      </circle>
    </svg>
  );

  // 文字版本 - 带文字的完整logo
  const FullLogo = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <IconLogo />
      <div>
        <span
          style={{
            fontSize: size * 0.5,
            fontWeight: 700,
            color: textColor,
            lineHeight: 1,
            letterSpacing: '-0.5px',
          }}
        >
          TokenMachine
        </span>
      </div>
    </div>
  );

  // 只显示文字版本
  const TextLogo = () => (
    <div>
      <span
        style={{
          fontSize: size * 0.6,
          fontWeight: 700,
          color: textColor,
          lineHeight: 1,
          letterSpacing: '-0.5px',
        }}
      >
        TokenMachine
      </span>
    </div>
  );

  if (variant === 'icon') {
    return <IconLogo />;
  }

  if (variant === 'text') {
    return <TextLogo />;
  }

  return <FullLogo />;
};

export default Logo;

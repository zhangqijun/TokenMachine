import { useState } from 'react';
import {
  Card,
  Form,
  Select,
  Switch,
  Button,
  Space,
  Typography,
  Divider,
  Row,
  Col,
  ColorPicker,
  Input,
  InputNumber,
  Radio,
  message,
  Upload,
  Tabs,
} from 'antd';
import {
  BgColorsOutlined,
  SaveOutlined,
  ReloadOutlined,
  EyeOutlined,
  MoonOutlined,
  SunOutlined,
  FontSizeOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import type { ColorPickerProps } from 'antd/es/color-picker';

const { Title, Text } = Typography;

const InterfaceSettings = () => {
  const [form] = Form.useForm();
  const [logoUrl, setLogoUrl] = useState<string>('/logo.png');

  const handleSave = () => {
    form.validateFields().then(() => {
      message.success('界面设置保存成功');
    });
  };

  const handleReset = () => {
    form.resetFields();
    message.info('已重置为默认设置');
  };

  const handleLogoUpload = (info: any) => {
    if (info.file.status === 'done') {
      setLogoUrl(info.file.response.url);
      message.success('Logo上传成功');
    }
  };

  const themePresets = [
    { label: '默认蓝', value: 'default', primaryColor: '#1890ff' },
    { label: '极光绿', value: 'green', primaryColor: '#52c41a' },
    { label: '暮山紫', value: 'purple', primaryColor: '#722ed1' },
    { label: '日暮红', value: 'red', primaryColor: '#f5222d' },
    { label: '明黄', value: 'yellow', primaryColor: '#faad14' },
    { label: '极客黑', value: 'dark', primaryColor: '#262626' },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <BgColorsOutlined />
            <span>界面定制</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="theme"
          items={[
            {
              key: 'theme',
              label: '主题设置',
              children: (
                <Form
                  form={form}
                  layout="vertical"
                  initialValues={{
                    theme_mode: 'light',
                    primary_color: '#1890ff',
                    compact_mode: false,
                    enable_animation: true,
                  }}
                >
                  <Form.Item label="主题模式" name="theme_mode">
                    <Radio.Group>
                      <Radio.Button value="light">
                        <SunOutlined /> 浅色
                      </Radio.Button>
                      <Radio.Button value="dark">
                        <MoonOutlined /> 深色
                      </Radio.Button>
                      <Radio.Button value="auto">
                        <EyeOutlined /> 跟随系统
                      </Radio.Button>
                    </Radio.Group>
                  </Form.Item>

                  <Form.Item label="主题预设" name="theme_preset">
                    <Radio.Group optionType="button" buttonStyle="solid">
                      {themePresets.map((theme) => (
                        <Radio.Button key={theme.value} value={theme.value}>
                          <span
                            style={{
                              display: 'inline-block',
                              width: 12,
                              height: 12,
                              borderRadius: '50%',
                              backgroundColor: theme.primaryColor,
                              marginRight: 8,
                            }}
                          />
                          {theme.label}
                        </Radio.Button>
                      ))}
                    </Radio.Group>
                  </Form.Item>

                  <Form.Item label="自定义主题色" name="primary_color">
                    <ColorPicker
                      showText
                      format="hex"
                      onChange={(color) => {
                        form.setFieldValue('primary_color', color.toHexString());
                      }}
                    />
                  </Form.Item>

                  <Divider>界面布局</Divider>

                  <Form.Item
                    label="紧凑模式"
                    name="compact_mode"
                    valuePropName="checked"
                    extra="启用后界面元素间距更紧凑"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item
                    label="启用动画"
                    name="enable_animation"
                    valuePropName="checked"
                    extra="启用界面过渡动画效果"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item label="菜单布局" name="menu_layout">
                    <Radio.Group>
                      <Radio value="top">顶部菜单</Radio>
                      <Radio value="side">侧边菜单</Radio>
                      <Radio value="mix">混合菜单</Radio>
                    </Radio.Group>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'branding',
              label: '品牌定制',
              children: (
                <Form
                  layout="vertical"
                  initialValues={{
                    site_name: 'TokenMachine',
                    site_title: 'Enterprise AI Model Deployment Platform',
                    favicon: '',
                    logo_width: 40,
                  }}
                >
                  <Form.Item label="系统名称" name="site_name">
                    <Input placeholder="TokenMachine" />
                  </Form.Item>

                  <Form.Item label="页面标题" name="site_title">
                    <Input placeholder="Enterprise AI Model Deployment Platform" />
                  </Form.Item>

                  <Form.Item label="系统Logo" name="logo">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Upload
                        name="logo"
                        listType="picture-card"
                        showUploadList={false}
                        action="/api/upload"
                        onChange={handleLogoUpload}
                      >
                        {logoUrl ? (
                          <img src={logoUrl} alt="logo" style={{ width: '100%' }} />
                        ) : (
                          <div>
                            <UploadOutlined />
                            <div style={{ marginTop: 8 }}>上传Logo</div>
                          </div>
                        )}
                      </Upload>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        推荐尺寸：200x60px，支持PNG、SVG格式
                      </Text>
                    </Space>
                  </Form.Item>

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item label="Logo宽度" name="logo_width">
                        <InputNumber min={20} max={100} suffix="px" style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item label="Logo圆角" name="logo_radius">
                        <InputNumber min={0} max={20} suffix="px" style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item label="Favicon" name="favicon">
                    <Upload
                      name="favicon"
                      showUploadList={false}
                      action="/api/upload"
                      accept=".ico,.png"
                    >
                      <Button icon={<UploadOutlined />}>上传Favicon</Button>
                    </Upload>
                  </Form.Item>

                  <Form.Item label="自定义CSS" name="custom_css">
                    <Input.TextArea
                      rows={8}
                      placeholder={`/* 自定义CSS样式 */\n.header {\n  background: custom-color;\n}`}
                    />
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'display',
              label: '显示设置',
              children: (
                <Form
                  layout="vertical"
                  initialValues={{
                    language: 'zh-CN',
                    date_format: 'YYYY-MM-DD HH:mm:ss',
                    timezone: 'Asia/Shanghai',
                    page_size: 20,
                    density: 'middle',
                  }}
                >
                  <Form.Item label="界面语言" name="language">
                    <Select>
                      <Select.Option value="zh-CN">简体中文</Select.Option>
                      <Select.Option value="zh-TW">繁體中文</Select.Option>
                      <Select.Option value="en-US">English</Select.Option>
                      <Select.Option value="ja-JP">日本語</Select.Option>
                    </Select>
                  </Form.Item>

                  <Form.Item label="日期格式" name="date_format">
                    <Select>
                      <Select.Option value="YYYY-MM-DD HH:mm:ss">
                        2024-01-19 10:30:00
                      </Select.Option>
                      <Select.Option value="YYYY/MM/DD HH:mm:ss">
                        2024/01/19 10:30:00
                      </Select.Option>
                      <Select.Option value="MM-DD-YYYY HH:mm:ss">
                        01-19-2024 10:30:00
                      </Select.Option>
                      <Select.Option value="DD-MM-YYYY HH:mm:ss">
                        19-01-2024 10:30:00
                      </Select.Option>
                    </Select>
                  </Form.Item>

                  <Form.Item label="时区" name="timezone">
                    <Select>
                      <Select.Option value="Asia/Shanghai">
                        Asia/Shanghai (UTC+8)
                      </Select.Option>
                      <Select.Option value="America/New_York">
                        America/New_York (UTC-5)
                      </Select.Option>
                      <Select.Option value="Europe/London">
                        Europe/London (UTC+0)
                      </Select.Option>
                      <Select.Option value="Asia/Tokyo">
                        Asia/Tokyo (UTC+9)
                      </Select.Option>
                    </Select>
                  </Form.Item>

                  <Divider>列表设置</Divider>

                  <Form.Item label="默认分页大小" name="page_size">
                    <Radio.Group>
                      <Radio.Button value={10}>10条/页</Radio.Button>
                      <Radio.Button value={20}>20条/页</Radio.Button>
                      <Radio.Button value={50}>50条/页</Radio.Button>
                      <Radio.Button value={100}>100条/页</Radio.Button>
                    </Radio.Group>
                  </Form.Item>

                  <Form.Item label="组件密度" name="density">
                    <Radio.Group>
                      <Radio.Button value="small">紧凑</Radio.Button>
                      <Radio.Button value="middle">默认</Radio.Button>
                      <Radio.Button value="large">宽松</Radio.Button>
                    </Radio.Group>
                  </Form.Item>

                  <Form.Item
                    label="显示列边框"
                    name="show_borders"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'dashboard',
              label: '仪表盘设置',
              children: (
                <Form
                  layout="vertical"
                  initialValues={{
                    refresh_interval: 30,
                    enable_realtime: true,
                    default_dashboard: 'overview',
                  }}
                >
                  <Form.Item
                    label="刷新间隔"
                    name="refresh_interval"
                    extra="仪表盘数据自动刷新间隔"
                  >
                    <Radio.Group>
                      <Radio.Button value={10}>10秒</Radio.Button>
                      <Radio.Button value={30}>30秒</Radio.Button>
                      <Radio.Button value={60}>1分钟</Radio.Button>
                      <Radio.Button value={300}>5分钟</Radio.Button>
                    </Radio.Group>
                  </Form.Item>

                  <Form.Item
                    label="实时更新"
                    name="enable_realtime"
                    valuePropName="checked"
                    extra="启用WebSocket实时数据推送"
                  >
                    <Switch />
                  </Form.Item>

                  <Divider>默认仪表盘</Divider>

                  <Form.Item label="默认页面" name="default_dashboard">
                    <Radio.Group>
                      <Radio value="overview">系统概览</Radio>
                      <Radio value="models">模型与实例</Radio>
                      <Radio value="deployments">节点与后端</Radio>
                      <Radio value="monitoring">监控面板</Radio>
                    </Radio.Group>
                  </Form.Item>

                  <Form.Item
                    label="显示卡片阴影"
                    name="card_shadow"
                    valuePropName="checked"
                    initialValue={true}
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item
                    label="显示图表动画"
                    name="chart_animation"
                    valuePropName="checked"
                    initialValue={true}
                  >
                    <Switch />
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />

        <Divider />

        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button icon={<ReloadOutlined />} onClick={handleReset}>
            重置
          </Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
            保存设置
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default InterfaceSettings;

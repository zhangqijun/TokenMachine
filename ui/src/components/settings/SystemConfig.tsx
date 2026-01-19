import { useState } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Space,
  Typography,
  Divider,
  Row,
  Col,
  Tabs,
  message,
  Alert,
  Upload,
} from 'antd';
import {
  SettingOutlined,
  SaveOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined,
  KeyOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  SecurityScanOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

const SystemConfig = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSave = () => {
    setLoading(true);
    form.validateFields().then(() => {
      setTimeout(() => {
        setLoading(false);
        message.success('系统配置保存成功，部分配置需要重启服务后生效');
      }, 1000);
    });
  };

  const handleReset = () => {
    form.resetFields();
    message.info('已重置为上次保存的配置');
  };

  const handleExport = () => {
    message.success('配置导出成功');
  };

  const handleImport = () => {
    message.success('配置导入成功');
  };

  return (
    <div>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>系统配置</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出配置
            </Button>
            <Upload accept=".json,.yaml" showUploadList={false} onChange={handleImport}>
              <Button icon={<UploadOutlined />}>导入配置</Button>
            </Upload>
          </Space>
        }
      >
        <Alert
          message="配置修改提示"
          description="部分配置项修改后需要重启相关服务才能生效，请谨慎操作。建议在非业务高峰期进行配置变更。"
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Tabs
          defaultActiveKey="basic"
          items={[
            {
              key: 'basic',
              label: '基础配置',
              children: (
                <Form
                  form={form}
                  layout="vertical"
                  initialValues={{
                    system_name: 'TokenMachine',
                    log_level: 'info',
                    timezone: 'Asia/Shanghai',
                    enable_metrics: true,
                    max_workers: 16,
                    task_timeout: 300,
                  }}
                >
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="系统名称"
                        name="system_name"
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item label="时区" name="timezone">
                        <Select>
                          <Select.Option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</Select.Option>
                          <Select.Option value="America/New_York">
                            America/New_York (UTC-5)
                          </Select.Option>
                          <Select.Option value="Europe/London">
                            Europe/London (UTC+0)
                          </Select.Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="日志级别"
                        name="log_level"
                        extra="日志记录的详细程度"
                      >
                        <Select>
                          <Select.Option value="debug">Debug (调试)</Select.Option>
                          <Select.Option value="info">Info (信息)</Select.Option>
                          <Select.Option value="warning">Warning (警告)</Select.Option>
                          <Select.Option value="error">Error (错误)</Select.Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item label="日志保留天数" name="log_retention" initialValue={30}>
                        <InputNumber min={1} max={365} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="最大Worker数"
                        name="max_workers"
                        extra="后台任务最大并发数"
                      >
                        <InputNumber min={1} max={128} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item label="任务超时时间(秒)" name="task_timeout">
                        <InputNumber min={10} max={3600} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    label="启用指标采集"
                    name="enable_metrics"
                    valuePropName="checked"
                    extra="启用Prometheus指标采集"
                  >
                    <Switch />
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'gpu',
              label: 'GPU配置',
              children: (
                <Form
                  layout="vertical"
                  initialValues={{
                    gpu_memory_utilization: 90,
                    max_model_length: 8192,
                    enable_tensor_parallel: true,
                    tensor_parallel_degree: 2,
                    enable_pipeline_parallel: false,
                  }}
                >
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="GPU显存利用率 (%)"
                        name="gpu_memory_utilization"
                        extra="vLLM显存利用率，建议80-95"
                      >
                        <InputNumber min={50} max={99} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="最大模型长度"
                        name="max_model_length"
                        extra="模型支持的最大上下文长度"
                      >
                        <InputNumber min={1024} max={32768} step={1024} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Divider>张量并行</Divider>

                  <Form.Item
                    label="启用张量并行"
                    name="enable_tensor_parallel"
                    valuePropName="checked"
                    extra="多GPU并行计算"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item label="并行度" name="tensor_parallel_degree">
                    <Select>
                      <Select.Option value={1}>1 (不并行)</Select.Option>
                      <Select.Option value={2}>2 (2卡)</Select.Option>
                      <Select.Option value={4}>4 (4卡)</Select.Option>
                      <Select.Option value={8}>8 (8卡)</Select.Option>
                    </Select>
                  </Form.Item>

                  <Divider>流水线并行</Divider>

                  <Form.Item
                    label="启用流水线并行"
                    name="enable_pipeline_parallel"
                    valuePropName="checked"
                    extra="跨节点流水线并行"
                  >
                    <Switch />
                  </Form.Item>

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="Block大小"
                        name="block_size"
                        initialValue={16}
                        extra="vLLM KV cache block size"
                      >
                        <InputNumber min={8} max={32} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="GPU利用率阈值 (%)"
                        name="gpu_util_threshold"
                        initialValue={95}
                      >
                        <InputNumber min={50} max={100} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                </Form>
              ),
            },
            {
              key: 'storage',
              label: '存储配置',
              children: (
                <Form
                  layout="vertical"
                  initialValues={{
                    model_storage_path: '/data/models',
                    log_storage_path: '/data/logs',
                    backup_storage_path: '/data/backups',
                    max_upload_size: 100,
                    enable_compression: true,
                    auto_cleanup: true,
                  }}
                >
                  <Form.Item
                    label="模型存储路径"
                    name="model_storage_path"
                    rules={[{ required: true }]}
                  >
                    <Input prefix={<DatabaseOutlined />} />
                  </Form.Item>

                  <Form.Item
                    label="日志存储路径"
                    name="log_storage_path"
                    rules={[{ required: true }]}
                  >
                    <Input prefix={<DatabaseOutlined />} />
                  </Form.Item>

                  <Form.Item
                    label="备份存储路径"
                    name="backup_storage_path"
                    rules={[{ required: true }]}
                  >
                    <Input prefix={<DatabaseOutlined />} />
                  </Form.Item>

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="最大上传大小 (GB)"
                        name="max_upload_size"
                        extra="单文件上传大小限制"
                      >
                        <InputNumber min={1} max={1000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="备份保留天数"
                        name="backup_retention"
                        initialValue={30}
                      >
                        <InputNumber min={1} max={365} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    label="启用压缩"
                    name="enable_compression"
                    valuePropName="checked"
                    extra="自动压缩日志和备份文件"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item
                    label="自动清理"
                    name="auto_cleanup"
                    valuePropName="checked"
                    extra="自动清理过期文件"
                  >
                    <Switch />
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'security',
              label: '安全配置',
              children: (
                <Form
                  layout="vertical"
                  initialValues={{
                    enable_auth: true,
                    session_timeout: 7200,
                    max_login_attempts: 5,
                    lockout_duration: 300,
                    enable_https: true,
                    api_rate_limit: 1000,
                  }}
                >
                  <Form.Item
                    label="启用身份认证"
                    name="enable_auth"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="会话超时时间 (秒)"
                        name="session_timeout"
                        extra="用户登录会话有效期"
                      >
                        <InputNumber min={300} max={86400} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item label="最大登录尝试次数" name="max_login_attempts">
                        <InputNumber min={3} max={20} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item label="锁定时长 (秒)" name="lockout_duration">
                        <InputNumber min={60} max={3600} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="API速率限制 (请求/分钟)"
                        name="api_rate_limit"
                        extra="单个用户每分钟最大请求次数"
                      >
                        <InputNumber min={10} max={10000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Divider>HTTPS 配置</Divider>

                  <Form.Item
                    label="启用HTTPS"
                    name="enable_https"
                    valuePropName="checked"
                    extra="需要配置SSL证书"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item label="SSL证书路径" name="ssl_cert_path">
                    <Input />
                  </Form.Item>

                  <Form.Item label="SSL私钥路径" name="ssl_key_path">
                    <Input.Password />
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'network',
              label: '网络配置',
              children: (
                <Form
                  layout="vertical"
                  initialValues={{
                    api_host: '0.0.0.0',
                    api_port: 8000,
                    cors_origins: '*',
                    proxy_enabled: false,
                  }}
                >
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="API服务地址"
                        name="api_host"
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="API服务端口"
                        name="api_port"
                        rules={[{ required: true }]}
                      >
                        <InputNumber min={1024} max={65535} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    label="CORS允许来源"
                    name="cors_origins"
                    extra="跨域请求允许的来源，*表示允许所有"
                  >
                    <Input placeholder="http://localhost:3000, https://example.com" />
                  </Form.Item>

                  <Divider>代理设置</Divider>

                  <Form.Item
                    label="启用代理"
                    name="proxy_enabled"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item label="HTTP代理地址" name="http_proxy">
                    <Input placeholder="http://proxy.example.com:8080" />
                  </Form.Item>

                  <Form.Item label="HTTPS代理地址" name="https_proxy">
                    <Input placeholder="https://proxy.example.com:8080" />
                  </Form.Item>

                  <Form.Item label="代理绕过列表" name="no_proxy">
                    <TextArea
                      rows={3}
                      placeholder="localhost,127.0.0.1,*.internal.com"
                    />
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
          <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave}>
            保存配置
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default SystemConfig;

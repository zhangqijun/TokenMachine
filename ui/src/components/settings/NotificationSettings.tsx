import { useState } from 'react';
import {
  Card,
  Form,
  Switch,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Divider,
  Row,
  Col,
  Tabs,
  Table,
  Tag,
  message,
  Modal,
} from 'antd';
import {
  BellOutlined,
  MailOutlined,
  SoundOutlined,
  WechatOutlined,
  DingdingOutlined,
  SlackOutlined,
  SendOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  SaveOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface NotificationRule {
  id: string;
  name: string;
  type: 'email' | 'webhook' | 'wechat' | 'dingtalk';
  trigger: string;
  enabled: boolean;
}

const NotificationSettings = () => {
  const [form] = Form.useForm();
  const [testModalVisible, setTestModalVisible] = useState(false);
  const [testForm] = Form.useForm();

  const notificationChannels = [
    {
      key: 'email',
      icon: <MailOutlined />,
      name: '邮件通知',
      description: '通过邮件发送告警信息',
    },
    {
      key: 'webhook',
      icon: <SendOutlined />,
      name: 'Webhook',
      description: '自定义 Webhook 接收告警',
    },
    {
      key: 'wechat',
      icon: <WechatOutlined />,
      name: '企业微信',
      description: '推送到企业微信群聊',
    },
    {
      key: 'dingtalk',
      icon: <DingdingOutlined />,
      name: '钉钉机器人',
      description: '推送到钉钉群聊',
    },
    {
      key: 'slack',
      icon: <SlackOutlined />,
      name: 'Slack',
      description: '推送到 Slack 频道',
    },
  ];

  const notificationRules: NotificationRule[] = [
    {
      id: '1',
      name: 'GPU 温度告警',
      type: 'email',
      trigger: 'GPU温度 > 80°C',
      enabled: true,
    },
    {
      id: '2',
      name: '服务异常告警',
      type: 'dingtalk',
      trigger: '服务宕机或无响应',
      enabled: true,
    },
    {
      id: '3',
      name: '模型部署失败',
      type: 'webhook',
      trigger: '模型部署失败',
      enabled: true,
    },
    {
      id: '4',
      name: '磁盘空间不足',
      type: 'wechat',
      trigger: '磁盘使用率 > 90%',
      enabled: false,
    },
  ];

  const handleSave = () => {
    form.validateFields().then(() => {
      message.success('通知设置保存成功');
    });
  };

  const handleSendTest = (channel: string) => {
    setTestModalVisible(true);
  };

  const handleSendTestNotification = () => {
    testForm.validateFields().then(() => {
      message.success('测试通知已发送');
      setTestModalVisible(false);
      testForm.resetFields();
    });
  };

  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '通知渠道',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const config: Record<string, { color: string; label: string }> = {
          email: { color: 'blue', label: '邮件' },
          webhook: { color: 'purple', label: 'Webhook' },
          wechat: { color: 'green', label: '企业微信' },
          dingtalk: { color: 'cyan', label: '钉钉' },
        };
        return <Tag color={config[type]?.color}>{config[type]?.label}</Tag>;
      },
    },
    {
      title: '触发条件',
      dataIndex: 'trigger',
      key: 'trigger',
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: NotificationRule) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />}>
            编辑
          </Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const channelConfigCards = notificationChannels.map((channel) => (
    <Card key={channel.key} size="small" style={{ marginBottom: 12 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <span style={{ fontSize: 18, color: '#1890ff' }}>{channel.icon}</span>
            <Text strong>{channel.name}</Text>
          </Space>
          <Form.Item name={`enabled_${channel.key}`} valuePropName="checked" noStyle>
            <Switch />
          </Form.Item>
        </div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {channel.description}
        </Text>
        {channel.key === 'email' && (
          <div>
            <Form.Item
              label="SMTP服务器"
              name={['email', 'smtp_host']}
              initialValue="smtp.gmail.com"
            >
              <Input placeholder="smtp.gmail.com" />
            </Form.Item>
            <Row gutter={8}>
              <Col span={12}>
                <Form.Item label="端口" name={['email', 'smtp_port']} initialValue={587}>
                  <Input type="number" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="发件人" name={['email', 'from']}>
                  <Input placeholder="noreply@tokenmachine.ai" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="用户名" name={['email', 'username']}>
              <Input placeholder="邮箱地址" />
            </Form.Item>
            <Form.Item label="密码" name={['email', 'password']}>
              <Input.Password placeholder="邮箱密码或授权码" />
            </Form.Item>
          </div>
        )}
        {channel.key === 'webhook' && (
          <div>
            <Form.Item label="Webhook URL" name={['webhook', 'url']}>
              <Input placeholder="https://your-server.com/webhook" />
            </Form.Item>
            <Form.Item label="认证方式" name={['webhook', 'auth_type']}>
              <Select>
                <Select.Option value="none">无认证</Select.Option>
                <Select.Option value="bearer">Bearer Token</Select.Option>
                <Select.Option value="basic">Basic Auth</Select.Option>
              </Select>
            </Form.Item>
          </div>
        )}
        {channel.key === 'dingtalk' && (
          <div>
            <Form.Item label="Webhook URL" name={['dingtalk', 'url']}>
              <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx" />
            </Form.Item>
            <Form.Item label="密钥" name={['dingtalk', 'secret']}>
              <Input.Password placeholder="加签密钥（可选）" />
            </Form.Item>
          </div>
        )}
        {(channel.key === 'wechat' || channel.key === 'slack') && (
          <div>
            <Form.Item label="Webhook URL" name={[channel.key, 'url']}>
              <Input placeholder="Webhook URL" />
            </Form.Item>
          </div>
        )}
        <Button
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={() => handleSendTest(channel.key)}
        >
          发送测试
        </Button>
      </Space>
    </Card>
  ));

  return (
    <div>
      <Card
        title={
          <Space>
            <BellOutlined />
            <span>通知设置</span>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="channels"
          items={[
            {
              key: 'channels',
              label: '通知渠道',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>配置通知渠道</Text>
                    <Divider style={{ margin: '12px 0' }} />
                  </div>

                  <Form
                    form={form}
                    layout="vertical"
                    initialValues={{
                      enabled_email: true,
                      enabled_webhook: false,
                      enabled_wechat: false,
                      enabled_dingtalk: true,
                      enabled_slack: false,
                    }}
                  >
                    <Row gutter={16}>
                      <Col xs={24} lg={12}>
                        {channelConfigCards.filter((_, i) => i % 2 === 0)}
                      </Col>
                      <Col xs={24} lg={12}>
                        {channelConfigCards.filter((_, i) => i % 2 === 1)}
                      </Col>
                    </Row>
                  </Form>

                  <div style={{ marginTop: 24, textAlign: 'right' }}>
                    <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                      保存设置
                    </Button>
                  </div>
                </div>
              ),
            },
            {
              key: 'rules',
              label: '告警规则',
              children: (
                <div>
                  <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>告警规则列表</Text>
                    <Button type="primary" size="small" icon={<PlusOutlined />}>
                      添加规则
                    </Button>
                  </div>

                  <Table
                    columns={ruleColumns}
                    dataSource={notificationRules}
                    rowKey="id"
                    pagination={false}
                    size="small"
                  />
                </div>
              ),
            },
            {
              key: 'templates',
              label: '消息模板',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>自定义告警消息模板</Text>
                    <Divider style={{ margin: '12px 0' }} />
                  </div>

                  <Form layout="vertical">
                    <Form.Item label="邮件主题模板" name="email_subject">
                      <Input placeholder="[告警] {{.AlertName}} - {{.Level}}" />
                    </Form.Item>

                    <Form.Item label="邮件内容模板" name="email_body">
                      <TextArea
                        rows={8}
                        placeholder={`告警名称: {{.AlertName}}
告警级别: {{.Level}}
触发时间: {{.Timestamp}}
触发条件: {{.Condition}}
详细信息: {{.Details}}`}
                      />
                    </Form.Item>

                    <Form.Item label="企业微信/钉钉消息模板" name="im_body">
                      <TextArea
                        rows={6}
                        placeholder={`## {{.AlertName}}
> 级别: {{.Level}}
> 时间: {{.Timestamp}}

**触发条件:** {{.Condition}}

**详细信息:**
{{.Details}}`}
                      />
                    </Form.Item>

                    <Form.Item>
                      <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                        保存模板
                      </Button>
                    </Form.Item>
                  </Form>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="发送测试通知"
        open={testModalVisible}
        onOk={handleSendTestNotification}
        onCancel={() => {
          setTestModalVisible(false);
          testForm.resetFields();
        }}
      >
        <Form form={testForm} layout="vertical">
          <Form.Item label="测试内容" name="content" initialValue="这是一条测试通知">
            <TextArea rows={4} />
          </Form.Item>

          <Form.Item label="接收者" name="receiver" initialValue="admin@example.com">
            <Input placeholder="邮箱地址或手机号" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default NotificationSettings;

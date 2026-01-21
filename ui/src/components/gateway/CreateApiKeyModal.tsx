import { useState } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Checkbox,
  InputNumber,
  Radio,
  Space,
  Button,
  message,
  Card,
  Divider,
} from 'antd';
import {
  KeyOutlined,
  LockOutlined,
  DollarOutlined,
  SplitCellsOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useStore } from '../../store';
import dayjs from 'dayjs';

interface CreateApiKeyModalProps {
  open: boolean;
  onCancel: () => void;
}

const CreateApiKeyModal = ({ open, onCancel }: CreateApiKeyModalProps) => {
  const { createApiKey, isLoading } = useStore();
  const [form] = Form.useForm();
  const [quotaType, setQuotaType] = useState<'unlimited' | 'custom'>('unlimited');
  const [expireType, setExpireType] = useState<'never' | 'days' | 'custom'>('never');
  const [enableRouting, setEnableRouting] = useState(false);
  const [dedicatedRouting, setDedicatedRouting] = useState(false);

  const handleSubmit = async (values: any) => {
    try {
      const quotaTokens = quotaType === 'unlimited' ? 1000000000 : values.quota_tokens;
      const expiresAt = expireType === 'never'
        ? dayjs().add(10, 'year').toISOString()
        : expireType === 'days'
        ? dayjs().add(values.expires_in, 'day').toISOString()
        : values.expires_at;

      await createApiKey({
        name: values.name,
        quota_tokens: quotaTokens,
        tokens_used: 0,
        is_active: true,
        expires_at: expiresAt,
      });

      message.success('API 密钥创建成功');

      Modal.success({
        title: '✓ 密钥创建成功',
        content: (
          <div>
            <p style={{ marginBottom: 16 }}>您的 API 密钥:</p>
            <div style={{
              background: '#f5f5f5',
              padding: '12px',
              borderRadius: 4,
              fontFamily: 'monospace',
              fontSize: 14,
              marginBottom: 16,
            }}>
              tmachine_sk_{'x'.repeat(32)}
            </div>
            <p style={{ color: '#52c41a', marginBottom: 16 }}>🔑 路由配置摘要:</p>
            <ul style={{ fontSize: 13, color: '#666', paddingLeft: 20 }}>
              <li>语义路由: qwen.* → qwen-2.5-7b (90%)</li>
              <li>API 聚合: /v1/models/unified (统一端点)</li>
              <li>动态调度: ✅ 已启用 (队列阈值: 20)</li>
              <li>故障转移: ✅ 已启用 (重试 3 次)</li>
            </ul>
            <p style={{ color: '#ff4d4f', fontSize: 12, marginTop: 16 }}>
              ⚠️ 警告: 请立即复制并妥善保管，关闭此窗口后将无法再次查看。
            </p>
          </div>
        ),
        okText: '我已复制，关闭',
        onOk: () => {
          form.resetFields();
          onCancel();
        },
      });
    } catch (error) {
      message.error('创建失败');
    }
  };

  return (
    <Modal
      title={
        <Space>
          <KeyOutlined />
          创建 API 密钥
        </Space>
      }
      open={open}
      onCancel={() => {
        form.resetFields();
        setQuotaType('unlimited');
        setExpireType('never');
        setEnableRouting(false);
        setDedicatedRouting(false);
        onCancel();
      }}
      footer={null}
      width={720}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {/* 基本信息 */}
        <Card
          size="small"
          title={<span style={{ fontSize: 14 }}>基本信息</span>}
          style={{ marginBottom: 16 }}
        >
          <Form.Item
            label="密钥名称"
            name="name"
            rules={[{ required: true, message: '请输入密钥名称' }]}
          >
            <Input placeholder="Production API Key" />
          </Form.Item>

          <Form.Item
            label="描述说明"
            name="description"
          >
            <Input.TextArea placeholder="用于生产环境的 API 密钥" rows={2} />
          </Form.Item>
        </Card>

        {/* 权限配置 */}
        <Card
          size="small"
          title={
            <Space>
              <LockOutlined />
              <span style={{ fontSize: 14 }}>权限配置</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Form.Item label="可访问的模型">
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Checkbox value="qwen">qwen2.5-7b-prod</Checkbox>
                <Checkbox value="llama">llama-3-8b-staging</Checkbox>
                <Checkbox value="glm">glm-4-9b</Checkbox>
                <Checkbox value="mistral">mistral-7b</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Form.Item label="允许的操作">
            <Checkbox.Group>
              <Space wrap>
                <Checkbox value="chat">Chat 对话</Checkbox>
                <Checkbox value="completion">Text Completion</Checkbox>
                <Checkbox value="embedding">Embedding</Checkbox>
                <Checkbox value="image">Image Generate</Checkbox>
                <Checkbox value="audio">Audio TTS</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Form.Item label="速率限制">
            <Space>
              <Form.Item name="concurrent_limit" noStyle initialValue={10}>
                <InputNumber min={1} max={1000} addonBefore="并发限制" style={{ width: 140 }} />
              </Form.Item>
              <Form.Item name="qps_limit" noStyle initialValue={100}>
                <InputNumber min={1} max={10000} addonBefore="QPS 限制" style={{ width: 140 }} />
              </Form.Item>
            </Space>
          </Form.Item>
        </Card>

        {/* 配额管理 */}
        <Card
          size="small"
          title={
            <Space>
              <DollarOutlined />
              <span style={{ fontSize: 14 }}>配额管理</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Form.Item label="配额类型">
            <Radio.Group value={quotaType} onChange={(e) => setQuotaType(e.target.value)}>
              <Space direction="vertical">
                <Radio value="unlimited">⦿ 无限制 (生产环境推荐)</Radio>
                <Radio value="custom">○ 自定义配额</Radio>
              </Space>
            </Radio.Group>
          </Form.Item>

          {quotaType === 'custom' && (
            <>
              <Form.Item
                label="Token 配额"
                name="quota_tokens"
                rules={[{ required: true }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={1000}
                  max={1000000000}
                  formatter={(value) => `${value?.toLocaleString()} tokens`}
                  addonAfter="tokens"
                />
              </Form.Item>

              <Form.Item name="request_limit" label="请求数限制">
                <InputNumber style={{ width: '100%' }} min={1} addonAfter="次/天" />
              </Form.Item>

              <Form.Item name="concurrent_quota" label="并发数限制">
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>

              <Form.Item name="budget" label="费用预算">
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  prefix="¥"
                  addonAfter="/月"
                />
              </Form.Item>
            </>
          )}
        </Card>

        {/* 路由配置 */}
        <Card
          size="small"
          title={
            <Space>
              <SplitCellsOutlined />
              <span style={{ fontSize: 14 }}>路由配置（绑定现有路由策略）</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Form.Item label="选择路由策略">
            <Select
              placeholder="选择路由策略"
              options={[
                { label: 'qwen-智能路由', value: 'qwen-smart' },
                { label: 'llama-灰度发布', value: 'llama-canary' },
                { label: '统一入口 (Round-Robin)', value: 'round-robin' },
              ]}
            />
            <Button type="link" style={{ padding: 0, marginTop: 4 }}>
              + 创建新路由
            </Button>
          </Form.Item>

          <Form.Item>
            <Checkbox
              checked={dedicatedRouting}
              onChange={(e) => setDedicatedRouting(e.target.checked)}
            >
              或为该密钥创建专属路由 (不共享其他密钥)
            </Checkbox>
          </Form.Item>

          {dedicatedRouting && (
            <div style={{ marginLeft: 24, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
              <Form.Item label="路由模式" style={{ marginBottom: 8 }}>
                <Radio.Group size="small">
                  <Radio.Button value="semantic">语义路由</Radio.Button>
                  <Radio.Button value="weight">权重路由</Radio.Button>
                  <Radio.Button value="round-robin">轮询</Radio.Button>
                  <Radio.Button value="least-conn">最少连接</Radio.Button>
                </Radio.Group>
              </Form.Item>

              <Form.Item label="语义规则" style={{ marginBottom: 8 }}>
                <Input placeholder="qwen.* → qwen-2.5-7b" />
              </Form.Item>

              <Space size="middle">
                <Form.Item label="权重分配" style={{ marginBottom: 0 }}>
                  <InputNumber min={0} max={100} formatter={(v) => `${v}%`} />
                </Form.Item>
                <Form.Item label="动态调度" style={{ marginBottom: 0 }}>
                  <Checkbox defaultChecked>启用</Checkbox>
                </Form.Item>
                <Form.Item label="故障转移" style={{ marginBottom: 0 }}>
                  <Checkbox defaultChecked>启用</Checkbox>
                </Form.Item>
                <Form.Item label="重试次数" style={{ marginBottom: 0 }}>
                  <InputNumber min={1} max={10} defaultValue={3} />
                </Form.Item>
              </Space>
            </div>
          )}
        </Card>

        {/* 过期时间 */}
        <Card
          size="small"
          title={
            <Space>
              <ClockCircleOutlined />
              <span style={{ fontSize: 14 }}>过期时间</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Form.Item label="">
            <Radio.Group value={expireType} onChange={(e) => setExpireType(e.target.value)}>
              <Space direction="vertical">
                <Radio value="never">⦿ 永不过期</Radio>
                <Radio value="days">○ 30 天后过期</Radio>
                <Radio value="custom">○ 自定义日期</Radio>
              </Space>
            </Radio.Group>
          </Form.Item>

          {expireType === 'custom' && (
            <Form.Item name="expires_at" rules={[{ required: true }]}>
              <Input type="date" />
            </Form.Item>
          )}
        </Card>

        <Divider style={{ margin: '16px 0' }} />

        <div style={{
          padding: 12,
          background: '#e6f7ff',
          border: '1px solid #91d5ff',
          borderRadius: 4,
          marginBottom: 16,
          fontSize: 13,
        }}>
          创建成功后，密钥将仅显示一次，请妥善保存。
        </div>

        <Form.Item style={{ marginBottom: 0 }}>
          <Space>
            <Button onClick={onCancel}>取消</Button>
            <Button type="primary" htmlType="submit" loading={isLoading}>
              创建密钥
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateApiKeyModal;

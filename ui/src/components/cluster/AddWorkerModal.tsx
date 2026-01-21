import { useState, useEffect, useRef } from 'react';
import { Modal, Form, Input, Select, Button, Space, message, Row, Col, Tag, Progress, Steps } from 'antd';
import { CopyOutlined, CheckCircleOutlined, LoadingOutlined } from '@ant-design/icons';

interface AddWorkerModalProps {
  visible: boolean;
  onCancel: () => void;
  onOk: (worker: any) => void;
  onWorkerRegistered?: (workerName: string) => void; // 新增：worker注册成功的回调
}

interface WorkerFormData {
  name: string;
  registerToken: string;
  labels: Record<string, string>;
}

const AddWorkerModal = ({ visible, onCancel, onOk, onWorkerRegistered }: AddWorkerModalProps) => {
  const [form] = Form.useForm();
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [labelKey, setLabelKey] = useState('');
  const [labelValue, setLabelValue] = useState('');
  const [registrationStatus, setRegistrationStatus] = useState<'idle' | 'waiting' | 'registering' | 'success'>('idle');
  const [pollingCount, setPollingCount] = useState(0);
  const [currentToken, setCurrentToken] = useState<string>('');
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 当modal打开时自动生成token
  useEffect(() => {
    if (visible) {
      const token = 'tm_worker_' + Math.random().toString(36).substring(2, 15) +
                    Math.random().toString(36).substring(2, 15);
      form.setFieldValue('registerToken', token);
      setCurrentToken(token);
      setRegistrationStatus('idle');
      setPollingCount(0);
    }
  }, [visible, form]);

  // 清理轮询定时器
  useEffect(() => {
    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
      }
    };
  }, []);

  const generateToken = () => {
    const token = 'tm_worker_' + Math.random().toString(36).substring(2, 15) +
                  Math.random().toString(36).substring(2, 15);
    form.setFieldValue('registerToken', token);
  };

  // 开始轮询worker注册状态
  const startPolling = async (workerName: string) => {
    setRegistrationStatus('waiting');
    setPollingCount(0);

    // 模拟轮询worker注册状态
    pollingTimerRef.current = setInterval(() => {
      setPollingCount(prev => {
        const newCount = prev + 1;
        console.log(`轮询中... (${newCount})`);

        // 模拟：第3次轮询时发现worker已注册（实际应该调用API检查）
        if (newCount >= 3) {
          if (pollingTimerRef.current) {
            clearInterval(pollingTimerRef.current);
            pollingTimerRef.current = null;
          }
          setRegistrationStatus('success');

          // 通知父组件worker已注册
          if (onWorkerRegistered) {
            onWorkerRegistered(workerName);
          }

          // 1秒后自动关闭modal
          setTimeout(() => {
            handleCancel();
          }, 1000);
        }
        return newCount;
      });
    }, 2000); // 每2秒轮询一次
  };

  const startRegistration = async () => {
    try {
      const values = await form.validateFields();
      const workerName = values.name;

      // 模拟开始添加worker
      setRegistrationStatus('registering');

      // 调用父组件的onOk添加worker到列表
      onOk({
        name: workerName,
        ip: '192.168.1.' + Math.floor(Math.random() * 254 + 1),
        labels: labels,
        gpu_count: 4,
        gpu_memory_total: 160,
      });

      // 开始轮询worker注册状态
      startPolling(workerName);

      message.success('Worker配置已保存，等待节点注册...');
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleCopyToken = () => {
    const token = form.getFieldValue('registerToken');
    navigator.clipboard.writeText(token);
    message.success('Token 已复制到剪贴板');
  };

  const handleCopyCommand = () => {
    const command = `curl -sfL https://get.tokenmachine.io | bash -s -- ${currentToken}`;
    navigator.clipboard.writeText(command);
    message.success('安装命令已复制到剪贴板（含真实Token）');
  };

  const handleAddLabel = () => {
    if (labelKey && labelValue) {
      setLabels({ ...labels, [labelKey]: labelValue });
      setLabelKey('');
      setLabelValue('');
    }
  };

  const handleRemoveLabel = (key: string) => {
    const newLabels = { ...labels };
    delete newLabels[key];
    setLabels(newLabels);
  };

  const handleOk = async () => {
    await startRegistration();
  };

  const handleCancel = () => {
    // 清理轮询定时器
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    form.resetFields();
    setLabels({});
    setRegistrationStatus('idle');
    setPollingCount(0);
    onCancel();
  };

  return (
    <Modal
      title="添加 Worker 节点"
      open={visible}
      onOk={handleOk}
      onCancel={handleCancel}
      width={900}
      okText={registrationStatus === 'idle' ? '确认添加' : '添加中...'}
      cancelText="取消"
      okButtonProps={{
        loading: registrationStatus === 'registering',
        disabled: registrationStatus !== 'idle',
      }}
      cancelButtonProps={{
        disabled: false, // 取消按钮始终可用
      }}
      maskClosable={registrationStatus === 'idle'} // 轮询期间禁止点击遮罩关闭
    >
      <Row gutter={24}>
        <Col span={12}>
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              registerToken: '',
            }}
          >
            <Form.Item
              label="节点名称"
              name="name"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input placeholder="worker-05" />
            </Form.Item>

            <Form.Item
              label="注册 Token"
              name="registerToken"
              rules={[{ required: true, message: '请生成注册 Token' }]}
            >
              <Input.Search
                placeholder="Token 已自动生成"
                readOnly
                enterButton={<Button type="primary" icon={<CopyOutlined />} />}
                onSearch={handleCopyToken}
              />
            </Form.Item>

            <Form.Item label="标签（可选）">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space.Compact style={{ width: '100%' }}>
                  <Input
                    placeholder="键 (如: gpu-type)"
                    value={labelKey}
                    onChange={(e) => setLabelKey(e.target.value)}
                  />
                  <Input
                    placeholder="值 (如: a100)"
                    value={labelValue}
                    onChange={(e) => setLabelValue(e.target.value)}
                  />
                  <Button onClick={handleAddLabel}>添加</Button>
                </Space.Compact>
                <div>
                  {Object.entries(labels).map(([key, value]) => (
                    <Tag
                      key={key}
                      closable
                      onClose={() => handleRemoveLabel(key)}
                    >
                      {key}={value}
                    </Tag>
                  ))}
                </div>
              </Space>
            </Form.Item>
          </Form>
        </Col>

        <Col span={12}>
          <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 8 }}>
            {registrationStatus === 'idle' && (
              <>
                <h4>Worker 注册流程：</h4>
                <ol style={{ paddingLeft: 20, marginTop: 8 }}>
                  <li>在 Worker 节点安装 agent</li>
                  <li>复制注册 Token</li>
                  <li>启动 Worker 服务</li>
                  <li>等待节点上线</li>
                </ol>

                <h4 style={{ marginTop: 16 }}>安装命令：</h4>
                <div
                  style={{
                    background: '#fff',
                    padding: 8,
                    borderRadius: 4,
                    fontFamily: 'monospace',
                    fontSize: 12,
                    marginTop: 8,
                    wordBreak: 'break-all',
                  }}
                >
                  {currentToken
                    ? `curl -sfL https://get.tokenmachine.io | bash -s -- ${currentToken}`
                    : 'curl -sfL https://get.tokenmachine.io | bash -s -- [TOKEN]'
                  }
                </div>

                <Button
                  type="primary"
                  icon={<CopyOutlined />}
                  onClick={handleCopyCommand}
                  style={{ marginTop: 8 }}
                >
                  复制安装命令
                </Button>

                <div style={{ marginTop: 16 }}>
                  <h4>预计上线时间：&lt; 1 分钟</h4>
                </div>
              </>
            )}

            {(registrationStatus === 'registering' || registrationStatus === 'waiting') && (
              <>
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <LoadingOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
                  <h4>正在等待 Worker 注册...</h4>
                  <p style={{ color: '#666', marginTop: 8 }}>
                    请在 Worker 节点上执行安装命令
                  </p>
                  <Progress
                    percent={Math.min(pollingCount * 10, 90)}
                    status="active"
                    style={{ marginTop: 16 }}
                  />
                  <p style={{ color: '#999', fontSize: 12, marginTop: 8 }}>
                    轮询检测中... ({pollingCount})
                  </p>
                </div>
              </>
            )}

            {registrationStatus === 'success' && (
              <>
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a', marginBottom: 16 }} />
                  <h4 style={{ color: '#52c41a' }}>Worker 注册成功！</h4>
                  <p style={{ color: '#666', marginTop: 8 }}>
                    节点已成功上线，窗口将自动关闭
                  </p>
                  <Progress
                    percent={100}
                    status="success"
                    style={{ marginTop: 16 }}
                  />
                </div>
              </>
            )}
          </div>
        </Col>
      </Row>
    </Modal>
  );
};

export default AddWorkerModal;

import { useState } from 'react';
import { Modal, Form, Input, Select, Button, Space, message, Row, Col, Tag } from 'antd';
import { CopyOutlined } from '@ant-design/icons';

interface AddWorkerModalProps {
  visible: boolean;
  onCancel: () => void;
  onOk: (worker: any) => void;
}

interface WorkerFormData {
  name: string;
  registerToken: string;
  labels: Record<string, string>;
}

const AddWorkerModal = ({ visible, onCancel, onOk }: AddWorkerModalProps) => {
  const [form] = Form.useForm();
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [labelKey, setLabelKey] = useState('');
  const [labelValue, setLabelValue] = useState('');

  const generateToken = () => {
    const token = 'tm_worker_' + Math.random().toString(36).substring(2, 15) +
                  Math.random().toString(36).substring(2, 15);
    form.setFieldValue('registerToken', token);
  };

  const handleCopyToken = () => {
    const token = form.getFieldValue('registerToken');
    navigator.clipboard.writeText(token);
    message.success('Token 已复制到剪贴板');
  };

  const handleCopyCommand = () => {
    const token = form.getFieldValue('registerToken');
    const command = `curl -sfL https://get.tokenmachine.io | bash -s -- ${token}`;
    navigator.clipboard.writeText(command);
    message.success('安装命令已复制到剪贴板');
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
    try {
      const values = await form.validateFields();
      onOk({
        name: values.name,
        ip: '192.168.1.' + Math.floor(Math.random() * 254 + 1),
        labels: labels,
        gpu_count: 4,
        gpu_memory_total: 160,
      });
      form.resetFields();
      setLabels({});
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setLabels({});
    onCancel();
  };

  return (
    <Modal
      title="添加 Worker 节点"
      open={visible}
      onOk={handleOk}
      onCancel={handleCancel}
      width={900}
      okText="确认添加"
      cancelText="取消"
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
              extra={
                <Button type="link" onClick={generateToken} style={{ paddingLeft: 0 }}>
                  生成新的 Token
                </Button>
              }
            >
              <Input.Search
                placeholder="点击生成 Token"
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
              curl -sfL https://get.tokenmachine.io | bash -s -- [TOKEN]
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
          </div>
        </Col>
      </Row>
    </Modal>
  );
};

export default AddWorkerModal;

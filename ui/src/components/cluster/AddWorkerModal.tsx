import { useState, useEffect, useRef } from 'react';
import { Modal, Form, Input, Button, Space, message, Row, Col, Tag, Progress, Steps } from 'antd';
import { CopyOutlined, CheckCircleOutlined, LoadingOutlined, ArrowRightOutlined } from '@ant-design/icons';
import api from '../../api/client';
import type { WorkerCreateResponse } from '../../api';

interface AddWorkerModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

interface WorkerFormData {
  name: string;
}

type StepType = 1 | 2 | 3;

const AddWorkerModal = ({ visible, onCancel, onSuccess }: AddWorkerModalProps) => {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState<StepType>(1);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [labelKey, setLabelKey] = useState('');
  const [labelValue, setLabelValue] = useState('');

  // Worker 创建相关
  const [workerData, setWorkerData] = useState<WorkerCreateResponse | null>(null);
  const [installCommand, setInstallCommand] = useState('');

  // 轮询相关
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pollingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [pollingCount, setPollingCount] = useState(0);
  const [isPolling, setIsPolling] = useState(false);

  // Mock: 已存在的 Worker 名称列表（暂时硬编码，实际应该从后端获取）
  const existingWorkerNames = useRef<Set<string>>(new Set(['worker-01', 'worker-02', 'gpu-node-01']));

  // 从浏览器获取主机地址
  const getBackendUrl = () => {
    const hostname = window.location.hostname;
    // 如果是本地开发，使用 localhost 或实际 IP
    // 如果是生产环境，使用当前域名
    return hostname === 'localhost' || hostname === '127.0.0.1'
      ? 'http://localhost:8000'
      : `http://${hostname}:8000`;
  };

  // 重置状态
  const resetModal = () => {
    setCurrentStep(1);
    setLabels({});
    setLabelKey('');
    setLabelValue('');
    setWorkerData(null);
    setInstallCommand('');
    setPollingCount(0);
    setIsPolling(false);
    form.resetFields();

    // 清理定时器
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
  };

  // Modal 关闭时重置
  useEffect(() => {
    if (!visible) {
      resetModal();
    }
  }, [visible]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
      }
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
      }
    };
  }, []);

  // 第一步：创建 Worker（使用 Mock 数据）
  const handleCreateWorker = async () => {
    try {
      const values = await form.validateFields();
      const workerName = values.name;

      // Mock: 检查 Worker 名称是否已存在
      // TODO: 下个版本改为调用后端 API 检查
      if (existingWorkerNames.current.has(workerName)) {
        message.error(`Worker 名称 "${workerName}" 已存在，请使用其他名称`);
        return;
      }

      // Mock: 模拟 API 调用延迟
      message.loading({ content: '正在创建 Worker...', key: 'createWorker' });

      // Mock: 模拟创建 Worker
      await new Promise(resolve => setTimeout(resolve, 500));

      // Mock: 生成假的 Worker 数据
      const mockWorkerId = Math.floor(Math.random() * 10000) + 1000;
      const mockToken = `tm_worker_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;

      const mockWorkerData: WorkerCreateResponse = {
        id: mockWorkerId,
        name: workerName,
        status: 'REGISTERING',
        register_token: mockToken,
        expected_gpu_count: 0,
        current_gpu_count: 0,
        created_at: new Date().toISOString(),
      };

      setWorkerData(mockWorkerData);

      // 生成安装命令
      const backendUrl = getBackendUrl();
      const command = `curl -sfL ${backendUrl}/install.sh | bash -s -- ${mockToken}`;
      setInstallCommand(command);

      // 添加到已存在列表（Mock）
      existingWorkerNames.current.add(workerName);

      message.success({ content: 'Worker 创建成功（Mock），请复制安装命令', key: 'createWorker' });

      // 进入第二步
      setCurrentStep(2);
    } catch (error: any) {
      console.error('创建 Worker 失败:', error);
      if (error.message) {
        message.error(error.message);
      } else {
        message.error('创建 Worker 失败，请重试');
      }
    }
  };

  // 第二步：开始轮询
  const handleStartPolling = () => {
    setCurrentStep(3);
    startPolling();
  };

  // 开始轮询 Worker 状态（使用 Mock）
  const startPolling = () => {
    if (!workerData) return;

    setIsPolling(true);
    setPollingCount(0);

    // 设置 3 分钟超时
    pollingTimeoutRef.current = setTimeout(() => {
      handlePollingTimeout();
    }, 3 * 60 * 1000); // 3 分钟

    // Mock: 每 2 秒轮询一次，模拟第 5 次成功
    pollingTimerRef.current = setInterval(async () => {
      try {
        // TODO: 下个版本改为调用真实 API: api.get<Worker>(`/workers/${workerData.id}`)
        setPollingCount(prev => {
          const newCount = prev + 1;

          // Mock: 模拟第 5 次轮询时 Worker 上线
          if (newCount >= 5) {
            handlePollingSuccess();
          }

          return newCount;
        });
      } catch (error) {
        console.error('轮询 Worker 状态失败:', error);
      }
    }, 2000);
  };

  // 轮询成功
  const handlePollingSuccess = () => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    setIsPolling(false);
    message.success('Worker 注册成功！');

    // 1.5 秒后关闭 Modal 并刷新列表
    setTimeout(() => {
      handleCancel();
      onSuccess();
    }, 1500);
  };

  // 轮询超时
  const handlePollingTimeout = () => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }

    setIsPolling(false);
    message.warning('Worker 注册超时（3 分钟），请检查节点状态或联系管理员');
  };

  // 复制安装命令
  const handleCopyCommand = () => {
    navigator.clipboard.writeText(installCommand);
    message.success('安装命令已复制到剪贴板');
  };

  // 添加标签
  const handleAddLabel = () => {
    if (labelKey && labelValue) {
      setLabels({ ...labels, [labelKey]: labelValue });
      setLabelKey('');
      setLabelValue('');
    }
  };

  // 删除标签
  const handleRemoveLabel = (key: string) => {
    const newLabels = { ...labels };
    delete newLabels[key];
    setLabels(newLabels);
  };

  // 返回上一步
  const handleBack = () => {
    setCurrentStep(prev => (prev > 1 ? (prev - 1) as StepType : 1));
  };

  // 取消/关闭
  const handleCancel = () => {
    if (isPolling) {
      Modal.confirm({
        title: '确认取消？',
        content: 'Worker 正在注册中，取消将中断轮询流程',
        onOk: () => {
          resetModal();
          onCancel();
        },
      });
    } else {
      resetModal();
      onCancel();
    }
  };

  // 渲染第一步：输入信息
  const renderStep1 = () => (
    <Row gutter={24}>
      <Col span={24}>
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            label="节点名称"
            name="name"
            rules={[
              { required: true, message: '请输入节点名称' },
              { pattern: /^[a-zA-Z0-9-_]+$/, message: '只能包含字母、数字、横线和下划线' },
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve();
                  // Mock: 检查 Worker 名称是否已存在
                  // TODO: 下个版本改为调用后端 API 检查
                  if (existingWorkerNames.current.has(value)) {
                    return Promise.reject(new Error(`Worker 名称 "${value}" 已存在`));
                  }
                  return Promise.resolve();
                }
              }
            ]}
            validateTrigger={['onChange', 'onBlur']}
          >
            <Input placeholder="worker-05" />
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
    </Row>
  );

  // 渲染第二步：显示安装命令
  const renderStep2 = () => (
    <Row gutter={24}>
      <Col span={24}>
        <div style={{ marginBottom: 24 }}>
          <h4>Worker 注册 Token：</h4>
          <Input
            value={workerData?.register_token || ''}
            readOnly
            style={{ marginBottom: 8 }}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <h4>安装步骤：</h4>
          <ol style={{ paddingLeft: 20, marginTop: 8 }}>
            <li>复制下方安装命令</li>
            <li>在 Worker 节点终端中执行命令</li>
            <li>等待 agent 安装完成</li>
            <li>点击"下一步"开始轮询节点状态</li>
          </ol>
        </div>

        <div style={{ marginBottom: 16 }}>
          <h4>安装命令：</h4>
          <div
            style={{
              background: '#f5f5f5',
              padding: 12,
              borderRadius: 4,
              fontFamily: 'monospace',
              fontSize: 12,
              marginTop: 8,
              wordBreak: 'break-all',
              border: '1px solid #d9d9d9',
            }}
          >
            {installCommand}
          </div>
          <Button
            type="primary"
            icon={<CopyOutlined />}
            onClick={handleCopyCommand}
            style={{ marginTop: 8 }}
          >
            复制安装命令
          </Button>
        </div>
      </Col>
    </Row>
  );

  // 渲染第三步：轮询状态
  const renderStep3 = () => (
    <Row gutter={24}>
      <Col span={24}>
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          {!isPolling ? (
            <>
              <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a', marginBottom: 16 }} />
              <h4 style={{ color: '#52c41a', fontSize: 18 }}>Worker 注册成功！</h4>
              <p style={{ color: '#666', marginTop: 8 }}>
                节点已成功上线
              </p>
            </>
          ) : (
            <>
              <LoadingOutlined style={{ fontSize: 64, color: '#1890ff', marginBottom: 16 }} />
              <h4>正在等待 Worker 上线...</h4>
              <p style={{ color: '#666', marginTop: 8 }}>
                请在 Worker 节点上执行安装命令
              </p>
              <Progress
                percent={Math.min(pollingCount * 5, 90)}
                status="active"
                style={{ marginTop: 24, marginBottom: 16 }}
              />
              <p style={{ color: '#999', fontSize: 12 }}>
                已轮询 {pollingCount} 次（超时时间：3 分钟）
              </p>
              <p style={{ color: '#999', fontSize: 12 }}>
                Worker 状态：{workerData?.status || 'REGISTERING'}
              </p>
            </>
          )}
        </div>
      </Col>
    </Row>
  );

  // 步骤配置
  const steps = [
    { title: '输入信息' },
    { title: '获取命令' },
    { title: '等待上线' },
  ];

  return (
    <Modal
      title="添加 Worker 节点"
      open={visible}
      onCancel={handleCancel}
      width={800}
      footer={null}
      maskClosable={!isPolling}
    >
      <Steps current={currentStep - 1} style={{ marginBottom: 32 }}>
        {steps.map((step, index) => (
          <Steps.Step key={index} title={step.title} />
        ))}
      </Steps>

      {currentStep === 1 && renderStep1()}

      {currentStep === 2 && renderStep2()}

      {currentStep === 3 && renderStep3()}

      {/* 底部按钮 */}
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Space>
          {currentStep > 1 && currentStep !== 3 && (
            <Button onClick={handleBack}>
              上一步
            </Button>
          )}
          <Button onClick={handleCancel} disabled={isPolling}>
            取消
          </Button>
          {currentStep === 1 && (
            <Button type="primary" onClick={handleCreateWorker}>
              下一步
              <ArrowRightOutlined />
            </Button>
          )}
          {currentStep === 2 && (
            <Button type="primary" onClick={handleStartPolling}>
              下一步
              <ArrowRightOutlined />
            </Button>
          )}
        </Space>
      </div>
    </Modal>
  );
};

export default AddWorkerModal;

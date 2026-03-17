import { useState } from 'react';
import { Card, Form, Input, Button, Checkbox, message, Space } from 'antd';
import { UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import Logo from '../components/common/Logo';

const Login = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (values: { username: string; password: string; remember?: boolean }) => {
    setLoading(true);

    try {
      // 模拟登录请求
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // 简单的模拟验证
      if (values.username === 'admin' && values.password === 'admin123') {
        message.success('登录成功');
        // 保存token到localStorage
        localStorage.setItem('token', 'mock-jwt-token');
        localStorage.setItem('user', JSON.stringify({ username: values.username }));
        // 跳转到首页
        navigate('/dashboard');
      } else {
        message.error('用户名或密码错误');
      }
    } catch (error) {
      message.error('登录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: 24,
      }}
    >
      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo和标题 */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              marginBottom: 24,
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <Logo
              size={100}
              variant="full"
              showText={true}
              textColor="#fff"
              backgroundColor="#fff"
            />
          </div>
          <p
            style={{
              color: 'rgba(255,255,255,0.85)',
              fontSize: 14,
              marginTop: 8,
              textShadow: '0 1px 2px rgba(0,0,0,0.1)',
            }}
          >
            企业级 AI 模型部署管理平台
          </p>
        </div>

        {/* 登录卡片 */}
        <Card
          style={{
            boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
            borderRadius: 12,
            border: 'none',
          }}
          styles={{
            body: { padding: '40px 32px' },
          }}
        >
          <Form
            form={form}
            name="login"
            onFinish={handleLogin}
            initialValues={{ remember: false }}
            size="large"
            layout="vertical"
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3个字符' },
              ]}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'rgba(0,0,0,0.25)' }} />}
                placeholder="用户名"
                autoComplete="username"
                style={{
                  borderRadius: 8,
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'rgba(0,0,0,0.25)' }} />}
                placeholder="密码"
                autoComplete="current-password"
                visibilityToggle={{
                  visible: passwordVisible,
                  onVisibleChange: setPasswordVisible,
                }}
                iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
                style={{
                  borderRadius: 8,
                }}
              />
            </Form.Item>

            <Form.Item>
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>记住密码</Checkbox>
              </Form.Item>
              <a style={{ float: 'right' }} href="#" onClick={(e) => e.preventDefault()}>
                忘记密码？
              </a>
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{
                  height: 44,
                  borderRadius: 8,
                  fontSize: 16,
                  fontWeight: 500,
                }}
              >
                {loading ? '登录中...' : '登 录'}
              </Button>
            </Form.Item>
          </Form>

          <div style={{ marginTop: 24, paddingTop: 24, borderTop: '1px solid #f0f0f0' }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div style={{ textAlign: 'center', color: '#8c8c8c', fontSize: 12 }}>
                <p style={{ margin: 0 }}>测试账号：admin / admin123</p>
              </div>
            </Space>
          </div>
        </Card>

        {/* 底部版权信息 */}
        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <p style={{ color: 'rgba(255,255,255,0.75)', fontSize: 12, margin: 0 }}>
            © 2024 TokenMachine. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;

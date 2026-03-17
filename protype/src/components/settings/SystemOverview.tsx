import { Row, Col, Card, Statistic, Progress, Tag, List, Typography, Space } from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

const SystemOverview = () => {
  const alarms = [
    {
      type: 'warning',
      icon: <WarningOutlined style={{ color: '#faad14' }} />,
      content: 'worker-03 GPU 温度过高 (85°C)',
      time: '5分钟前',
    },
    {
      type: 'success',
      icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      content: '已恢复: worker-03 GPU 温度正常',
      time: '2分钟前',
    },
  ];

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="用户总数" value={128} suffix="人" />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="在线用户" value={45} suffix="人" styles={{ content: { color: '#3f8600' } }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="部署数" value={24} suffix="个" />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="API 调用" value={1200000} suffix="/天" />
          </Card>
        </Col>
      </Row>

      <Card title="系统健康状态" style={{ marginTop: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <div>
            <Text strong>API 服务：</Text>
            <Tag color="success" icon={<CheckCircleOutlined />}>
              正常 (99.9% 可用)
            </Tag>
          </div>
          <div>
            <Text strong>数据库：</Text>
            <Tag color="success" icon={<CheckCircleOutlined />}>
              正常 (延迟 12ms)
            </Tag>
          </div>
          <div>
            <Text strong>Redis：</Text>
            <Tag color="success" icon={<CheckCircleOutlined />}>
              正常 (内存使用 45%)
            </Tag>
          </div>
          <div>
            <Text strong>Worker 集群：</Text>
            <Tag color="success" icon={<CheckCircleOutlined />}>
              正常 (8/8 节点在线)
            </Tag>
          </div>
          <div>
            <Text strong>监控服务：</Text>
            <Tag color="success" icon={<CheckCircleOutlined />}>
              正常
            </Tag>
          </div>
        </Space>
      </Card>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="资源使用情况">
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <div>
                <Text strong>GPU：</Text>
                <Progress percent={79} status="active" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  76/96 (79%)
                </Text>
              </div>
              <div>
                <Text strong>内存：</Text>
                <Progress percent={50} status="active" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  256GB/512GB
                </Text>
              </div>
              <div>
                <Text strong>磁盘：</Text>
                <Progress percent={60} status="active" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  1.2TB/2TB
                </Text>
              </div>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="存储使用情况">
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <div>
                <Text strong>模型存储：</Text>
                <Progress percent={45} status="active" strokeColor="#1890ff" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  450GB / 1TB
                </Text>
              </div>
              <div>
                <Text strong>日志存储：</Text>
                <Progress percent={12} status="active" strokeColor="#52c41a" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  12GB / 100GB
                </Text>
              </div>
              <div>
                <Text strong>备份存储：</Text>
                <Progress percent={40} status="active" strokeColor="#faad14" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  80GB / 200GB
                </Text>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card
        title="最近告警"
        style={{ marginTop: 16 }}
        extra={<a href="#">查看全部</a>}
      >
        <List
          size="small"
          dataSource={alarms}
          renderItem={(item) => (
            <List.Item>
              <Space>
                {item.icon}
                <Text>{item.content}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  <ClockCircleOutlined /> {item.time}
                </Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default SystemOverview;

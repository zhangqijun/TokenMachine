import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider, Layout } from 'antd';

const { Content } = Layout;

function App() {
  return (
    <ConfigProvider>
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <Content style={{ padding: '50px' }}>
            <h1>Router Test</h1>
            <p>React Router is working!</p>
          </Content>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;

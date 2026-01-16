import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import Models from './pages/models';
import Deployments from './pages/Deployments';
import Monitoring from './pages/Monitoring';
import ApiKeys from './pages/ApiKeys';
import Resources from './pages/Resources';
import Clusters from './pages/Clusters';
import Playground from './pages/Playground';
import Settings from './pages/Settings';

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
        components: {
          Layout: {
            headerBg: '#001529',
            siderBg: '#001529',
          },
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="models" element={<Models />} />
            <Route path="deployments" element={<Deployments />} />
            <Route path="resources" element={<Resources />} />
            <Route path="clusters" element={<Clusters />} />
            <Route path="playground" element={<Playground />} />
            <Route path="monitoring" element={<Monitoring />} />
            <Route path="api-keys" element={<ApiKeys />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import Models from './pages/Models';
import Deployments from './pages/Deployments';
import Monitoring from './pages/Monitoring';
import Gateway from './pages/Gateway';
import ClusterOverview from './pages/ClusterOverview';
import WorkerDetail from './pages/WorkerDetail';
import Playground from './pages/Playground';
import Settings from './pages/Settings';
import Login from './pages/Login';
import NodesDeployments from './pages/NodesDeployments';

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
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="nodes-deployments" element={<NodesDeployments />} />
            <Route path="models" element={<Models />} />
            <Route path="playground" element={<Playground />} />
            <Route path="deployments" element={<Deployments />} />
            <Route path="cluster" element={<ClusterOverview />} />
            <Route path="cluster/workers/:id" element={<WorkerDetail />} />
            <Route path="monitoring" element={<Monitoring />} />
            <Route path="gateway" element={<Gateway />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;

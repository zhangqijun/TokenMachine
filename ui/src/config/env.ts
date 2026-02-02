/**
 * Frontend configuration
 */
const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  apiTimeout: 30000,
  useMockData: import.meta.env.VITE_USE_MOCK_DATA === 'true',
};

export default config;

import { useState, useEffect } from 'react';
import { Row, Col, Card, Tag, Button, Input, Select, Space, Spin, Empty, Modal, Progress, Alert, Slider, InputNumber, Tooltip } from 'antd';
import { SearchOutlined, ThunderboltOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined, InfoCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons';

interface ModelCard {
  model_card_name: string;
  input_modality: string[];
  output_modality: string[];
  category: string[];
  description: string;
  fe_config: null | any;
  dimension: number;
  min_input_price: number;
  max_input_price: number;
  min_output_price: number;
  max_output_price: number;
  min_context_length: number;
  max_context_length: number;
  tags: string[];
  discount_rate: number;
  model_price_info: null | any;
  estimated_vram_gb: number;
  estimated_tps: number;
  params_b: number;
  quantization: string;
}

const Models = () => {
  const [models, setModels] = useState<ModelCard[]>([]);
  const [logos, setLogos] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [selectedSeries, setSelectedSeries] = useState('all');
  const [sortBy, setSortBy] = useState<'vram' | 'tps' | 'name'>('name');
  const [deployModalVisible, setDeployModalVisible] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelCard | null>(null);

  // 部署参数状态
  const [deployParams, setDeployParams] = useState({
    engine: 'vLLM',
    quantization: 'INT4',
    gpuMemoryUtil: 0.85,
    maxModelLen: 8192,
    tensorParallelSize: 1,
    batchSize: 32,
  });

  // 当前节点的GPU显存大小（GB）- 模拟数据
  const currentNodeVRAM = 24;

  // 获取模型系列
  const getModelSeries = (name: string): string => {
    if (name.includes('DeepSeek')) return 'DeepSeek';
    if (name.includes('Qwen') || name.includes('QwQ')) return 'Qwen';
    if (name.includes('GLM')) return 'GLM';
    if (name.includes('Kimi')) return 'Kimi';
    if (name.includes('MiniMax')) return 'MiniMax';
    return '其他';
  };

  // 获取模型logo
  const getModelLogo = (name: string): string | undefined => {
    // 先尝试精确匹配
    if (logos[name]) return logos[name];

    // 提取系列名称匹配
    const series = name.split('-')[0];
    if (logos[series]) return logos[series];

    // 特殊处理
    if (name.includes('Qwen') || name.includes('QwQ')) return logos['Qwen'];
    if (name.includes('DeepSeek')) return logos['DeepSeek'];
    if (name.includes('GLM')) return logos['GLM'];
    if (name.includes('Kimi')) return logos['Kimi'];
    if (name.includes('MiniMax')) return logos['MiniMax'];

    return undefined;
  };

  useEffect(() => {
    // 加载模型数据和logo数据
    Promise.all([
      fetch('/data/model_card.json').then(res => res.json()),
      fetch('/data/model_logos.json').then(res => res.json())
    ])
      .then(([modelData, logoData]) => {
        setModels(modelData);
        setLogos(logoData);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load data:', err);
        setLoading(false);
      });
  }, []);

  // 获取所有系列及数量
  const seriesList = ['all', 'DeepSeek', 'Qwen', 'GLM', 'Kimi', 'MiniMax'];

  const getSeriesCount = (series: string) => {
    if (series === 'all') return models.length;
    return models.filter(m => getModelSeries(m.model_card_name) === series).length;
  };

  // 过滤和排序
  const filteredModels = models
    .filter(m => {
      const matchSearch = m.model_card_name.toLowerCase().includes(searchText.toLowerCase()) ||
                         m.description.toLowerCase().includes(searchText.toLowerCase());
      const matchSeries = selectedSeries === 'all' || getModelSeries(m.model_card_name) === selectedSeries;
      return matchSearch && matchSeries;
    })
    .sort((a, b) => {
      if (sortBy === 'vram') {
        return a.estimated_vram_gb - b.estimated_vram_gb;
      } else if (sortBy === 'tps') {
        return b.estimated_tps - a.estimated_tps;
      }
      return a.model_card_name.localeCompare(b.model_card_name);
    });

  // 格式化上下文长度
  const formatContext = (length: number) => {
    if (length >= 1000000) return `${(length / 1000000).toFixed(1)}M`;
    if (length >= 1000) return `${(length / 1000).toFixed(0)}K`;
    return length.toString();
  };

  // 格式化显存大小
  const formatVRAM = (vram: number) => {
    return `${vram.toFixed(1)} GB`;
  };

  // 格式化TPS
  const formatTPS = (tps: number) => {
    return `${tps.toFixed(1)} tok/s`;
  };

  // 判断模型是否可以部署
  const canDeploy = (model: ModelCard) => {
    return model.estimated_vram_gb <= currentNodeVRAM;
  };

  // 分析部署适配性
  const analyzeDeployment = (model: ModelCard, params: typeof deployParams) => {
    // 根据量化方式重新计算显存需求
    let vramMultiplier = 1;
    if (params.quantization === 'FP16') {
      vramMultiplier = 2.5;
    } else if (params.quantization === 'INT8') {
      vramMultiplier = 1.2;
    } else if (params.quantization === 'INT4') {
      vramMultiplier = 0.6;
    }

    // 基础显存需求
    let baseVRAM = model.params_b * vramMultiplier;

    // 加上上下文长度的KV cache开销
    const kvCacheOverhead = (params.maxModelLen / 1000) * 0.1; // 每增加1K上下文约0.1GB
    const totalVRAM = baseVRAM + kvCacheOverhead;

    // 考虑GPU显存利用率
    const effectiveVRAM = currentNodeVRAM * params.gpuMemoryUtil;
    const vramUtilization = (totalVRAM / effectiveVRAM) * 100;

    let fitLevel: 'perfect' | 'good' | 'marginal' | 'insufficient';
    let runMode: string;

    // 判断适配等级
    if (vramUtilization <= 60) {
      fitLevel = 'perfect';
      runMode = 'GPU 纯显存推理';
    } else if (vramUtilization <= 80) {
      fitLevel = 'good';
      runMode = 'GPU 纯显存推理';
    } else if (vramUtilization <= 100) {
      fitLevel = 'marginal';
      runMode = 'GPU 显存 + CPU 卸载';
    } else {
      fitLevel = 'insufficient';
      runMode = '无法部署';
    }

    // 重新计算TPS（基于参数调整）
    let tpsMultiplier = 1;
    if (params.quantization === 'INT4') {
      tpsMultiplier = 1.0;
    } else if (params.quantization === 'INT8') {
      tpsMultiplier = 0.7;
    } else if (params.quantization === 'FP16') {
      tpsMultiplier = 0.5;
    }

    // 批处理大小影响
    const batchMultiplier = Math.min(1.5, 1 + (params.batchSize - 32) / 100);

    const estimatedTPS = model.estimated_tps * tpsMultiplier * batchMultiplier;

    return {
      fitLevel,
      vramUtilization,
      runMode,
      totalVRAM,
      effectiveVRAM,
      estimatedTPS,
    };
  };

  // 获取推荐参数
  const getRecommendedParams = (model: ModelCard) => {
    const baseUtil = Math.min(0.9, (model.estimated_vram_gb / currentNodeVRAM) * 1.15);
    const maxLen = model.max_context_length;

    return {
      engine: baseUtil > 0.9 ? 'llama.cpp' : 'vLLM',
      quantization: model.quantization || 'INT4',
      gpuMemoryUtil: Math.min(0.9, baseUtil),
      maxModelLen: maxLen > 32000 ? 8192 : maxLen,
      tensorParallelSize: 1,
      batchSize: 32,
    };
  };

  // 打开部署分析Modal
  const handleDeploy = (model: ModelCard) => {
    setSelectedModel(model);
    // 设置推荐参数
    const recommended = getRecommendedParams(model);
    setDeployParams(recommended);
    setDeployModalVisible(true);
  };

  // 获取模态图标
  const getModalityIcon = (modality: string[]) => {
    if (modality.includes('图片')) return '🖼️';
    if (modality.includes('音频')) return '🎵';
    return '📝';
  };

  // 获取标签颜色
  const getTagColor = (tag: string) => {
    const colors: Record<string, string> = {
      '推理': '#1890ff',
      '工具调用 Tools': '#52c41a',
      '视觉 Vision': '#722ed1',
      '代码': '#fa8c16',
      '长文本': '#13c2c2',
    };
    return colors[tag] || '#8c8c8c';
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <Spin size="large" tip="加载模型数据..." />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      {/* 顶部标题和搜索栏 */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: '0 0 16px 0', fontSize: 28, fontWeight: 600, color: '#262626' }}>
          模型列表
        </h1>

        <Space size={16} wrap>
          {/* 搜索框 */}
          <Input
            placeholder="搜索模型名称或描述..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{ width: 300, borderRadius: 8 }}
            allowClear
          />

          {/* 排序 */}
          <Select
            value={sortBy}
            onChange={setSortBy}
            style={{ width: 150, borderRadius: 8 }}
          >
            <Select.Option value="name">按名称排序</Select.Option>
            <Select.Option value="vram">按显存排序</Select.Option>
            <Select.Option value="tps">按速度排序</Select.Option>
          </Select>
        </Space>
      </div>

      {/* 系列筛选标签 - 放在最上面 */}
      <div style={{ marginBottom: 24, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {seriesList.map(series => (
          <Button
            key={series}
            type={selectedSeries === series ? 'primary' : 'default'}
            onClick={() => setSelectedSeries(series)}
            style={{
              borderRadius: 16,
              height: 36,
              minWidth: 100,
              fontSize: 14,
              fontWeight: selectedSeries === series ? 600 : 400,
            }}
          >
            {series === 'all' ? '全部' : series}
            <span style={{ marginLeft: 8, opacity: 0.8 }}>({getSeriesCount(series)})</span>
          </Button>
        ))}
      </div>

      {/* 模型统计和节点信息 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ color: '#8c8c8c' }}>
          共找到 <span style={{ color: '#1890ff', fontWeight: 600 }}>{filteredModels.length}</span> 个模型，
          可部署 <span style={{ color: '#52c41a', fontWeight: 600 }}>{filteredModels.filter(m => canDeploy(m)).length}</span> 个
        </div>
        <div style={{ color: '#8c8c8c', fontSize: 13 }}>
          当前节点显存: <span style={{ color: '#1890ff', fontWeight: 600 }}>{currentNodeVRAM} GB</span>
        </div>
      </div>

      {/* 模型卡片网格 */}
      {filteredModels.length === 0 ? (
        <Empty description="未找到匹配的模型" style={{ marginTop: 100 }} />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredModels.map((model, index) => (
            <Col xs={24} sm={12} md={8} lg={6} key={index}>
              <Card
                hoverable
                style={{
                  borderRadius: 12,
                  border: '1px solid #e8e8e8',
                  transition: 'all 0.3s',
                  height: '100%',
                }}
                styles={{ body: { padding: 20 } }}
              >
                {/* 模型名称和Logo */}
                <div style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    {getModelLogo(model.model_card_name) ? (
                      <img
                        src={getModelLogo(model.model_card_name)}
                        alt={model.model_card_name}
                        style={{ width: 32, height: 32, objectFit: 'contain' }}
                      />
                    ) : (
                      <span style={{ fontSize: 24 }}>{getModalityIcon(model.input_modality)}</span>
                    )}
                    <div style={{ fontSize: 16, fontWeight: 600, color: '#262626', flex: 1 }}>
                      {model.model_card_name}
                    </div>
                  </div>

                  {/* 分类标签 */}
                  <Space size={[4, 8]} wrap>
                    {model.category.map((cat, i) => (
                      <Tag key={i} color="blue" style={{ borderRadius: 4, fontSize: 12 }}>
                        {cat}
                      </Tag>
                    ))}
                  </Space>
                </div>

                {/* 模型描述 */}
                <div
                  style={{
                    marginBottom: 16,
                    fontSize: 13,
                    color: '#8c8c8c',
                    lineHeight: 1.6,
                    minHeight: 44,
                    overflow: 'hidden',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                  }}
                >
                  {model.description}
                </div>

                {/* 显存、TPS和上下文信息 */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: '#8c8c8c' }}>显存需求:</span>
                    <span style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: canDeploy(model) ? '#52c41a' : '#ff4d4f'
                    }}>
                      {formatVRAM(model.estimated_vram_gb)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: '#8c8c8c' }}>预估速度:</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#1890ff' }}>
                      {formatTPS(model.estimated_tps)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, color: '#8c8c8c' }}>上下文长度:</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#722ed1' }}>
                      {formatContext(model.max_context_length)}
                    </span>
                  </div>
                </div>

                {/* 功能标签 */}
                {model.tags && model.tags.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <Space size={[4, 8]} wrap>
                      {model.tags.map((tag, i) => (
                        <Tag
                          key={i}
                          style={{
                            borderRadius: 4,
                            background: `${getTagColor(tag)}15`,
                            color: getTagColor(tag),
                            border: `1px solid ${getTagColor(tag)}30`,
                            fontSize: 12,
                          }}
                        >
                          {tag}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}

                {/* 操作按钮 */}
                <Button
                  type="primary"
                  block
                  icon={<ThunderboltOutlined />}
                  disabled={!canDeploy(model)}
                  onClick={() => handleDeploy(model)}
                  style={{
                    borderRadius: 8,
                    height: 40,
                    fontSize: 14,
                  }}
                >
                  {canDeploy(model) ? '立即部署' : '显存不足'}
                </Button>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 部署配置Modal */}
      <Modal
        title={null}
        open={deployModalVisible}
        onCancel={() => setDeployModalVisible(false)}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        {selectedModel && (
          <div>
            {/* 模型标题 */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              marginBottom: 24,
              paddingBottom: 16,
              borderBottom: '1px solid #f0f0f0'
            }}>
              {getModelLogo(selectedModel.model_card_name) ? (
                <img
                  src={getModelLogo(selectedModel.model_card_name)}
                  alt={selectedModel.model_card_name}
                  style={{ width: 40, height: 40, objectFit: 'contain' }}
                />
              ) : (
                <span style={{ fontSize: 32 }}>{getModalityIcon(selectedModel.input_modality)}</span>
              )}
              <div style={{ flex: 1 }}>
                <h2 style={{ margin: 0, fontSize: 20 }}>{selectedModel.model_card_name}</h2>
                <div style={{ fontSize: 13, color: '#8c8c8c', marginTop: 4 }}>
                  {selectedModel.params_b}B 参数 · {selectedModel.category.join(' · ')}
                </div>
              </div>
              <Button
                size="small"
                onClick={() => {
                  const recommended = getRecommendedParams(selectedModel);
                  setDeployParams(recommended);
                }}
              >
                恢复推荐值
              </Button>
            </div>

            {(() => {
              const analysis = analyzeDeployment(selectedModel, deployParams);

              return (
                <Row gutter={24}>
                  {/* 左侧：参数配置 */}
                  <Col span={14}>
                    <h3 style={{ marginBottom: 16 }}><InfoCircleOutlined style={{ marginRight: 8, color: '#1890ff' }} />部署参数配置</h3>

                    <div style={{ marginBottom: 20 }}>
                      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>推理引擎</span>
                        <Tooltip title="选择推理引擎。vLLM适合高吞吐量，llama.cpp适合低资源场景">
                          <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c', fontSize: 12 }} />
                        </Tooltip>
                      </div>
                      <Select
                        value={deployParams.engine}
                        onChange={(value) => setDeployParams({ ...deployParams, engine: value })}
                        style={{ width: '100%' }}
                        options={[
                          { label: 'vLLM - 高吞吐量优化', value: 'vLLM' },
                          { label: 'SGLang - 结构化生成', value: 'SGLang' },
                          { label: 'llama.cpp - 轻量级', value: 'llama.cpp' },
                        ]}
                      />
                    </div>

                    <div style={{ marginBottom: 20 }}>
                      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>量化方式</span>
                        <Tooltip title="量化精度。INT4最省显存但精度略降，FP16精度最高但显存占用大">
                          <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c', fontSize: 12 }} />
                        </Tooltip>
                      </div>
                      <Select
                        value={deployParams.quantization}
                        onChange={(value) => setDeployParams({ ...deployParams, quantization: value })}
                        style={{ width: '100%' }}
                        options={[
                          { label: 'INT4 - 4bit量化（推荐）', value: 'INT4' },
                          { label: 'INT8 - 8bit量化', value: 'INT8' },
                          { label: 'FP16 - 半精度浮点', value: 'FP16' },
                        ]}
                      />
                    </div>

                    <div style={{ marginBottom: 20 }}>
                      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <span style={{ fontSize: 13, fontWeight: 500 }}>GPU显存利用率</span>
                          <Tooltip title="分配给模型的显存比例。建议0.8-0.9之间">
                            <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c', fontSize: 12 }} />
                          </Tooltip>
                        </div>
                        <span style={{ fontSize: 14, fontWeight: 600, color: '#1890ff' }}>
                          {deployParams.gpuMemoryUtil.toFixed(2)}
                        </span>
                      </div>
                      <Slider
                        min={0.5}
                        max={0.95}
                        step={0.01}
                        value={deployParams.gpuMemoryUtil}
                        onChange={(value) => setDeployParams({ ...deployParams, gpuMemoryUtil: value })}
                        marks={{ 0.5: '50%', 0.75: '75%', 0.9: '90%', 0.95: '95%' }}
                      />
                    </div>

                    <div style={{ marginBottom: 20 }}>
                      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>最大上下文长度</span>
                        <Tooltip title="模型支持的最大token数。越大显存占用越多">
                          <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c', fontSize: 12 }} />
                        </Tooltip>
                      </div>
                      <Select
                        value={deployParams.maxModelLen}
                        onChange={(value) => setDeployParams({ ...deployParams, maxModelLen: value })}
                        style={{ width: '100%' }}
                        options={[
                          { label: '4,096 tokens', value: 4096 },
                          { label: '8,192 tokens（推荐）', value: 8192 },
                          { label: '16,384 tokens', value: 16384 },
                          { label: '32,768 tokens', value: 32768 },
                          { label: '65,536 tokens', value: 65536 },
                        ]}
                      />
                    </div>

                    <div style={{ marginBottom: 20 }}>
                      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>张量并行度</span>
                        <Tooltip title="多GPU并行数量。单卡设为1">
                          <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c', fontSize: 12 }} />
                        </Tooltip>
                      </div>
                      <InputNumber
                        min={1}
                        max={8}
                        value={deployParams.tensorParallelSize}
                        onChange={(value) => setDeployParams({ ...deployParams, tensorParallelSize: value || 1 })}
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div style={{ marginBottom: 20 }}>
                      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>批处理大小</span>
                        <Tooltip title="并发处理的请求数。越大吞吐量越高但显存占用也增加">
                          <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c', fontSize: 12 }} />
                        </Tooltip>
                      </div>
                      <InputNumber
                        min={1}
                        max={256}
                        value={deployParams.batchSize}
                        onChange={(value) => setDeployParams({ ...deployParams, batchSize: value || 32 })}
                        style={{ width: '100%' }}
                      />
                    </div>
                  </Col>

                  {/* 右侧：实时分析 */}
                  <Col span={10}>
                    <h3 style={{ marginBottom: 16 }}>
                      {analysis.fitLevel === 'perfect' && <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />}
                      {analysis.fitLevel === 'good' && <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />}
                      {analysis.fitLevel === 'marginal' && <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />}
                      {analysis.fitLevel === 'insufficient' && <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />}
                      实时分析
                    </h3>

                    {/* 显存使用情况 */}
                    <div style={{ background: '#fafafa', padding: 16, borderRadius: 8, marginBottom: 16 }}>
                      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 13 }}>显存需求：</span>
                        <span style={{ fontSize: 14, fontWeight: 600, color: analysis.fitLevel === 'insufficient' ? '#ff4d4f' : '#262626' }}>
                          {formatVRAM(analysis.totalVRAM)}
                        </span>
                      </div>
                      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 13 }}>可用显存：</span>
                        <span style={{ fontSize: 14, fontWeight: 600 }}>{formatVRAM(analysis.effectiveVRAM)}</span>
                      </div>
                      <Progress
                        percent={analysis.vramUtilization}
                        strokeColor={
                          analysis.fitLevel === 'perfect' ? '#52c41a' :
                          analysis.fitLevel === 'good' ? '#52c41a' :
                          analysis.fitLevel === 'marginal' ? '#faad14' : '#ff4d4f'
                        }
                        format={() => `${analysis.vramUtilization.toFixed(1)}%`}
                      />
                    </div>

                    {/* 适配状态 */}
                    {analysis.fitLevel === 'insufficient' && (
                      <Alert
                        message="显存不足"
                        description="请降低GPU显存利用率、选择更低的量化精度或减少上下文长度"
                        type="error"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                    )}

                    {analysis.fitLevel === 'marginal' && (
                      <Alert
                        message="显存紧张"
                        description="当前配置接近显存上限，建议适当调整参数"
                        type="warning"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                    )}

                    {/* 性能预估 */}
                    <div style={{ background: '#f0f5ff', padding: 16, borderRadius: 8, marginBottom: 16 }}>
                      <div style={{ fontSize: 13, color: '#8c8c8c', marginBottom: 8 }}>预估性能</div>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <span style={{ fontSize: 28, fontWeight: 600, color: '#1890ff' }}>
                          {analysis.estimatedTPS.toFixed(1)}
                        </span>
                        <span style={{ fontSize: 14, color: '#8c8c8c' }}>tokens/s</span>
                      </div>
                    </div>

                    {/* 运行模式 */}
                    <div style={{ background: '#f9f0ff', padding: 16, borderRadius: 8 }}>
                      <div style={{ fontSize: 13, color: '#8c8c8c', marginBottom: 8 }}>运行模式</div>
                      <div style={{ fontSize: 14, fontWeight: 500 }}>{analysis.runMode}</div>
                    </div>
                  </Col>
                </Row>
              );
            })()}

            {/* 操作按钮 */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
              <Button onClick={() => setDeployModalVisible(false)}>取消</Button>
              {(() => {
                const analysis = analyzeDeployment(selectedModel, deployParams);
                return analysis.fitLevel !== 'insufficient' && (
                  <Button type="primary" icon={<ThunderboltOutlined />}>
                    开始部署
                  </Button>
                );
              })()}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Models;

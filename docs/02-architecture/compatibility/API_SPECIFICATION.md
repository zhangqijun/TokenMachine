# 兼容性组件 API 规范

## 概述

本文档定义了兼容性组件的所有 API 端点、请求/响应格式和错误处理。

## 基础信息

- **Base URL**: `https://api.tokenmachine.example/api/v1`
- **认证方式**: JWT Bearer Token
- **Content-Type**: `application/json`
- **API 版本**: v1.0.0

---

## 端点列表

### 1. 兼容性检查

检查特定配置组合的兼容性。

**端点**: `POST /compatibility/check`

**权限**: 公开 (无需认证)

**请求参数**:
```json
{
  "backend": "vllm",                      // 必填: vllm | sglang | llamacpp
  "hardware_vendor": "NVIDIA",            // 必填: NVIDIA | AMD | Huawei | Intel
  "hardware_model": "H100",               // 必填: 硬件型号
  "hardware_count": 4,                    // 必填: GPU/NPU 数量
  "model_architecture": "llama",          // 可选: 模型架构
  "model_dtype": "float16",               // 可选: float16 | int8 | bfloat16
  "tensor_parallel_size": 4               // 可选: 张量并行度
}
```

**响应示例**:
```json
{
  "compatible": true,
  "confidence": "high",
  "verified_count": 12,
  "status": "compatible",
  "recommendations": {
    "tensor_parallel_size": 4,
    "gpu_memory_utilization": 0.9,
    "max_model_len": 4096,
    "features": ["prefix_caching", "speculative_decoding"]
  },
  "alternatives": [
    {
      "backend": "sglang",
      "reason": "有 8 条兼容记录，性能可能更优"
    }
  ],
  "warnings": [
    "在 8-GPU 配置下表现最佳",
    "建议启用 prefix_caching"
  ],
  "errors": []
}
```

**错误响应**:
```json
{
  "error": "InvalidRequest",
  "message": "hardware_model is required",
  "details": {
    "field": "hardware_model",
    "constraint": "required"
  }
}
```

---

### 2. 获取兼容性统计

获取兼容性数据的统计概览。

**端点**: `GET /compatibility/stats`

**权限**: 公开

**响应示例**:
```json
{
  "total_records": 1523,
  "by_backend": {
    "vllm": 856,
    "sglang": 445,
    "llamacpp": 222
  },
  "by_hardware": {
    "NVIDIA": 987,
    "AMD": 312,
    "Huawei": 156,
    "Intel": 68
  },
  "by_model": {
    "llama": 456,
    "qwen": 234,
    "falcon": 123,
    "mpt": 89
  },
  "compatibility_rate": 0.87
}
```

---

### 3. 查询兼容性记录

查询兼容性记录列表，支持分页和过滤。

**端点**: `GET /compatibility/records`

**权限**: 公开

**查询参数**:
- `backend` (string, optional): 后端框架名称
- `hardware_vendor` (string, optional): 硬件厂商
- `hardware_model` (string, optional): 硬件型号
- `model_architecture` (string, optional): 模型架构
- `status` (string, optional): compatible | partial | incompatible
- `page` (integer, optional): 页码，默认 1
- `page_size` (integer, optional): 每页数量，默认 20，最大 100

**请求示例**:
```
GET /compatibility/records?backend=vllm&hardware_vendor=NVIDIA&status=compatible&page=1&page_size=20
```

**响应示例**:
```json
{
  "total": 856,
  "page": 1,
  "page_size": 20,
  "records": [
    {
      "id": "rec_1234567890",
      "created_at": "2025-01-21T10:30:00Z",
      "metadata": {
        "source": "vllm_usage_stats",
        "confidence": "high",
        "verified": true
      },
      "backend": {
        "name": "vllm",
        "version": "v0.6.0"
      },
      "hardware": {
        "vendor": "NVIDIA",
        "model": "H100",
        "count": 8,
        "memory_per_device": 80,
        "architecture": "Hopper",
        "features": ["tensorcore", "bf16"]
      },
      "model": {
        "architecture": "llama",
        "dtype": "float16",
        "quantization": null,
        "parameters": "70B"
      },
      "config": {
        "tensor_parallel_size": 8,
        "pipeline_parallel_size": 1,
        "gpu_memory_utilization": 0.9,
        "max_model_len": 4096,
        "features": ["prefix_caching"]
      },
      "compatibility": {
        "status": "compatible",
        "openai_api_compatible": true,
        "batch_inference_supported": true,
        "notes": "Production tested"
      },
      "performance": {
        "tps": 145.6,
        "ttft_ms": 234.5,
        "memory_usage_gb": 624.5,
        "throughput": 12.3
      }
    }
  ]
}
```

---

### 4. 提交兼容性报告

提交用户测试的兼容性报告。

**端点**: `POST /compatibility/reports`

**权限**: 需要登录 (Bearer Token)

**请求参数**:
```json
{
  "backend": {
    "name": "vllm",
    "version": "v0.6.0"
  },
  "hardware": {
    "vendor": "NVIDIA",
    "model": "H100",
    "count": 4,
    "memory_per_device": 80,
    "architecture": "Hopper",
    "features": ["tensorcore"]
  },
  "model": {
    "name": "meta-llama/Llama-2-70b-hf",
    "architecture": "llama",
    "dtype": "float16",
    "quantization": "awq",
    "parameters": "70B"
  },
  "config": {
    "tensor_parallel_size": 4,
    "pipeline_parallel_size": 1,
    "gpu_memory_utilization": 0.9,
    "max_model_len": 4096
  },
  "test_results": {
    "status": "success",
    "tps": 89.5,
    "ttft_ms": 312.4,
    "memory_usage_gb": 312.0,
    "error_message": null
  },
  "notes": "Tested in production environment",
  "environment": {
    "os": "Ubuntu 22.04",
    "driver_version": "535.129.03",
    "cuda_version": "12.2"
  },
  "anonymous": true,
  "public": false
}
```

**响应示例**:
```json
{
  "status": "submitted",
  "record_id": "rec_9876543210",
  "message": "Report submitted for review. Thank you for your contribution!",
  "review_estimated_time": "24-48 hours"
}
```

**错误响应**:
```json
{
  "error": "ValidationError",
  "message": "Invalid hardware configuration",
  "details": [
    {
      "field": "hardware.count",
      "message": "GPU count must be between 1 and 256"
    },
    {
      "field": "config.tensor_parallel_size",
      "message": "TP size cannot exceed GPU count"
    }
  ]
}
```

---

### 5. 获取用户提交的报告

获取当前用户提交的所有兼容性报告。

**端点**: `GET /compatibility/reports`

**权限**: 需要登录

**响应示例**:
```json
{
  "total": 5,
  "reports": [
    {
      "id": "rep_1234567890",
      "created_at": "2025-01-21T10:30:00Z",
      "status": "pending",  // pending | approved | rejected
      "public": false,
      "backend": "vllm",
      "hardware": {
        "vendor": "NVIDIA",
        "model": "H100",
        "count": 4
      },
      "model": {
        "architecture": "llama",
        "parameters": "70B"
      },
      "compatibility": {
        "status": "compatible"
      },
      "review_note": "Under review"
    }
  ]
}
```

---

### 6. 删除报告

删除用户提交的兼容性报告。

**端点**: `DELETE /compatibility/reports/{report_id}`

**权限**: 报告所有者或管理员

**响应示例**:
```json
{
  "status": "deleted",
  "message": "Report deleted successfully"
}
```

**错误响应**:
```json
{
  "error": "NotFound",
  "message": "Report not found or you don't have permission to delete it"
}
```

---

### 7. 批量导入 (管理员)

批量导入兼容性数据（仅管理员）。

**端点**: `POST /compatibility/import`

**权限**: 管理员

**请求参数**:
```json
{
  "source": "sglang_ci",
  "format": "json",
  "data": [
    {
      "metadata": {
        "source": "sglang_ci",
        "run_id": "1234567890",
        "run_date": "2025-01-21T10:00:00Z",
        "commit_sha": "abc123def456"
      },
      "hardware": {
        "vendor": "NVIDIA",
        "model": "H100",
        "count": 4
      },
      "test": {
        "suite": "stage-b-test-large-4-gpu",
        "hw": "cuda"
      },
      "models": ["llama-2-70b"],
      "result": {
        "status": "success",
        "duration_seconds": 450
      }
    }
  ]
}
```

**响应示例**:
```json
{
  "status": "imported",
  "imported_count": 45,
  "skipped_count": 3,
  "failed_count": 0,
  "details": {
    "skipped": [
      {
        "index": 12,
        "reason": "Duplicate record (run_id: 1234567890)"
      }
    ]
  }
}
```

---

### 8. 导出数据

导出兼容性数据为 CSV 或 JSON 格式。

**端点**: `GET /compatibility/export`

**权限**: 公开

**查询参数**:
- `format` (string): csv | json，默认 json
- `filters` (string, optional): JSON 编码的过滤条件

**请求示例**:
```
GET /compatibility/export?format=csv&filters={"backend":"vllm","hardware_vendor":"NVIDIA"}
```

**响应**: CSV 或 JSON 文件下载

---

## 错误代码

| HTTP 状态码 | 错误类型 | 说明 |
|------------|----------|------|
| 200 | - | 成功 |
| 400 | BadRequest | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 权限不足 |
| 404 | NotFound | 资源不存在 |
| 409 | Conflict | 资源冲突（如重复提交） |
| 422 | ValidationError | 数据验证失败 |
| 429 | RateLimitExceeded | 请求频率超限 |
| 500 | InternalError | 服务器内部错误 |

---

## 速率限制

| 端点类型 | 限制 |
|----------|------|
| 兼容性检查 | 100 次/分钟/IP |
| 查询记录 | 200 次/分钟/IP |
| 提交报告 | 10 次/小时/用户 |
| 批量导入 | 1 次/小时/管理员 |

---

## 数据模型

### CompatibilityRecord

```typescript
interface CompatibilityRecord {
  id: string;                        // UUID
  created_at: string;                // ISO 8601

  metadata: {
    source: 'vllm_usage_stats' | 'sglang_ci' | 'user_upload' | 'manual';
    confidence: 'high' | 'medium' | 'low';
    verified: boolean;
  };

  backend: {
    name: 'vllm' | 'sglang' | 'llamacpp';
    version: string;
  };

  hardware: {
    vendor: string;
    model: string;
    count: number;
    memory_per_device?: number;
    architecture?: string;
    features?: string[];
  };

  model: {
    architecture: string;
    dtype: string;
    quantization?: string;
    parameters?: string;
  };

  config: {
    tensor_parallel_size: number;
    pipeline_parallel_size?: number;
    gpu_memory_utilization: number;
    max_model_len: number;
    features?: string[];
  };

  compatibility: {
    status: 'compatible' | 'partial' | 'incompatible';
    openai_api_compatible: boolean;
    batch_inference_supported: boolean;
    notes?: string;
  };

  performance?: {
    tps?: number;
    ttft_ms?: number;
    memory_usage_gb?: number;
    throughput?: number;
  };

  error?: {
    type: string;
    message: string;
    solution?: string;
  };
}
```

---

## 使用示例

### Python

```python
import requests

# 检查兼容性
response = requests.post(
    "https://api.tokenmachine.example/api/v1/compatibility/check",
    json={
        "backend": "vllm",
        "hardware_vendor": "NVIDIA",
        "hardware_model": "H100",
        "hardware_count": 4,
        "model_architecture": "llama",
        "tensor_parallel_size": 4
    }
)

result = response.json()
if result["compatible"]:
    print(f"兼容! 置信度: {result['confidence']}")
    print(f"推荐配置: {result['recommendations']}")
else:
    print(f"不兼容: {result['errors']}")
    print(f"替代方案: {result['alternatives']}")
```

### JavaScript/TypeScript

```typescript
import axios from 'axios';

// 检查兼容性
const response = await axios.post(
  'https://api.tokenmachine.example/api/v1/compatibility/check',
  {
    backend: 'vllm',
    hardware_vendor: 'NVIDIA',
    hardware_model: 'H100',
    hardware_count: 4,
    model_architecture: 'llama',
    tensor_parallel_size: 4
  }
);

const result = response.data;
if (result.compatible) {
  console.log(`兼容! 置信度: ${result.confidence}`);
  console.log(`推荐配置:`, result.recommendations);
} else {
  console.log(`不兼容:`, result.errors);
  console.log(`替代方案:`, result.alternatives);
}
```

### cURL

```bash
# 检查兼容性
curl -X POST \
  https://api.tokenmachine.example/api/v1/compatibility/check \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "vllm",
    "hardware_vendor": "NVIDIA",
    "hardware_model": "H100",
    "hardware_count": 4,
    "model_architecture": "llama",
    "tensor_parallel_size": 4
  }'

# 提交报告 (需要认证)
curl -X POST \
  https://api.tokenmachine.example/api/v1/compatibility/reports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "backend": {"name": "vllm", "version": "v0.6.0"},
    "hardware": {"vendor": "NVIDIA", "model": "H100", "count": 4},
    "model": {"architecture": "llama", "dtype": "float16"},
    "config": {"tensor_parallel_size": 4},
    "test_results": {"status": "success", "tps": 89.5}
  }'
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-21

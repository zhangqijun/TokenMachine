#!/usr/bin/env python3
"""
简单测试脚本：添加本地模型（使用 API Key 认证）

使用方法：
1. 确保后端服务运行在 http://localhost:8000
2. 修改下面的 API_KEY 为有效的管理员 API Key
3. 运行: python3 test_add_local_model_simple.py
"""
import requests
import json
import sys

# ==================== 配置区域 ====================
BASE_URL = "http://localhost:8000"
API_KEY = "tmachine_dev_oBt5vAYj-nYudOl54fb6c417"  # 替换为你的管理员 API Key

# 模型信息
MODEL_DATA = {
    "name": "Qwen3-Coder-30B",
    "version": "v1.0.0",
    "local_path": "/home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16",
    "category": "llm",
    "quantization": "Int4-W4A16"
}
# ==================================================


def test_backend_connection():
    """测试后端连接"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务运行正常")
            return True
        else:
            print(f"⚠️  后端响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确认后端是否运行")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False


def add_local_model():
    """添加本地模型"""
    url = f"{BASE_URL}/api/v1/admin/models/local"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print("\n" + "=" * 60)
    print("添加本地模型")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"API Key: {API_KEY[:20]}...")
    print(f"\n模型数据:")
    print(json.dumps(MODEL_DATA, indent=2, ensure_ascii=False))
    print("=" * 60)

    try:
        response = requests.post(url, json=MODEL_DATA, headers=headers, timeout=30)

        print(f"\n响应状态码: {response.status_code}")

        if response.status_code == 201:
            print("✅ 模型添加成功！")
            result = response.json()
            print(f"\n模型信息:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        elif response.status_code == 401:
            print("❌ 认证失败：API Key 无效或没有管理员权限")
            print(f"错误详情: {response.text}")
            return False
        elif response.status_code == 400:
            print("❌ 请求参数错误")
            print(f"错误详情: {response.text}")
            return False
        else:
            print(f"❌ 添加失败 (HTTP {response.status_code})")
            print(f"错误详情: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ 请求超时，模型目录可能很大，正在计算大小...")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def list_models():
    """列出所有模型"""
    url = f"{BASE_URL}/api/v1/admin/models"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    print("\n" + "=" * 60)
    print("查询模型列表")
    print("=" * 60)

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            models = response.json()
            if isinstance(models, list):
                print(f"\n共有 {len(models)} 个模型:")
                for model in models:
                    status_icon = "✅" if model.get("status") == "ready" else "⏳"
                    print(f"  {status_icon} [{model['id']}] {model['name']}:{model['version']}")
                    print(f"      状态: {model.get('status', 'unknown')}")
                    print(f"      路径: {model.get('path', 'N/A')}")
                    print(f"      大小: {model.get('size_gb', 'N/A')} GB")
            else:
                print(f"响应格式异常: {models}")
        elif response.status_code == 401:
            print("❌ 认证失败：API Key 无效")
        else:
            print(f"❌ 查询失败 (HTTP {response.status_code})")

    except Exception as e:
        print(f"❌ 查询失败: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("本地模型添加测试工具")
    print("=" * 60)

    # 检查后端连接
    if not test_backend_connection():
        print("\n⚠️  请先启动后端服务：")
        print("   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)

    # 添加模型
    success = add_local_model()

    # 无论成功与否，都显示模型列表
    list_models()

    if success:
        print("\n" + "=" * 60)
        print("✅ 测试完成！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 添加失败，请检查错误信息")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

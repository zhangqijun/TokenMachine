#!/usr/bin/env python3
"""
Test script for adding local model via API.
"""
import requests
import json

# API 配置
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
ADMIN_ENDPOINT = f"{API_PREFIX}/admin"

# 模型信息
MODEL_DATA = {
    "name": "Qwen3-Coder-30B",
    "version": "v1.0.0",
    "local_path": "/home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16",
    "category": "llm",
    "quantization": "Int4-W4A16"
}


def get_admin_token():
    """获取管理员 token（这里假设使用测试用户）"""
    # 首先尝试创建一个测试用户并获取 token
    # 实际使用中需要替换为真实的管理员 token
    login_url = f"{BASE_URL}{API_PREFIX}/auth/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"登录失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
    except Exception as e:
        print(f"登录请求失败: {e}")
        return None


def add_local_model(token):
    """添加本地模型"""
    url = f"{BASE_URL}{ADMIN_ENDPOINT}/models/local"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n正在添加本地模型...")
    print(f"URL: {url}")
    print(f"数据: {json.dumps(MODEL_DATA, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(url, json=MODEL_DATA, headers=headers)

        print(f"\n状态码: {response.status_code}")

        if response.status_code == 201:
            print("✅ 模型添加成功！")
            print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            return response.json()
        else:
            print("❌ 添加失败")
            print(f"错误信息: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def list_models(token):
    """列出所有模型"""
    url = f"{BASE_URL}{ADMIN_ENDPOINT}/models"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    print(f"\n正在查询模型列表...")

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            models = response.json()
            print(f"\n共有 {len(models)} 个模型:")
            for model in models:
                print(f"  - [{model['id']}] {model['name']}:{model['version']} ({model['status']})")
        else:
            print(f"查询失败: {response.status_code}")

    except Exception as e:
        print(f"查询请求失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("测试添加本地模型 API")
    print("=" * 60)

    # 获取管理员 token
    print("\n步骤 1: 获取管理员 token...")
    token = get_admin_token()

    if not token:
        print("\n❌ 无法获取管理员 token，退出...")
        return

    print(f"✅ Token 获取成功: {token[:20]}...")

    # 添加本地模型
    print("\n步骤 2: 添加本地模型...")
    result = add_local_model(token)

    if result:
        print("\n步骤 3: 验证模型是否添加成功...")
        list_models(token)
    else:
        print("\n步骤 3: 查看现有模型...")
        list_models(token)


if __name__ == "__main__":
    main()

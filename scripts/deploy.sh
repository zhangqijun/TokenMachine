#!/bin/bash
# TokenMachine Multi-Environment Deployment Script
# 用法: ./scripts/deploy.sh [environment]
# 环境选项: development | test | production

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 环境信息
ENVIRONMENTS=(
    "development:当前机器-RTX 4090"
    "test:Bulbaser-7卡RTX 3090"
    "production:Bowser-RTX 3090"
)

# 显示使用方法
show_usage() {
    echo -e "${BLUE}TokenMachine Deployment Script${NC}"
    echo "================================"
    echo ""
    echo "用法: $0 [environment] [options]"
    echo ""
    echo -e "${GREEN}可用环境:${NC}"
    for env in "${ENVIRONMENTS[@]}"; do
        IFS=':' read -r name desc <<< "$env"
        echo "  - $name: $desc"
    done
    echo ""
    echo "选项:"
    echo "  --init-mock     初始化 mock 数据 (开发/测试环境)"
    echo "  --skip-mock     跳过 mock 数据初始化"
    echo "  --clear-data    清空现有数据后初始化"
    echo ""
    echo "示例:"
    echo "  $0 development          # 部署到开发环境"
    echo "  $0 development --init-mock  # 部署并初始化 mock 数据"
    echo "  $0 test --init-mock     # 部署测试环境并初始化数据"
    echo "  $0 production           # 部署到生产环境"
    echo ""
    exit 1
}

# 检查环境参数
if [ $# -eq 0 ]; then
    show_usage
fi

ENVIRONMENT=$1
INIT_MOCK=false
SKIP_MOCK=false
CLEAR_DATA=false

# 解析参数
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --init-mock)
            INIT_MOCK=true
            ;;
        --skip-mock)
            SKIP_MOCK=true
            ;;
        --clear-data)
            CLEAR_DATA=true
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_usage
            ;;
    esac
    shift
done

# 验证环境
VALID_ENV=false
for env in "${ENVIRONMENTS[@]}"; do
    IFS=':' read -r name desc <<< "$env"
    if [ "$name" = "$ENVIRONMENT" ]; then
        VALID_ENV=true
        break
    fi
done

if [ "$VALID_ENV" = false ]; then
    echo -e "${RED}错误: 无效的环境 '$ENVIRONMENT'${NC}"
    echo ""
    show_usage
fi

# 自动决定是否初始化 mock 数据（开发/测试环境默认初始化）
if [ "$INIT_MOCK" = false ] && [ "$SKIP_MOCK" = false ]; then
    if [ "$ENVIRONMENT" = "development" ] || [ "$ENVIRONMENT" = "test" ]; then
        INIT_MOCK=true
        echo -e "${YELLOW}注意: 开发/测试环境将自动初始化 mock 数据${NC}"
    fi
fi

# 显示环境信息
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TokenMachine 部署${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}环境:${NC} $ENVIRONMENT"
for env in "${ENVIRONMENTS[@]}"; do
    IFS=':' read -r name desc <<< "$env"
    if [ "$name" = "$ENVIRONMENT" ]; then
        echo -e "${GREEN}描述:${NC} $desc"
        break
    fi
done
echo ""

# 确认部署
if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${YELLOW}警告: 即将部署到生产环境!${NC}"
    read -p "确认继续? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo -e "${RED}部署已取消${NC}"
        exit 1
    fi
fi

# 进入 docker 目录
cd "$(dirname "$0")/../infra/docker"

# 检查环境文件
ENV_FILE="../../.env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}错误: 环境文件不存在: $ENV_FILE${NC}"
    exit 1
fi

# 复制环境文件
echo -e "${YELLOW}正在配置环境...${NC}"
cp "$ENV_FILE" .env

# 生产环境特殊检查
if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${YELLOW}检查生产环境配置...${NC}"

    # 检查 SSL 证书
    if [ ! -d "$HOME/zhangqijun.cn_apache" ]; then
        echo -e "${RED}警告: SSL 证书目录不存在: $HOME/zhangqijun.cn_apache${NC}"
        echo "请确保证书文件已正确配置"
    fi

    # 检查密码配置
    if grep -q "change_me" .env; then
        echo -e "${RED}警告: 检测到默认密码，请修改 .env 中的密码配置${NC}"
        read -p "继续部署? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            exit 1
        fi
    fi
fi

# 确定 docker compose 命令
COMPOSE_FILES="docker-compose.yml"
if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILES="docker-compose.yml -f docker-compose.production.yml"
elif [ "$ENVIRONMENT" = "test" ]; then
    COMPOSE_FILES="docker-compose.yml -f docker-compose.test.yml"
fi

# 停止现有服务
echo -e "${YELLOW}停止现有服务...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.yml down
else
    eval "docker-compose -f $COMPOSE_FILES down"
fi

# 构建镜像
echo -e "${YELLOW}构建 Docker 镜像...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.yml build
else
    eval "docker-compose -f $COMPOSE_FILES build"
fi

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.yml up -d
else
    eval "docker-compose -f $COMPOSE_FILES up -d"
fi

# 等待服务就绪
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 15

# 检查服务状态
echo -e "${YELLOW}检查服务状态...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.yml ps
else
    eval "docker-compose -f $COMPOSE_FILES ps"
fi

# 初始化 mock 数据（如果需要）
if [ "$INIT_MOCK" = true ]; then
    echo ""
    echo -e "${YELLOW}初始化 mock 数据...${NC}"

    # 构建初始化命令
    if [ "$ENVIRONMENT" = "development" ]; then
        INIT_CMD="docker-compose -f docker-compose.yml exec -T api python scripts/init_mock_data.py --environment $ENVIRONMENT"
    else
        INIT_CMD="docker-compose -f $COMPOSE_FILES exec -T api python scripts/init_mock_data.py --environment $ENVIRONMENT"
    fi

    if [ "$CLEAR_DATA" = true ]; then
        INIT_CMD="$INIT_CMD --clear"
    fi

    # 等待 API 容器完全就绪
    echo -e "${YELLOW}等待 API 容器就绪...${NC}"
    for i in {1..30}; do
        if docker-compose -f docker-compose.yml exec -T api python -c "import sys; sys.exit(0)" 2>/dev/null; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""

    # 执行初始化
    if eval $INIT_CMD; then
        echo -e "${GREEN}✓ Mock 数据初始化成功${NC}"
    else
        echo -e "${RED}✗ Mock 数据初始化失败${NC}"
        echo -e "${YELLOW}可以稍后手动执行: docker-compose exec api python scripts/init_mock_data.py${NC}"
    fi
fi

# 显示访问信息
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}部署完成!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

case $ENVIRONMENT in
    development)
        echo -e "${BLUE}开发环境访问地址:${NC}"
        echo "  - API:         http://localhost:8000"
        echo "  - API 文档:    http://localhost:8000/docs"
        echo "  - Web UI:      http://localhost:8081"
        echo "  - Grafana:     http://localhost:3001 (admin/admin)"
        echo "  - Prometheus:  http://localhost:9091"
        ;;
    test)
        echo -e "${BLUE}测试环境访问地址 (Bulbaser):${NC}"
        echo "  - API:         http://10.0.0.100:8000"
        echo "  - API 文档:    http://10.0.0.100:8000/docs"
        echo "  - Web UI:      http://10.0.0.100:8081"
        echo "  - Grafana:     http://10.0.0.100:3001"
        echo "  - Prometheus:  http://10.0.0.100:9091"
        echo ""
        echo -e "${YELLOW}注意: 测试环境需要多节点配置${NC}"
        ;;
    production)
        echo -e "${BLUE}生产环境访问地址 (Bowser):${NC}"
        echo "  - API:         https://zhangqijun.cn:8443/api"
        echo "  - API 文档:    https://zhangqijun.cn:8443/docs"
        echo "  - Web UI:      https://zhangqijun.cn:8443"
        echo "  - Grafana:     http://zhangqijun.cn:3001"
        echo "  - Prometheus:  http://zhangqijun.cn:9091"
        echo ""
        echo -e "${YELLOW}局域网访问:${NC}"
        echo "  - API:         https://10.0.0.147:8443/api"
        echo "  - Web UI:      https://10.0.0.147:8443"
        echo ""
        echo -e "${YELLOW}注意: 确保路由器端口转发已配置${NC}"
        ;;
esac

echo ""
echo -e "${YELLOW}查看日志:${NC} docker-compose logs -f"
echo -e "${YELLOW}停止服务:${NC} docker-compose down"
echo ""

#!/bin/bash
# ============================================
# AI经营决策平台 - 一键部署脚本
# 适用于 Ubuntu/Debian 云服务器
# ============================================
set -e

echo "=========================================="
echo "  AI经营决策平台 部署脚本"
echo "=========================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo ">>> 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo ">>> Docker 安装完成"
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo ">>> 安装 Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin
    echo ">>> Docker Compose 安装完成"
fi

# Create .env from template if not exists
if [ ! -f .env ]; then
    cp .env.docker .env
    echo ">>> 已创建 .env 文件，请修改其中的数据库密码"
fi

# Build and start
echo ">>> 构建镜像并启动服务..."
docker compose build
docker compose up -d

# Wait for services to be ready
echo ">>> 等待服务启动..."
sleep 10

# Health check
echo ">>> 检查服务状态..."
for i in {1..6}; do
    if curl -s http://localhost/health | grep -q "ok\|healthy\|status"; then
        echo ">>> 后端服务正常"
        break
    fi
    echo "    等待后端就绪... ($i/6)"
    sleep 5
done

# Check frontend
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo ">>> 前端服务正常"
else
    echo ">>> 警告: 前端可能未就绪，请检查 docker compose logs"
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址:  http://$(hostname -I | awk '{print $1}')"
echo ""
echo "  服务状态:"
echo "    docker compose ps     # 查看运行状态"
echo "    docker compose logs   # 查看日志"
echo "    docker compose down   # 停止服务"
echo "    docker compose up -d  # 重新启动"
echo ""
echo "  数据导入:"
echo "    1. 打开浏览器访问上面的地址"
echo "    2. 进入「数据导入」页面"
echo "    3. 上传旺店通导出的Excel文件"
echo ""
echo "=========================================="

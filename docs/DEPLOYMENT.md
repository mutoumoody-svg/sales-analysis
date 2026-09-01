# AI经营决策平台 - 云端部署指南

## 架构概览

```
                    ┌─────────────┐
   手机/电脑  ──────►│   Nginx:80  │ (前端容器)
                    └──────┬──────┘
                           │ /api/* 代理
                    ┌──────▼──────┐
                    │  FastAPI:8000│ (后端容器)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL:5432│ (数据库容器)
                    └─────────────┘
```

## 前置条件

- 云服务器（推荐配置：2核4G，Ubuntu 22.04+）
- 已开放端口 **80**（HTTP）和 **8000**（API直连，可选）
- 服务器已安装 git（用于拉取代码）

## 部署步骤

### 1. 上传代码到服务器

```bash
# 在服务器上
cd /opt
git clone https://github.com/mutoumoody-svg/sales-analysis.git
cd sales-analysis
```

或使用 scp 上传：
```bash
# 在本地电脑
scp -r c:\Users\jingz\WorkBuddy\20260801200541\* user@server_ip:/opt/sales-analysis/
```

### 2. 一键部署

```bash
cd /opt/sales-analysis
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：
- 安装 Docker 和 Docker Compose（如果未安装）
- 构建三个容器镜像（数据库 + 后端 + 前端）
- 启动所有服务
- 检查健康状态

### 3. 验证部署

- **前端页面**：浏览器打开 `http://服务器IP`
- **API 健康检查**：`http://服务器IP/health`
- **API 文档**：`http://服务器IP:8000/docs`

### 4. 导入业务数据

1. 打开 `http://服务器IP`
2. 点击底部导航栏「更多」→「数据导入」
3. 分别上传旺店通导出的：
   - 销售出库明细表.xlsx
   - 货品销售汇总表.xlsx
4. 选择对应月份，点击导入

## 手机使用

### 方式一：浏览器直接访问

1. 手机浏览器打开 `http://服务器IP`
2. 界面自动适配为手机版（底部导航栏）

### 方式二：添加到桌面（PWA）

**iPhone (Safari)**：
1. Safari 打开 `http://服务器IP`
2. 点击底部「分享」按钮
3. 选择「添加到主屏幕」
4. 点击「添加」

**Android (Chrome)**：
1. Chrome 打开 `http://服务器IP`
2. 点击右上角「⋮」菜单
3. 选择「添加到主屏幕」或「安装应用」

安装后桌面上会出现「AI经营」图标，点击即可全屏使用，体验类似原生APP。

## 常用运维命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f          # 所有服务
docker compose logs -f backend  # 仅后端
docker compose logs -f frontend # 仅前端

# 重启服务
docker compose restart backend

# 停止/启动所有服务
docker compose down
docker compose up -d

# 更新代码后重新构建
git pull
docker compose build
docker compose up -d

# 备份数据库
docker compose exec db pg_dump -U postgres sales_analysis > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker compose exec -T db psql -U postgres sales_analysis < backup_20260802.sql
```

## HTTPS 配置（推荐）

如果需要域名 + HTTPS（用于生产环境）：

```bash
# 1. 安装 certbot
apt install -y certbot python3-certbot-nginx

# 2. 申请证书（需要先有域名指向服务器）
certbot --nginx -d your-domain.com

# 3. 修改 docker-compose.yml，将 80 端口改为不直接暴露
# 4. 使用宿主机 nginx 反代到 docker 的 80 端口
```

或使用 Caddy 自动 HTTPS：
```bash
# docker-compose.yml 中添加 caddy 服务替代前端 nginx
```

## 性能优化建议

- 服务器内存 ≥ 4G 时，后端可增加 workers：`--workers 4`
- 数据量大时，PostgreSQL 可配置 `shared_buffers = 1GB`
- 前端已做代码分割（react/antd/echarts 分包），首次加载约 500KB
- PWA 缓存静态资源，二次访问秒开

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| 页面打不开 | `docker compose ps` 检查是否运行，`docker compose logs` 看错误 |
| API 404 | 检查 nginx.conf 的 proxy_pass 是否指向 `backend:8000` |
| 数据库连接失败 | 检查 `.env` 中 DB_PASSWORD 是否一致 |
| 导入数据超时 | nginx 已设置 300s 超时，超大文件可调大 `client_max_body_size` |
| 手机访问白屏 | 确保手机和服务器在同一网络，或使用公网IP |

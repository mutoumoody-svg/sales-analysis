# 配置规范

## 配置文件分工

| 场景 | 模板 | 本地文件 |
| --- | --- | --- |
| Docker Compose | `/.env.example` | `/.env` |
| 后端本地开发 | `/backend/.env.example` | `/backend/.env` |
| 前端本地开发 | `/frontend/.env.example` | `/frontend/.env.local` |

本地配置文件不得提交。新增配置项时，必须同时更新对应模板和本文件。

## Docker 配置

`DB_PASSWORD` 为必填项。生产部署还应显式设置：

- `CORS_ORIGINS`：允许访问 API 的前端来源，多个来源用英文逗号分隔。
- `ADMIN_API_KEY`：保护数据导入、外部同步、成本维护和采购确认等写操作。生产环境必填。
- `FRONTEND_BIND_ADDRESS`、`FRONTEND_PORT`：前端对外监听地址和端口。
- `BACKEND_BIND_ADDRESS`：默认 `127.0.0.1`，只有确需 API 直连时才改为 `0.0.0.0`。
- `POSTGRES_BIND_ADDRESS`：默认 `127.0.0.1`，生产环境不应直接暴露数据库。

旺店通密钥仅放入 `.env` 或部署平台的密钥管理服务，不得写入源码、脚本、日志或截图。

运营设置页面中的管理员密钥只写入浏览器 `sessionStorage`，关闭会话后失效。不要在共享电脑上长期保存管理员密钥。

## 后端配置

后端使用 `pydantic-settings` 从环境变量和 `/backend/.env` 加载配置。`DATABASE_URL` 没有代码内默认值；缺失时应立即启动失败，以避免误连测试库或弱密码数据库。

`CORS_ORIGINS` 示例：

```text
CORS_ORIGINS=https://example.com,https://admin.example.com
```

## 前端配置

所有暴露给浏览器的变量必须使用 `VITE_` 前缀。不得在前端环境变量中放置数据库密码、旺店通密钥或其他服务端秘密。

默认使用相对地址 `/api/v1`，由 Vite 开发代理或生产 Nginx 转发到后端。只有前后端分域部署时才需要覆盖 `VITE_API_BASE_URL`。

## 变更要求

每次配置变更至少完成以下检查：

1. 后端能加载目标环境配置。
2. `npm run build` 能通过。
3. `docker compose --env-file .env.example config` 能解析。
4. 不在 Git 差异中出现真实密码、API Key 或密钥。

# ENVIRONMENT SETUP

# 开发环境配置 V1.0


## Backend


Python:

3.12+


Framework:

FastAPI



---

## Database


PostgreSQL:

16+



---

## Frontend


Node:

20+


Framework:

React



---

# 环境变量


.env


包括：


DATABASE_URL


API_KEY


SECRET_KEY



---

# 本地启动流程


## Backend


安装：

pip install -r requirements.txt


启动：


uvicorn main:app



---

## Frontend


安装：


npm install


启动：


npm run dev



---

# 开发原则


不要直接修改生产环境。


所有修改：

本地测试

提交Git

再部署。

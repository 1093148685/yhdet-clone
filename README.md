# 泓聊社区 Clone

一个可运行的社区论坛全栈项目：React 前端 + FastAPI 后端 + SQLite 本地数据库。项目包含社区首页、帖子、评论、用户、搜索、公告、捐赠者展示等基础功能。
<img width="1276" height="673" alt="image" src="https://github.com/user-attachments/assets/e99e3161-e3dc-4bbe-8783-3e78b8477e3e" />

## 功能

- 用户注册、登录、Token 会话
- 首页帖子列表、统计栏、公告条、捐赠者、公告栏
- 发帖、帖子详情、评论发布与展示
- 用户主页、用户帖子列表
- 帖子/用户搜索
- 小游戏、音乐入口页面
- FastAPI 托管构建后的 React SPA

## 技术栈

- 前端：React、Vite
- 后端：FastAPI、Uvicorn
- 数据库：SQLite（运行后自动生成）

## 目录结构

```text
backend/
  main.py              # FastAPI 后端、SQLite 初始化、API、SPA 托管
  static/              # 静态资源
frontend/
  src/main.jsx         # React 页面与路由
  src/styles.css       # 页面样式
  package.json         # 前端依赖与脚本
run.sh                 # 本地启动脚本
tests_api_regression.py # API 回归测试
```

## 本地运行

```bash
# 进入项目
cd yhdet-clone

# 安装并构建前端
cd frontend
npm install
npm run build
cd ..

# 安装后端依赖
python3 -m venv .venv
. .venv/bin/activate
pip install fastapi uvicorn pydantic

# 启动
uvicorn backend.main:app --host 0.0.0.0 --port 8124
```

访问：`http://127.0.0.1:8124/`

## 测试

```bash
python tests_api_regression.py
```

覆盖：健康检查、首页数据、注册、登录态、发帖、帖子详情、评论、帖子搜索、用户搜索、未登录拦截、SPA 直达路由。

## 数据说明

- SQLite 数据库位于 `backend/data/community.db`，运行后自动生成。
- 仓库不会提交数据库、依赖目录、构建产物、虚拟环境和日志文件。
- 首次启动会生成演示用户与示例内容；请在生产环境中自行调整默认演示数据。

## License

MIT

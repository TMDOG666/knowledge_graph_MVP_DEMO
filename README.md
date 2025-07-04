# knowledge_study_agent_graph_app

## 项目简介

本项目是一个知识图谱学习与智能对话系统，旨在通过图谱化的知识管理和智能问答，为用户提供高效的知识查询与学习体验。系统采用前后端分离架构，支持知识的可视化、对话记录管理和知识检索。

## 目录结构

```
knowledge_study_agent_graph_app/
├── backend/                # 后端服务
│   ├── main.py             # 后端主入口
│   ├── factory.py          # 工厂模式相关代码
│   ├── data_manager.py     # 数据管理模块
│   ├── data/               # 存储知识图谱和对话数据
│   ├── db/                 # 数据库文件
│   └── knowledge/          # 知识库文件
└── frontend/               # 前端页面
    ├── index.html          # 主页面
    ├── app.js              # 前端逻辑
    └── style.css           # 样式表
```

## 主要功能

- **知识图谱管理**：支持知识的结构化存储与管理。
- **智能对话**：记录用户与系统的对话内容，支持基于知识的问答。
- **数据可视化**：前端页面可视化展示知识结构和对话流程。
- **数据持久化**：所有知识和对话数据均持久化存储于本地数据库和文件系统。

## 部署与运行

## 依赖说明

- 后端依赖：
  - Python 3.x
  - FastAPI
  - Uvicorn
  - pydantic
  - 以及你实际用到的模型/向量库相关依赖（如 transformers、chroma、sqlite3 等）

### 后端依赖安装
```bash
pip install fastapi uvicorn pydantic chromadb python-dotenv langchain langchain-openai langchain-community
```

### 后端

1. 进入 `backend` 目录，确保已安装 Python 3 及相关依赖。
2. 运行后端服务：
   ```bash
   uvicorn main:app --reload
   ```

### 前端

1. 进入 `frontend` 目录。
2. 直接用浏览器打开 `index.html` 即可访问前端页面。



- 前端依赖：原生 HTML/CSS/JS，无需额外依赖。

## 数据存储

- 知识数据和对话记录存储于 `backend/data/` 目录下的 JSON 文件。
- 数据库文件位于 `backend/db/` 目录。

## 贡献与反馈

如需贡献代码或反馈问题，请提交 issue 或 pull request。 
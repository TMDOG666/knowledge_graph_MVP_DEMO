# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from factory import AgentFactory # 引入你的工厂
import data_manager # 引入数据管理模块

app = FastAPI()

# --- CORS 中间件，允许前端跨域请求 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允许所有来源，仅限开发
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 实例化 Agent 工厂 ---
# 注意：这会在启动时就加载模型和创建向量库，对于Demo来说可以接受
# 在生产环境中，可能需要懒加载
agent_factory = AgentFactory(agent_llm_model="Qwen/Qwen3-32B",embedding_model="BAAI/bge-m3")

# 定义一个Agent配置（可以从配置文件读取）
PYTHON_RAG_CONFIG = {
    "doc_path": "knowledge/python_expert.txt",
    "tool_name": "Python专业知识库",
    "tool_description": "当你需要回答关于Python编程语言的专业问题时，请使用这个工具。",
    "persist_path": "./db/python_db"
}
PYTHON_PERSONALITY = "你是一个资深的Python技术专家，精通Python底层原理和高级用法。你的回答严谨、专业、深入浅出。"

# 创建一个常驻的Agent实例
# 注意：为简化MVP，我们只创建一个Agent。每个会话的memory是独立的。
# AgentExecutor的memory是会话级的，每次调用 invoke/stream 都会使用其内部的memory。
# 为了实现持久化聊天，我们需要手动管理历史记录。
python_agent = agent_factory.create_agent(
    personality=PYTHON_PERSONALITY,
    rag_config=PYTHON_RAG_CONFIG,
    temperature=0.2,
    use_memory=False,
    use_rag=False,
)


# --- API Models ---
class NodeIn(BaseModel):
    node_type: str
    title: str

class EdgeIn(BaseModel):
    source_id: str
    target_id: str
    edge_type: str
    label: str = ""

class ChatIn(BaseModel):
    node_id: str # 关联到哪个知识节点
    prompt: str

# --- API Endpoints ---

@app.get("/api/graph")
async def get_graph():
    """获取完整的图谱数据"""
    return data_manager.get_graph_data()

@app.post("/api/nodes", status_code=201)
async def create_node(node_in: NodeIn):
    """创建一个新节点"""
    new_node = data_manager.add_node(
        node_type=node_in.node_type,
        title=node_in.title
    )
    return new_node

@app.post("/api/edges", status_code=201)
async def create_edge(edge_in: EdgeIn):
    """创建一条边"""
    data_manager.add_edge(**edge_in.dict())
    return {"message": "Edge created successfully"}

@app.post("/api/chat")
async def chat_with_agent(chat_in: ChatIn):
    """与Agent进行聊天"""
    # 1. 当前节点历史
    history = data_manager.get_chat_history(chat_in.node_id)
    history_str = "\n".join([f"Human: {h['human']}\nAI: {h['ai']}" for h in history])

    # 2. 获取前驱节点
    predecessor_ids = data_manager.get_predecessor_node_ids(chat_in.node_id)
    predecessor_histories = []
    for pid in predecessor_ids:
        phistory = data_manager.get_chat_history(pid)
        phistory_str = "\n".join([f"Human: {h['human']}\nAI: {h['ai']}" for h in phistory])
        if phistory_str:
            predecessor_histories.append(f"【前驱节点 {pid} 的历史】\n{phistory_str}")

    # 3. 拼接 prompt
    full_prompt = ""
    if predecessor_histories:
        full_prompt += "\n".join(predecessor_histories) + "\n"
    full_prompt += f"【当前节点历史】\n{history_str}\n\n新问题: {chat_in.prompt}"

    print(full_prompt)
    try:
        result = python_agent.invoke({"input": full_prompt})
        ai_response = result.get('output', "抱歉，我无法回答这个问题。")
        history.append({"human": chat_in.prompt, "ai": ai_response})
        data_manager.save_chat_history(chat_in.node_id, history)
        return {"response": ai_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/{node_id}")
async def get_node_chat_history(node_id: str):
    """获取特定节点的聊天记录"""
    return data_manager.get_chat_history(node_id)
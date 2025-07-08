# backend/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import shutil, os

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

# --- Agent 懒加载优化 ---
_agent_factory = None
_python_agent = None
_loading = False

# 定义一个Agent配置（可以从配置文件读取）
PYTHON_RAG_CONFIG = {
    "doc_path": "knowledge/python_expert.txt",
    "tool_name": "Python专业知识库",
    "tool_description": "当你需要回答关于Python编程语言的专业问题时，请使用这个工具。",
    "persist_path": "./db/python_db"
}
PYTHON_PERSONALITY = "你是一个资深的Python技术专家，精通Python底层原理和高级用法。你的回答严谨、专业、深入浅出。"

def get_python_agent():
    global _agent_factory, _python_agent, _loading
    if _python_agent is None:
        if _loading:
            raise HTTPException(status_code=503, detail="Agent is loading, please try again later.")
        _loading = True
        try:
            if _agent_factory is None:
                _agent_factory = AgentFactory(agent_llm_model="Qwen/Qwen3-32B", embedding_model="BAAI/bge-m3")
            _python_agent = _agent_factory.create_agent(
                personality=PYTHON_PERSONALITY,
                rag_config=PYTHON_RAG_CONFIG,
                temperature=0.2,
                use_memory=False,
                use_rag=False,
            )
        finally:
            _loading = False
    return _python_agent

def get_agent_by_topic_id(topic_id: str):
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = AgentFactory(agent_llm_model="Qwen/Qwen3-32B", embedding_model="BAAI/bge-m3")
    if topic_id not in _agent_factory.knowledge_bases:
        topic = data_manager.get_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        rag_config = topic.get('rag_config')
        if not rag_config:
            rag_config = {
                "doc_paths": topic["doc_paths"],
                "tool_name": f"{topic['name']}知识库",
                "tool_description": f"{topic['name']}领域的知识库。",
                "persist_path": f"./backend/db/{topic['id']}_db"
            }
        personality = topic.get('personality', f"你是{topic['name']}领域的专家，善于引导新手入门。")
        _agent_factory.register_knowledge_base(topic_id, rag_config, personality)
    return _agent_factory.create_agent_by_kb_name(topic_id)

# --- API Models ---
class NodeIn(BaseModel):
    node_type: str
    title: str

class NodeUpdateIn(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None

class EdgeIn(BaseModel):
    source_id: str
    target_id: str
    edge_type: str
    label: str = ""

class ChatIn(BaseModel):
    node_id: str # 关联到哪个知识节点
    prompt: str

class TopicCreateIn(BaseModel):
    name: str
    # 文档上传用API时用UploadFile，这里先用路径列表模拟
    doc_paths: List[str]

class TopicUpdateIn(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = None
    rag_config: Optional[dict] = None
    doc_paths: Optional[List[str]] = None

# --- API Endpoints ---

@app.get("/api/graph")
async def get_graph(topic_id: Optional[str] = Query(None)):
    """获取指定主题的图谱数据"""
    return data_manager.get_graph_data(topic_id)

@app.post("/api/nodes", status_code=201)
async def create_node(node_in: NodeIn, topic_id: Optional[str] = Query(None)):
    """创建一个新节点"""
    new_node = data_manager.add_node(
        node_type=node_in.node_type,
        title=node_in.title,
        topic_id=topic_id
    )
    return new_node

@app.put("/api/nodes/{node_id}")
async def update_node(node_id: str, node_update: NodeUpdateIn, topic_id: Optional[str] = Query(None)):
    """更新节点信息"""
    success = data_manager.update_node(
        node_id=node_id,
        title=node_update.title,
        content=node_update.content,
        tags=node_update.tags,
        topic_id=topic_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"message": "Node updated successfully"}

@app.delete("/api/nodes/{node_id}")
async def delete_node(node_id: str, topic_id: Optional[str] = Query(None)):
    """删除一个节点及其相关的边"""
    success = data_manager.delete_node(node_id, topic_id=topic_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"message": "Node deleted successfully"}

@app.post("/api/edges", status_code=201)
async def create_edge(edge_in: EdgeIn, topic_id: Optional[str] = Query(None)):
    """创建一条边"""
    data_manager.add_edge(
        source_id=edge_in.source_id,
        target_id=edge_in.target_id,
        edge_type=edge_in.edge_type,
        label=edge_in.label,
        topic_id=topic_id
    )
    return {"message": "Edge created successfully"}

@app.delete("/api/edges")
async def delete_edge(source_id: str, target_id: str, topic_id: Optional[str] = Query(None)):
    """删除一条边"""
    success = data_manager.delete_edge(source_id, target_id, topic_id=topic_id)
    if not success:
        raise HTTPException(status_code=404, detail="Edge not found")
    return {"message": "Edge deleted successfully"}

@app.post("/api/chat")
async def chat_with_agent(chat_in: ChatIn, topic_id: Optional[str] = Query(None)):
    """与Agent进行聊天，支持按主题切换agent"""
    # 1. 当前节点历史
    history = data_manager.get_chat_history(chat_in.node_id)
    history_str = "\n".join([f"Human: {h['human']}\nAI: {h['ai']}" for h in history])
    # 2. 获取前驱节点
    predecessor_ids = data_manager.get_predecessor_node_ids(chat_in.node_id, topic_id=topic_id)
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
        if topic_id:
            agent = get_agent_by_topic_id(topic_id)
        else:
            agent = get_python_agent()
        result = agent.invoke({"input": full_prompt})
        ai_response = result.get('output', "抱歉，我无法回答这个问题。")
        history.append({"human": chat_in.prompt, "ai": ai_response})
        data_manager.save_chat_history(chat_in.node_id, history)
        return {"response": ai_response}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/{node_id}")
async def get_node_chat_history(node_id: str):
    """获取特定节点的聊天记录"""
    return data_manager.get_chat_history(node_id)

@app.post("/api/topics", status_code=201)
async def create_topic(
    name: str = Form(...),
    personality: str = Form(...),
    files: List[UploadFile] = File(...),
    use_rag: Optional[str] = Form(None),
    tool_name: Optional[str] = Form(None),
    tool_description: Optional[str] = Form(None)
):
    """创建新主题，支持上传多个txt文件和自定义personality/rag_config。"""
    knowledge_dir = os.path.join(os.path.dirname(__file__), 'knowledge')
    os.makedirs(knowledge_dir, exist_ok=True)
    doc_paths = []
    for file in files:
        if not file.filename.lower().endswith('.txt'):
            return JSONResponse(status_code=400, content={"error": "只允许上传txt文件"})
        save_path = os.path.join(knowledge_dir, file.filename)
        with open(save_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        doc_paths.append(save_path)
    rag_config = {
        "doc_paths": doc_paths,
        "tool_name": tool_name or f"{name}知识库",
        "tool_description": tool_description or f"{name}领域的知识库。",
        "persist_path": f"./db/{name}_db"
    }
    if use_rag is not None:
        rag_config["use_rag"] = (use_rag == 'true')
    topic = data_manager.add_topic(name, doc_paths, personality=personality, rag_config=rag_config)
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = AgentFactory(agent_llm_model="Qwen/Qwen3-32B", embedding_model="BAAI/bge-m3")
    _agent_factory.register_knowledge_base(topic['id'], rag_config, personality)
    return topic

@app.get("/api/topics")
async def list_topics():
    """获取所有主题列表"""
    return data_manager.list_topics()

@app.put("/api/topics/{topic_id}")
async def update_topic_api(topic_id: str, topic_update: TopicUpdateIn = Body(...)):
    """更新主题内容，支持修改name、personality、rag_config、doc_paths等。"""
    updated = data_manager.update_topic(
        topic_id,
        name=topic_update.name,
        personality=topic_update.personality,
        rag_config=topic_update.rag_config,
        doc_paths=topic_update.doc_paths
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Topic not found")
    return updated
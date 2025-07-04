# backend/data_manager.py
import json
import os
import uuid
from typing import List, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
GRAPH_FILE = os.path.join(DATA_DIR, 'graph_data.json')
CHATS_DIR = os.path.join(DATA_DIR, 'chats')

# 确保目录存在
os.makedirs(CHATS_DIR, exist_ok=True)

def get_graph_data() -> Dict[str, List[Dict[str, Any]]]:
    """读取图谱数据"""
    if not os.path.exists(GRAPH_FILE):
        return {"nodes": [], "edges": []}
    with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_graph_data(data: Dict[str, List[Dict[str, Any]]]):
    """保存图谱数据"""
    with open(GRAPH_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_node(node_type: str, title: str, content: str = "", tags: List[str] = None) -> Dict[str, Any]:
    """添加一个新节点"""
    graph_data = get_graph_data()
    new_node = {
        "id": str(uuid.uuid4()), # 使用UUID确保唯一性
        "label": title, # vis-network 使用 'label'
        "type": node_type,
        "content": content,
        "tags": tags or []
    }
    graph_data["nodes"].append(new_node)
    save_graph_data(graph_data)
    return new_node
    
def add_edge(source_id: str, target_id: str, edge_type: str, label: str = ""):
    """添加一条边"""
    graph_data = get_graph_data()
    new_edge = {
        "from": source_id, # vis-network 使用 'from' 和 'to'
        "to": target_id,
        "type": edge_type,
        "label": label
    }
    graph_data["edges"].append(new_edge)
    save_graph_data(graph_data)

def get_chat_history(node_id: str) -> List[Dict[str, str]]:
    """获取某个节点的聊天历史"""
    chat_file = os.path.join(CHATS_DIR, f"{node_id}.json")
    if not os.path.exists(chat_file):
        return []
    with open(chat_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_chat_history(node_id: str, history: List[Dict[str, str]]):
    """保存某个节点的聊天历史"""
    chat_file = os.path.join(CHATS_DIR, f"{node_id}.json")
    with open(chat_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def get_predecessor_node_ids(node_id: str) -> list:
    """获取所有指向 node_id 的前驱节点id"""
    graph_data = get_graph_data()
    return [edge['from'] for edge in graph_data['edges'] if edge['to'] == node_id]
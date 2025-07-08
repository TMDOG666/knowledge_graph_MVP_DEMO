# backend/data_manager.py
import json
import os
import uuid
from typing import List, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
GRAPH_DIR = os.path.join(DATA_DIR, 'graph')
CHATS_DIR = os.path.join(DATA_DIR, 'chats')
TOPICS_FILE = os.path.join(DATA_DIR, 'topics.json')

# 确保目录存在
os.makedirs(CHATS_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)

def get_graph_file_path(topic_id: str = None) -> str:
    if topic_id:
        return os.path.join(GRAPH_DIR, f'{topic_id}.json')
    return os.path.join(GRAPH_DIR, 'default.json')

def get_graph_data(topic_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """读取指定主题的图谱数据"""
    graph_file = get_graph_file_path(topic_id)
    if not os.path.exists(graph_file):
        return {"nodes": [], "edges": []}
    with open(graph_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_graph_data(data: Dict[str, List[Dict[str, Any]]], topic_id: str = None):
    """保存指定主题的图谱数据"""
    graph_file = get_graph_file_path(topic_id)
    with open(graph_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_node(node_type: str, title: str, content: str = "", tags: List[str] = None, topic_id: str = None) -> Dict[str, Any]:
    """添加一个新节点到指定主题"""
    graph_data = get_graph_data(topic_id)
    new_node = {
        "id": str(uuid.uuid4()),
        "label": title,
        "type": node_type,
        "content": content,
        "tags": tags or []
    }
    graph_data["nodes"].append(new_node)
    save_graph_data(graph_data, topic_id)
    return new_node

def add_edge(source_id: str, target_id: str, edge_type: str, label: str = "", topic_id: str = None):
    """添加一条边到指定主题"""
    graph_data = get_graph_data(topic_id)
    new_edge = {
        "from": source_id,
        "to": target_id,
        "type": edge_type,
        "label": label
    }
    graph_data["edges"].append(new_edge)
    save_graph_data(graph_data, topic_id)

def delete_node(node_id: str, topic_id: str = None) -> bool:
    """删除指定主题的一个节点及其相关的边"""
    graph_data = get_graph_data(topic_id)
    node_to_delete = None
    for node in graph_data["nodes"]:
        if node["id"] == node_id:
            node_to_delete = node
            break
    if not node_to_delete:
        return False
    graph_data["nodes"] = [node for node in graph_data["nodes"] if node["id"] != node_id]
    graph_data["edges"] = [edge for edge in graph_data["edges"] if edge["from"] != node_id and edge["to"] != node_id]
    save_graph_data(graph_data, topic_id)
    chat_file = os.path.join(CHATS_DIR, f"{node_id}.json")
    if os.path.exists(chat_file):
        os.remove(chat_file)
    return True

def delete_edge(source_id: str, target_id: str, topic_id: str = None) -> bool:
    """删除指定主题的一条边"""
    graph_data = get_graph_data(topic_id)
    edge_to_delete = None
    for edge in graph_data["edges"]:
        if edge["from"] == source_id and edge["to"] == target_id:
            edge_to_delete = edge
            break
    if not edge_to_delete:
        return False
    graph_data["edges"] = [edge for edge in graph_data["edges"] if not (edge["from"] == source_id and edge["to"] == target_id)]
    save_graph_data(graph_data, topic_id)
    return True

def update_node(node_id: str, title: str = None, content: str = None, tags: List[str] = None, topic_id: str = None) -> bool:
    """更新指定主题的节点信息"""
    graph_data = get_graph_data(topic_id)
    for node in graph_data["nodes"]:
        if node["id"] == node_id:
            if title is not None:
                node["label"] = title
            if content is not None:
                node["content"] = content
            if tags is not None:
                node["tags"] = tags
            save_graph_data(graph_data, topic_id)
            return True
    return False

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

def get_predecessor_node_ids(node_id: str, topic_id: str = None) -> list:
    """获取指定主题所有指向 node_id 的前驱节点id"""
    graph_data = get_graph_data(topic_id)
    return [edge['from'] for edge in graph_data['edges'] if edge['to'] == node_id]

def add_topic(name: str, doc_paths: list, personality: str = None, rag_config: dict = None) -> dict:
    """创建新主题，返回主题对象。支持自定义personality和rag_config。"""
    topics = []
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
            topics = json.load(f)
    topic_id = str(uuid.uuid4())
    topic = {
        'id': topic_id,
        'name': name,
        'doc_paths': doc_paths,
        'root_node_id': None
    }
    if personality:
        topic['personality'] = personality
    if rag_config:
        topic['rag_config'] = rag_config
    topics.append(topic)
    with open(TOPICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(topics, f, indent=4, ensure_ascii=False)
    return topic

def get_topic(topic_id: str) -> dict:
    """根据id获取主题。"""
    if not os.path.exists(TOPICS_FILE):
        return None
    with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
        topics = json.load(f)
    for topic in topics:
        if topic['id'] == topic_id:
            return topic
    return None

def list_topics() -> list:
    """列出所有主题。"""
    if not os.path.exists(TOPICS_FILE):
        return []
    with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_topic(topic_id: str, name: str = None, personality: str = None, rag_config: dict = None, doc_paths: list = None) -> dict:
    """更新主题内容，支持修改name、personality、rag_config、doc_paths等。返回更新后的主题。"""
    if not os.path.exists(TOPICS_FILE):
        return None
    with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
        topics = json.load(f)
    updated = None
    for topic in topics:
        if topic['id'] == topic_id:
            if name is not None:
                topic['name'] = name
            if personality is not None:
                topic['personality'] = personality
            if rag_config is not None:
                topic['rag_config'] = rag_config
            if doc_paths is not None:
                topic['doc_paths'] = doc_paths
            updated = topic
            break
    if updated:
        with open(TOPICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(topics, f, indent=4, ensure_ascii=False)
    return updated
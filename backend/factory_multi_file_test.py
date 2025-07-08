# factory_multi_file_test.py
from factory import AgentFactory
import os

def main():
    factory = AgentFactory()

    # 假设有多个知识文档
    doc_paths = [
        os.path.join("backend","knowledge", "python_expert.txt"),
        os.path.join("backend","knowledge", "python_advanced.txt"),  # 你可以创建这个文件做测试
        os.path.join("backend","knowledge", "python_tricks.txt")     # 你可以创建这个文件做测试
    ]
    rag_config = {
        "doc_paths": doc_paths,
        "tool_name": "Python多文档知识库",
        "tool_description": "多个文档合并的Python知识库",
        "persist_path": "./db/python_multi_db"
    }
    personality = "你是一个资深的Python专家，能够整合多个文档的知识为用户解答。"
    factory.register_knowledge_base("python_multi", rag_config, personality)

    print("已注册知识库:", factory.list_knowledge_bases())

    agent = factory.create_agent_by_kb_name("python_multi", temperature=0.2, use_memory=False, use_rag=True)

    print("\n--- 多文件知识库 Agent 测试 ---")
    result = agent.invoke({"input": "请简要介绍Python的GIL和常见高级用法。"})
    print("[Agent]:", result.get("output"))

if __name__ == "__main__":
    main() 
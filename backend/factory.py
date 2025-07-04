# factory.py

import os
from dotenv import load_dotenv

from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader
from langchain.chains import RetrievalQA
from langchain.agents import AgentExecutor, create_react_agent, Tool
from langchain.prompts import PromptTemplate

# --- 1. 全局配置 ---
load_dotenv()
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
EMBEDDING_MODEL = "BAAI/bge-m3"

# --- 2. Agent 工厂类 ---
class AgentFactory:
    def __init__(self, agent_llm_model="Qwen/Qwen3-235B-A22B", llm_base_url=None, embedding_model="BAAI/bge-m3", embedding_base_url=None):
        """
        工厂初始化，可以设置一些通用的配置。
        agent_llm_model: LLM基础模型名
        llm_base_url: LLM API Base URL
        embedding_model: 嵌入模型名
        embedding_base_url: 嵌入API Base URL
        """
        self.agent_llm_model = agent_llm_model
        self.llm_base_url = llm_base_url or SILICONFLOW_BASE_URL
        self.embedding_model = embedding_model
        self.embedding_base_url = embedding_base_url or SILICONFLOW_BASE_URL
        print(f"工厂已初始化，默认 Agent LLM 为: {self.agent_llm_model}")

    def _create_rag_tool(self, doc_path: str, tool_name: str, tool_description: str, persist_path: str) -> Tool:
        """
        一个私有方法，用于创建针对特定知识库的RAG工具。
        所有硬编码的部分都变成了参数。
        """
        print(f"--- 正在为 '{tool_name}' 创建RAG工具 ---")
        print(f"知识库路径: {doc_path}")
        print(f"向量数据库持久化路径: {persist_path}")

        # 1. 加载和分割文档
        loader = TextLoader(doc_path, encoding="utf-8")
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        documents = text_splitter.split_documents(docs)

        # 2. 设置 Embedding 和向量数据库
        embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            openai_api_base=self.embedding_base_url,
            openai_api_key=SILICONFLOW_API_KEY,
        )
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_path
        )
        retriever = vectorstore.as_retriever()

        # 3. 创建 RAG 链
        rag_llm = ChatOpenAI(
            model_name=self.agent_llm_model,
            openai_api_base=self.llm_base_url,
            openai_api_key=SILICONFLOW_API_KEY,
            temperature=0.0
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=rag_llm, chain_type="stuff", retriever=retriever
        )

        # 4. 创建并返回工具
        rag_tool = Tool(
            name=tool_name,
            func=qa_chain.run,
            description=tool_description,
        )
        print("--- RAG工具创建完毕 ---")
        return rag_tool

    def create_agent(self, personality: str, rag_config: dict, temperature=0.7, use_memory=True, use_rag=True, llm_model=None, llm_base_url=None, embedding_model=None, embedding_base_url=None):
        """
        创建并返回一个完整的 AgentExecutor。
        use_memory: 是否启用会话记忆（ConversationBufferMemory）
        use_rag: 是否启用RAG工具
        llm_model/llm_base_url/embedding_model/embedding_base_url: 可自定义基础模型和API
        """
        print(f"\n======= 开始创建 Agent: {rag_config['tool_name']} =======")
        # 1. 创建RAG工具或空tools
        tools = []
        if use_rag:
            rag_tool = self._create_rag_tool(
                doc_path=rag_config['doc_path'],
                tool_name=rag_config['tool_name'],
                tool_description=rag_config['tool_description'],
                persist_path=rag_config['persist_path']
            )
            tools = [rag_tool]

        # 2. 创建 Agent 的大脑 LLM
        agent_llm = ChatOpenAI(
            model_name=llm_model or self.agent_llm_model,
            openai_api_base=llm_base_url or self.llm_base_url,
            openai_api_key=SILICONFLOW_API_KEY,
            temperature=temperature
        )
        
        # 3. 创建带有"个性"的 Prompt 模板
        if use_memory:
            template = f"""
            {personality}

            You have access to the following tools:
            {{tools}}

            Use the following format:

            Thought: Do I need to use a tool? Yes
            Action: the action to take, should be one of [{{tool_names}}]
            Action Input: the input to the action
            Observation: the result of the action

            When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:
            Thought: Do I need to use a tool? No
            Final Answer: [your response here]

            Begin!

            Previous conversation history:
            {{chat_history}}

            New input: {{input}}
            {{agent_scratchpad}}
            """
        else:
            template = f"""
            {personality}

            You have access to the following tools:
            {{tools}}

            Use the following format:

            Thought: Do I need to use a tool? Yes
            Action: the action to take, should be one of [{{tool_names}}]
            Action Input: the input to the action
            Observation: the result of the action

            When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:
            Thought: Do I need to use a tool? No
            Final Answer: [your response here]

            Begin!

            New input: {{input}}
            {{agent_scratchpad}}
            """
        prompt = PromptTemplate.from_template(template)

        # 4. 创建 Agent 和执行器
        if use_memory:
            memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            agent = create_react_agent(agent_llm, tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=True,
                handle_parsing_errors=True
            )
        else:
            agent = create_react_agent(agent_llm, tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True
            )
        print(f"======= Agent: {rag_config['tool_name']} 创建成功! =======")
        return agent_executor


# # --- 3. 如何使用工厂 ---
# def main():
#     # 实例化工厂
#     factory = AgentFactory()

#     # 定义第一个 Agent: Python 专家
#     python_rag_config = {
#         "doc_path": "python_expert.txt",
#         "tool_name": "Python专业知识库",
#         "tool_description": "当你需要回答关于Python编程语言的专业问题时，请使用这个工具。例如GIL、多线程、装饰器等。",
#         "persist_path": "./db/python_db"
#     }
#     python_personality = "你是一个资深的Python技术专家，精通Python底层原理和高级用法。你的回答严谨、专业、深入浅出。"
#     python_agent = factory.create_agent(
#         personality=python_personality,
#         rag_config=python_rag_config,
#         temperature=0.2
#     )

#     # 定义第二个 Agent: 项目经理
#     pm_rag_config = {
#         "doc_path": "project_manager.txt",
#         "tool_name": "项目管理知识库",
#         "tool_description": "当你需要回答关于项目管理、敏捷开发、Scrum等问题时，请使用这个工具。",
#         "persist_path": "./db/pm_db"
#     }
#     pm_personality = "你是一个经验丰富的项目经理，擅长敏捷开发和团队沟通。你的回答注重实践、流程和协作。"
#     pm_agent = factory.create_agent(
#         personality=pm_personality,
#         rag_config=pm_rag_config,
#         temperature=0.7
#     )

#     # --- 和 Agent 交互 ---
#     # 你可以选择和哪个 Agent 对话
#     print("\n--- 现在与 Python 专家对话 ---")
    
#     # --- 这是修改后的流式输出代码 ---
#     print("\n[Python 专家]: ", end="", flush=True)
#     # 循环处理 stream 返回的每一个数据块
#     for chunk in python_agent.stream({"input": "请解释一下Python的GIL是什么？"}):
#         # 检查这个数据块中是否包含我们想要的'output'键
#         if "output" in chunk:
#             # 如果有，就打印'output'的值。
#             # end="" 表示打印后不换行，让文字在同一行连续输出。
#             # flush=True 表示立即将内容输出到控制台，而不是等待缓冲区满了再输出。
#             print(chunk["output"], end="", flush=True)
#     # 整个流结束后，打印一个换行符，让下次的提示符在新的一行开始。
#     print()
    
#     print("\n--- 现在与项目经理对话 ---")
#     result = pm_agent.invoke({"input": "敏捷开发的核心价值观是什么？"})
#     print("\n[项目经理]:", result['output'])

#     # 也可以创建一个交互式循环，让用户选择和谁聊天
#     # ... 此处可以添加一个聊天循环 ...

# if __name__ == "__main__":
#     main()
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
        self.knowledge_bases = {}  # 新增：存储多知识库配置
        print(f"工厂已初始化，默认 Agent LLM 为: {self.agent_llm_model}")

    def register_knowledge_base(self, name: str, rag_config: dict, personality: str):
        """
        注册一个知识库配置，供后续按名称创建agent。
        name: 唯一标识
        rag_config: RAG配置
        personality: agent个性
        """
        self.knowledge_bases[name] = {
            "rag_config": rag_config,
            "personality": personality
        }
        print(f"知识库 '{name}' 已注册")

    def list_knowledge_bases(self):
        """返回所有已注册知识库名称"""
        return list(self.knowledge_bases.keys())

    def create_agent_by_kb_name(self, name: str, **kwargs):
        """
        按知识库名称创建agent。
        kwargs可覆盖rag_config/personality/temperature等。
        """
        if name not in self.knowledge_bases:
            raise ValueError(f"知识库 '{name}' 未注册")
        kb = self.knowledge_bases[name]
        rag_config = kwargs.get("rag_config", kb["rag_config"])
        personality = kwargs.get("personality", kb["personality"])
        temperature = kwargs.get("temperature", 0.7)
        use_memory = kwargs.get("use_memory", False)
        use_rag = kwargs.get("use_rag", True)
        llm_model = kwargs.get("llm_model")
        llm_base_url = kwargs.get("llm_base_url")
        embedding_model = kwargs.get("embedding_model")
        embedding_base_url = kwargs.get("embedding_base_url")
        return self.create_agent(
            personality=personality,
            rag_config=rag_config,
            temperature=temperature,
            use_memory=use_memory,
            use_rag=use_rag,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            embedding_model=embedding_model,
            embedding_base_url=embedding_base_url
        )

    def _create_rag_tool(self, doc_path: str = None, tool_name: str = None, tool_description: str = None, persist_path: str = None, doc_paths: list = None) -> Tool:
        """
        支持多文件知识库加载：doc_paths为文件路径列表，兼容单文件doc_path。
        """
        print(f"--- 正在为 '{tool_name}' 创建RAG工具 ---")
        print(f"知识库路径: {doc_paths if doc_paths else doc_path}")
        print(f"向量数据库持久化路径: {persist_path}")

        # 1. 加载和分割文档
        all_docs = []
        if doc_paths:
            for path in doc_paths:
                loader = TextLoader(path, encoding="utf-8")
                docs = loader.load()
                all_docs.extend(docs)
        elif doc_path:
            loader = TextLoader(doc_path, encoding="utf-8")
            docs = loader.load()
            all_docs.extend(docs)
        else:
            raise ValueError("必须提供doc_path或doc_paths")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        documents = text_splitter.split_documents(all_docs)

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
                doc_path=rag_config.get('doc_path'),
                doc_paths=rag_config.get('doc_paths'),
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

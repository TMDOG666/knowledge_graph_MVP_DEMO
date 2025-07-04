document.addEventListener('DOMContentLoaded', () => {
    const API_URL = 'http://xxx:5000'; // 你的FastAPI地址
    let network = null;
    let nodes = new vis.DataSet([]);
    let edges = new vis.DataSet([]);
    let selectedNodeId = null;

    // 初始化图谱
    function initGraph() {
        const container = document.getElementById('mynetwork');
        const data = { nodes, edges };
        const options = {
            edges: { arrows: 'to' },
            interaction: { navigationButtons: true, keyboard: true }
        };
        network = new vis.Network(container, data, options);

        // 监听节点点击事件
        network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                selectNode(nodeId);
            }
        });
    }

    // 从后端加载图谱数据
    async function loadGraphData() {
        try {
            const response = await fetch(`${API_URL}/api/graph`);
            const data = await response.json();
            nodes.clear();
            edges.clear();
            nodes.add(data.nodes);
            edges.add(data.edges);
        } catch (error) {
            console.error('Error loading graph data:', error);
        }
    }

    // 添加新节点
    document.getElementById('add-node-btn').addEventListener('click', async () => {
        const title = document.getElementById('node-title').value;
        if (!title) return alert('Please enter a title.');

        const response = await fetch(`${API_URL}/api/nodes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_type: 'knowledge', title: title })
        });
        const newNode = await response.json();
        nodes.add(newNode);
        document.getElementById('node-title').value = '';
    });
    
    // 选中一个节点，显示聊天面板
    function selectNode(nodeId) {
        selectedNodeId = nodeId;
        const node = nodes.get(nodeId);
        
        const chatPanel = document.getElementById('chat-panel');
        chatPanel.classList.remove('hidden');
        document.getElementById('chat-title').innerText = `Chat about: ${node.label}`;
        
        loadChatHistory(nodeId);
    }
    
    // 加载聊天记录
    async function loadChatHistory(nodeId) {
        const chatHistoryDiv = document.getElementById('chat-history');
        chatHistoryDiv.innerHTML = 'Loading...';
        
        const response = await fetch(`${API_URL}/api/chats/${nodeId}`);
        const history = await response.json();
        
        chatHistoryDiv.innerHTML = '';
        history.forEach(msg => {
            appendMessage('human', msg.human);
            appendMessage('ai', msg.ai);
        });
    }
    
    // 发送聊天消息
    document.getElementById('send-chat-btn').addEventListener('click', async () => {
        if (!selectedNodeId) return alert('Please select a node first.');
        const input = document.getElementById('chat-input');
        const prompt = input.value;
        if (!prompt) return;

        appendMessage('human', prompt);
        input.value = '';
        
        const response = await fetch(`${API_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: selectedNodeId, prompt: prompt })
        });
        const data = await response.json();
        appendMessage('ai', data.response);
    });

    // 辅助函数：在聊天窗口追加消息
    function appendMessage(sender, text) {
        const chatHistoryDiv = document.getElementById('chat-history');
        const msgDiv = document.createElement('div');
        msgDiv.classList.add(sender === 'human' ? 'human-msg' : 'ai-msg');
        msgDiv.innerText = text;
        chatHistoryDiv.appendChild(msgDiv);
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight; // 自动滚动到底部
    }

    // 刷新下拉框选项
    function refreshNodeSelectOptions() {
        const sourceSelect = document.getElementById('edge-source');
        const targetSelect = document.getElementById('edge-target');
        if (!sourceSelect || !targetSelect) return;
        sourceSelect.innerHTML = '';
        targetSelect.innerHTML = '';
        nodes.forEach(node => {
            const option1 = document.createElement('option');
            option1.value = node.id;
            option1.text = node.label;
            sourceSelect.appendChild(option1);

            const option2 = document.createElement('option');
            option2.value = node.id;
            option2.text = node.label;
            targetSelect.appendChild(option2);
        });
    }

    // 每次节点变化后刷新下拉框
    nodes.on('*', refreshNodeSelectOptions);

    // 添加边按钮事件
    const addEdgeBtn = document.getElementById('add-edge-btn');
    if (addEdgeBtn) {
        addEdgeBtn.addEventListener('click', async () => {
            const source_id = document.getElementById('edge-source').value;
            const target_id = document.getElementById('edge-target').value;
            const edge_type = "default"; // 可根据需要扩展为用户输入
            const label = ""; // 可根据需要扩展为用户输入
            if (!source_id || !target_id) return alert('请选择起点和终点');
            if (source_id === target_id) return alert('不能连接自己');
            try {
                const response = await fetch(`${API_URL}/api/edges`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ source_id, target_id, edge_type, label })
                });
                if (!response.ok) throw new Error('添加边失败');
                const newEdge = await response.json();
                edges.add({from: source_id, to: target_id, type: edge_type, label: label});
            } catch (error) {
                alert('添加边失败: ' + error.message);
            }
        });
    }

    // --- 初始化 ---
    initGraph();
    loadGraphData();
    refreshNodeSelectOptions();
});
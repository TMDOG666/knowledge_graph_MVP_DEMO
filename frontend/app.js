document.addEventListener('DOMContentLoaded', () => {
    const API_URL = 'http://127.0.0.1:8000'; // 你的FastAPI地址
    let network = null;
    let nodes = new vis.DataSet([]);
    let edges = new vis.DataSet([]);
    let selectedNodeId = null;
    let currentTopicId = null;
    let editingTopic = null;
    let editingDocPaths = [];

    // 强制初始化隐藏编辑主题弹框
    document.getElementById('edit-topic-modal').classList.add('hidden');

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
        if (!currentTopicId) {
            nodes.clear();
            edges.clear();
            return;
        }
        try {
            // 假设后端支持按主题id加载图谱
            const response = await fetch(`${API_URL}/api/graph?topic_id=${currentTopicId}`);
            const data = await response.json();
            nodes.clear();
            edges.clear();
            nodes.add(data.nodes);
            edges.add(data.edges);
        } catch (error) {
            nodes.clear();
            edges.clear();
            console.error('Error loading graph data:', error);
        }
    }

    // 添加新节点
    document.getElementById('add-node-btn').addEventListener('click', async () => {
        const title = document.getElementById('node-title').value;
        if (!title) return alert('Please enter a title.');

        const response = await fetch(`${API_URL}/api/nodes?topic_id=${currentTopicId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_type: 'knowledge', title: title })
        });
        const newNode = await response.json();
        nodes.add(newNode);
        document.getElementById('node-title').value = '';
    });
    
    // 选中一个节点，显示聊天面板和编辑面板
    function selectNode(nodeId) {
        selectedNodeId = nodeId;
        const node = nodes.get(nodeId);
        
        // 显示聊天面板
        const chatPanel = document.getElementById('chat-panel');
        chatPanel.classList.remove('hidden');
        document.getElementById('chat-title').innerText = `Chat about: ${node.label}`;
        
        // 显示编辑面板并填充数据
        const editSection = document.getElementById('edit-node-section');
        editSection.style.display = 'block';
        
        document.getElementById('edit-node-title').value = node.label || '';
        document.getElementById('edit-node-content').value = node.content || '';
        document.getElementById('edit-node-tags').value = (node.tags || []).join(', ');
        
        loadChatHistory(nodeId);
    }
    
    // 更新节点
    document.getElementById('update-node-btn').addEventListener('click', async () => {
        if (!selectedNodeId) return alert('Please select a node first.');
        
        const title = document.getElementById('edit-node-title').value;
        const content = document.getElementById('edit-node-content').value;
        const tagsStr = document.getElementById('edit-node-tags').value;
        const tags = tagsStr ? tagsStr.split(',').map(tag => tag.trim()).filter(tag => tag) : [];
        
        try {
            const response = await fetch(`${API_URL}/api/nodes/${selectedNodeId}?topic_id=${currentTopicId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content, tags })
            });
            
            if (response.ok) {
                // 更新本地数据
                const node = nodes.get(selectedNodeId);
                node.label = title;
                node.content = content;
                node.tags = tags;
                nodes.update(node);
                alert('Node updated successfully!');
            } else {
                alert('Failed to update node');
            }
        } catch (error) {
            alert('Error updating node: ' + error.message);
        }
    });
    
    // 删除节点
    document.getElementById('delete-node-btn').addEventListener('click', async () => {
        if (!selectedNodeId) return alert('Please select a node first.');
        
        if (!confirm('Are you sure you want to delete this node? This will also delete all connected edges.')) {
            return;
        }
        
        try {
            const response = await fetch(`${API_URL}/api/nodes/${selectedNodeId}?topic_id=${currentTopicId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // 从本地数据中删除
                nodes.remove(selectedNodeId);
                // 隐藏编辑面板
                document.getElementById('edit-node-section').style.display = 'none';
                document.getElementById('chat-panel').classList.add('hidden');
                selectedNodeId = null;
                alert('Node deleted successfully!');
            } else {
                alert('Failed to delete node');
            }
        } catch (error) {
            alert('Error deleting node: ' + error.message);
        }
    });
    
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
        const deleteSourceSelect = document.getElementById('delete-edge-source');
        const deleteTargetSelect = document.getElementById('delete-edge-target');
        
        if (!sourceSelect || !targetSelect || !deleteSourceSelect || !deleteTargetSelect) return;
        
        // 清空所有下拉框
        sourceSelect.innerHTML = '';
        targetSelect.innerHTML = '';
        deleteSourceSelect.innerHTML = '';
        deleteTargetSelect.innerHTML = '';
        
        nodes.forEach(node => {
            const option1 = document.createElement('option');
            option1.value = node.id;
            option1.text = node.label;
            sourceSelect.appendChild(option1);

            const option2 = document.createElement('option');
            option2.value = node.id;
            option2.text = node.label;
            targetSelect.appendChild(option2);
            
            const option3 = document.createElement('option');
            option3.value = node.id;
            option3.text = node.label;
            deleteSourceSelect.appendChild(option3);
            
            const option4 = document.createElement('option');
            option4.value = node.id;
            option4.text = node.label;
            deleteTargetSelect.appendChild(option4);
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
                const response = await fetch(`${API_URL}/api/edges?topic_id=${currentTopicId}`, {
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

    // 删除边按钮事件
    const deleteEdgeBtn = document.getElementById('delete-edge-btn');
    if (deleteEdgeBtn) {
        deleteEdgeBtn.addEventListener('click', async () => {
            const source_id = document.getElementById('delete-edge-source').value;
            const target_id = document.getElementById('delete-edge-target').value;
            if (!source_id || !target_id) return alert('请选择起点和终点');
            
            if (!confirm('Are you sure you want to delete this edge?')) {
                return;
            }
            
            try {
                const response = await fetch(`${API_URL}/api/edges?source_id=${source_id}&target_id=${target_id}&topic_id=${currentTopicId}`, {
                    method: 'DELETE'
                });
                if (!response.ok) throw new Error('删除边失败');
                
                // 从本地数据中删除边
                const edgeToRemove = edges.get().find(edge => 
                    edge.from === source_id && edge.to === target_id
                );
                if (edgeToRemove) {
                    edges.remove(edgeToRemove.id);
                }
                alert('边删除成功!');
            } catch (error) {
                alert('删除边失败: ' + error.message);
            }
        });
    }

    // 主题相关
    async function loadTopics() {
        const topicListDiv = document.getElementById('topic-list');
        topicListDiv.innerHTML = '加载中...';
        try {
            const resp = await fetch(`${API_URL}/api/topics`);
            const topics = await resp.json();
            topicListDiv.innerHTML = '';
            if (topics.length === 0) {
                topicListDiv.innerHTML = '<div style="color:#888">暂无主题</div>';
                return;
            }
            topics.forEach(topic => {
                const wrap = document.createElement('div');
                wrap.style.display = 'flex';
                wrap.style.alignItems = 'center';
                wrap.style.marginBottom = '6px';
                const btn = document.createElement('button');
                btn.textContent = topic.name;
                btn.className = 'topic-btn';
                btn.style.flex = '1';
                btn.onclick = () => switchTopic(topic.id);
                if (topic.id === currentTopicId) btn.style.background = '#007bff';
                wrap.appendChild(btn);
                // 编辑按钮
                const editBtn = document.createElement('button');
                editBtn.textContent = '编辑';
                editBtn.style.marginLeft = '6px';
                editBtn.style.background = '#ffc107';
                editBtn.style.color = '#333';
                editBtn.style.fontSize = '13px';
                editBtn.onclick = () => openEditTopicModal(topic);
                wrap.appendChild(editBtn);
                topicListDiv.appendChild(wrap);
            });
        } catch (e) {
            topicListDiv.innerHTML = '加载失败';
        }
    }

    async function switchTopic(topicId) {
        currentTopicId = topicId;
        await loadGraphData();
        // 清空右侧面板
        document.getElementById('edit-node-section').style.display = 'none';
        document.getElementById('chat-panel').classList.add('hidden');
        selectedNodeId = null;
        loadTopics(); // 刷新高亮
    }

    // 编辑主题弹窗逻辑
    function openEditTopicModal(topic) {
        editingTopic = topic;
        editingDocPaths = [...(topic.doc_paths || [])];
        document.getElementById('edit-topic-modal').classList.remove('hidden');
        document.getElementById('edit-topic-name').value = topic.name || '';
        document.getElementById('edit-topic-personality').value = topic.personality || '';
        document.getElementById('edit-topic-use-rag').checked = !!(topic.rag_config && topic.rag_config.use_rag !== false && topic.rag_config.use_rag !== 'false');
        renderEditTopicDocsList(editingDocPaths);
        document.getElementById('edit-topic-add-files').value = '';
    }
    document.getElementById('close-edit-topic').onclick = () => {
        document.getElementById('edit-topic-modal').classList.add('hidden');
        editingTopic = null;
        editingDocPaths = [];
        console.log('弹框已关闭');
    };
    function renderEditTopicDocsList(docPaths) {
        const listDiv = document.getElementById('edit-topic-docs-list');
        listDiv.innerHTML = '';
        docPaths.forEach((path, idx) => {
            const item = document.createElement('div');
            item.className = 'doc-item';
            const span = document.createElement('span');
            span.textContent = path.split('/').pop();
            item.appendChild(span);
            const rmBtn = document.createElement('button');
            rmBtn.textContent = '移除';
            rmBtn.className = 'remove-doc-btn';
            rmBtn.onclick = () => {
                editingDocPaths.splice(idx, 1);
                renderEditTopicDocsList(editingDocPaths);
            };
            item.appendChild(rmBtn);
            listDiv.appendChild(item);
        });
    }
    // 编辑主题表单提交
    document.getElementById('edit-topic-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!editingTopic) return;
        const name = document.getElementById('edit-topic-name').value;
        const personality = document.getElementById('edit-topic-personality').value;
        const use_rag = document.getElementById('edit-topic-use-rag').checked;
        const addFiles = document.getElementById('edit-topic-add-files').files;
        let doc_paths = [...editingDocPaths];
        if (addFiles.length > 0) {
            // 上传新文件到后端，复用创建逻辑
            const formData = new FormData();
            formData.append('name', name);
            formData.append('personality', personality);
            for (let i = 0; i < addFiles.length; i++) {
                formData.append('files', addFiles[i]);
            }
            // 用POST /api/topics上传文件，取返回的doc_paths
            const resp = await fetch(`${API_URL}/api/topics`, { method: 'POST', body: formData });
            if (resp.ok) {
                const newTopic = await resp.json();
                doc_paths = [...doc_paths, ...newTopic.doc_paths.filter(p => !doc_paths.includes(p))];
            } else {
                alert('文件上传失败');
                return;
            }
        }
        // 构造rag_config
        const rag_config = Object.assign({}, editingTopic.rag_config || {}, {
            use_rag,
            doc_paths,
            tool_name: `${name}知识库`,
            tool_description: `${name}领域的知识库。`,
            persist_path: editingTopic.rag_config ? editingTopic.rag_config.persist_path : `./db/${editingTopic.id}_db`
        });
        // PUT /api/topics/{id}
        const resp = await fetch(`${API_URL}/api/topics/${editingTopic.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, personality, rag_config, doc_paths })
        });
        if (resp.ok) {
            alert('主题已更新');
            document.getElementById('edit-topic-modal').classList.add('hidden');
            editingTopic = null;
            editingDocPaths = [];
            await loadTopics();
        } else {
            alert('主题更新失败');
        }
    });

    // 主题创建表单
    document.getElementById('create-topic-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        // 读取自定义rag_config参数
        const use_rag = document.getElementById('topic-use-rag').checked;
        const tool_name = document.getElementById('topic-tool-name').value;
        const tool_description = document.getElementById('topic-tool-desc').value;
        // 通过FormData传递自定义rag_config
        formData.append('use_rag', use_rag ? 'true' : 'false');
        if (tool_name) formData.append('tool_name', tool_name);
        if (tool_description) formData.append('tool_description', tool_description);
        try {
            const resp = await fetch(`${API_URL}/api/topics`, {
                method: 'POST',
                body: formData
            });
            if (!resp.ok) {
                const err = await resp.json();
                alert(err.error || '主题创建失败');
                return;
            }
            form.reset();
            // 默认勾选知识库
            document.getElementById('topic-use-rag').checked = true;
            await loadTopics();
            alert('主题创建成功！');
        } catch (err) {
            alert('主题创建失败: ' + err.message);
        }
    });

    // 初始化
    initGraph();
    loadTopics().then(async () => {
        // 默认选中第一个主题
        const topicListDiv = document.getElementById('topic-list');
        const btn = topicListDiv.querySelector('button');
        if (btn) {
            btn.click();
        }
    });
});
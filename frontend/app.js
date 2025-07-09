document.addEventListener('DOMContentLoaded', () => {

    // --- 1. 全局状态与配置 ---
    const state = {
        network: null,
        nodes: new vis.DataSet([]),
        edges: new vis.DataSet([]),
        selectedNodeId: null,
        currentTopicId: null,
        editingTopic: null,
        editingDocPaths: [],
    };

    // --- 2. DOM 元素缓存 ---
    const DOM = {
        apiUrl: 'http://127.0.0.1:8000', // 你的FastAPI地址
        
        // 主题栏
        topicList: document.getElementById('topic-list'),
        createTopicForm: document.getElementById('create-topic-form'),
        topicNameInput: document.getElementById('topic-name'),
        topicUseRagCheckbox: document.getElementById('topic-use-rag'),
        topicToolNameInput: document.getElementById('topic-tool-name'),
        topicToolDescInput: document.getElementById('topic-tool-desc'),
        
        // 主题编辑弹窗
        editTopicModal: document.getElementById('edit-topic-modal'),
        closeEditTopicBtn: document.getElementById('close-edit-topic'),
        editTopicForm: document.getElementById('edit-topic-form'),
        editTopicNameInput: document.getElementById('edit-topic-name'),
        editTopicPersonalityTextarea: document.getElementById('edit-topic-personality'),
        editTopicUseRagCheckbox: document.getElementById('edit-topic-use-rag'),
        editTopicDocsList: document.getElementById('edit-topic-docs-list'),
        editTopicAddFilesInput: document.getElementById('edit-topic-add-files'),

        // 图谱容器
        graphContainer: document.getElementById('mynetwork'),

        // 右侧操作面板
        addNodeBtn: document.getElementById('add-node-btn'),
        nodeTitleInput: document.getElementById('node-title'),
        editNodeSection: document.getElementById('edit-node-section'),
        editNodeTitleInput: document.getElementById('edit-node-title'),
        editNodeContentTextarea: document.getElementById('edit-node-content'),
        editNodeTagsInput: document.getElementById('edit-node-tags'),
        updateNodeBtn: document.getElementById('update-node-btn'),
        deleteNodeBtn: document.getElementById('delete-node-btn'),

        // 边操作
        edgeSourceSelect: document.getElementById('edge-source'),
        edgeTargetSelect: document.getElementById('edge-target'),
        addEdgeBtn: document.getElementById('add-edge-btn'),
        deleteEdgeSourceSelect: document.getElementById('delete-edge-source'),
        deleteEdgeTargetSelect: document.getElementById('delete-edge-target'),
        deleteEdgeBtn: document.getElementById('delete-edge-btn'),
        
        // 聊天面板
        chatPanel: document.getElementById('chat-panel'),
        chatTitle: document.getElementById('chat-title'),
        chatHistory: document.getElementById('chat-history'),
        chatInput: document.getElementById('chat-input'),
        sendChatBtn: document.getElementById('send-chat-btn'),
    };

    // --- 3. API 通信 ---
    /**
     * 封装的 API 请求函数
     * @param {string} endpoint - API 端点，例如 '/api/topics'
     * @param {object} options - fetch 的配置对象
     * @returns {Promise<any>} - 解析后的 JSON 数据
     */
    async function apiRequest(endpoint, options = {}) {
        try {
            const response = await fetch(`${DOM.apiUrl}${endpoint}`, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || 'API request failed');
            }
            // 如果 DELETE 请求成功，可能没有 body
            if (options.method === 'DELETE' && response.status === 204) {
                return null;
            }
            return response.json();
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            alert(`操作失败: ${error.message}`);
            throw error; // 重新抛出错误，以便调用者可以捕获
        }
    }

    // --- 4. UI 渲染与更新 ---

    /** 渲染主题列表 */
    function renderTopics(topics) {
        DOM.topicList.innerHTML = '';
        if (topics.length === 0) {
            DOM.topicList.innerHTML = '<div style="color:#888; padding: 10px;">暂无主题，请在下方创建。</div>';
            return;
        }
        topics.forEach(topic => {
            const topicItem = document.createElement('div');
            topicItem.className = 'topic-item';
            topicItem.textContent = topic.name;
            topicItem.onclick = () => switchTopic(topic.id);

            // IMPORTANT: 使用 classList.add('active') 来高亮当前主题
            if (topic.id === state.currentTopicId) {
                topicItem.classList.add('active');
            }

            const editBtn = document.createElement('button');
            editBtn.innerHTML = '✎'; // Pencil icon
            editBtn.title = '编辑主题';
            editBtn.className = 'edit-topic-btn'; // 可以为编辑按钮添加特定样式
            editBtn.style.cssText = `
                background: none; border: none; font-size: 16px; cursor: pointer; 
                padding: 5px; color: inherit; margin-left: 10px;`;
            editBtn.onclick = (e) => {
                e.stopPropagation(); // 防止触发 switchTopic
                openEditTopicModal(topic);
            };
            
            topicItem.appendChild(editBtn);
            DOM.topicList.appendChild(topicItem);
        });
    }

    /** 渲染编辑主题弹窗中的文档列表 */
    function renderEditTopicDocsList(docPaths) {
        DOM.editTopicDocsList.innerHTML = '';
        docPaths.forEach((path, idx) => {
            const item = document.createElement('div');
            item.className = 'doc-item';
            const span = document.createElement('span');
            span.textContent = path.split(/[\\/]/).pop(); // 兼容 Windows 和 Unix 路径
            span.title = path;
            item.appendChild(span);

            const rmBtn = document.createElement('button');
            rmBtn.innerHTML = '×';
            rmBtn.className = 'remove-doc-btn';
            rmBtn.title = '移除此文件';
            rmBtn.onclick = () => {
                state.editingDocPaths.splice(idx, 1);
                renderEditTopicDocsList(state.editingDocPaths);
            };
            item.appendChild(rmBtn);
            DOM.editTopicDocsList.appendChild(item);
        });
    }
    
    /** 刷新添加/删除边的下拉框 */
    function refreshNodeSelectOptions() {
        const selects = [DOM.edgeSourceSelect, DOM.edgeTargetSelect, DOM.deleteEdgeSourceSelect, DOM.deleteEdgeTargetSelect];
        selects.forEach(select => select.innerHTML = '');

        const allNodes = state.nodes.get({ fields: ['id', 'label'] });
        allNodes.forEach(node => {
            selects.forEach(select => {
                // 使用 new Option() 构造函数，更简洁
                select.add(new Option(node.label, node.id));
            });
        });
    }

    /** 在聊天窗口追加消息 */
    function appendMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add(sender === 'human' ? 'human-msg' : 'ai-msg');
        // 使用marked解析markdown，并插入为HTML
        msgDiv.innerHTML = marked.parse(text);
        DOM.chatHistory.appendChild(msgDiv);
        DOM.chatHistory.scrollTop = DOM.chatHistory.scrollHeight;
    }

    /** 重置右侧面板状态 */
    function resetSidePanel() {
        DOM.editNodeSection.classList.add('hidden');
        DOM.chatPanel.classList.add('hidden');
        state.selectedNodeId = null;
    }

    // --- 5. 核心业务逻辑 ---

    /** 初始化图谱 */
    function initGraph() {
        const data = { nodes: state.nodes, edges: state.edges };
        const options = {
            edges: { 
                arrows: 'to',
                color: {
                    color: '#848484',
                    highlight: '#007aff',
                    hover: '#2998ff'
                },
                smooth: {
                    enabled: true,
                    type: "dynamic"
                }
            },
            nodes: {
                shape: 'dot',
                size: 16,
                font: {
                    size: 14,
                    color: '#333'
                },
                borderWidth: 2
            },
            interaction: { navigationButtons: true, keyboard: true, hover: true },
            physics: {
                forceAtlas2Based: {
                    gravitationalConstant: -26,
                    centralGravity: 0.005,
                    springLength: 230,
                    springConstant: 0.18
                },
                maxVelocity: 146,
                solver: 'forceAtlas2Based',
                timestep: 0.35,
                stabilization: { iterations: 150 }
            }
        };
        state.network = new vis.Network(DOM.graphContainer, data, options);
        state.network.on('click', (params) => {
            if (params.nodes.length > 0) {
                selectNode(params.nodes[0]);
            } else {
                resetSidePanel();
            }
        });
        state.nodes.on('*', refreshNodeSelectOptions);
    }
    
    /** 切换当前主题 */
    async function switchTopic(topicId) {
        state.currentTopicId = topicId;
        resetSidePanel();
        await loadGraphData();
        await loadTopics(); // 重新加载以更新高亮
    }
    
    /** 加载主题列表 */
    async function loadTopics() {
        DOM.topicList.innerHTML = '<div style="padding: 10px;">加载中...</div>';
        try {
            const topics = await apiRequest('/api/topics');
            renderTopics(topics);
            // 如果没有当前选中的主题，并且列表不为空，则默认选中第一个
            if (!state.currentTopicId && topics.length > 0) {
                await switchTopic(topics[0].id);
            }
        } catch (error) {
            DOM.topicList.innerHTML = '<div style="color: red; padding: 10px;">加载主题失败</div>';
        }
    }
    
    /** 加载图谱数据 */
    async function loadGraphData() {
        state.nodes.clear();
        state.edges.clear();
        if (!state.currentTopicId) return;

        try {
            const data = await apiRequest(`/api/graph?topic_id=${state.currentTopicId}`);
            state.nodes.add(data.nodes);
            state.edges.add(data.edges);
        } catch (error) {
            console.error('Error loading graph data:', error);
        }
    }
    
    /** 选中节点，显示相关面板 */
    function selectNode(nodeId) {
        state.selectedNodeId = nodeId;
        const node = state.nodes.get(nodeId);
        
        // 显示聊天面板
        DOM.chatPanel.classList.remove('hidden');
        DOM.chatTitle.textContent = `关于 "${node.label}" 的对话`;
        loadChatHistory(nodeId);
        
        // 显示编辑面板并填充数据
        DOM.editNodeSection.classList.remove('hidden');
        DOM.editNodeTitleInput.value = node.label || '';
        DOM.editNodeContentTextarea.value = node.content || '';
        DOM.editNodeTagsInput.value = (node.tags || []).join(', ');
    }

    /** 加载聊天记录 */
    async function loadChatHistory(nodeId) {
        DOM.chatHistory.innerHTML = '<div style="color:#888; text-align:center; padding: 10px;">加载记录中...</div>';
        try {
            const history = await apiRequest(`/api/chats/${nodeId}`);
            DOM.chatHistory.innerHTML = '';
            if (history.length === 0) {
                 DOM.chatHistory.innerHTML = '<div style="color:#888; text-align:center; padding: 10px;">暂无对话记录</div>';
            }
            history.forEach(msg => {
                if (msg.human) appendMessage('human', msg.human);
                if (msg.ai) appendMessage('ai', msg.ai);
            });
        } catch (error) {
            DOM.chatHistory.innerHTML = '<div style="color:red; text-align:center; padding: 10px;">加载失败</div>';
        }
    }
    
    /** 打开编辑主题弹窗 */
    function openEditTopicModal(topic) {
        state.editingTopic = topic;
        state.editingDocPaths = [...(topic.doc_paths || [])];
        
        DOM.editTopicNameInput.value = topic.name || '';
        DOM.editTopicPersonalityTextarea.value = topic.personality || '';
        DOM.editTopicUseRagCheckbox.checked = !!(topic.rag_config && topic.rag_config.use_rag !== false);
        DOM.editTopicAddFilesInput.value = '';
        renderEditTopicDocsList(state.editingDocPaths);
        
        // 修复弹窗无法弹出：移除 hidden，添加 visible
        DOM.editTopicModal.classList.remove('hidden');
        DOM.editTopicModal.classList.add('visible');
    }

    /** 关闭编辑主题弹窗 */
    function closeEditTopicModal() {
        // 修复弹窗关闭：移除 visible，添加 hidden
        DOM.editTopicModal.classList.remove('visible');
        DOM.editTopicModal.classList.add('hidden');
        state.editingTopic = null;
        state.editingDocPaths = [];
    }

    // --- 6. 事件监听器 ---

    // 创建主题
    DOM.createTopicForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(DOM.createTopicForm);
        // 手动添加复选框状态，因为 FormData 不会包含未勾选的复选框
        formData.append('use_rag', DOM.topicUseRagCheckbox.checked ? 'true' : 'false');

        try {
            await apiRequest('/api/topics', { method: 'POST', body: formData });
            alert('主题创建成功！');
            DOM.createTopicForm.reset();
            DOM.topicUseRagCheckbox.checked = true; // 保持默认勾选
            await loadTopics();
        } catch (error) {
            // apiRequest 已经 alert 了错误信息
        }
    });

    // 编辑主题
    DOM.editTopicForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!state.editingTopic) return;

        // 使用 FormData 处理文件上传和普通字段
        const formData = new FormData();
        formData.append('name', DOM.editTopicNameInput.value);
        formData.append('personality', DOM.editTopicPersonalityTextarea.value);
        formData.append('use_rag', DOM.editTopicUseRagCheckbox.checked);
        
        // 添加需要保留的旧文件路径
        state.editingDocPaths.forEach(path => formData.append('existing_doc_paths', path));

        // 添加新上传的文件
        const newFiles = DOM.editTopicAddFilesInput.files;
        for (let i = 0; i < newFiles.length; i++) {
            formData.append('files', newFiles[i]);
        }

        try {
            // 后端需要调整为接收 FormData
            await apiRequest(`/api/topics/${state.editingTopic.id}`, {
                method: 'PUT',
                body: formData
            });
            alert('主题已更新');
            closeEditTopicModal();
            await loadTopics(); // 刷新列表以显示新名称
        } catch (error) {
             // apiRequest 已经 alert 了错误信息
        }
    });

    DOM.closeEditTopicBtn.addEventListener('click', closeEditTopicModal);

    // 添加节点
    DOM.addNodeBtn.addEventListener('click', async () => {
        const title = DOM.nodeTitleInput.value.trim();
        if (!title) return alert('请输入节点标题。');
        if (!state.currentTopicId) return alert('请先选择一个主题。');

        try {
            const newNode = await apiRequest(`/api/nodes?topic_id=${state.currentTopicId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_type: 'knowledge', title: title })
            });
            state.nodes.add(newNode);
            DOM.nodeTitleInput.value = '';
        } catch (error) { /* ignored */ }
    });

    // 更新节点
    DOM.updateNodeBtn.addEventListener('click', async () => {
        if (!state.selectedNodeId) return alert('请先选择一个节点。');
        
        const title = DOM.editNodeTitleInput.value.trim();
        const content = DOM.editNodeContentTextarea.value.trim();
        const tags = DOM.editNodeTagsInput.value.split(',').map(t => t.trim()).filter(Boolean);

        try {
            const updatedNodeData = { title, content, tags };
            await apiRequest(`/api/nodes/${state.selectedNodeId}?topic_id=${state.currentTopicId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedNodeData)
            });
            state.nodes.update({ id: state.selectedNodeId, label: title, content, tags });
            alert('节点更新成功！');
        } catch (error) { /* ignored */ }
    });
    
    // 删除节点
    DOM.deleteNodeBtn.addEventListener('click', async () => {
        if (!state.selectedNodeId) return alert('请先选择一个节点。');
        if (!confirm('确定要删除此节点吗？所有相关的边也会被删除。')) return;

        try {
            await apiRequest(`/api/nodes/${state.selectedNodeId}?topic_id=${state.currentTopicId}`, {
                method: 'DELETE'
            });
            state.nodes.remove(state.selectedNodeId);
            resetSidePanel();
            alert('节点删除成功！');
        } catch (error) { /* ignored */ }
    });

    // 添加边
    DOM.addEdgeBtn.addEventListener('click', async () => {
        const source_id = DOM.edgeSourceSelect.value;
        const target_id = DOM.edgeTargetSelect.value;
        if (!source_id || !target_id) return alert('请选择起点和终点。');
        if (source_id === target_id) return alert('节点不能连接到自身。');

        const body = { source_id, target_id, edge_type: "default", label: "" };
        try {
            const newEdge = await apiRequest(`/api/edges?topic_id=${state.currentTopicId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            state.edges.add(newEdge);
        } catch (error) { /* ignored */ }
    });
    
    // 删除边
    DOM.deleteEdgeBtn.addEventListener('click', async () => {
        const source_id = DOM.deleteEdgeSourceSelect.value;
        const target_id = DOM.deleteEdgeTargetSelect.value;
        if (!source_id || !target_id) return alert('请选择要删除的边的起点和终点。');
        
        const edgeToDelete = state.edges.get({
            filter: edge => edge.from == source_id && edge.to == target_id
        });

        if (edgeToDelete.length === 0) return alert('找不到指定的边。');
        if (!confirm('确定要删除这条边吗？')) return;

        try {
            await apiRequest(`/api/edges?source_id=${source_id}&target_id=${target_id}&topic_id=${state.currentTopicId}`, {
                method: 'DELETE'
            });
            state.edges.remove(edgeToDelete[0].id);
            alert('边删除成功！');
        } catch (error) { /* ignored */ }
    });
    
    // 发送聊天
    DOM.sendChatBtn.addEventListener('click', async () => {
        const prompt = DOM.chatInput.value.trim();
        if (!prompt) return;
        if (!state.selectedNodeId) return alert('请先选择一个节点进行对话。');
        
        appendMessage('human', prompt);
        DOM.chatInput.value = '';
        DOM.chatInput.disabled = true; // 防止连续发送

        try {
            const data = await apiRequest('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic_id: state.currentTopicId, node_id: state.selectedNodeId, prompt: prompt })
            });
            appendMessage('ai', data.response);
        } catch (error) {
             appendMessage('ai', `抱歉，出错了: ${error.message}`);
        } finally {
            DOM.chatInput.disabled = false;
            DOM.chatInput.focus();
        }
    });

    // 允许按 Enter 键发送聊天
    DOM.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            DOM.sendChatBtn.click();
        }
    });

    // --- 7. 初始化 ---
    initGraph();
    loadTopics();
});
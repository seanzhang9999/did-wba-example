// DOM元素
const serverStatusEl = document.getElementById('server-status');
const chatStatusEl = document.getElementById('chat-status');
const toggleServerBtn = document.getElementById('toggle-server');
const toggleChatBtn = document.getElementById('toggle-chat');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const chatMessages = document.getElementById('chat-messages');
const bookmarksList = document.getElementById('bookmarks-list');
const agentNameInput = document.getElementById('agent-name');
const addBookmarkBtn = document.getElementById('add-bookmark');
const clearHistoryBtn = document.getElementById('clear-history');

// 状态变量
let serverRunning = false;
let chatRunning = false;
let bookmarks = [];

// API端点
const API_BASE = '';
const API_ENDPOINTS = {
    serverStart: '/api/server/start',
    serverStop: '/api/server/stop',
    serverStatus: '/api/server/status',
    chatStart: '/api/chat/start',
    chatStop: '/api/chat/stop',
    chatStatus: '/api/chat/status',
    sendMessage: '/api/chat/send',
    getBookmarks: '/api/bookmarks',
    addBookmark: '/api/bookmarks/add'
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查服务器和聊天状态
    checkServerStatus();
    loadBookmarks();
    loadChatHistory(); // 加载聊天历史
    
    // 事件监听器
    toggleServerBtn.addEventListener('click', toggleServer);
    toggleChatBtn.addEventListener('click', toggleChat);
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    addBookmarkBtn.addEventListener('click', addBookmark);
    clearHistoryBtn.addEventListener('click', clearChatHistory);
});

// 加载聊天历史
async function loadChatHistory() {
    try {
        const response = await fetch('/api/chat/history');
        const data = await response.json();
        
        if (data.success && data.history && data.history.length > 0) {
            // 清空当前消息区域
            chatMessages.innerHTML = '';
            
            // 添加历史消息
            data.history.forEach(item => {
                if (item.type === 'user') {
                    addUserMessage(item.message);
                } else if (item.type === 'assistant') {
                    addAssistantMessage(item.message);
                } else if (item.type === 'system') {
                    addSystemMessage(item.message);
                }
            });
            
            // 滚动到底部
            scrollToBottom();
        }
    } catch (error) {
        console.error('加载聊天历史出错:', error);
    }
}

// 清除聊天历史
async function clearChatHistory() {
    try {
        const response = await fetch('/api/chat/clear-history', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            // 清空当前消息区域
            chatMessages.innerHTML = '';
            addSystemMessage('聊天历史已清除');
        }
    } catch (error) {
        console.error('清除聊天历史出错:', error);
    }
}

// 检查服务器状态
async function checkServerStatus() {
    try {
        const response = await fetch(API_ENDPOINTS.serverStatus);
        const data = await response.json();
        
        serverRunning = data.running;
        updateServerStatus();
        
        // 如果服务器在运行，检查聊天状态
        if (serverRunning) {
            checkChatStatus();
        }
    } catch (error) {
        console.error('检查服务器状态出错:', error);
        serverRunning = false;
        updateServerStatus();
    }
}

// 检查聊天状态
async function checkChatStatus() {
    try {
        const response = await fetch(API_ENDPOINTS.chatStatus);
        const data = await response.json();
        
        chatRunning = data.running;
        updateChatStatus();
    } catch (error) {
        console.error('检查聊天状态出错:', error);
        chatRunning = false;
        updateChatStatus();
    }
}

// 更新服务器状态UI
function updateServerStatus() {
    if (serverRunning) {
        serverStatusEl.textContent = '在线';
        serverStatusEl.className = 'status-badge status-online';
        toggleServerBtn.textContent = '停止服务器';
        toggleChatBtn.disabled = false;
    } else {
        serverStatusEl.textContent = '离线';
        serverStatusEl.className = 'status-badge status-offline';
        toggleServerBtn.textContent = '启动服务器';
        toggleChatBtn.disabled = true;
        
        // 如果服务器离线，聊天也必须离线
        chatRunning = false;
        updateChatStatus();
    }
}

// 更新聊天状态UI
function updateChatStatus() {
    if (chatRunning) {
        chatStatusEl.textContent = '在线';
        chatStatusEl.className = 'status-badge status-online';
        toggleChatBtn.textContent = '停止聊天';
        messageInput.disabled = false;
        sendButton.disabled = false;
    } else {
        chatStatusEl.textContent = '离线';
        chatStatusEl.className = 'status-badge status-offline';
        toggleChatBtn.textContent = '启动聊天';
        messageInput.disabled = true;
        sendButton.disabled = true;
    }
}

// 切换服务器状态
async function toggleServer() {
    try {
        const endpoint = serverRunning ? API_ENDPOINTS.serverStop : API_ENDPOINTS.serverStart;
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            serverRunning = !serverRunning;
            updateServerStatus();
            
            // 添加系统消息
            addSystemMessage(serverRunning ? '服务器已启动' : '服务器已停止');
            
            // 如果启动了服务器，检查聊天状态
            if (serverRunning) {
                checkChatStatus();
            }
        } else {
            addSystemMessage(`服务器操作失败: ${data.message}`);
        }
    } catch (error) {
        console.error('切换服务器状态出错:', error);
        addSystemMessage('服务器操作失败，请检查控制台获取详细信息');
    }
}

// 切换聊天状态
async function toggleChat() {
    if (!serverRunning) {
        addSystemMessage('请先启动服务器');
        return;
    }
    
    try {
        const endpoint = chatRunning ? API_ENDPOINTS.chatStop : API_ENDPOINTS.chatStart;
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            chatRunning = !chatRunning;
            updateChatStatus();
            
            // 添加系统消息
            addSystemMessage(chatRunning ? '聊天已启动' : '聊天已停止');
        } else {
            addSystemMessage(`聊天操作失败: ${data.message}`);
        }
    } catch (error) {
        console.error('切换聊天状态出错:', error);
        addSystemMessage('聊天操作失败，请检查控制台获取详细信息');
    }
}

// 发送消息
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    if (!chatRunning) {
        addSystemMessage('请先启动聊天');
        return;
    }
    
    // 检查是否是智能体命令
    if (message.startsWith('@') && message.includes(' ')) {
        sendAgentMessage(message);
    } else {
        sendRegularMessage(message);
    }
    
    // 清空输入框
    messageInput.value = '';
}

// 发送普通消息
async function sendRegularMessage(message) {
    // 添加用户消息到UI
    addUserMessage(message);
    
    try {
        const response = await fetch(API_ENDPOINTS.sendMessage, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 添加助手回复到UI
            addAssistantMessage(data.response);
        } else {
            addSystemMessage(`发送消息失败: ${data.message}`);
        }
    } catch (error) {
        console.error('发送消息出错:', error);
        addSystemMessage('发送消息失败，请检查控制台获取详细信息');
    }
}

// 发送智能体消息
async function sendAgentMessage(message) {
    // 添加用户消息到UI
    addUserMessage(message);
    
    try {
        const response = await fetch(API_ENDPOINTS.sendMessage, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message, isAgentCommand: true })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 添加助手回复到UI
            addAssistantMessage(data.response);
            
            // 启动轮询，检查智能体回复
            startPollingForAgentResponse();
        } else {
            addSystemMessage(`发送智能体消息失败: ${data.message}`);
        }
    } catch (error) {
        console.error('发送智能体消息出错:', error);
        addSystemMessage('发送智能体消息失败，请检查控制台获取详细信息');
    }
}

// 轮询检查智能体回复
let pollingInterval = null;
function startPollingForAgentResponse() {
    // 清除之前的轮询
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    // 记录当前消息数量
    const initialMessageCount = chatMessages.childElementCount;
    
    // 添加等待提示
    const waitingMsg = document.createElement('div');
    waitingMsg.className = 'system-message waiting-message';
    waitingMsg.textContent = '正在等待智能体回复...';
    chatMessages.appendChild(waitingMsg);
    scrollToBottom();
    
    // 设置轮询间隔
    let pollCount = 0;
    pollingInterval = setInterval(async () => {
        try {
            // 获取最新的聊天历史
            const response = await fetch('/api/chat/history');
            const data = await response.json();
            
            if (data.success && data.history) {
                // 检查是否有新消息
                const newMessages = data.history.filter(msg => 
                    msg.type === 'assistant' && 
                    msg.from_agent === true && 
                    !document.querySelector(`.agent-response[data-timestamp="${msg.timestamp}"]`)
                );
                
                if (newMessages.length > 0) {
                    // 移除等待提示
                    const waitingElement = document.querySelector('.waiting-message');
                    if (waitingElement) {
                        waitingElement.remove();
                    }
                    
                    // 添加新消息到UI
                    newMessages.forEach(msg => {
                        const messageEl = document.createElement('div');
                        messageEl.className = 'message assistant-message agent-response';
                        messageEl.setAttribute('data-timestamp', msg.timestamp);
                        messageEl.textContent = msg.message;
                        chatMessages.appendChild(messageEl);
                    });
                    
                    scrollToBottom();
                    
                    // 停止轮询
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    
                    // 添加成功提示
                    addSystemMessage('已收到智能体回复');
                } else {
                    // 超过30秒（15次轮询）后停止
                    pollCount++;
                    if (pollCount >= 15) {
                        // 移除等待提示
                        const waitingElement = document.querySelector('.waiting-message');
                        if (waitingElement) {
                            waitingElement.remove();
                        }
                        
                        // 添加超时提示
                        addSystemMessage('智能体回复超时，请稍后刷新页面查看');
                        
                        // 停止轮询
                        clearInterval(pollingInterval);
                        pollingInterval = null;
                    }
                }
            }
        } catch (error) {
            console.error('轮询智能体回复出错:', error);
        }
    }, 2000); // 每2秒检查一次
}

// 添加用户消息到UI
function addUserMessage(message) {
    const messageEl = document.createElement('div');
    messageEl.className = 'message user-message';
    messageEl.textContent = message;
    chatMessages.appendChild(messageEl);
    scrollToBottom();
}

// 添加助手消息到UI
function addAssistantMessage(message) {
    const messageEl = document.createElement('div');
    messageEl.className = 'message assistant-message';
    messageEl.textContent = message;
    chatMessages.appendChild(messageEl);
    scrollToBottom();
}

// 添加系统消息到UI
function addSystemMessage(message) {
    const messageEl = document.createElement('div');
    messageEl.className = 'system-message';
    messageEl.textContent = message;
    chatMessages.appendChild(messageEl);
    scrollToBottom();
}

// 滚动到聊天底部
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 加载智能体书签
async function loadBookmarks() {
    try {
        const response = await fetch(API_ENDPOINTS.getBookmarks);
        const data = await response.json();
        
        if (data.success) {
            bookmarks = data.bookmarks;
            renderBookmarks();
        } else {
            console.error('加载书签失败:', data.message);
        }
    } catch (error) {
        console.error('加载书签出错:', error);
    }
}

// 渲染智能体书签
function renderBookmarks() {
    bookmarksList.innerHTML = '';
    
    if (bookmarks.length === 0) {
        const noBookmarks = document.createElement('div');
        noBookmarks.className = 'no-bookmarks';
        noBookmarks.textContent = '暂无智能体书签';
        bookmarksList.appendChild(noBookmarks);
        return;
    }
    
    bookmarks.forEach(bookmark => {
        const bookmarkEl = document.createElement('div');
        bookmarkEl.className = 'bookmark-item';
        
        const nameEl = document.createElement('div');
        nameEl.className = 'bookmark-name';
        nameEl.textContent = bookmark.name;
        
        const actionsEl = document.createElement('div');
        actionsEl.className = 'bookmark-actions';
        
        const useBtn = document.createElement('button');
        useBtn.className = 'btn btn-sm btn-outline-primary';
        useBtn.textContent = '使用';
        useBtn.addEventListener('click', () => useBookmark(bookmark));
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.textContent = '删除';
        deleteBtn.addEventListener('click', () => deleteBookmark(bookmark.id));
        
        actionsEl.appendChild(useBtn);
        actionsEl.appendChild(deleteBtn);
        
        bookmarkEl.appendChild(nameEl);
        bookmarkEl.appendChild(actionsEl);
        
        bookmarksList.appendChild(bookmarkEl);
    });
}

// 使用智能体书签
function useBookmark(bookmark) {
    if (!chatRunning) {
        addSystemMessage('请先启动聊天');
        return;
    }
    
    // 在输入框中填入智能体命令
    messageInput.value = `@${bookmark.name} `;
    messageInput.focus();
}

// 添加智能体书签
async function addBookmark() {
    const name = agentNameInput.value.trim();
    if (!name) return;
    
    try {
        const response = await fetch(API_ENDPOINTS.addBookmark, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        
        if (data.success) {
            bookmarks.push(data.bookmark);
            renderBookmarks();
            agentNameInput.value = '';
            addSystemMessage(`已添加智能体书签: ${name}`);
        } else {
            addSystemMessage(`添加书签失败: ${data.message}`);
        }
    } catch (error) {
        console.error('添加书签出错:', error);
        addSystemMessage('添加书签失败，请检查控制台获取详细信息');
    }
}

// 删除智能体书签
async function deleteBookmark(id) {
    try {
        const response = await fetch(`${API_ENDPOINTS.getBookmarks}/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            bookmarks = bookmarks.filter(b => b.id !== id);
            renderBookmarks();
            addSystemMessage('已删除智能体书签');
        } else {
            addSystemMessage(`删除书签失败: ${data.message}`);
        }
    } catch (error) {
        console.error('删除书签出错:', error);
        addSystemMessage('删除书签失败，请检查控制台获取详细信息');
    }
}
class PaperQAChatbot {
    constructor() {
        this.apiUrl = 'http://localhost:8001';
        this.sessionId = 'web_session_' + Date.now();
        this.messageHistory = [];
        this.isProcessing = false;
        this.isWelcomeVisible = true;
        
        this.initializeElements();
        this.attachEventListeners();
        this.initializeUI();
    }
    
    initializeElements() {
        this.sidebar = document.getElementById('sidebar');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messages = document.getElementById('messages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.serverStatus = document.getElementById('serverStatus');
        this.charCount = document.querySelector('.char-count');
        this.chatHistory = document.getElementById('chatHistory');
        this.cachedPapers = document.getElementById('cachedPapers');
        this.refreshPapersBtn = document.getElementById('refreshPapers');
        
        // PDF Modal elements
        this.pdfModal = document.getElementById('pdfModal');
        this.pdfModalOverlay = document.getElementById('pdfModalOverlay');
        this.pdfTitle = document.getElementById('pdfTitle');
        this.pdfViewer = document.getElementById('pdfViewer');
        this.pdfLoading = document.getElementById('pdfLoading');
        this.pdfError = document.getElementById('pdfError');
        this.closePdfModal = document.getElementById('closePdfModal');
        this.downloadPdf = document.getElementById('downloadPdf');
        this.openNewTab = document.getElementById('openNewTab');
        this.retryPdf = document.getElementById('retryPdf');
    }
    
    attachEventListeners() {
        // Send message
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Keyboard shortcuts
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!this.isProcessing && this.messageInput.value.trim()) {
                    this.sendMessage();
                }
            }
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateCharCount();
            this.updateSendButton();
        });
        
        // Sidebar toggle
        this.sidebarToggle?.addEventListener('click', () => {
            this.sidebar.classList.toggle('open');
        });
        
        // New chat
        this.newChatBtn?.addEventListener('click', () => {
            this.startNewChat();
        });
        
        // Clear chat button
        document.querySelector('.action-btn')?.addEventListener('click', () => {
            this.clearChat();
        });
        
        // Refresh papers
        this.refreshPapersBtn?.addEventListener('click', () => {
            this.loadCachedPapers();
        });
        
        // PDF Modal events
        this.closePdfModal?.addEventListener('click', () => {
            this.closePdfViewer();
        });
        
        this.pdfModalOverlay?.addEventListener('click', () => {
            this.closePdfViewer();
        });
        
        this.downloadPdf?.addEventListener('click', () => {
            this.downloadCurrentPdf();
        });
        
        this.openNewTab?.addEventListener('click', () => {
            this.openPdfInNewTab();
        });
        
        this.retryPdf?.addEventListener('click', () => {
            this.retryPdfLoad();
        });
        
        // ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.pdfModal.style.display !== 'none') {
                this.closePdfViewer();
            }
        });
    }
    
    async initializeUI() {
        this.updateSendButton();
        this.updateCharCount();
        await this.checkServerHealth();
        await this.loadChatHistory();
        await this.loadCachedPapers();
        
        // Start periodic cache updates check
        this.startCacheUpdateInterval();
    }
    
    startCacheUpdateInterval() {
        // Check for cache updates every 30 seconds when not actively processing
        this.cacheUpdateInterval = setInterval(() => {
            if (!this.isProcessing) {
                this.checkAndUpdateCachedPapers();
            }
        }, 30000);
    }
    
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }
    
    updateCharCount() {
        const count = this.messageInput.value.length;
        const maxLength = parseInt(this.messageInput.getAttribute('maxlength'));
        
        this.charCount.textContent = `${count}/${maxLength}`;
        
        if (count > maxLength * 0.9) {
            this.charCount.className = 'char-count error';
        } else if (count > maxLength * 0.8) {
            this.charCount.className = 'char-count warning';
        } else {
            this.charCount.className = 'char-count';
        }
    }
    
    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isProcessing;
    }
    
    async checkServerHealth() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.updateServerStatus('online', 'Online');
            } else {
                this.updateServerStatus('offline', 'Server Error');
            }
        } catch (error) {
            this.updateServerStatus('offline', 'Disconnected');
            console.error('Server health check failed:', error);
        }
    }
    
    updateServerStatus(status, text) {
        const indicator = this.serverStatus.querySelector('.status-indicator');
        const span = this.serverStatus.querySelector('span');
        
        indicator.className = `status-indicator ${status}`;
        span.textContent = text;
    }
    
    hideWelcome() {
        if (this.isWelcomeVisible) {
            const welcomeSection = document.querySelector('.welcome-section');
            if (welcomeSection) {
                welcomeSection.style.display = 'none';
            }
            this.isWelcomeVisible = false;
        }
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isProcessing) return;
        
        this.hideWelcome();
        this.isProcessing = true;
        this.updateUI(true);
        
        // Add user message
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.autoResizeTextarea();
        this.updateCharCount();
        
        try {
            await this.callStreamingAPI(message);
        } catch (error) {
            this.addMessage(`Sorry, I encountered an error: ${error.message}`, 'error');
        } finally {
            this.isProcessing = false;
            this.updateUI(false);
        }
    }
    
    
    async callStreamingAPI(message) {
        return new Promise((resolve, reject) => {
            // Use EventSource for better real-time streaming
            const eventSource = new EventSource(`${this.apiUrl}/chat/stream?` + new URLSearchParams({
                message: message,
                session_id: this.sessionId
            }));
            
            let currentBotMessage = null;
            let currentProgressContainer = null;
            
            eventSource.onopen = () => {
                console.log('[SSE] Connection opened');
            };
            
            eventSource.onmessage = (event) => {
                console.log(`[${new Date().toISOString()}] Received SSE data:`, event.data);
                
                if (event.data === '[DONE]') {
                    eventSource.close();
                    resolve();
                    return;
                }
                
                try {
                    const parsed = JSON.parse(event.data);
                    console.log(`[${new Date().toISOString()}] Parsed streaming data:`, parsed);
                    
                    if (parsed.type === 'progress') {
                        // Handle progress update
                        if (!currentProgressContainer) {
                            // Create initial bot message with progress container
                            currentBotMessage = this.addMessageWithProgress('', 'bot');
                            currentProgressContainer = currentBotMessage.querySelector('.progress-container');
                        }
                        this.addProgressItem(currentProgressContainer, parsed.progress);
                        
                    } else if (parsed.type === 'message') {
                        // Skip intermediate message updates - only show progress
                        // The message content will be updated only on final response
                        
                    } else if (parsed.type === 'final') {
                        // Handle final response
                        if (!currentBotMessage) {
                            currentBotMessage = this.addMessageWithProgress('', 'bot');
                            currentProgressContainer = currentBotMessage.querySelector('.progress-container');
                        }
                        this.updateMessageContent(currentBotMessage, parsed.response);
                        
                        // Mark progress as complete and make it collapsible
                        if (currentProgressContainer) {
                            currentProgressContainer.classList.add('completed');
                            this.makeProgressCollapsible(currentProgressContainer);
                        }
                        
                        // Store in history
                        this.messageHistory.push({
                            content: parsed.response,
                            type: 'bot',
                            timestamp: new Date(),
                            id: Date.now() + Math.random(),
                            progresses: parsed.progresses
                        });
                        
                        // Update chat preview
                        this.updateChatPreview(parsed.response, 'bot');
                        
                        // Check if new papers were cached and update the list
                        this.checkAndUpdateCachedPapers();
                        
                        eventSource.close();
                        resolve();
                    }
                } catch (e) {
                    console.error('Error parsing streaming data:', e);
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('[SSE] Error:', error);
                eventSource.close();
                reject(new Error('Streaming connection failed'));
            };
        });
    }
    
    async checkAndUpdateCachedPapers() {
        try {
            // Get current cached papers
            const response = await fetch(`${this.apiUrl}/papers/cached`);
            const data = await response.json();
            
            // Get current paper IDs
            const currentPaperIds = new Set();
            this.cachedPapers.querySelectorAll('.paper-item').forEach(item => {
                currentPaperIds.add(item.dataset.paperId);
            });
            
            // Check for new papers
            const newPapers = data.papers.filter(paper => !currentPaperIds.has(paper.id));
            
            if (newPapers.length > 0) {
                // New papers were added, refresh the list
                this.renderCachedPapers(data.papers);
                
                // Show a subtle notification
                this.showCacheUpdateNotification(newPapers.length);
                
                // Highlight new papers briefly
                setTimeout(() => {
                    newPapers.forEach(paper => {
                        const paperElement = this.cachedPapers.querySelector(`[data-paper-id="${paper.id}"]`);
                        if (paperElement) {
                            paperElement.classList.add('newly-cached');
                            setTimeout(() => {
                                paperElement.classList.remove('newly-cached');
                            }, 2000);
                        }
                    });
                }, 100);
            }
        } catch (error) {
            console.error('Failed to check cached papers:', error);
        }
    }
    
    showCacheUpdateNotification(newCount) {
        // Create or update notification
        let notification = document.querySelector('.cache-update-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.className = 'cache-update-notification';
            this.cachedPapers.parentElement.appendChild(notification);
        }
        
        notification.textContent = `${newCount} new paper${newCount > 1 ? 's' : ''} cached`;
        notification.classList.add('show');
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }
    
    addMessage(content, type, saveToHistory = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        // Add avatar
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const avatarIcon = document.createElement('div');
        avatarIcon.className = 'avatar-icon';
        avatarIcon.textContent = type === 'user' ? '👤' : '🤖';
        avatar.appendChild(avatarIcon);
        
        // Add message content
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (type === 'error') {
            messageDiv.className = 'message bot-message error-message';
        }
        
        // Format message content
        const formattedContent = this.formatMessage(content);
        messageContent.innerHTML = formattedContent;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        this.messages.appendChild(messageDiv);
        
        // Scroll to bottom with smooth animation
        this.scrollToBottom();
        
        // Store in history (only for new messages, not when loading from history)
        if (saveToHistory) {
            this.messageHistory.push({ 
                content, 
                type, 
                timestamp: new Date(),
                id: Date.now() + Math.random()
            });
            
            // Update chat preview in sidebar
            this.updateChatPreview(content, type);
        }
        
        return messageDiv;
    }
    
    addMessageWithProgress(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        // Add avatar
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const avatarIcon = document.createElement('div');
        avatarIcon.className = 'avatar-icon';
        avatarIcon.textContent = type === 'user' ? '👤' : '🤖';
        avatar.appendChild(avatarIcon);
        
        // Add message content container
        const messageContentContainer = document.createElement('div');
        messageContentContainer.className = 'message-content-container';
        
        // Add progress container (shown first)
        const progressContainer = document.createElement('div');
        progressContainer.className = 'progress-container';
        
        // Add main message content
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (type === 'error') {
            messageDiv.className = 'message bot-message error-message';
        }
        
        // If no content, show typing indicator
        if (!content) {
            messageContent.innerHTML = '<div class="inline-typing-indicator"><span></span><span></span><span></span></div>';
        } else {
            // Format message content
            const formattedContent = this.formatMessage(content);
            messageContent.innerHTML = formattedContent;
        }
        
        // Structure: avatar + [progress-container + message-content]
        messageContentContainer.appendChild(progressContainer);
        messageContentContainer.appendChild(messageContent);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContentContainer);
        this.messages.appendChild(messageDiv);
        
        // Scroll to bottom with smooth animation
        this.scrollToBottom();
        
        return messageDiv;
    }
    
    addProgressItem(progressContainer, progressText) {
        const progressItem = document.createElement('div');
        progressItem.className = 'progress-item';
        
        const progressIcon = document.createElement('div');
        progressIcon.className = 'progress-icon';
        progressIcon.innerHTML = '○';
        
        const progressTextEl = document.createElement('div');
        progressTextEl.className = 'progress-text';
        progressTextEl.textContent = progressText;
        
        progressItem.appendChild(progressIcon);
        progressItem.appendChild(progressTextEl);
        progressContainer.appendChild(progressItem);
        
        // Auto-scroll to show new progress
        this.scrollToBottom();
        
        // Mark previous items as completed
        const allItems = progressContainer.querySelectorAll('.progress-item');
        if (allItems.length > 1) {
            for (let i = 0; i < allItems.length - 1; i++) {
                allItems[i].classList.add('completed');
                allItems[i].querySelector('.progress-icon').innerHTML = '●';
            }
        }
    }
    
    updateMessageContent(messageDiv, content) {
        const messageContent = messageDiv.querySelector('.message-content');
        if (messageContent) {
            const formattedContent = this.formatMessage(content);
            messageContent.innerHTML = formattedContent;
            this.scrollToBottom();
        }
    }
    
    makeProgressCollapsible(progressContainer) {
        // Add collapsed class to shrink the container
        progressContainer.classList.add('collapsed');
        
        // Create toggle header
        const toggleHeader = document.createElement('div');
        toggleHeader.className = 'progress-toggle-header';
        toggleHeader.innerHTML = `
            <span class="progress-toggle-title">Internal Process</span>
            <span class="progress-toggle-icon">▼</span>
        `;
        
        // Create collapsible content wrapper
        const progressContent = document.createElement('div');
        progressContent.className = 'progress-content';
        
        // Move existing progress items to content wrapper
        const existingItems = Array.from(progressContainer.children);
        existingItems.forEach(item => {
            progressContent.appendChild(item);
        });
        
        // Clear container and add new structure
        progressContainer.innerHTML = '';
        progressContainer.appendChild(toggleHeader);
        progressContainer.appendChild(progressContent);
        
        // Add click handler for toggle
        toggleHeader.addEventListener('click', () => {
            const isExpanded = progressContainer.classList.contains('expanded');
            const icon = toggleHeader.querySelector('.progress-toggle-icon');
            
            if (isExpanded) {
                progressContainer.classList.remove('expanded');
                icon.textContent = '▼';
            } else {
                progressContainer.classList.add('expanded');
                icon.textContent = '▲';
            }
        });
    }
    
    formatMessage(content) {
        // Convert line breaks to <br>
        let formatted = content.replace(/\n/g, '<br>');
        
        // Make URLs clickable
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        formatted = formatted.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
        
        // Format code blocks (simple version)
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        return formatted;
    }
    
    showTypingIndicator() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }
    
    updateUI(isLoading) {
        this.updateSendButton();
        
        if (isLoading) {
            this.updateServerStatus('connecting', 'Processing...');
        } else {
            this.updateServerStatus('online', 'Online');
        }
    }
    
    updateChatPreview(content, type) {
        const chatItem = document.querySelector('.chat-item.active');
        if (chatItem) {
            const preview = chatItem.querySelector('.chat-preview');
            if (type === 'user') {
                preview.textContent = content.substring(0, 50) + (content.length > 50 ? '...' : '');
            }
        }
    }
    
    async loadChatHistory() {
        try {
            const response = await fetch(`${this.apiUrl}/chat/sessions`);
            const data = await response.json();
            this.renderChatHistory(data.sessions);
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    }
    
    renderChatHistory(sessions) {
        // Keep the current session item
        const currentSession = this.chatHistory.querySelector('.chat-item.active');
        this.chatHistory.innerHTML = '';
        
        if (currentSession) {
            this.chatHistory.appendChild(currentSession);
        }
        
        sessions.forEach(session => {
            if (session.id !== this.sessionId) {
                const sessionItem = this.createChatHistoryItem(session);
                this.chatHistory.appendChild(sessionItem);
            }
        });
    }
    
    createChatHistoryItem(session) {
        const item = document.createElement('div');
        item.className = 'chat-item';
        item.dataset.session = session.id;
        
        const timeAgo = this.getTimeAgo(new Date(session.updated_at));
        
        item.innerHTML = `
            <div class="chat-item-content">
                <div class="chat-title">${session.title}</div>
                <div class="chat-preview">${session.preview}</div>
            </div>
            <div class="chat-actions">
                <button class="delete-btn" data-session-id="${session.id}" title="Delete chat">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c0 1 1 2 2 2v2"/>
                    </svg>
                </button>
            </div>
        `;
        
        // Add click handler
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.delete-btn')) {
                this.loadChatSession(session.id);
            }
        });
        
        // Add delete handler
        const deleteBtn = item.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteChatSession(session.id);
        });
        
        return item;
    }
    
    async loadChatSession(sessionId) {
        try {
            const response = await fetch(`${this.apiUrl}/chat/sessions/${sessionId}`);
            const session = await response.json();
            
            // Switch to this session
            this.sessionId = sessionId;
            this.clearChat();
            
            // Load messages
            session.messages.forEach(msg => {
                if (msg.progresses && msg.progresses.length > 0) {
                    // Create message with progress for historical messages
                    const messageDiv = this.addMessageWithProgress(msg.content, msg.type);
                    const progressContainer = messageDiv.querySelector('.progress-container');
                    
                    // Add all progress items as completed
                    msg.progresses.forEach(progress => {
                        const progressItem = document.createElement('div');
                        progressItem.className = 'progress-item completed';
                        
                        const progressIcon = document.createElement('div');
                        progressIcon.className = 'progress-icon';
                        progressIcon.innerHTML = '●';
                        
                        const progressTextEl = document.createElement('div');
                        progressTextEl.className = 'progress-text';
                        progressTextEl.textContent = progress;
                        
                        progressItem.appendChild(progressIcon);
                        progressItem.appendChild(progressTextEl);
                        progressContainer.appendChild(progressItem);
                    });
                    
                    // Mark container as completed and make it collapsible
                    progressContainer.classList.add('completed');
                    this.makeProgressCollapsible(progressContainer);
                } else {
                    // Regular message without progress
                    this.addMessage(msg.content, msg.type, false); // false = don't save to history
                }
            });
            
            // Update active state
            document.querySelectorAll('.chat-item').forEach(item => item.classList.remove('active'));
            document.querySelector(`[data-session="${sessionId}"]`)?.classList.add('active');
            
            this.hideWelcome();
        } catch (error) {
            console.error('Failed to load chat session:', error);
        }
    }
    
    async deleteChatSession(sessionId) {
        if (!confirm('Are you sure you want to delete this chat?')) return;
        
        try {
            await fetch(`${this.apiUrl}/chat/sessions/${sessionId}`, {
                method: 'DELETE'
            });
            
            // Remove from UI
            document.querySelector(`[data-session="${sessionId}"]`)?.remove();
            
            // If current session was deleted, start new chat
            if (sessionId === this.sessionId) {
                this.startNewChat();
            }
        } catch (error) {
            console.error('Failed to delete chat session:', error);
        }
    }
    
    async loadCachedPapers() {
        try {
            this.cachedPapers.innerHTML = '<div class="loading-item">Loading papers...</div>';
            const response = await fetch(`${this.apiUrl}/papers/cached`);
            const data = await response.json();
            this.renderCachedPapers(data.papers);
        } catch (error) {
            console.error('Failed to load cached papers:', error);
            this.cachedPapers.innerHTML = '<div class="empty-item">Failed to load papers</div>';
        }
    }
    
    renderCachedPapers(papers) {
        if (papers.length === 0) {
            this.cachedPapers.innerHTML = '<div class="empty-item">No cached papers</div>';
            return;
        }
        
        this.cachedPapers.innerHTML = '';
        
        papers.forEach(paper => {
            const item = this.createPaperItem(paper);
            this.cachedPapers.appendChild(item);
        });
    }
    
    createPaperItem(paper) {
        const item = document.createElement('div');
        item.className = 'paper-item';
        item.dataset.paperId = paper.id;
        
        const cachedDate = new Date(paper.cached_at);
        const timeAgo = this.getTimeAgo(cachedDate);
        
        item.innerHTML = `
            <div class="paper-content">
                <div class="paper-title">${paper.title}</div>
                <div class="paper-meta">
                    <span class="paper-id">${paper.id}</span>
                    <span>•</span>
                    <span>${paper.file_count} files</span>
                    <span>•</span>
                    <span>${timeAgo}</span>
                </div>
            </div>
            <div class="paper-actions">
                <button class="paper-action-btn view-pdf-btn" title="View PDF">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                    </svg>
                </button>
                <button class="paper-action-btn ask-btn" title="Ask about this paper">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M9,9a3,3,0,1,1,4,2.5L12,14"/>
                        <circle cx="12" cy="17.5" r="0.5"/>
                    </svg>
                </button>
                <button class="paper-action-btn delete" data-paper-id="${paper.id}" title="Delete cached paper">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c0 1 1 2 2 2v2"/>
                    </svg>
                </button>
            </div>
        `;
        
        // Add click handler to view PDF (main click area)
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.paper-action-btn')) {
                this.showPdfModal(paper.id);
            }
        });
        
        // Add click handler for PDF view button
        const viewBtn = item.querySelector('.view-pdf-btn');
        viewBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showPdfModal(paper.id);
        });
        
        // Add click handler for ask button
        const askBtn = item.querySelector('.ask-btn');
        askBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.askAboutPaper(paper.id, paper.title);
        });
        
        // Add delete handler
        const deleteBtn = item.querySelector('.delete');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteCachedPaper(paper.id);
        });
        
        // Add scrolling animation for long titles
        this.setupTitleScrolling(item);
        
        return item;
    }
    
    setupTitleScrolling(paperItem) {
        const titleElement = paperItem.querySelector('.paper-title');
        if (!titleElement) return;
        
        let scrollTimeout;
        let isScrolling = false;
        
        titleElement.addEventListener('mouseenter', () => {
            // Wait for next frame to ensure accurate measurements
            requestAnimationFrame(() => {
                // Check if text is truncated (scrollWidth > clientWidth)
                const containerWidth = titleElement.clientWidth;
                const textWidth = titleElement.scrollWidth;
                
                if (textWidth > containerWidth + 5) { // 5px tolerance
                    // Calculate scroll distance needed to show full text
                    const scrollDistance = textWidth - containerWidth + 30; // 30px padding for better visibility
                    
                    // Set CSS custom property for animation
                    titleElement.style.setProperty('--scroll-distance', `-${scrollDistance}px`);
                    
                    // Calculate animation duration based on text length (minimum 3s, maximum 10s)
                    const duration = Math.min(Math.max(scrollDistance / 25, 3), 10);
                    titleElement.style.animationDuration = `${duration}s`;
                    
                    // Start scrolling animation after a short delay
                    scrollTimeout = setTimeout(() => {
                        titleElement.classList.add('scrolling');
                        isScrolling = true;
                    }, 300);
                }
            });
        });
        
        titleElement.addEventListener('mouseleave', () => {
            // Clear timeout and stop animation
            clearTimeout(scrollTimeout);
            titleElement.classList.remove('scrolling');
            titleElement.style.removeProperty('--scroll-distance');
            titleElement.style.removeProperty('animation-duration');
            isScrolling = false;
        });
        
        // Reset animation on animation end for smooth looping
        titleElement.addEventListener('animationiteration', () => {
            if (!isScrolling) {
                titleElement.classList.remove('scrolling');
            }
        });
    }
    
    askAboutPaper(paperId, paperTitle) {
        // Use title if available, otherwise fall back to ID
        const paperRef = paperTitle && !paperTitle.startsWith('Paper ') ? `"${paperTitle}"` : paperId;
        const question = `Tell me about the paper ${paperRef}`;
        this.messageInput.value = question;
        this.messageInput.focus();
        this.updateSendButton();
    }
    
    async deleteCachedPaper(paperId) {
        if (!confirm(`Are you sure you want to delete cached paper ${paperId}?`)) return;
        
        try {
            await fetch(`${this.apiUrl}/papers/cached/${paperId}`, {
                method: 'DELETE'
            });
            
            // Remove from UI
            document.querySelector(`[data-paper-id="${paperId}"]`)?.remove();
            
            // Reload if no papers left
            if (this.cachedPapers.children.length === 0) {
                this.cachedPapers.innerHTML = '<div class="empty-item">No cached papers</div>';
            }
        } catch (error) {
            console.error('Failed to delete cached paper:', error);
        }
    }
    
    getTimeAgo(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString();
    }
    
    startNewChat() {
        // Archive current session by reloading chat history
        this.loadChatHistory();
        
        // Start new session
        this.sessionId = 'web_session_' + Date.now();
        this.clearChat();
        this.isWelcomeVisible = true;
        document.querySelector('.welcome-section').style.display = 'block';
        
        // Update current session item
        const currentItem = document.querySelector('.chat-item.active');
        if (currentItem) {
            const title = currentItem.querySelector('.chat-title');
            const preview = currentItem.querySelector('.chat-preview');
            title.textContent = 'Current Session';
            preview.textContent = 'Ready to help with papers';
        }
    }
    
    clearChat() {
        this.messages.innerHTML = '';
        this.messageHistory = [];
    }
    
    // PDF Modal Methods
    showPdfModal(paperId) {
        this.currentPaperId = paperId;
        this.pdfTitle.textContent = `Paper ${paperId}`;
        
        // Show modal
        this.pdfModal.style.display = 'flex';
        
        // Reset states
        this.pdfLoading.style.display = 'flex';
        this.pdfViewer.style.display = 'none';
        this.pdfError.style.display = 'none';
        
        // Load PDF
        this.loadPdf(paperId);
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }
    
    closePdfViewer() {
        this.pdfModal.style.display = 'none';
        this.pdfViewer.src = '';
        this.currentPaperId = null;
        
        // Restore body scroll
        document.body.style.overflow = '';
    }
    
    async loadPdf(paperId) {
        try {
            const pdfUrl = `${this.apiUrl}/papers/cached/${encodeURIComponent(paperId)}/pdf`;
            console.log('Loading PDF:', pdfUrl);
            
            // First, test if the URL is accessible
            try {
                const testResponse = await fetch(pdfUrl, { 
                    method: 'GET',
                    headers: { 'Accept': 'application/pdf' }
                });
                console.log('PDF URL test response:', testResponse.status, testResponse.headers.get('content-type'));
                
                if (!testResponse.ok) {
                    throw new Error(`PDF not accessible: ${testResponse.status}`);
                }
                
                if (!testResponse.headers.get('content-type')?.includes('pdf')) {
                    console.warn('Response is not a PDF, got:', testResponse.headers.get('content-type'));
                }
            } catch (fetchError) {
                console.error('PDF accessibility test failed:', fetchError);
                this.showPdfError();
                return;
            }
            
            // Reset iframe
            this.pdfViewer.src = '';
            
            // Set up iframe load handlers
            let hasLoaded = false;
            let loadAttempts = 0;
            
            const handleLoad = () => {
                console.log('PDF iframe loaded, attempt:', loadAttempts + 1);
                
                // Check if iframe actually loaded PDF content
                try {
                    const iframeDoc = this.pdfViewer.contentDocument;
                    if (iframeDoc && iframeDoc.title.includes('404') || 
                        iframeDoc && iframeDoc.body && iframeDoc.body.innerHTML.includes('Not Found')) {
                        console.warn('Iframe loaded but shows 404 content');
                        this.showPdfError();
                        return;
                    }
                } catch (e) {
                    // Cross-origin access blocked, which is expected for PDF
                    console.log('Cross-origin access blocked (normal for PDF)');
                }
                
                hasLoaded = true;
                setTimeout(() => {
                    this.pdfLoading.style.display = 'none';
                    this.pdfViewer.style.display = 'block';
                    this.pdfError.style.display = 'none';
                }, 1000);
            };
            
            const handleError = () => {
                console.error('PDF iframe error, attempt:', loadAttempts + 1);
                if (!hasLoaded) {
                    this.showPdfError();
                }
            };
            
            // Remove any existing listeners
            this.pdfViewer.removeEventListener('load', handleLoad);
            this.pdfViewer.removeEventListener('error', handleError);
            
            // Add new listeners
            this.pdfViewer.addEventListener('load', handleLoad);
            this.pdfViewer.addEventListener('error', handleError);
            
            // Use PDF viewer page to avoid X-Frame-Options issues
            const viewerUrl = `/static/pdf-viewer.html?pdf=${encodeURIComponent(pdfUrl)}`;
            console.log('Setting iframe src to PDF viewer:', viewerUrl);
            this.pdfViewer.src = viewerUrl;
            loadAttempts++;
            
            // Timeout fallback
            setTimeout(() => {
                if (!hasLoaded && this.pdfLoading.style.display !== 'none') {
                    console.warn('PDF loading timeout, trying alternative approach');
                    loadAttempts++;
                    
                    // Try with PDF.js viewer if available
                    const pdfJsUrl = `/static/pdfjs/web/viewer.html?file=${encodeURIComponent(pdfUrl)}`;
                    console.log('Trying PDF.js viewer:', pdfJsUrl);
                    this.pdfViewer.src = pdfJsUrl;
                    
                    // Final timeout
                    setTimeout(() => {
                        if (!hasLoaded) {
                            console.error('All PDF loading attempts failed');
                            this.showPdfError();
                        }
                    }, 5000);
                }
            }, 5000); // Reduced initial timeout
            
        } catch (error) {
            console.error('Failed to load PDF:', error);
            this.showPdfError();
        }
    }
    
    showPdfError() {
        this.pdfLoading.style.display = 'none';
        this.pdfViewer.style.display = 'none';
        this.pdfError.style.display = 'block';
        
        // Update error message with more helpful text
        const errorMessage = this.pdfError.querySelector('.error-message p');
        if (errorMessage) {
            errorMessage.innerHTML = `
                The PDF could not be displayed in the viewer. This might be due to browser limitations.
                <br><br>
                Try using the "Open in New Tab" or "Download" buttons above to view the PDF.
            `;
        }
    }
    
    retryPdfLoad() {
        if (this.currentPaperId) {
            this.pdfError.style.display = 'none';
            this.pdfLoading.style.display = 'flex';
            this.loadPdf(this.currentPaperId);
        }
    }
    
    downloadCurrentPdf() {
        if (this.currentPaperId) {
            const downloadUrl = `${this.apiUrl}/papers/cached/${this.currentPaperId}/pdf`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `${this.currentPaperId}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
    openPdfInNewTab() {
        if (this.currentPaperId) {
            const pdfUrl = `${this.apiUrl}/papers/cached/${this.currentPaperId}/pdf`;
            window.open(pdfUrl, '_blank');
        }
    }
}

// Example question function
function setExample(question) {
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.value = question;
        messageInput.focus();
        
        // Trigger input event to update UI
        const event = new Event('input', { bubbles: true });
        messageInput.dispatchEvent(event);
        
        // Auto-resize
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
    }
}

// Initialize the chatbot when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new PaperQAChatbot();
    
    // Add some helpful styling for links and code
    const style = document.createElement('style');
    style.textContent = `
        .message-content a {
            color: #667eea;
            text-decoration: underline;
        }
        .message-content a:hover {
            color: #5a67d8;
        }
        .message-content code {
            background: #f7fafc;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
            font-size: 14px;
        }
        .user-message .message-content code {
            background: rgba(255, 255, 255, 0.2);
        }
    `;
    document.head.appendChild(style);
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Cmd/Ctrl + K to focus input
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('messageInput')?.focus();
    }
    
    // Escape to clear input
    if (e.key === 'Escape') {
        const input = document.getElementById('messageInput');
        if (input && document.activeElement === input) {
            input.value = '';
            input.blur();
        }
    }
});

// Handle window resize for mobile
window.addEventListener('resize', () => {
    const sidebar = document.getElementById('sidebar');
    if (window.innerWidth > 768) {
        sidebar?.classList.remove('open');
    }
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    
    if (window.innerWidth <= 768 && 
        sidebar?.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !sidebarToggle?.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});
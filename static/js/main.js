document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    const libraryList = document.querySelector('.space_y_1.overflow_y_auto');

    // Handle Upload Button Click
    uploadBtn.addEventListener('click', () => fileInput.click());

    // Handle File Selection and Upload
    fileInput.addEventListener('change', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        // UI Feedback: Add "Processing" item to library
        const processingItem = addLibraryItem(file.name, true);

        try {
            // Step 1: Upload the file
            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const uploadData = await uploadResponse.json();
            if (!uploadResponse.ok) throw new Error(uploadData.error || 'Upload failed');

            // Step 2: Trigger Indexing
            updateLibraryItem(processingItem, 'Indexing...', false, true);

            const indexResponse = await fetch('/api/index', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: uploadData.file_path })
            });

            const indexData = await indexResponse.json();
            if (!indexResponse.ok) throw new Error(indexData.error || 'Indexing failed');

            // Mark as Indexed
            updateLibraryItem(processingItem, 'Indexed');
            appendMessage('ai', `Successfully uploaded and indexed **${file.name}**. You can now ask questions about it.`, []);

        } catch (error) {
            console.error('Error:', error);
            updateLibraryItem(processingItem, 'Failed', true);
            appendMessage('ai', `**Action Needed:** ${error.message}`, []);
        }
    });

    function addLibraryItem(name, isProcessing = false) {
        const item = document.createElement('div');
        item.className = 'group flex flex-col p-2.5 rounded-lg bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 shadow-sm cursor-pointer hover:border-primary transition-all';
        item.innerHTML = `
            <div class="flex items-center gap-3 mb-1">
                <span class="material-symbols-outlined text-red-500">picture_as_pdf</span>
                <span class="text-sm font-semibold truncate flex-1">${name}</span>
                <span class="status-icon material-symbols-outlined text-xs ${isProcessing ? 'text-primary animate-pulse' : 'text-green-500 font-bold'}">${isProcessing ? 'sync' : 'check_circle'}</span>
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-400 px-8">
                <span class="status-text ${isProcessing ? 'text-primary italic' : ''}">${isProcessing ? 'Uploading...' : 'Indexed'}</span>
            </div>
        `;
        libraryList.prepend(item);
        return item;
    }

    function updateLibraryItem(item, text, isError = false, isIndexing = false) {
        const statusText = item.querySelector('.status-text');
        const statusIcon = item.querySelector('.status-icon');
        statusText.textContent = text;

        if (isError) {
            statusText.className = 'status-text text-red-500';
            statusIcon.textContent = 'error';
            statusIcon.className = 'status-icon material-symbols-outlined text-xs text-red-500';
            statusIcon.classList.remove('animate-pulse');
        } else if (isIndexing) {
            statusText.className = 'status-text text-primary italic';
            statusIcon.textContent = 'sync';
            statusIcon.className = 'status-icon material-symbols-outlined text-xs text-primary animate-pulse';
        } else {
            statusText.className = 'status-text text-green-500';
            statusIcon.textContent = 'check_circle';
            statusIcon.className = 'status-icon material-symbols-outlined text-xs text-green-500 font-bold';
            statusIcon.classList.remove('animate-pulse');
        }
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;

        // Append User Message
        appendMessage('user', query);
        chatInput.value = '';

        // Show Loading Indicator
        const loadingId = appendLoading();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();

            // Remove Loading Indicator
            removeLoading(loadingId);

            // Append AI Message with Citations
            appendMessage('ai', data.response, data.citations);

        } catch (error) {
            console.error('Error:', error);
            removeLoading(loadingId);
            appendMessage('ai', 'Sorry, I encountered an error processing your request. Please check the backend connection or API key.', []);
        }
    });

    function appendMessage(role, text, citations = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex gap-4 message-bubble ${role === 'user' ? '' : ''}`;

        const avatarColor = role === 'user' ? 'bg-slate-200 dark:bg-slate-800' : 'bg-primary';
        const avatarIcon = role === 'user' ? 'person' : 'auto_awesome';
        const textColor = role === 'user' ? 'text-slate-800 dark:text-slate-200' : 'text-slate-800 dark:text-slate-200';
        const bgColor = role === 'user' ? '' : 'bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 p-4 rounded-2xl rounded-tl-none';
        const iconColor = role === 'user' ? '' : 'text-white';

        let citationHtml = '';
        if (citations.length > 0) {
            citationHtml = `
                <div class="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 flex flex-wrap gap-2">
                    ${citations.map((c, i) => `
                        <button class="inline-flex items-center px-1.5 py-0.5 rounded bg-primary/20 text-primary text-[10px] font-bold hover:bg-primary/30 transition-all cursor-pointer">
                            ${c}
                        </button>
                    `).join('')}
                </div>
            `;
        }

        messageDiv.innerHTML = `
            <div class="h-8 w-8 rounded-full ${avatarColor} shrink-0 flex items-center justify-center">
                <span class="material-symbols-outlined text-sm ${iconColor}">${avatarIcon}</span>
            </div>
            <div class="flex flex-col gap-1 flex-1">
                <div class="${bgColor}">
                    <p class="text-sm leading-relaxed ${textColor}">${text}</p>
                    ${citationHtml}
                </div>
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendLoading() {
        const loadingId = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.id = loadingId;
        loadingDiv.className = 'flex gap-4 message-bubble opacity-50';
        loadingDiv.innerHTML = `
            <div class="h-8 w-8 rounded-full bg-primary shrink-0 flex items-center justify-center animate-pulse">
                <span class="material-symbols-outlined text-sm text-white">auto_awesome</span>
            </div>
            <div class="flex flex-col gap-4">
                <div class="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 p-4 rounded-2xl rounded-tl-none">
                    <div class="flex gap-1">
                        <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"></span>
                        <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0.2s]"></span>
                        <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0.4s]"></span>
                    </div>
                </div>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return loadingId;
    }

    function removeLoading(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }
});

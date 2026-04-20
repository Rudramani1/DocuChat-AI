document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const fileName = document.getElementById('file-name');
    const processBtn = document.getElementById('process-btn');
    const uploadStatus = document.getElementById('upload-status');
    const docStatus = document.getElementById('doc-status');
    
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');

    let selectedFile = null;

    // File selection handling
    fileUpload.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            selectedFile = e.target.files[0];
            fileName.textContent = selectedFile.name;
            processBtn.disabled = false;
        }
    });

    // Process document click handler
    processBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);

        uploadStatus.textContent = 'Processing document... This may take a minute.';
        uploadStatus.className = 'status-msg loading';
        processBtn.disabled = true;
        fileUpload.disabled = true;

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                uploadStatus.textContent = '✓ Document indexed successfully!';
                uploadStatus.className = 'status-msg success';
                
                // Update UI to allow chatting
                docStatus.innerHTML = '<span class="dot green"></span> Document loaded';
                chatInput.disabled = false;
                sendBtn.disabled = false;
                chatInput.focus();
                
                addSystemMessage("I've analyzed your document. What would you like to know about it?");
            } else {
                throw new Error(result.error || 'Failed to process document');
            }
        } catch (error) {
            uploadStatus.textContent = `Error: ${error.message}`;
            uploadStatus.className = 'status-msg error';
            processBtn.disabled = false;
        } finally {
            fileUpload.disabled = false;
        }
    });

    // Chat form submission handler
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const query = chatInput.value.trim();
        if (!query) return;

        // Add user message to UI
        addUserMessage(query);
        chatInput.value = '';
        
        // Disable input while generating
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // Show typing indicator
        const typingId = addTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });

            const result = await response.json();
            
            // Remove typing indicator
            document.getElementById(typingId).remove();

            if (response.ok) {
                addSystemMessage(result.answer);
            } else {
                addSystemMessage(`Error: ${result.error}`);
            }
        } catch (error) {
            document.getElementById(typingId).remove();
            addSystemMessage('Sorry, there was an error connecting to the server.');
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
            scrollToBottom();
        }
    });

    // Helper to add user message
    function addUserMessage(text) {
        const msgHtml = `
            <div class="message user-message">
                <div class="avatar"><i class='bx bx-user'></i></div>
                <div class="content"><p>${escapeHtml(text)}</p></div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', msgHtml);
        scrollToBottom();
    }

    // Helper to add system message (with basic markdown parsing)
    function addSystemMessage(text) {
        let formattedText = escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
            
        const msgHtml = `
            <div class="message system-message">
                <div class="avatar"><i class='bx bx-bot'></i></div>
                <div class="content"><p>${formattedText}</p></div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', msgHtml);
        scrollToBottom();
    }

    // Helper to add typing indicator
    function addTypingIndicator() {
        const id = 'typing-' + Date.now();
        const msgHtml = `
            <div class="message system-message" id="${id}">
                <div class="avatar"><i class='bx bx-bot'></i></div>
                <div class="content">
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', msgHtml);
        scrollToBottom();
        return id;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});

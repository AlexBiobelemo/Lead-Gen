document.addEventListener('DOMContentLoaded', function () {
    const chatWindow = document.getElementById('chat-window');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const generateEmailBtn = document.getElementById('generateEmailBtn');
    const sendBtn = document.querySelector('#chat-form button[type="submit"]');

    // Set initial state
    if (chatWindow) {
        const welcomeMessage = `
            <div class="message bot-message">
                Hello {{ current_user.username }}! What can I do for you today?
            </div>
        `;
        chatWindow.innerHTML = welcomeMessage;
    }

    if (chatForm) {
        chatForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const message = chatInput.value.trim();
            if (!message) return;

            // Add user message to chat
            addMessage(message, 'user');
            chatInput.value = '';
            showThinking(true);

            try {
                const response = await fetch(chatForm.action, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                addMessage(data.response, 'bot');
            } catch (error) {
                addMessage('Sorry, something went wrong.', 'bot');
                console.error('Chat Error:', error);
            } finally {
                showThinking(false);
            }
        });
    }

    if (generateEmailBtn) {
        generateEmailBtn.addEventListener('click', async function () {
            const button = this;
            toggleButtonSpinner(button, true, 'Generating...');

            try {
                const response = await fetch(button.dataset.url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                if (data.email_body) {
                    addMessage(data.email_body, 'bot');
                } else {
                    addMessage(data.error || 'Failed to generate email.', 'bot');
                }
            } catch (error) {
                addMessage('Sorry, something went wrong while generating the email.', 'bot');
                console.error('Email Generation Error:', error);
            } finally {
                toggleButtonSpinner(button, false);
            }
        });
    }

    function addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);
        
        // Use a safer method to set content
        const contentParagraph = document.createElement('p');
        contentParagraph.textContent = content;
        messageDiv.appendChild(contentParagraph);

        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function showThinking(isLoading) {
        const thinkingDiv = document.getElementById('thinking');
        if (isLoading) {
            if (!thinkingDiv) {
                const thinkingElement = document.createElement('div');
                thinkingElement.id = 'thinking';
                thinkingElement.classList.add('message', 'bot-message');
                thinkingElement.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Thinking...';
                chatWindow.appendChild(thinkingElement);
                chatWindow.scrollTop = chatWindow.scrollHeight;
            }
        } else {
            if (thinkingDiv) {
                thinkingDiv.remove();
            }
        }
    }

    function toggleButtonSpinner(button, isLoading, loadingText = 'Loading...') {
        if (isLoading) {
            button.setAttribute('disabled', 'true');
            button.dataset.originalText = button.innerHTML;
            button.innerHTML = `
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                ${loadingText}
            `;
        } else {
            button.removeAttribute('disabled');
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
            }
        }
    }
});
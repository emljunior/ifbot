class Chatbot {
    constructor() {
        this.chatbox = document.getElementById('chatbox');
        this.toggleButton = document.getElementById('toggleChatbot');
        this.resetButton = document.getElementById('resetChat');
        this.messagesDiv = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.uploadButton = document.getElementById('uploadButton');
        this.sendEmailButton = document.getElementById('sendEmailButton');
        this.uploadForm = document.getElementById('uploadForm');
        this.userId = Date.now().toString(); 

        this.toggleButton.addEventListener('click', () => this.toggleChatbot());
        this.resetButton.addEventListener('click', () => this.resetChat());
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.uploadButton.addEventListener('click', () => this.uploadFile());
        this.sendEmailButton.addEventListener('click', () => this.sendEmail());
        document.addEventListener('DOMContentLoaded', () => {
            this.showWelcomeMessage();
            this.loadInitialOptions();
        });
    }
    
    sendMessage(message = null) {
        const userInput = message || this.userInput.value;
        this.addMessage(userInput, 'user');
        this.userInput.value = '';
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: userInput, user_id: this.userId })
        })
        .then(response => response.json())
        .then(data => {
            if (typeof data === 'string') {
                this.addMessage(data, 'bot');
            } else if (data && data.response) {
                this.addMessage(data.response, 'bot', true);
                if (data.show_upload_buttons !== undefined) {
                    this.showUploadButtons(data.show_upload_buttons);
                }
            } else {
                console.error('Formato de resposta desconhecido:', data);
            }
        })
        .catch(error => {
            console.error('Erro ao enviar mensagem:', error);
        });
    }
    
    showWelcomeMessage() {
        this.addMessage('Bem-vindo! Como posso ajudar você?', 'bot');
    }

    loadInitialOptions() {
        fetch('/initial-options')
            .then(response => response.json())
            .then(data => {
                this.addMessage('Escolha a opção que aproxima da sua necessidade:', 'bot');                
                this.addOptions(data.options);
            });
    }

    uploadFile() {
        const formData = new FormData();
        formData.append('file', document.querySelector('input[type="file"]').files[0]);
        formData.append('user_id', this.userId);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            this.addMessage(data.status, 'bot');
        });
    }

    sendEmail() {
        fetch('/send-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: this.userId })
        })
        .then(response => response.json())
        .then(data => {
            this.addMessage(data.status, 'bot');
            this.showUploadButtons(data.show_upload_buttons);
            if (data.show_initial_options) {
                this.loadInitialOptions();
            }
        });
    }
// addmessage para suportar innerHTML
    addMessage(text, sender, useInnerHTML = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        if (useInnerHTML) {
            messageDiv.innerHTML = text; // Renderiza tags HTML
        } else {
            messageDiv.textContent = text; // Renderiza texto puro
        }

        this.messagesDiv.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addOptions(options) {
        const optionsDiv = document.createElement('div');
        optionsDiv.classList.add('options');
        options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option.text;
            button.addEventListener('click', () => this.selectOption(option.id));
            optionsDiv.appendChild(button);
        });
        this.messagesDiv.appendChild(optionsDiv);
        this.scrollToBottom();
    }

    selectOption(optionId) {
        fetch('/select-option', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ option_id: optionId, user_id: this.userId })
        })
        .then(response => response.json())
        .then(data => {
            this.addMessage(data.response, 'bot');
            this.showUploadButtons(data.show_upload_buttons);
        });
    }

    toggleChatbot() {
        if (this.chatbox.style.display === 'none' || this.chatbox.style.display === '') {
            this.chatbox.style.display = 'flex';
        } else {
            this.chatbox.style.display = 'none';
        }
    }

    resetChat() {
        this.messagesDiv.innerHTML = '';
        this.showWelcomeMessage();
        this.loadInitialOptions();
    }

    showUploadButtons(show) {
        this.uploadForm.style.display = show ? 'block' : 'none';
        this.sendEmailButton.style.display = show ? 'block' : 'none';
    }

    scrollToBottom() {
        this.messagesDiv.scrollTop = this.messagesDiv.scrollHeight;
    }
}

new Chatbot();

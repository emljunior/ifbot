async function sendMessage() {
    const userInput = document.getElementById('user-input').value;
    const chatBox = document.getElementById('chat-box');
    
    if (!userInput) return;

    chatBox.innerHTML += `<div><strong>Você:</strong> ${userInput}</div>`;

    const response = await fetch('http://127.0.0.1:5000/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userInput })
    });

    const data = await response.json();
    chatBox.innerHTML += `<div><strong>Bot:</strong> ${data.response}</div>`;

    document.getElementById('user-input').value = '';
    chatBox.scrollTop = chatBox.scrollHeight;
}

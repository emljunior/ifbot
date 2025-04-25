from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

with open('responses.json') as f:
    responses = json.load(f)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    response = get_response(user_message)
    return jsonify({'response': response})

def get_response(message):
    for item in responses['responses']:
        if message.lower() in item['question'].lower():
            return item['answer']
    return "Desculpe, não entendi sua pergunta."

if __name__ == '__main__':
    app.run(debug=True)
